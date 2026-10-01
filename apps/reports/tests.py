from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.services import register_user
from apps.categories.models import Category
from apps.transactions.models import Transaction
from .services import monthly_report


@override_settings(SECURE_SSL_REDIRECT=False)
class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = register_user("dashboard@example.com", "Jardim!82-Ponte-Laranja")
        cls.other = register_user("other@example.com", "Jardim!82-Ponte-Laranja")

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.user)

    def movement(self, kind="DESPESA", amount="10.00", day=date(2024, 2, 15), user=None, description="Teste", category_name=None):
        user = user or self.user
        category = Category.objects.get(user=user, name=category_name or ("Trabalho" if kind == "RECEITA" else "Alimentação"))
        return Transaction.objects.create(user=user, type=kind, amount=Decimal(amount), category=category,
                                          subcategory=category.subcategories.first(), payment_method="PIX",
                                          transaction_date=day, description=description)

    def report(self, **params):
        return self.client.get("/api/v1/dashboard", {"year": 2024, "month": 2, **params})

    def test_exact_monthly_totals_and_result(self):
        self.movement("RECEITA", "1000.10")
        self.movement("RECEITA", "0.20")
        self.movement("DESPESA", "250.15")
        response = self.report()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["income"], "1000.30")
        self.assertEqual(response.data["expenses"], "250.15")
        self.assertEqual(response.data["result"], "750.15")
        self.assertEqual(response.data["count"], 3)

    def test_month_boundaries_and_leap_year(self):
        self.movement(amount="999", day=date(2024, 1, 31))
        self.movement(amount="1", day=date(2024, 2, 1))
        self.movement(amount="2", day=date(2024, 2, 29))
        self.movement(amount="999", day=date(2024, 3, 1))
        data = self.report().data
        self.assertEqual(data["expenses"], "3.00")
        self.assertEqual(len(data["daily"]), 29)
        self.assertEqual(data["daily"][0]["expenses"], "1.00")
        self.assertEqual(data["daily"][-1]["expenses"], "2.00")

    def test_december_to_january_and_selected_year(self):
        self.movement(amount="12", day=date(2023, 12, 31))
        self.movement(amount="1", day=date(2024, 1, 1))
        self.movement(amount="100", day=date(2023, 1, 1))
        self.assertEqual(self.report(year=2023, month=12).data["expenses"], "12.00")
        self.assertEqual(self.report(month=1).data["expenses"], "1.00")

    def test_current_local_month_is_default(self):
        self.movement("RECEITA", "15", date(2024, 2, 1))
        with patch("apps.reports.serializers.timezone.localdate", return_value=date(2024, 2, 1)):
            data = self.client.get("/api/v1/dashboard").data
        self.assertEqual((data["year"], data["month"]), (2024, 2))
        self.assertEqual(data["income"], "15.00")

    def test_other_users_and_soft_deleted_rows_excluded_everywhere(self):
        self.movement("RECEITA", "30")
        self.movement("RECEITA", "9999", user=self.other, description="SEGREDO DE OUTRO USUÁRIO")
        deleted = self.movement("DESPESA", "777", description="REGISTRO EXCLUÍDO")
        deleted.deleted_at = timezone.now()
        deleted.save()
        data = self.report().data
        self.assertEqual(data["income"], "30.00")
        self.assertEqual(data["expenses"], "0.00")
        self.assertEqual(data["expense_categories"], [])
        self.assertEqual(len(data["recent"]), 1)
        response = self.client.get("/", {"year": 2024, "month": 2})
        self.assertNotContains(response, "SEGREDO DE OUTRO USUÁRIO")
        self.assertNotContains(response, "REGISTRO EXCLUÍDO")

    def test_empty_month_returns_zero_and_html_empty_state(self):
        data = self.report().data
        self.assertEqual((data["income"], data["expenses"], data["result"]), ("0.00", "0.00", "0.00"))
        self.assertEqual(data["recent"], [])
        self.assertEqual(data["expense_categories"], [])
        self.assertEqual(data["income_categories"], [])
        self.assertTrue(all(day["income"] == "0.00" and day["expenses"] == "0.00" for day in data["daily"]))
        self.assertContains(self.client.get("/", {"year": 2024, "month": 2}), "Nenhuma movimentação neste mês.")

    def test_negative_result_and_expense_only_chart(self):
        self.movement(amount="22.50")
        self.assertEqual(self.report().data["result"], "-22.50")
        self.assertContains(self.client.get("/", {"year": 2024, "month": 2}), "-22,50")

    def test_category_subcategory_grouping_and_inactive_history(self):
        first = self.movement(amount="30")
        self.movement(amount="20")
        self.movement(amount="50", category_name="Moradia")
        self.movement("RECEITA", "80")
        first.category.is_active = False
        first.category.save()
        first.subcategory.is_active = False
        first.subcategory.save()
        data = self.report().data
        self.assertEqual(data["expenses"], "100.00")
        self.assertEqual(len(data["expense_categories"]), 2)
        self.assertEqual({row["percentage"] for row in data["expense_categories"]}, {"50.00"})
        self.assertEqual(data["income_categories"][0]["amount"], "80.00")
        self.assertEqual(data["expense_categories"][0]["subcategories"][0]["amount"], "50.00")

    def test_recent_rows_are_limited_and_ordered_by_date_then_id(self):
        rows = [self.movement(day=date(2024, 2, 10) + timedelta(days=i), description=f"Registro {i}") for i in range(8)]
        latest = self.movement(day=date(2024, 2, 17), description="Último no mesmo dia")
        self.movement(day=date(2024, 3, 1), description="Fora do mês")
        recent = self.report().data["recent"]
        self.assertEqual(len(recent), 6)
        self.assertEqual([row["id"] for row in recent], [latest.pk, *[row.pk for row in reversed(rows[-5:])]])

    def test_edit_and_soft_delete_are_reflected_without_cached_summary(self):
        row = self.movement(amount="10")
        self.assertEqual(self.report().data["expenses"], "10.00")
        row.amount = Decimal("20.25")
        row.save()
        self.assertEqual(self.report().data["expenses"], "20.25")
        row.transaction_date = date(2024, 3, 1)
        row.save()
        self.assertEqual(self.report().data["expenses"], "0.00")

    def test_report_reads_a_single_snapshot(self):
        self.movement()
        with self.assertNumQueries(1):
            report = monthly_report(self.user, 2024, 2)
        self.assertEqual(report["expenses"], Decimal("10.00"))

    def test_invalid_period_and_owner_injection_rejected(self):
        for params in ({"month": 0}, {"month": 13}, {"month": "abc"}, {"year": 0}, {"year": 9999}, {"user_id": self.other.pk}):
            with self.subTest(params=params):
                self.assertEqual(self.report(**params).status_code, 400)
                self.assertEqual(self.client.get("/", {"year": 2024, "month": 2, **params}).status_code, 400)

    def test_dashboard_and_settings_require_authentication(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/dashboard").status_code, 403)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/configuracoes/").status_code, 302)

    def test_settings_and_integrated_categories_preserve_navigation(self):
        response = self.client.get("/configuracoes/")
        self.assertContains(response, self.user.email)
        self.assertNotContains(response, self.other.email)
        response = self.client.get("/categorias/")
        self.assertContains(response, "Adicionar subcategoria")
        self.assertContains(response, "Mercado")
        self.assertNotContains(response, '>Subcategorias</span>')

    def test_month_links_preserve_period_in_full_history(self):
        self.movement()
        response = self.client.get("/", {"year": 2024, "month": 2})
        self.assertContains(response, '/movimentacoes/?month=2&year=2024')
        self.assertContains(response, '?month=1&year=2024')
        self.assertContains(response, '?month=3&year=2024')

    def test_search_and_month_filters_preserve_old_date_filters_and_isolation(self):
        self.movement(description="Compra especial", day=date(2024, 2, 15))
        self.movement(description="Compra especial", day=date(2024, 3, 15))
        self.movement(description="Compra especial", day=date(2024, 2, 15), user=self.other)
        filters = {"q": "especial", "month": 2, "year": 2024, "date_from": "2024-02-15", "date_to": "2024-02-15", "type": "DESPESA"}
        data = self.client.get("/api/v1/transactions", filters).data
        self.assertEqual(data["count"], 1)
        response = self.client.get("/movimentacoes/", filters)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Compra especial")
        self.assertEqual(self.client.get("/api/v1/transactions", {"q": "Moradia"}).data["count"], 0)
        self.assertEqual(self.client.get("/api/v1/transactions", {"month": 2}).status_code, 400)
        self.assertEqual(self.client.get("/api/v1/transactions", {"year": 2024}).status_code, 400)

    def test_subcategory_prefill_is_scoped_to_authenticated_user(self):
        category = Category.objects.get(user=self.user, name="Alimentação")
        response = self.client.get("/subcategorias/nova/", {"category": category.pk})
        self.assertEqual(response.context["form"].initial["category"], category)
        other = Category.objects.filter(user=self.other).first()
        self.assertEqual(self.client.get("/subcategorias/nova/", {"category": other.pk}).status_code, 404)
