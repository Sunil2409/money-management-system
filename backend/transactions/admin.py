"""
Django Admin configuration for Transaction model.
"""

from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'amount', 'category', 'status', 'description_short', 'created_at']
    list_filter = ['status', 'category', 'date']
    search_fields = ['description']
    ordering = ['-date', '-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def description_short(self, obj):
        """Truncate long descriptions in the list view."""
        return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description
    description_short.short_description = 'Description'
