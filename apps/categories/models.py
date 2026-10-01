from django.conf import settings
from django.db import models
from django.db.models.functions import Lower, Trim


class MovementType(models.TextChoices):
    INCOME = "RECEITA", "Receita"
    EXPENSE = "DESPESA", "Despesa"


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    name = models.CharField(max_length=100, db_collation="und-x-icu")
    type = models.CharField(max_length=7, choices=MovementType.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type", "name", "id"]
        constraints = [
            models.UniqueConstraint(Lower(Trim("name")), "user", "type", name="category_name_owner_type_unique"),
            models.UniqueConstraint(fields=["id", "user"], name="category_id_owner_unique"),
            models.UniqueConstraint(fields=["id", "user", "type"], name="category_id_owner_type_unique"),
            models.CheckConstraint(condition=models.Q(type__in=MovementType.values), name="category_valid_type"),
            models.CheckConstraint(condition=~models.Q(name__regex=r"^\s*$"), name="category_name_not_blank"),
        ]

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="subcategories")
    name = models.CharField(max_length=100, db_collation="und-x-icu")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(Lower(Trim("name")), "category", name="subcategory_name_category_unique"),
            models.UniqueConstraint(fields=["id", "category", "user"], name="subcategory_id_category_owner_unique"),
            models.CheckConstraint(condition=~models.Q(name__regex=r"^\s*$"), name="subcategory_name_not_blank"),
        ]

    def __str__(self):
        return self.name
