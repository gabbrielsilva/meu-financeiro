from django.conf import settings
from django.db import models
from apps.categories.models import Category, MovementType, Subcategory


class PaymentMethod(models.TextChoices):
    PIX = "PIX", "Pix"
    CASH = "DINHEIRO", "Dinheiro"
    TRANSFER = "TRANSFERENCIA", "Transferência"
    DEBIT = "DEBITO", "Débito"
    BOLETO = "BOLETO", "Boleto"
    OTHER = "OUTRO", "Outro"


class Transaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    type = models.CharField(max_length=7, choices=MovementType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    payment_method = models.CharField(max_length=13, choices=PaymentMethod.choices)
    description = models.CharField(max_length=500, blank=True, default="")
    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    request_id = models.UUIDField(null=True, blank=True, editable=False)
    request_fingerprint = models.CharField(max_length=64, blank=True, default="", editable=False)

    class Meta:
        ordering = ["-transaction_date", "-id"]
        indexes = [models.Index(fields=["user", "transaction_date"], condition=models.Q(deleted_at__isnull=True), name="transaction_owner_date_live")]
        constraints = [
            models.UniqueConstraint(fields=["user", "request_id"], name="transaction_owner_request_unique"),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="transaction_amount_positive"),
            models.CheckConstraint(condition=models.Q(type__in=MovementType.values), name="transaction_valid_type"),
            models.CheckConstraint(condition=models.Q(payment_method__in=PaymentMethod.values), name="transaction_valid_method"),
        ]
