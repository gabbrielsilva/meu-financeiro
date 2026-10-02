from decimal import Decimal
import hashlib
import json
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from apps.accounts.serializers import StrictSerializer
from apps.categories.models import Category, MovementType, Subcategory
from apps.categories.serializers import OwnedSerializer
from .models import PaymentMethod, Transaction


class TransactionSerializer(OwnedSerializer):
    request_id = serializers.UUIDField(write_only=True, required=False)
    expected_version = serializers.DateTimeField(write_only=True, required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none())
    subcategory = serializers.PrimaryKeyRelatedField(queryset=Subcategory.objects.none(), required=True, allow_null=False)
    category_name = serializers.CharField(source="category.name", read_only=True)
    subcategory_name = serializers.CharField(source="subcategory.name", read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "type", "amount", "category", "category_name", "subcategory", "subcategory_name", "payment_method", "description", "transaction_date", "created_at", "updated_at", "request_id", "expected_version"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.context["request"].user
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=user).select_related("category")

    def validate(self, attrs):
        if self.instance:
            if "request_id" in attrs:
                raise serializers.ValidationError({"request_id": "Não pode ser alterado na edição."})
            if "expected_version" not in attrs:
                raise serializers.ValidationError({"expected_version": "Recarregue o registro antes de editar."})
            if attrs["expected_version"] != self.instance.updated_at:
                raise serializers.ValidationError({"non_field_errors": ["Este registro foi alterado. Recarregue a página e confira os dados antes de salvar."]})
        elif "request_id" not in attrs:
            raise serializers.ValidationError({"request_id": "Identificador do envio obrigatório. Reabra o formulário."})
        elif "expected_version" in attrs:
            raise serializers.ValidationError({"expected_version": "Não se aplica a uma nova movimentação."})
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

    def create(self, validated_data):
        # OwnedSerializer.save() owns the transaction. Serialize creates per owner
        # so competing retries see the committed result before trying to insert.
        user = self.context["request"].user
        get_user_model().objects.select_for_update().get(pk=user.pk)
        payload = {key: str(getattr(value, "pk", value)) for key, value in validated_data.items()
                   if key not in {"request_id", "user"}}
        payload.setdefault("description", "")
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        previous = Transaction.objects.filter(user=user, request_id=validated_data["request_id"]).first()
        if previous:
            if previous.deleted_at or previous.request_fingerprint != fingerprint:
                raise serializers.ValidationError({"non_field_errors": ["Este envio já foi utilizado. Abra uma nova movimentação para registrar outros dados."]})
            return previous
        return super().create({**validated_data, "user": user, "request_fingerprint": fingerprint})

    def update(self, instance, validated_data):
        validated_data.pop("expected_version")
        return super().update(instance, validated_data)


class VersionSerializer(StrictSerializer):
    expected_version = serializers.DateTimeField()


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
