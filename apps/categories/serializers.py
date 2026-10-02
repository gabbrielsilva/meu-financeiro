from django.db import IntegrityError, transaction
from collections.abc import Mapping
import logging
from rest_framework import serializers
from apps.accounts.serializers import StrictSerializer
from .models import Category, MovementType, Subcategory


class OwnedSerializer(StrictSerializer, serializers.ModelSerializer):
    """Write rules used by both HTML forms and REST endpoints."""

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Envie um objeto com os campos esperados."]})
        forbidden = set(data) & {name for name, field in self.fields.items() if field.read_only}
        if forbidden:
            raise serializers.ValidationError({key: "Campo não permitido." for key in forbidden})
        return super().to_internal_value(data)

    def save(self, **kwargs):
        try:
            with transaction.atomic():
                return super().save(**kwargs)
        except IntegrityError as exc:
            logging.getLogger(__name__).warning("Conflito de integridade", exc_info=True)
            raise serializers.ValidationError({"non_field_errors": ["Dados conflitantes. Verifique os vínculos e nomes já cadastrados."]}) from exc

    def update(self, instance, validated_data):
        # save() owns the transaction; compare the snapshot after acquiring the lock.
        current = type(instance).objects.select_for_update().get(pk=instance.pk, user=instance.user)
        if current.updated_at != instance.updated_at or getattr(current, "deleted_at", None):
            raise serializers.ValidationError({"non_field_errors": ["Este registro foi alterado ou excluído em outra solicitação. Recarregue a página antes de tentar novamente."]})
        return super().update(current, validated_data)


class CategorySerializer(OwnedSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "type", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def validate(self, attrs):
        if self.instance and attrs.get("type", self.instance.type) != self.instance.type:
            raise serializers.ValidationError({"type": "O tipo de uma categoria não pode ser alterado."})
        name = attrs.get("name", self.instance.name if self.instance else "")
        movement_type = attrs.get("type", self.instance.type if self.instance else None)
        matches = Category.objects.filter(user=self.context["request"].user, type=movement_type, name__iexact=name)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError({"name": "Já existe uma categoria com este nome e tipo, inclusive inativa."})
        return attrs


class SubcategorySerializer(OwnedSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none())
    category_name = serializers.CharField(source="category.name", read_only=True)
    effective_active = serializers.SerializerMethodField()

    class Meta:
        model = Subcategory
        fields = ["id", "name", "category", "category_name", "is_active", "effective_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.context["request"].user)

    def get_effective_active(self, obj):
        return obj.is_active and obj.category.is_active

    def validate(self, attrs):
        category = attrs.get("category", self.instance.category if self.instance else None)
        if self.instance and category.pk != self.instance.category_id:
            raise serializers.ValidationError({"category": "Não é permitido mover uma subcategoria."})
        if not self.instance and not category.is_active:
            raise serializers.ValidationError({"category": "Selecione uma categoria ativa."})
        name = attrs.get("name", self.instance.name if self.instance else "")
        matches = Subcategory.objects.filter(user=self.context["request"].user, category=category, name__iexact=name)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError({"name": "Já existe uma subcategoria com este nome, inclusive inativa."})
        return attrs


class CategoryFilters(StrictSerializer):
    type = serializers.ChoiceField(choices=MovementType.choices, required=False)
    is_active = serializers.BooleanField(required=False)


class SubcategoryFilters(CategoryFilters):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=self.context["request"].user)
