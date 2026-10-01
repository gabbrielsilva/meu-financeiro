from django.urls import include, path
from rest_framework.routers import SimpleRouter
from apps.accounts import web as accounts
from apps.categories import web as categories
from apps.transactions import web as transactions
from apps.categories.api import CategoryViewSet, SubcategoryViewSet
from apps.transactions.api import PaymentMethodsView, TransactionViewSet
from apps.reports.views import dashboard, DashboardView

router = SimpleRouter(trailing_slash=False)
router.register("categories", CategoryViewSet, basename="category")
router.register("subcategories", SubcategoryViewSet, basename="subcategory")
router.register("transactions", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/payment-methods", PaymentMethodsView.as_view()),
    path("api/v1/dashboard", DashboardView.as_view(), name="dashboard-api"),
    path("api/v1/", include(router.urls)),
    path("", dashboard, name="home"),
    path("configuracoes/", accounts.settings_page, name="settings"),
    path("cadastro/", accounts.register_page, name="register"),
    path("entrar/", accounts.login_page, name="login"),
    path("sair/", accounts.logout_page, name="logout"),
    path("categorias/", categories.category_list, name="categories"),
    path("categorias/nova/", categories.category_edit, name="category-create"),
    path("categorias/<int:pk>/editar/", categories.category_edit, name="category-edit"),
    path("subcategorias/", categories.subcategory_list, name="subcategories"),
    path("subcategorias/nova/", categories.subcategory_edit, name="subcategory-create"),
    path("subcategorias/<int:pk>/editar/", categories.subcategory_edit, name="subcategory-edit"),
    path("movimentacoes/", transactions.transaction_list, name="transactions"),
    path("movimentacoes/nova/", transactions.transaction_edit, name="transaction-create"),
    path("movimentacoes/<int:pk>/editar/", transactions.transaction_edit, name="transaction-edit"),
    path("movimentacoes/<int:pk>/excluir/", transactions.transaction_delete, name="transaction-delete"),
]
