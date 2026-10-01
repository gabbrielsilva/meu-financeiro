from django.utils import timezone


def soft_delete(movement):
    movement.deleted_at = timezone.now()
    movement.save(update_fields=["deleted_at", "updated_at"])
