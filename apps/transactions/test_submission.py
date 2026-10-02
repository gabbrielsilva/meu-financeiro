from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import register_user
from apps.categories.models import Category
from .models import Transaction
from .serializers import TransactionSerializer


class SubmissionFixtures:
    def setUp(self):
        self.user = register_user('submission@example.test', 'Only-Test!984-Safe')
        self.other = register_user('other-submission@example.test', 'Only-Test!984-Safe')
        category = Category.objects.get(user=self.user, name='Alimentação')
        self.payload = {'request_id': str(uuid4()), 'type': 'DESPESA', 'amount': '12.50',
                        'category': category.pk, 'subcategory': category.subcategories.first().pk,
                        'payment_method': 'PIX', 'transaction_date': timezone.localdate().isoformat(), 'description': 'Test'}
        self.client = APIClient()
        self.client.force_login(self.user)


@override_settings(SECURE_SSL_REDIRECT=False)
class SubmissionTests(SubmissionFixtures, TestCase):
    def create(self, **changes):
        return self.client.post('/api/v1/transactions', {**self.payload, **changes}, format='json')

    def test_identical_retry_returns_same_movement(self):
        first, retry = self.create(), self.create()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(first.data['id'], retry.data['id'])
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.client.get('/api/v1/dashboard').data['expenses'], '12.50')

    def test_same_key_different_payload_is_rejected(self):
        self.create()
        self.assertEqual(self.create(amount='25.00').status_code, 400)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_distinct_keys_allow_legitimate_identical_purchases(self):
        self.create()
        self.assertEqual(self.create(request_id=str(uuid4())).status_code, 201)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_key_is_scoped_to_owner(self):
        self.create()
        self.client.force_login(self.other)
        category = Category.objects.get(user=self.other, name='Alimentação')
        self.assertEqual(self.create(category=category.pk, subcategory=category.subcategories.first().pk).status_code, 201)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_invalid_submission_does_not_consume_key(self):
        self.assertEqual(self.create(amount='0').status_code, 400)
        self.assertEqual(self.create().status_code, 201)

    def test_missing_key_is_rejected(self):
        payload = dict(self.payload)
        payload.pop('request_id')
        self.assertEqual(self.client.post('/api/v1/transactions', payload, format='json').status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_deleted_submission_cannot_be_recreated_by_retry(self):
        first = self.create().data
        endpoint = f"/api/v1/transactions/{first['id']}"
        self.assertEqual(self.client.delete(endpoint, {'expected_version': first['updated_at']}, format='json').status_code, 204)
        self.assertEqual(self.create().status_code, 400)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertIsNotNone(Transaction.objects.get().deleted_at)

    def test_stale_api_edit_and_delete_are_rejected(self):
        first = self.create().data
        endpoint = f"/api/v1/transactions/{first['id']}"
        self.assertEqual(self.client.patch(endpoint, {'amount': '15.00', 'expected_version': first['updated_at']}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(endpoint, {'amount': '50.00', 'expected_version': first['updated_at']}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(endpoint, {'expected_version': first['updated_at']}, format='json').status_code, 400)
        self.assertEqual(str(Transaction.objects.get().amount), '15.00')
        self.assertIsNone(Transaction.objects.get().deleted_at)

    def test_missing_version_cannot_bypass_protection(self):
        first = self.create().data
        endpoint = f"/api/v1/transactions/{first['id']}"
        self.assertEqual(self.client.patch(endpoint, {'amount': '15.00'}, format='json').status_code, 400)
        self.assertEqual(self.client.delete(endpoint).status_code, 400)

    def test_html_retries_keep_key_and_stale_form_keeps_input(self):
        initial = self.client.get('/movimentacoes/nova/').context['form'].initial
        payload = {**self.payload, 'request_id': str(initial['request_id']), 'amount': '12,50'}
        for _ in range(2):
            self.assertRedirects(self.client.post('/movimentacoes/nova/', payload), '/movimentacoes/')
        self.assertEqual(Transaction.objects.count(), 1)
        row = Transaction.objects.get()
        endpoint = f'/movimentacoes/{row.pk}/editar/'
        old_version = self.client.get(endpoint).context['form'].initial['expected_version']
        current = self.client.patch(f'/api/v1/transactions/{row.pk}', {'amount': '15.00', 'expected_version': old_version}, format='json')
        self.assertEqual(current.status_code, 200)
        response = self.client.post(endpoint, {**payload, 'amount': '99,00', 'expected_version': old_version})
        self.assertContains(response, 'Este registro foi alterado')
        self.assertEqual(response.context['form']['amount'].value(), '99,00')
        row.refresh_from_db()
        self.assertEqual(str(row.amount), '15.00')
        self.assertEqual(response.context['form']['expected_version'].value(), old_version)

    def test_old_delete_confirmation_requires_new_confirmation(self):
        first = self.create().data
        endpoint = f"/movimentacoes/{first['id']}/excluir/"
        self.client.patch(f"/api/v1/transactions/{first['id']}", {'amount': '15.00', 'expected_version': first['updated_at']}, format='json')
        self.assertRedirects(self.client.post(endpoint, {'expected_version': first['updated_at']}), endpoint)
        self.assertIsNone(Transaction.objects.get().deleted_at)


@override_settings(SECURE_SSL_REDIRECT=False)
class ConcurrentSubmissionTests(SubmissionFixtures, TransactionTestCase):
    def test_simultaneous_retries_create_one_row(self):
        barrier = Barrier(2)
        def worker(_):
            close_old_connections()
            try:
                serializer = TransactionSerializer(data=self.payload, context={'request': SimpleNamespace(user=self.user)})
                serializer.is_valid(raise_exception=True)
                barrier.wait(timeout=10)
                return serializer.save(user=self.user).pk
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            identifiers = list(pool.map(worker, range(2)))
        self.assertEqual(identifiers[0], identifiers[1])
        self.assertEqual(Transaction.objects.count(), 1)
