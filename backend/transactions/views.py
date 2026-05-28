"""
API Views for the Transaction resource.

Uses DRF's ModelViewSet for full CRUD + a custom 'summary' action.
All queries are scoped to the authenticated user — each user can
only see, create, and manage their own transactions.

Performance:
    - select_related('user') prevents N+1 queries
    - Summary endpoint is cached in Redis with per-user keys
    - Cache is invalidated on any write operation (create/update/delete)
"""

import logging
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Sum, Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction
from .serializers import TransactionSerializer

logger = logging.getLogger(__name__)

# Cache TTL for summary endpoint (5 minutes)
SUMMARY_CACHE_TTL = 300


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Transaction CRUD operations.
    All queries are scoped to request.user.

    Endpoints:
        GET    /api/transactions/          → List user's transactions
        POST   /api/transactions/          → Create a transaction
        GET    /api/transactions/{id}/     → Retrieve a transaction
        PUT    /api/transactions/{id}/     → Update a transaction
        DELETE /api/transactions/{id}/     → Delete a transaction
        GET    /api/transactions/summary/  → Get user's spending summary
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'category', 'date']

    def get_queryset(self):
        """
        Return only the authenticated user's transactions.
        Uses select_related to prevent N+1 queries on user FK.
        Supports filtering via django-filter (status, category, date).
        """
        return (
            Transaction.objects
            .select_related('user')
            .filter(user=self.request.user)
        )

    def perform_create(self, serializer):
        """Save transaction with authenticated user and invalidate summary cache."""
        instance = serializer.save(user=self.request.user)
        cache.delete(f'summary_{self.request.user.id}')
        logger.info(
            "Transaction created: id=%s user=%s amount=%s category=%s",
            instance.id, self.request.user.username,
            instance.amount, instance.category,
        )

    def perform_update(self, serializer):
        """Update transaction and invalidate summary cache."""
        instance = serializer.save()
        cache.delete(f'summary_{self.request.user.id}')
        logger.info(
            "Transaction updated: id=%s user=%s",
            instance.id, self.request.user.username,
        )

    def perform_destroy(self, instance):
        """Delete transaction and invalidate summary cache."""
        tx_id = instance.id
        cache.delete(f'summary_{self.request.user.id}')
        instance.delete()
        logger.info(
            "Transaction deleted: id=%s user=%s",
            tx_id, self.request.user.username,
        )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Returns aggregated spending statistics for the current user.
        Results are cached per-user in Redis with a 5-minute TTL.
        Cache is automatically invalidated on create/update/delete.
        """
        cache_key = f'summary_{request.user.id}'
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug("Summary cache HIT for user=%s", request.user.username)
            return Response(cached_result)

        logger.debug("Summary cache MISS for user=%s", request.user.username)
        transactions = self.get_queryset()

        total_spent = transactions.filter(status='spent').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        total_credited = transactions.filter(status='credited').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        category_data = (
            transactions
            .filter(status='spent')
            .values('category')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        category_breakdown = {
            item['category']: {
                'total': str(item['total']),
                'count': item['count']
            }
            for item in category_data
        }

        result = {
            'total_spent': str(total_spent),
            'total_credited': str(total_credited),
            'balance': str(total_credited - total_spent),
            'transaction_count': transactions.count(),
            'category_breakdown': category_breakdown,
        }

        cache.set(cache_key, result, timeout=SUMMARY_CACHE_TTL)
        return Response(result)
