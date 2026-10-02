from datetime import timedelta
from uuid import uuid4
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from apps.accounts.services import register_user
from apps.categories.models import Category, Subcategory
from apps.transactions.models import Transaction


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class WebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = "Somente-Teste!47-Maracuja"
        cls.user = register_user("web@example.com", cls.password)
        cls.other = register_user("other@example.com", cls.password)

    def setUp(self):
        cache.clear()
        self.category = Category.objects.get(user=self.user, name="Alimentação")
        self.sub = self.category.subcategories.get(name="Mercado")
        self.payload = {"request_id": str(uuid4()), "type": "DESPESA", "amount": "32,50", "category": self.category.pk, "subcategory": self.sub.pk, "payment_method": "PIX", "description": "Registro visual", "transaction_date": timezone.localdate().isoformat()}

    def test_private_pages_redirect_to_login(self):
        for path in ("/", "/categorias/", "/categorias/nova/", "/subcategorias/", "/subcategorias/nova/", "/movimentacoes/", "/movimentacoes/nova/", "/movimentacoes/1/editar/", "/movimentacoes/1/excluir/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith("/entrar/"))

    def test_registration_login_logout_via_html_with_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/cadastro/")
        data = {"email": "newweb@example.com", "password": self.password, "password_confirm": self.password}
        self.assertEqual(client.post("/cadastro/", data).status_code, 403)
        data["csrfmiddlewaretoken"] = client.cookies["csrftoken"].value
        self.assertRedirects(client.post("/cadastro/", data), "/entrar/")
        self.assertEqual(Category.objects.filter(user__email="newweb@example.com").count(), 6)
        login = {"email": "newweb@example.com", "password": self.password, "csrfmiddlewaretoken": client.cookies["csrftoken"].value}
        self.assertRedirects(client.post("/entrar/", login), "/")
        self.assertEqual(client.get("/sair/").status_code, 405)
        self.assertEqual(client.post("/sair/").status_code, 403)
        self.assertRedirects(client.post("/sair/", {"csrfmiddlewaretoken": client.cookies["csrftoken"].value}), "/entrar/")
        self.assertEqual(client.get("/").status_code, 302)

    def test_auth_form_errors_and_throttle(self):
        response = self.client.post("/cadastro/", {"email": "invalid", "password": "short", "password_confirm": "different"})
        self.assertContains(response, "As senhas não conferem")
        for _ in range(5):
            self.assertEqual(self.client.post("/entrar/", {"email": self.user.email, "password": "errada"}).status_code, 200)
        self.assertEqual(self.client.post("/entrar/", {}).status_code, 429)

    def test_main_pages_render_and_escape_user_input(self):
        self.client.force_login(self.user)
        for path in ("/", "/categorias/", "/categorias/nova/", "/subcategorias/", "/subcategorias/nova/", "/movimentacoes/", "/movimentacoes/nova/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
        self.client.post("/movimentacoes/nova/", {**self.payload, "description": "<script>alert(1)</script>"})
        response = self.client.get("/movimentacoes/")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_category_and_subcategory_html_crud(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/categorias/nova/", {"name": "Saúde", "type": "DESPESA", "is_active": "on"}), "/categorias/")
        category = Category.objects.get(user=self.user, name="Saúde")
        self.assertRedirects(self.client.post("/subcategorias/nova/", {"name": "Consulta", "category": category.pk, "is_active": "on"}), "/subcategorias/")
        sub = Subcategory.objects.get(category=category)
        self.assertRedirects(self.client.post(f"/subcategorias/{sub.pk}/editar/", {"name": "Consultas"}), "/subcategorias/")
        sub.refresh_from_db()
        self.assertFalse(sub.is_active)
        self.assertRedirects(self.client.post(f"/categorias/{category.pk}/editar/", {"name": "Saúde e cuidados"}), "/categorias/")
        category.refresh_from_db()
        self.assertFalse(category.is_active)
        self.assertEqual(category.type, "DESPESA")

    def test_html_create_edit_delete_and_persistence(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.post("/movimentacoes/nova/", self.payload), "/movimentacoes/")
        movement = Transaction.objects.get(user=self.user)
        self.assertEqual(str(movement.amount), "32.50")
        self.assertEqual(self.client.get(f"/movimentacoes/{movement.pk}/editar/").status_code, 200)
        self.assertRedirects(self.client.post(f"/movimentacoes/{movement.pk}/editar/", {**self.payload, "expected_version": movement.updated_at.isoformat(), "amount": "45,00"}), "/movimentacoes/")
        self.client.logout()
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/movimentacoes/"), "45,00")
        self.assertEqual(self.client.get(f"/movimentacoes/{movement.pk}/excluir/").status_code, 200)
        movement.refresh_from_db()
        self.assertIsNone(movement.deleted_at)
        self.assertRedirects(self.client.post(f"/movimentacoes/{movement.pk}/excluir/", {"expected_version": movement.updated_at.isoformat()}), "/movimentacoes/")
        movement.refresh_from_db()
        self.assertIsNotNone(movement.deleted_at)
        self.assertNotContains(self.client.get("/movimentacoes/"), "Registro visual")

    def test_html_cannot_use_or_access_other_users_data(self):
        self.client.force_login(self.user)
        self.client.post("/movimentacoes/nova/", self.payload)
        movement = Transaction.objects.get(user=self.user)
        self.client.force_login(self.other)
        for path in (f"/categorias/{self.category.pk}/editar/", f"/subcategorias/{self.sub.pk}/editar/", f"/movimentacoes/{movement.pk}/editar/", f"/movimentacoes/{movement.pk}/excluir/"):
            self.assertEqual(self.client.get(path).status_code, 404)
            self.assertEqual(self.client.post(path, {}).status_code, 404)
        self.assertNotContains(self.client.get("/movimentacoes/"), "Registro visual")
        self.client.post("/movimentacoes/nova/", self.payload)
        self.assertFalse(Transaction.objects.filter(user=self.other).exists())

    def test_html_validation_filters_and_inactive_history_edit(self):
        self.client.force_login(self.user)
        for changes in ({"amount": "0"}, {"subcategory": ""}, {"transaction_date": (timezone.localdate() + timedelta(days=1)).isoformat()}):
            self.assertEqual(self.client.post("/movimentacoes/nova/", {**self.payload, **changes}).status_code, 200)
            self.assertFalse(Transaction.objects.exists())
        self.client.post("/movimentacoes/nova/", self.payload)
        movement = Transaction.objects.get()
        self.assertNotContains(self.client.get("/movimentacoes/", {"type": "RECEITA"}), "Registro visual")
        self.assertContains(self.client.get("/movimentacoes/", {"type": "DESPESA", "date_from": "", "date_to": "", "category": "", "subcategory": ""}), "Registro visual")
        self.assertEqual(self.client.get("/movimentacoes/", {"page": "bad"}).status_code, 200)
        self.category.is_active = False
        self.category.save()
        self.assertRedirects(self.client.post(f"/movimentacoes/{movement.pk}/editar/", {**self.payload, "expected_version": movement.updated_at.isoformat(), "description": "Correção histórica"}), "/movimentacoes/")
