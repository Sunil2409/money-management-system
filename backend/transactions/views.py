"""
API Views for the Transaction resource.

Uses DRF's ModelViewSet for full CRUD + a custom
'summary' action. All queries are scoped to the
authenticated user — each user can only see, create,
and manage their own transactions.

Performance:
    - select_related('user') prevents N+1 queries
    - Summary endpoint is cached in Redis
    - Cache is invalidated on write operations
"""

import logging
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Sum, Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    AllowAny, IsAuthenticated
)
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction
from .serializers import TransactionSerializer

logger = logging.getLogger(__name__)

# Cache TTL for summary endpoint (5 minutes)
SUMMARY_CACHE_TTL = 300


class StatementDownloadView(APIView):
    """Presigned S3 download URL for monthly PDF."""

    permission_classes = [IsAuthenticated]

    def get(self, request, year: int, month: int):
        s3_key = (
            f"statements/user_{request.user.id}/"
            f"{year}_{int(month):02d}_statement.pdf"
        )
        s3_client = boto3.client(
            's3',
            region_name=settings.AWS_DEFAULT_REGION
        )

        try:
            # Verify the object exists first
            s3_client.head_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=s3_key
            )

            # Generate pre-signed URL (15 minutes)
            filename = (
                f'statement_{year}_{month:02d}.pdf'
            )
            disposition = (
                f'attachment; filename="{filename}"'
            )
            presigned_url = (
                s3_client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': (
                            settings
                            .AWS_STORAGE_BUCKET_NAME
                        ),
                        'Key': s3_key,
                        'ResponseContentDisposition': (
                            disposition
                        ),
                    },
                    ExpiresIn=900
                )
            )
            return Response({
                'download_url': presigned_url,
                'expires_in_seconds': 900,
            })
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return Response(
                    {
                        'error': (
                            'Statement for the requested'
                            ' month has not been'
                            ' generated yet.'
                        ),
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(
                {
                    'error': (
                        'Could not fetch statement.'
                        ' Try again later.'
                    ),
                },
                status=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            )


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Transaction CRUD with pagination.

    All queries are scoped to request.user.

    Endpoints:
        GET    /api/transactions/         → List
        GET    /api/transactions/?status= → Filter
        POST   /api/transactions/         → Create
        GET    /api/transactions/{id}/    → Retrieve
        PUT    /api/transactions/{id}/    → Update
        DELETE /api/transactions/{id}/    → Delete
        GET    /api/transactions/summary/ → Summary

    Pagination: 25 items per page
    Filtering: status, category, date
    Caching: Summary cached per-user (5-min TTL)
    """

    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    filterset_fields = ['status', 'category', 'date']

    def get_queryset(self):
        """
        Return only the authenticated user's transactions.
        Uses select_related to prevent N+1 queries.
        Results ordered by most recent first.
        """
        return (
            Transaction.objects
            .select_related('user')
            .filter(user=self.request.user)
            .order_by('-date', '-created_at')
        )

    def perform_create(self, serializer):
        """Save transaction with authenticated user."""
        instance = serializer.save(
            user=self.request.user
        )
        cache.delete(
            f'summary_{self.request.user.id}'
        )
        logger.info(
            "Transaction created: id=%s user=%s"
            " amount=%s category=%s",
            instance.id,
            self.request.user.username,
            instance.amount,
            instance.category,
        )

    def perform_update(self, serializer):
        """Update transaction and invalidate cache."""
        instance = serializer.save()
        cache.delete(
            f'summary_{self.request.user.id}'
        )
        logger.info(
            "Transaction updated: id=%s user=%s",
            instance.id,
            self.request.user.username,
        )

    def perform_destroy(self, instance):
        """Delete transaction and invalidate cache."""
        tx_id = instance.id
        cache.delete(
            f'summary_{self.request.user.id}'
        )
        instance.delete()
        logger.info(
            "Transaction deleted: id=%s user=%s",
            tx_id, self.request.user.username,
        )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Aggregated spending stats for current user.
        Cached per-user in Redis with 5-minute TTL.
        Invalidated on create/update/delete.
        """
        cache_key = f'summary_{request.user.id}'
        cached_result = cache.get(cache_key)
        if cached_result:
            logger.debug(
                "Summary cache HIT for user=%s",
                request.user.username
            )
            return Response(cached_result)

        logger.debug(
            "Summary cache MISS for user=%s",
            request.user.username
        )
        transactions = self.get_queryset()

        total_spent = (
            transactions
            .filter(status='spent')
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )

        total_credited = (
            transactions
            .filter(status='credited')
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )

        category_data = (
            transactions
            .filter(status='spent')
            .values('category')
            .annotate(
                total=Sum('amount'),
                count=Count('id')
            )
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
            'balance': str(
                total_credited - total_spent
            ),
            'transaction_count': (
                transactions.count()
            ),
            'category_breakdown': category_breakdown,
        }

        cache.set(
            cache_key, result,
            timeout=SUMMARY_CACHE_TTL
        )
        return Response(result)


class HealthCheckView(APIView):
    """Deep readiness probe for database and Redis."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        health_status = {
            "database": "healthy",
            "redis": "healthy",
        }

        # Test PostgreSQL connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
        except Exception as e:
            health_status["database"] = (
                f"unhealthy: {str(e)}"
            )

        # Test Redis ping
        try:
            cache.set(
                "health_check_ping", "pong",
                timeout=5
            )
            if cache.get("health_check_ping") != "pong":
                raise ValueError(
                    "Cache readback failed"
                )
        except Exception as e:
            health_status["redis"] = (
                f"unhealthy: {str(e)}"
            )

        is_healthy = all(
            v == "healthy"
            for v in health_status.values()
        )
        http_status = (
            status.HTTP_200_OK
            if is_healthy
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            health_status, status=http_status
        )
