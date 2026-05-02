"""
API Views for the Transaction resource.

Uses DRF's ModelViewSet for full CRUD + a custom 'summary' action.
All queries are scoped to the authenticated user — each user can
only see, create, and manage their own transactions.
"""

from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Transaction
from .serializers import TransactionSerializer


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

    def get_queryset(self):
        """
        Return only the authenticated user's transactions.
        Optionally filter by 'status' and 'category' query parameters.
        """
        qs = Transaction.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get('status')
        category_filter = self.request.query_params.get('category')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if category_filter:
            qs = qs.filter(category=category_filter)

        return qs

    def perform_create(self, serializer):
        """Automatically set the user field to the authenticated user."""
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Returns aggregated spending statistics for the current user.
        """
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

        return Response({
            'total_spent': str(total_spent),
            'total_credited': str(total_credited),
            'balance': str(total_credited - total_spent),
            'transaction_count': transactions.count(),
            'category_breakdown': category_breakdown,
        })
