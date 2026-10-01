from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

User = get_user_model()
PASSWORD = "Somente-Teste!47-Maracuja"
BASE = "/api/v1/auth/"


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AuthTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)

    def csrf(self, client=None):
        client = client or self.client
        response = client.get(BASE + "csrf")
        self.assertEqual(response.status_code, 200)
        client.credentials(HTTP_X_CSRFTOKEN=response.data["csrfToken"])

    def create_user(self, email="pessoa@example.com"):
        return User.objects.create_user(email=email, password=PASSWORD)

    def sign_in(self, client=None, email="pessoa@example.com"):
        client = client or self.client
        self.csrf(client)
        return client.post(BASE + "login", {"email": email, "password": PASSWORD}, format="json")

    def test_registration_hashes_password_and_does_not_start_session(self):
        self.csrf()
        response = self.client.post(BASE + "register", {
            "email": " Pessoa@Example.COM ", "password": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get()
        self.assertEqual(user.email, "pessoa@example.com")
        self.assertTrue(user.password.startswith("argon2$"))
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotIn("password", response.data)
        self.assertFalse(user.is_staff)
        self.assertEqual(self.client.get(BASE + "me").status_code, 403)

    def test_registration_rejects_weak_password_invalid_email_and_extra_fields(self):
        self.csrf()
        for payload in [
            {"email": "pessoa@example.com", "password": "123"},
            {"email": "invalid", "password": PASSWORD},
            {"email": "pessoa@example.com", "password": PASSWORD, "is_staff": True},
            {"email": "pessoa@example.com", "password": PASSWORD, "user_id": 99},
        ]:
            with self.subTest(payload=payload.keys()):
                self.assertEqual(self.client.post(BASE + "register", payload, format="json").status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_duplicate_email_is_case_insensitive_in_api_and_database(self):
        self.create_user()
        self.csrf()
        response = self.client.post(BASE + "register", {
            "email": "PESSOA@example.com", "password": PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="PESSOA@EXAMPLE.COM", password="!")])

    def test_login_me_logout_and_session_invalidation(self):
        user = self.create_user()
        self.assertEqual(self.sign_in(email="PESSOA@EXAMPLE.COM").status_code, 200)
        session_cookie = self.client.cookies["sessionid"].value
        self.assertTrue(self.client.cookies["sessionid"]["httponly"])
        self.assertEqual(self.client.cookies["sessionid"]["samesite"], "Lax")
        response = self.client.get(BASE + "me")
        self.assertEqual(response.data["id"], user.pk)
        self.assertIn("no-store", response["Cache-Control"])
        self.csrf()  # Login rotates the CSRF secret.
        self.assertEqual(self.client.post(BASE + "logout").status_code, 204)
        self.assertEqual(self.client.get(BASE + "me").status_code, 403)
        stale_client = APIClient()
        stale_client.cookies["sessionid"] = session_cookie
        self.assertEqual(stale_client.get(BASE + "me").status_code, 403)

    def test_private_routes_require_authentication(self):
        self.csrf()
        self.assertEqual(self.client.get(BASE + "me").status_code, 403)
        self.assertEqual(self.client.post(BASE + "logout").status_code, 403)

    def test_csrf_required_for_anonymous_registration_and_login(self):
        for endpoint in ("register", "login"):
            with self.subTest(endpoint=endpoint):
                response = self.client.post(BASE + endpoint, {
                    "email": "pessoa@example.com", "password": PASSWORD,
                }, format="json")
                self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.exists())

    def test_logout_requires_csrf_and_get_cannot_logout(self):
        self.create_user()
        self.sign_in()
        self.client.credentials()
        self.assertEqual(self.client.post(BASE + "logout").status_code, 403)
        self.assertEqual(self.client.get(BASE + "logout").status_code, 405)
        self.assertEqual(self.client.get(BASE + "me").status_code, 200)

    def test_untrusted_origin_rejected(self):
        self.csrf()
        response = self.client.post(BASE + "register", {
            "email": "pessoa@example.com", "password": PASSWORD,
        }, format="json", HTTP_ORIGIN="https://untrusted.example")
        self.assertEqual(response.status_code, 403)

    def test_invalid_password_and_inactive_user_cannot_login(self):
        user = self.create_user()
        self.csrf()
        response = self.client.post(BASE + "login", {
            "email": user.email, "password": "Senha-Incorreta!42",
        }, format="json")
        self.assertEqual(response.status_code, 400)
        user.is_active = False
        user.save()
        self.assertEqual(self.sign_in().status_code, 400)
        self.assertEqual(self.client.get(BASE + "me").status_code, 403)

    def test_sessions_are_isolated_between_users(self):
        first = self.create_user()
        second = self.create_user("segunda@example.com")
        other_client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.sign_in().status_code, 200)
        self.assertEqual(self.sign_in(other_client, second.email).status_code, 200)
        self.assertEqual(self.client.get(BASE + "me", {"user_id": second.pk}).data["id"], first.pk)
        self.assertEqual(other_client.get(BASE + "me").data["id"], second.pk)

    def test_login_rate_limit(self):
        self.csrf()
        for _ in range(5):
            self.assertEqual(self.client.post(BASE + "login", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post(BASE + "login", {}, format="json").status_code, 429)

    def test_user_manager_and_superuser(self):
        with self.assertRaises(ValueError):
            User.objects.create_user("", PASSWORD)
        with self.assertRaises(ValueError):
            User.objects.create_superuser("admin@example.com", PASSWORD, is_staff=False)
        admin = User.objects.create_superuser("ADMIN@example.com", PASSWORD)
        self.assertEqual(admin.email, "admin@example.com")
        self.assertTrue(admin.is_staff and admin.is_superuser)
