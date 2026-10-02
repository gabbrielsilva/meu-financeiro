from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import AuthRateBucket


class Command(BaseCommand):
    help = "Remove somente contadores de autenticação expirados."

    def handle(self, *args, **options):
        count, _ = AuthRateBucket.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Contadores expirados removidos: {count}")
