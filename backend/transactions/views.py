"""
API Views for the Transaction resource.

Uses DRF's ModelViewSet for full CRUD + a custom 'summary' action
for spending statistics.
"""

from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Transaction CRUD operations.

    Endpoints:
        GET    /api/transactions/          → List all transactions
        POST   /api/transactions/          → Create a transaction
        GET    /api/transactions/{id}/     → Retrieve a transaction
        PUT    /api/transactions/{id}/     → Update a transaction
        DELETE /api/transactions/{id}/     → Delete a transaction
        GET    /api/transactions/summary/  → Get spending summary
    """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """
        Optionally filter transactions by 'status' and 'category'
        query parameters from the URL.

        Examples:
            /api/transactions/?status=spent
            /api/transactions/?category=food
            /api/transactions/?status=credited&category=salary
        """
        qs = Transaction.objects.all()
        status_filter = self.request.query_params.get('status')
        category_filter = self.request.query_params.get('category')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)

        return qs

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Returns aggregated spending statistics:
        - Total spent
        - Total credited
        - Net balance
        - Transaction count
        - Breakdown by category
        """
        transactions = self.get_queryset()

        total_spent = transactions.filter(status='spent').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        total_credited = transactions.filter(status='credited').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        # Category breakdown (spent only)
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

        return Response({
            'total_spent': str(total_spent),
            'total_credited': str(total_credited),
            'balance': str(total_credited - total_spent),
            'transaction_count': transactions.count(),
            'category_breakdown': category_breakdown,
        })
