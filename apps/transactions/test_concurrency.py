from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.categories.models import Category, Subcategory
from .models import Transaction
from .serializers import TransactionSerializer
from .services import soft_delete


@override_settings(SECURE_SSL_REDIRECT=False)
class ConcurrentMovementTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('concurrency@example.test')
        self.category = Category.objects.create(user=self.user, name='Test', type='DESPESA')
        self.subcategory = Subcategory.objects.create(user=self.user, category=self.category, name='Test')
        self.row = Transaction.objects.create(user=self.user, category=self.category, subcategory=self.subcategory,
            type='DESPESA', amount=Decimal('10'), payment_method='PIX', transaction_date=timezone.localdate())

    def serializer(self, row, **data):
        serializer = TransactionSerializer(row, data={"expected_version": row.updated_at.isoformat(), **data}, partial=True, context={'request': SimpleNamespace(user=self.user)})
        serializer.is_valid(raise_exception=True)
        return serializer

    def test_stale_edit_never_resurrects_deleted_movement(self):
        edit = self.serializer(Transaction.objects.get(pk=self.row.pk), description='Old request')
        soft_delete(self.row)
        with self.assertRaises(ValidationError):
            edit.save()
        self.row.refresh_from_db()
        self.assertIsNotNone(self.row.deleted_at)

    def test_stale_partial_edit_never_overwrites_new_amount(self):
        edit = self.serializer(Transaction.objects.get(pk=self.row.pk), description='Old request')
        self.serializer(self.row, amount='25.00').save()
        with self.assertRaises(ValidationError):
            edit.save()
        self.row.refresh_from_db()
        self.assertEqual(self.row.amount, Decimal('25'))

    def test_concurrent_edits_report_conflict(self):
        barrier = Barrier(2)
        def worker(amount):
            close_old_connections()
            try:
                edit = self.serializer(Transaction.objects.get(pk=self.row.pk), amount=amount)
                barrier.wait(timeout=10)
                try:
                    edit.save()
                    return 'saved'
                except ValidationError:
                    return 'conflict'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, ['20.00', '30.00']))
        self.assertCountEqual(results, ['saved', 'conflict'])

    def test_delete_does_not_overwrite_new_amount(self):
        stale = Transaction.objects.get(pk=self.row.pk)
        self.serializer(self.row, amount='25.00').save()
        with self.assertRaises(ValidationError):
            soft_delete(stale)
        self.row.refresh_from_db()
        self.assertEqual(self.row.amount, Decimal('25'))
        self.assertIsNone(self.row.deleted_at)

    def test_malformed_json_objects_return_400(self):
        client = APIClient()
        client.force_login(self.user)
        for path in ['/api/v1/categories', '/api/v1/subcategories', '/api/v1/transactions']:
            for data in [[{}], [], 'text', 5]:
                with self.subTest(path=path, data=data):
                    self.assertEqual(client.post(path, data, format='json').status_code, 400)
