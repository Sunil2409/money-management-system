"""
DRF Serializers for the Transaction model.

Serializers handle:
1. Validation of incoming data (POST/PUT)
2. Conversion of model instances to JSON (GET responses)
3. Field-level and object-level validation rules
"""

from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaction CRUD operations.

    Includes computed fields:
    - category_display: Human-readable category name
    - status_display: Human-readable status name
    """
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            'id', 'amount', 'category', 'category_display',
            'status', 'status_display', 'description',
            'date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_amount(self, value):
        """Ensure amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class TransactionSummarySerializer(serializers.Serializer):
    """Serializer for the summary/stats endpoint."""
    total_spent = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_credited = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    transaction_count = serializers.IntegerField()
    category_breakdown = serializers.DictField()
