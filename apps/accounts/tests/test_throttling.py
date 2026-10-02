from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db import OperationalError, close_old_connections
from django.core.management import call_command
import io
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuthRateBucket
from apps.accounts.throttling import AuthRateThrottle, AuthThrottleUnavailable, client_ip


def attempt(forwarded="198.51.100.1"):
    request = RequestFactory().post('/entrar/', REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR=forwarded)
    return AuthRateThrottle().allow_request(request, SimpleNamespace(throttle_scope='login'))


class AuthThrottleTests(TestCase):
    def test_spoofed_forwarded_addresses_cannot_reset_limit(self):
        self.assertEqual([attempt(f'198.51.100.{i}') for i in range(6)], [True]*5 + [False])
        bucket = AuthRateBucket.objects.get()
        self.assertEqual(len(bucket.key), 64)
        self.assertNotIn('192.0.2', bucket.key)

    @override_settings(AUTH_TRUSTED_PROXY_IPS={'192.0.2.1'})
    def test_only_explicit_proxy_can_supply_client_address(self):
        factory = RequestFactory()
        request = factory.get('/', REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR='203.0.113.8, 198.51.100.5')
        self.assertEqual(client_ip(request), '198.51.100.5')
        request.META['REMOTE_ADDR'] = '192.0.2.2'
        self.assertEqual(client_ip(request), '192.0.2.2')
        request.META.update(REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR='invalid')
        self.assertEqual(client_ip(request), '192.0.2.1')

    def test_expired_window_resets(self):
        for _ in range(5):
            self.assertTrue(attempt())
        self.assertFalse(attempt())
        AuthRateBucket.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertTrue(attempt())

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_html_and_api_share_limit(self):
        client = APIClient()
        for _ in range(5):
            self.assertEqual(client.post('/entrar/', {}).status_code, 200)
        self.assertEqual(client.post('/api/v1/auth/login', {}, format='json').status_code, 429)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_database_failure_blocks_login_with_503(self):
        with patch('apps.accounts.throttling.AuthRateBucket.objects.select_for_update', side_effect=OperationalError('test failure')), self.assertLogs('apps.accounts.throttling', level='ERROR'):
            with self.assertRaises(AuthThrottleUnavailable):
                attempt()
            self.assertEqual(self.client.post('/entrar/', {}).status_code, 503)
            self.assertEqual(APIClient().post('/api/v1/auth/login', {}, format='json').status_code, 503)

    def test_cleanup_preserves_active_limits(self):
        attempt()
        AuthRateBucket.objects.create(key='expired', expires_at=timezone.now()-timedelta(seconds=1))
        call_command('clear_auth_limits', stdout=io.StringIO())
        self.assertEqual(AuthRateBucket.objects.count(), 1)
        self.assertEqual(AuthRateBucket.objects.get().count, 1)


class ConcurrentAuthThrottleTests(TransactionTestCase):
    def test_workers_share_atomic_limit(self):
        def worker(_):
            close_old_connections()
            try:
                return attempt()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(worker, range(6)))
        self.assertEqual(sum(results), 5)
        self.assertEqual(AuthRateBucket.objects.get().count, 5)
