from django.utils import timezone
from .models import Transaction
from rest_framework.exceptions import ValidationError


def soft_delete(movement, expected_version=None):
    now = timezone.now()
    # A narrow, atomic UPDATE never writes stale financial fields back to the DB.
    changed = Transaction.objects.filter(pk=movement.pk, user=movement.user, deleted_at__isnull=True,
        updated_at=expected_version or movement.updated_at).update(deleted_at=now, updated_at=now)
    if not changed:
        raise ValidationError({"non_field_errors": ["Este registro foi alterado ou excluído. Recarregue a página antes de confirmar a exclusão."]})
    movement.deleted_at = now
