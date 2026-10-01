from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import mixins, viewsets
from .models import Category, Subcategory
from .serializers import CategoryFilters, CategorySerializer, SubcategoryFilters, SubcategorySerializer


@method_decorator(never_cache, name="dispatch")
class OwnedViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(OwnedViewSet):
    serializer_class = CategorySerializer

    def get_queryset(self):
        rows = Category.objects.filter(user=self.request.user)
        if self.action == "list":
            filters = CategoryFilters(data=self.request.query_params.dict())
            filters.is_valid(raise_exception=True)
            rows = rows.filter(**filters.validated_data)
        return rows


class SubcategoryViewSet(OwnedViewSet):
    serializer_class = SubcategorySerializer

    def get_queryset(self):
        rows = Subcategory.objects.filter(user=self.request.user).select_related("category")
        if self.action == "list":
            filters = SubcategoryFilters(data=self.request.query_params.dict(), context={"request": self.request})
            filters.is_valid(raise_exception=True)
            data = dict(filters.validated_data)
            if "type" in data:
                rows = rows.filter(category__type=data.pop("type"))
            rows = rows.filter(**data)
        return rows
