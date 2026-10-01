from datetime import timedelta
from decimal import Decimal
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.services import register_user
from apps.categories.models import Category, Subcategory
from .models import Transaction


@override_settings(SECURE_SSL_REDIRECT=False)
class TransactionTests(TestCase):
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
        self.payload = {"type": "DESPESA", "amount": "32.50", "category": self.category.pk, "subcategory": self.sub.pk, "payment_method": "PIX", "transaction_date": timezone.localdate().isoformat(), "description": "Compra de teste"}

    def create(self, **changes):
        return self.client.post("/api/v1/transactions", {**self.payload, **changes}, format="json")

    def test_expense_and_income_are_positive_decimals(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["amount"], "32.50")
        self.assertEqual(Transaction.objects.get(pk=response.data["id"]).user, self.user)
        income = Category.objects.get(user=self.user, name="Trabalho")
        response = self.create(type="RECEITA", category=income.pk, subcategory=income.subcategories.first().pk, amount="600.00")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_zero_negative_precision_and_nonfinite_amount_rejected(self):
        for amount in ("0", "-1", "0.001", "NaN", "Infinity", "1000000000000.00"):
            with self.subTest(amount=amount):
                self.assertEqual(self.create(amount=amount).status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_subcategory_required_and_not_nullable(self):
        payload = self.payload.copy()
        del payload["subcategory"]
        self.assertEqual(self.client.post("/api/v1/transactions", payload, format="json").status_code, 400)
        self.assertEqual(self.create(subcategory=None).status_code, 400)

    def test_mismatched_category_type_and_subcategory_rejected(self):
        sub = Subcategory.objects.filter(user=self.user).exclude(category=self.category).first()
        self.assertEqual(self.create(type="RECEITA").status_code, 400)
        self.assertEqual(self.create(subcategory=sub.pk).status_code, 400)

    def test_other_user_references_and_injected_ownership_rejected(self):
        category = Category.objects.get(user=self.other, name="Alimentação")
        self.assertEqual(self.create(category=category.pk, subcategory=category.subcategories.first().pk).status_code, 400)
        self.assertEqual(self.create(subcategory=category.subcategories.first().pk).status_code, 400)
        self.assertEqual(self.create(user_id=self.other.pk).status_code, 400)
        self.assertEqual(self.create(deleted_at=timezone.now().isoformat()).status_code, 400)

    def test_inactive_classifications_cannot_be_selected(self):
        self.category.is_active = False
        self.category.save()
        self.assertEqual(self.create().status_code, 400)
        self.category.is_active = True
        self.category.save()
        self.sub.is_active = False
        self.sub.save()
        self.assertEqual(self.create().status_code, 400)

    def test_future_date_and_invalid_payment_method_rejected(self):
        self.assertEqual(self.create(transaction_date=(timezone.localdate() + timedelta(days=1)).isoformat()).status_code, 400)
        self.assertEqual(self.create(payment_method="CREDITO").status_code, 400)

    def test_partial_edit_validates_complete_result(self):
        pk = self.create().data["id"]
        endpoint = f"/api/v1/transactions/{pk}"
        self.assertEqual(self.client.patch(endpoint, {"amount": "40.01"}, format="json").status_code, 200)
        self.assertEqual(Transaction.objects.get(pk=pk).amount, Decimal("40.01"))
        for changes in ({"type": "RECEITA"}, {"subcategory": None}, {"category": Category.objects.get(user=self.user, name="Moradia").pk}, {"transaction_date": (timezone.localdate() + timedelta(days=1)).isoformat()}):
            self.assertEqual(self.client.patch(endpoint, changes, format="json").status_code, 400)

    def test_edit_can_keep_old_inactive_classification_but_not_switch_to_it(self):
        pk = self.create().data["id"]
        another = self.category.subcategories.exclude(pk=self.sub.pk).first()
        self.category.is_active = False
        self.category.save()
        self.sub.is_active = False
        self.sub.save()
        endpoint = f"/api/v1/transactions/{pk}"
        self.assertEqual(self.client.patch(endpoint, {"description": "Correção"}, format="json").status_code, 200)
        self.assertEqual(self.client.patch(endpoint, {"subcategory": another.pk}, format="json").status_code, 400)

    def test_soft_delete_hides_record_and_blocks_further_access(self):
        pk = self.create().data["id"]
        endpoint = f"/api/v1/transactions/{pk}"
        self.assertEqual(self.client.delete(endpoint).status_code, 204)
        self.assertIsNotNone(Transaction.objects.get(pk=pk).deleted_at)
        self.assertEqual(self.client.get("/api/v1/transactions").data["count"], 0)
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, {"amount": "50.00"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(endpoint).status_code, 404)

    def test_other_user_cannot_read_edit_delete_or_filter_by_private_records(self):
        pk = self.create().data["id"]
        self.client.force_login(self.other)
        endpoint = f"/api/v1/transactions/{pk}"
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(self.client.patch(endpoint, {"description": "Invasão"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(endpoint).status_code, 404)
        self.assertEqual(self.client.get("/api/v1/transactions").data["count"], 0)
        self.assertEqual(self.client.get("/api/v1/transactions", {"category": self.category.pk}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/transactions", {"subcategory": self.sub.pk}).status_code, 400)

    def test_filters_and_pagination(self):
        self.create()
        old = (timezone.localdate() - timedelta(days=40)).isoformat()
        self.create(transaction_date=old)
        response = self.client.get("/api/v1/transactions", {"date_from": self.payload["transaction_date"], "date_to": self.payload["transaction_date"], "category": self.category.pk, "subcategory": self.sub.pk, "type": "DESPESA"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.client.get("/api/v1/transactions", {"type": "RECEITA"}).data["count"], 0)
        self.assertEqual(self.client.get("/api/v1/transactions", {"date_from": self.payload["transaction_date"], "date_to": old}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/transactions", {"date_from": "bad"}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/transactions", {"page": "bad"}).status_code, 400)
        for _ in range(19):
            self.create()
        response = self.client.get("/api/v1/transactions")
        self.assertEqual(response.data["count"], 21)
        self.assertEqual(len(response.data["results"]), 20)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(len(self.client.get("/api/v1/transactions", {"page": 2}).data["results"]), 1)

    def test_private_api_requires_session_and_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        for path in ("categories", "subcategories", "transactions", "payment-methods"):
            self.assertEqual(client.get("/api/v1/" + path).status_code, 403)
        client.force_login(self.user)
        self.assertEqual(client.post("/api/v1/transactions", self.payload, format="json").status_code, 403)

    def test_database_constraints_reject_invalid_financial_relationships(self):
        good = dict(user=self.user, type="DESPESA", amount="1.00", category=self.category, subcategory=self.sub, payment_method="PIX", transaction_date=timezone.localdate())
        wrong_sub = Subcategory.objects.filter(user=self.user).exclude(category=self.category).first()
        for changes in ({"amount": "0"}, {"subcategory": None}, {"subcategory": wrong_sub}, {"user": self.other}, {"type": "RECEITA"}, {"payment_method": "INVALIDO"}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                Transaction.objects.create(**{**good, **changes})
