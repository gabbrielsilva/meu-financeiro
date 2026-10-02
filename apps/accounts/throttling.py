"""Atomic authentication limits shared by HTML/API and every application worker."""
from datetime import timedelta
from ipaddress import ip_address
import logging

from django.conf import settings
from django.db import DatabaseError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle, SimpleRateThrottle

from .models import AuthRateBucket


class AuthThrottleUnavailable(APIException):
    status_code = 503
    default_detail = "Não foi possível verificar o acesso. Tente novamente em instantes."


def client_ip(request):
    peer = request.META.get("REMOTE_ADDR", "")
    try:
        peer = str(ip_address(peer))
    except ValueError:
        return "unknown"
    trusted = settings.AUTH_TRUSTED_PROXY_IPS
    if peer not in trusted:
        return peer
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    try:
        chain = [str(ip_address(item.strip())) for item in forwarded.split(",")]
    except ValueError:
        return peer
    for address in reversed(chain):
        if address not in trusted:
            return address
    return chain[0] if chain else peer


class AuthRateThrottle(BaseThrottle):
    def allow_request(self, request, view):
        scope = view.throttle_scope
        limit, seconds = SimpleRateThrottle.parse_rate(self, settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"][scope])
        key = salted_hmac("auth-rate", f"{scope}:{client_ip(request)}", algorithm="sha256").hexdigest()
        try:
            with transaction.atomic():
                bucket, _ = AuthRateBucket.objects.select_for_update().get_or_create(key=key, defaults={"expires_at": timezone.now() + timedelta(seconds=seconds)})
                now = timezone.now()
                if bucket.expires_at <= now:
                    bucket.count = 0
                    bucket.expires_at = now + timedelta(seconds=seconds)
                self.wait_seconds = max(1, (bucket.expires_at - now).total_seconds())
                if bucket.count >= limit:
                    return False
                bucket.count += 1
                bucket.save(update_fields=["count", "expires_at"])
                return True
        except DatabaseError as exc:
            logging.getLogger(__name__).exception("Falha no controle de acesso")
            raise AuthThrottleUnavailable() from exc

    def wait(self):
        return self.wait_seconds
