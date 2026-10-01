from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.serializers import StrictSerializer
from apps.categories.models import Category, MovementType, Subcategory
from apps.categories.serializers import OwnedSerializer
from .models import PaymentMethod, Transaction


class TransactionSerializer(OwnedSerializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none())
    subcategory = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.none(), required=True, allow_null=False)
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "type", "amount", "category", "category_name", "subcategory", "subcategory_name", "payment_method", "description", "transaction_date", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=user).select_related("category")

    def validate(self, attrs):
        def value(key):
            return attrs[key] if key in attrs else getattr(self.instance, key)

        category, subcategory = value("category"), value("subcategory")
        errors = {}
        if category.type != value("type"):
            errors["category"] = "A categoria deve corresponder ao tipo da movimentação."
        if subcategory.category_id != category.pk:
            errors["subcategory"] = "A subcategoria deve pertencer à categoria selecionada."
        unchanged = self.instance and category.pk == self.instance.category_id and subcategory.pk == self.instance.subcategory_id
        if not unchanged:
            if not category.is_active:
                errors["category"] = "Selecione uma categoria ativa."
            if not subcategory.is_active:
                errors["subcategory"] = "Selecione uma subcategoria ativa."
        if value("transaction_date") > timezone.localdate():
            errors["transaction_date"] = "A data não pode estar no futuro."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class TransactionFilters(StrictSerializer):
    q = serializers.CharField(max_length=200, required=False)
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=1, max_value=9998, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    type = serializers.ChoiceField(choices=MovementType.choices, required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none(), required=False)
    subcategory = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.none(), required=False)
    page = serializers.IntegerField(min_value=1, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=user)

    def validate(self, attrs):
        if ("month" in attrs) != ("year" in attrs):
            raise serializers.ValidationError({"non_field_errors": "Informe mês e ano juntos."})
        if attrs.get("date_from") and attrs.get("date_to") and attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError({"date_to": "A data final deve ser igual ou posterior à inicial."})
        if attrs.get("category") and attrs.get("subcategory") and attrs["subcategory"].category_id != attrs["category"].pk:
            raise serializers.ValidationError({"subcategory": "Subcategoria incompatível com o filtro de categoria."})
        return attrs
