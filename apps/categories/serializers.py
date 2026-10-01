from django.db import IntegrityError, transaction
from rest_framework import serializers
from apps.accounts.serializers import StrictSerializer
from .models import Category, MovementType, Subcategory


class OwnedSerializer(StrictSerializer, serializers.ModelSerializer):
    """Write rules used by both HTML forms and REST endpoints."""

    def to_internal_value(self, data):
        forbidden = set(data) & {name for name, field in self.fields.items() if field.read_only}
        if forbidden:
            raise serializers.ValidationError({key: "Campo não permitido." for key in forbidden})
        return super().to_internal_value(data)

    def save(self, **kwargs):
        try:
            with transaction.atomic():
                return super().save(**kwargs)
        except IntegrityError as exc:
            raise serializers.ValidationError({"non_field_errors": ["Dados conflitantes. Verifique os vínculos e nomes já cadastrados."]}) from exc


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
