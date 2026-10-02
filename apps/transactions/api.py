from rest_framework import mixins
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.categories.api import OwnedViewSet
from .models import PaymentMethod, Transaction
from .queries import history
from .serializers import TransactionSerializer, VersionSerializer
from .services import soft_delete


class HistoryPagination(PageNumberPagination):
    page_size = 20


class TransactionViewSet(mixins.DestroyModelMixin, OwnedViewSet):
    serializer_class = TransactionSerializer
    pagination_class = HistoryPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if self.action == "list":
            return history(self.request)
        return Transaction.objects.filter(user=self.request.user, deleted_at__isnull=True).select_related("category", "subcategory")

    def perform_destroy(self, instance):
        version = VersionSerializer(data=self.request.data)
        version.is_valid(raise_exception=True)
        soft_delete(instance, version.validated_data["expected_version"])


class PaymentMethodsView(APIView):
    def get(self, request):
        return Response([{"value": value, "label": label} for value, label in PaymentMethod.choices])
