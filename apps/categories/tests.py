from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.services import register_user
from .defaults import create_defaults
from .models import Category, Subcategory


@override_settings(SECURE_SSL_REDIRECT=False)
class CategoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = register_user("first@example.com", "Somente-Teste!47-Maracuja")
        cls.other = register_user("other@example.com", "Somente-Teste!47-Maracuja")

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.force_login(self.user)
        self.category = Category.objects.get(user=self.user, name="Alimentação")
        self.sub = self.category.subcategories.get(name="Mercado")

    def test_defaults_are_individual_complete_and_idempotent(self):
        self.assertEqual(Category.objects.filter(user=self.user).count(), 6)
        self.assertEqual(Subcategory.objects.filter(user=self.user).count(), 20)
        self.assertEqual(Category.objects.filter(user=self.other).count(), 6)
        self.assertFalse(set(Category.objects.filter(user=self.user).values_list("pk", flat=True)) & set(Category.objects.filter(user=self.other).values_list("pk", flat=True)))
        create_defaults(self.user)
        self.assertEqual(Subcategory.objects.filter(user=self.user).count(), 20)

    def test_api_registration_creates_defaults(self):
        self.client.logout()
        response = self.client.post("/api/v1/auth/register", {"email": "new@example.com", "password": "Somente-Teste!47-Maracuja"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Category.objects.filter(user_id=response.data["id"]).count(), 6)

    def test_failed_defaults_roll_back_user(self):
        with patch("apps.accounts.services.create_defaults", side_effect=RuntimeError("seed failed")):
            with self.assertRaises(RuntimeError):
                register_user("failed@example.com", "Somente-Teste!47-Maracuja")
        self.assertFalse(get_user_model().objects.filter(email="failed@example.com").exists())

    def test_existing_account_seed_migration(self):
        from importlib import import_module
        from django.apps import apps
        user = get_user_model().objects.create_user("old@example.com", "Somente-Teste!47-Maracuja")
        seed = import_module("apps.categories.migrations.0002_owner_integrity_and_defaults").seed_existing_accounts
        seed(apps, SimpleNamespace(connection=SimpleNamespace(alias="default")))
        self.assertEqual(Category.objects.filter(user=user).count(), 6)
        self.assertEqual(Subcategory.objects.filter(user=user).count(), 20)

    def test_category_create_rename_deactivate_reactivate(self):
        response = self.client.post("/api/v1/categories", {"name": "  Saúde  ", "type": "DESPESA"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        category = Category.objects.get(pk=response.data["id"])
        self.assertEqual(category.user, self.user)
        self.assertEqual(category.name, "Saúde")
        endpoint = f"/api/v1/categories/{category.pk}"
        for changes in ({"name": "Bem-estar"}, {"is_active": False}, {"is_active": True}):
            self.assertEqual(self.client.patch(endpoint, changes, format="json").status_code, 200)
        self.assertEqual(self.client.delete(endpoint).status_code, 405)

    def test_category_duplicate_type_change_and_owner_injection_rejected(self):
        for payload in ({"name": "ALIMENTAÇÃO", "type": "DESPESA"}, {"name": "Teste", "type": "DESPESA", "user_id": self.other.pk}, {"name": "  ", "type": "DESPESA"}, {"name": "Teste", "type": "INVALIDO"}):
            self.assertEqual(self.client.post("/api/v1/categories", payload, format="json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/v1/categories/{self.category.pk}", {"type": "RECEITA"}, format="json").status_code, 400)

    def test_category_and_subcategory_owner_isolation(self):
        other_category = Category.objects.filter(user=self.other).first()
        other_sub = Subcategory.objects.filter(user=self.other).first()
        for resource, pk in (("categories", other_category.pk), ("subcategories", other_sub.pk)):
            self.assertEqual(self.client.get(f"/api/v1/{resource}/{pk}").status_code, 404)
            self.assertEqual(self.client.patch(f"/api/v1/{resource}/{pk}", {"name": "Invadido"}, format="json").status_code, 404)
        self.assertEqual(len(self.client.get("/api/v1/categories").data), 6)
        self.assertEqual(len(self.client.get("/api/v1/subcategories").data), 20)
        self.assertEqual(self.client.post("/api/v1/subcategories", {"name": "Invadida", "category": other_category.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/subcategories", {"category": other_category.pk}).status_code, 400)

    def test_subcategory_create_edit_toggle_and_no_move(self):
        response = self.client.post("/api/v1/subcategories", {"name": "Feira", "category": self.category.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        endpoint = f"/api/v1/subcategories/{response.data['id']}"
        for changes in ({"name": "Feira livre"}, {"is_active": False}, {"is_active": True}):
            self.assertEqual(self.client.patch(endpoint, changes, format="json").status_code, 200)
        other = Category.objects.get(user=self.user, name="Moradia")
        self.assertEqual(self.client.patch(endpoint, {"category": other.pk}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(endpoint).status_code, 405)
        self.assertEqual(self.client.post("/api/v1/subcategories", {"name": "MERCADO", "category": self.category.pk}, format="json").status_code, 400)

    def test_inactive_parent_effect_and_reactivation_preserve_child_state(self):
        self.sub.is_active = False
        self.sub.save()
        self.category.is_active = False
        self.category.save()
        self.assertEqual(self.client.post("/api/v1/subcategories", {"name": "Feira", "category": self.category.pk}, format="json").status_code, 400)
        data = self.client.get("/api/v1/subcategories", {"category": self.category.pk}).data
        self.assertTrue(all(not row["effective_active"] for row in data))
        self.category.is_active = True
        self.category.save()
        self.sub.refresh_from_db()
        self.assertFalse(self.sub.is_active)

    def test_classification_filters(self):
        response = self.client.get("/api/v1/categories", {"type": "RECEITA", "is_active": "true"})
        self.assertEqual(len(response.data), 2)
        self.assertEqual(len(self.client.get("/api/v1/subcategories", {"category": self.category.pk}).data), 4)
        self.assertEqual(self.client.get("/api/v1/categories", {"type": "INVALIDO"}).status_code, 400)

    def test_database_rejects_cross_owner_and_duplicate_names(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Subcategory.objects.create(user=self.other, category=self.category, name="Invasão")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(user=self.user, name=" ALIMENTAÇÃO ", type="DESPESA")
