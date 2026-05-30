"""
Unit Tests for Transactions API

Tests covering:
- CRUD operations (Create, Read, Update, Delete)
- User-scoped query filtering
- Summary aggregation endpoint
- Pagination (if enabled)
- Error cases and validation
"""

import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import Transaction


@pytest.mark.django_db
class TestTransactionCreate:
    """Tests for creating transactions."""

    def setup_method(self):
        """Setup test client and user."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='txntest',
            password='securepass123'
        )
        # Login
        self.client.post('/api/auth/login/', {
            'username': 'txntest',
            'password': 'securepass123',
        })

    def test_create_transaction_valid(self):
        """Test creating a valid transaction."""
        response = self.client.post('/api/transactions/', {
            'amount': '100.50',
            'category': 'food',
            'status': 'spent',
            'description': 'Lunch at restaurant',
            'date': '2024-01-15',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['amount'] == '100.50'
        assert response.data['category'] == 'food'
        assert response.data['status'] == 'spent'
        assert Transaction.objects.filter(user=self.user).count() == 1

    def test_create_transaction_income(self):
        """Test creating an income transaction."""
        response = self.client.post('/api/transactions/', {
            'amount': '5000.00',
            'category': 'salary',
            'status': 'credited',
            'description': 'Monthly salary',
            'date': '2024-01-01',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'credited'

    def test_create_transaction_negative_amount(self):
        """Test creating transaction with negative amount fails."""
        response = self.client.post('/api/transactions/', {
            'amount': '-100.00',
            'category': 'food',
            'status': 'spent',
            'description': 'Test',
            'date': '2024-01-15',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_transaction_missing_amount(self):
        """Test creating transaction without amount fails."""
        response = self.client.post('/api/transactions/', {
            'category': 'food',
            'status': 'spent',
            'description': 'Test',
            'date': '2024-01-15',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_transaction_invalid_category(self):
        """Test creating transaction with invalid category fails."""
        response = self.client.post('/api/transactions/', {
            'amount': '100.00',
            'category': 'invalid_category',
            'status': 'spent',
            'description': 'Test',
            'date': '2024-01-15',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_transaction_unauthenticated(self):
        """Test creating transaction without authentication fails."""
        client = APIClient()
        response = client.post('/api/transactions/', {
            'amount': '100.00',
            'category': 'food',
            'status': 'spent',
            'description': 'Test',
            'date': '2024-01-15',
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTransactionRead:
    """Tests for reading transactions."""

    def setup_method(self):
        """Setup test client, user, and transactions."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='readtest',
            password='securepass123'
        )
        self.other_user = User.objects.create_user(
            username='other',
            password='pass123'
        )

        # Create transactions
        self.txn1 = Transaction.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            category='food',
            status='spent',
            date=date(2024, 1, 15),
        )
        self.txn2 = Transaction.objects.create(
            user=self.user,
            amount=Decimal('50.00'),
            category='transport',
            status='spent',
            date=date(2024, 1, 16),
        )
        # Other user's transaction (should not be visible)
        Transaction.objects.create(
            user=self.other_user,
            amount=Decimal('999.00'),
            category='food',
            status='spent',
            date=date(2024, 1, 17),
        )

        # Login
        self.client.post('/api/auth/login/', {
            'username': 'readtest',
            'password': 'securepass123',
        })

    def test_list_transactions(self):
        """Test listing user's transactions."""
        response = self.client.get('/api/transactions/')

        assert response.status_code == status.HTTP_200_OK
        # Response could be paginated (list) or a dict with 'results'
        if isinstance(response.data, list):
            data = response.data
        else:
            data = response.data.get('results', [])
        assert len(data) == 2
        # Verify other user's transaction is not included
        amounts = [float(t['amount']) for t in data]
        assert 999.00 not in amounts

    def test_retrieve_single_transaction(self):
        """Test retrieving a single transaction."""
        response = self.client.get(f'/api/transactions/{self.txn1.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(self.txn1.id)
        assert response.data['amount'] == '100.00'

    def test_retrieve_other_users_transaction(self):
        """Test retrieving another user's transaction fails."""
        other_txn = Transaction.objects.filter(user=self.other_user).first()
        response = self.client.get(f'/api/transactions/{other_txn.id}/')

        # Should be 404 because user doesn't have access
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_by_status(self):
        """Test filtering transactions by status."""
        # Create an income transaction
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('5000.00'),
            category='salary',
            status='credited',
            date=date(2024, 1, 1),
        )

        response = self.client.get('/api/transactions/?status=spent')

        if isinstance(response.data, list):
            data = response.data
        else:
            data = response.data.get('results', [])
        assert all(t['status'] == 'spent' for t in data)
        assert len(data) == 2

    def test_filter_by_category(self):
        """Test filtering transactions by category."""
        response = self.client.get('/api/transactions/?category=food')

        if isinstance(response.data, list):
            data = response.data
        else:
            data = response.data.get('results', [])
        assert all(t['category'] == 'food' for t in data)
        assert len(data) == 1


@pytest.mark.django_db
class TestTransactionUpdate:
    """Tests for updating transactions."""

    def setup_method(self):
        """Setup test client and transaction."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='updatetest',
            password='securepass123'
        )
        self.txn = Transaction.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            category='food',
            status='spent',
            date=date(2024, 1, 15),
        )

        # Login
        self.client.post('/api/auth/login/', {
            'username': 'updatetest',
            'password': 'securepass123',
        })

    def test_update_transaction(self):
        """Test updating a transaction."""
        response = self.client.put(f'/api/transactions/{self.txn.id}/', {
            'amount': '150.00',
            'category': 'transport',
            'status': 'spent',
            'description': 'Updated',
            'date': '2024-01-20',
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['amount'] == '150.00'
        assert response.data['category'] == 'transport'

    def test_update_partial(self):
        """Test partial update of transaction."""
        response = self.client.patch(f'/api/transactions/{self.txn.id}/', {
            'amount': '200.00',
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['amount'] == '200.00'
        # Category should remain unchanged
        assert response.data['category'] == 'food'


@pytest.mark.django_db
class TestTransactionDelete:
    """Tests for deleting transactions."""

    def setup_method(self):
        """Setup test client and transaction."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='deletetest',
            password='securepass123'
        )
        self.txn = Transaction.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            category='food',
            status='spent',
            date=date(2024, 1, 15),
        )

        # Login
        self.client.post('/api/auth/login/', {
            'username': 'deletetest',
            'password': 'securepass123',
        })

    def test_delete_transaction(self):
        """Test deleting a transaction."""
        txn_id = self.txn.id
        response = self.client.delete(f'/api/transactions/{txn_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Transaction.objects.filter(id=txn_id).exists()


@pytest.mark.django_db
class TestTransactionSummary:
    """Tests for transaction summary endpoint."""

    def setup_method(self):
        """Setup test client and transactions."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='summarytest',
            password='securepass123'
        )

        # Create various transactions
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('100.00'),
            category='food',
            status='spent',
            date=date(2024, 1, 15),
        )
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('50.00'),
            category='transport',
            status='spent',
            date=date(2024, 1, 16),
        )
        Transaction.objects.create(
            user=self.user,
            amount=Decimal('5000.00'),
            category='salary',
            status='credited',
            date=date(2024, 1, 1),
        )

        # Login
        self.client.post('/api/auth/login/', {
            'username': 'summarytest',
            'password': 'securepass123',
        })

    def test_get_summary(self):
        """Test getting transaction summary."""
        response = self.client.get('/api/transactions/summary/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_spent' in response.data
        assert 'total_credited' in response.data
        assert 'balance' in response.data
        assert 'transaction_count' in response.data
        assert 'category_breakdown' in response.data

    def test_summary_calculations(self):
        """Test summary calculations are correct."""
        response = self.client.get('/api/transactions/summary/')

        data = response.data
        assert float(data['total_spent']) == 150.00
        assert float(data['total_credited']) == 5000.00
        assert float(data['balance']) == 4850.00
        assert data['transaction_count'] == 3

    def test_summary_category_breakdown(self):
        """Test category breakdown in summary."""
        response = self.client.get('/api/transactions/summary/')

        breakdown = response.data['category_breakdown']
        assert 'food' in breakdown
        assert 'transport' in breakdown
        assert 'salary' in breakdown
