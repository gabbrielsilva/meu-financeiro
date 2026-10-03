"""Configuration regression checks; production probes never connect to a database."""
import io
import json
import logging
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from config.logging import SafeProductionFormatter

ROOT = Path(__file__).resolve().parent.parent


class ProductionConfigurationTests(SimpleTestCase):
    def environment(self, **changes):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("DJANGO_", "POSTGRES_"))}
        env.update({
            "DJANGO_ENV": "production", "DJANGO_SETTINGS_MODULE": "config.settings",
            "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
            "DJANGO_ALLOWED_HOSTS": "testserver",
            "POSTGRES_DB": "unused", "POSTGRES_USER": "unused",
            "POSTGRES_PASSWORD": secrets.token_urlsafe(24),
            "POSTGRES_HOST": "127.0.0.1", "POSTGRES_PORT": "1",
            "POSTGRES_SSLMODE": "verify-full",
        })
        env.update(changes)
        return env

    def probe(self, env, code="import config.settings"):
        return subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                              capture_output=True, text=True, timeout=90)

    def test_production_rejects_insecure_or_missing_configuration(self):
        invalid = [
            {"DJANGO_DEBUG": "true"}, {"DJANGO_SECRET_KEY": ""},
            {"DJANGO_SECRET_KEY": "short"}, {"DJANGO_ALLOWED_HOSTS": ""},
            {"DJANGO_ALLOWED_HOSTS": "*"}, {"DJANGO_ALLOWED_HOSTS": ".example.com"},
            {"DJANGO_CSRF_TRUSTED_ORIGINS": "http://example.com"},
            {"POSTGRES_PASSWORD": ""}, {"POSTGRES_SSLMODE": ""},
            {"DJANGO_ENV": "prodution"}, {"DJANGO_HSTS_SECONDS": "-1"},
            {"DJANGO_TRUST_PROXY_HEADERS": "yes"},
            {"DJANGO_CLIENT_IP_HEADER": "HTTP_USER_SUPPLIED_IP"},
        ]
        for changes in invalid:
            with self.subTest(changes=changes):
                result = self.probe(self.environment(**changes))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("ImproperlyConfigured", result.stderr)

    def test_production_does_not_load_local_dotenv(self):
        env = self.environment()
        del env["DJANGO_SECRET_KEY"]
        result = self.probe(env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_production_security_and_proxy_opt_in(self):
        code = '''
import config.settings as s
assert s.DEBUG is False
assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE
assert s.SESSION_COOKIE_HTTPONLY and s.SECURE_SSL_REDIRECT
assert s.SECURE_PROXY_SSL_HEADER is None
assert s.SECURE_HSTS_SECONDS == 0
'''
        result = self.probe(self.environment(), code)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.probe(self.environment(DJANGO_TRUST_PROXY_HEADERS="true"),
                            "import config.settings as s; assert s.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_hsts_short_window_without_subdomain_or_preload(self):
        result = self.probe(self.environment(DJANGO_HSTS_SECONDS="3600"), '''
import django
django.setup()
from django.test import Client
r = Client().get('/hsts-test-missing/', secure=True)
assert r['Strict-Transport-Security'] == 'max-age=3600'
''')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_static_assets_errors_and_https_without_database(self):
        # The database points to port 1. Any accidental DB use would fail.
        code = '''
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import Client, override_settings
from django.urls import path
from django.core.exceptions import PermissionDenied
import io
def crash(request):
    raise RuntimeError("sensitive-example-must-not-appear")
def forbidden(request):
    raise PermissionDenied("sensitive-example-must-not-appear")
urlpatterns = [path("crash/", crash), path("forbidden/", forbidden)]
with override_settings(STATIC_ROOT=__import__('os').environ['PROBE_STATIC_ROOT']):
    call_command('collectstatic', interactive=False, verbosity=0)
    client = Client(raise_request_exception=False, enforce_csrf_checks=True)
    assert client.get('/entrar/').status_code == 301
    login = client.get('/entrar/', secure=True)
    assert login.status_code == 200
    assert login.cookies['csrftoken']['secure']
    assert client.post('/api/v1/auth/login', {}, secure=True).status_code == 403
    assert client.get('/entrar/', secure=True, HTTP_HOST='untrusted.invalid').status_code == 400
    for asset in ['app.css', 'navigation.js', 'transactions.js', 'icons.svg', 'vendor/bootstrap.min.css']:
        url = staticfiles_storage.url(asset)
        response = client.get(url, secure=True)
        assert response.status_code == 200, (asset, response.status_code)
        assert 'immutable' in response['Cache-Control']
        response.close()
    with override_settings(ROOT_URLCONF=__name__):
        for url, status in [('/missing/',404),('/crash/',500),('/forbidden/',403)]:
            response = client.get(url, secure=True)
            assert response.status_code == status
            assert b'Traceback' not in response.content
            assert b'sensitive-example-must-not-appear' not in response.content
            assert settings.SECRET_KEY.encode() not in response.content
print('Production smoke: HTTPS, CSRF, collected assets and 400/403/404/500 OK')
'''
        with TemporaryDirectory() as directory:
            result = self.probe(self.environment(PROBE_STATIC_ROOT=directory), code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Production smoke:", result.stdout)

    def test_logging_keeps_error_location_but_excludes_sensitive_payloads(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(SafeProductionFormatter())
        logger = logging.Logger("production-test")
        logger.addHandler(handler)
        secret = "sensitive-example-must-not-appear"
        try:
            raise ValueError(secret)
        except ValueError:
            logger.exception("password=%s", secret, extra={"status_code": 500, "request": secret})
        rendered = stream.getvalue()
        self.assertNotIn(secret, rendered)
        event = json.loads(rendered)
        self.assertEqual(event["exception"], "ValueError")
        self.assertEqual(event["status"], 500)
        self.assertTrue(event["stack"])
