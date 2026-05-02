"""
Transaction Model — Core data model for the Money Manager application.

Each transaction captures:
- Amount (decimal, up to 12 digits)
- Category (predefined choices for transaction type)
- Status (spent or credited)
- Description (free-text details)
- Date (when the transaction occurred)
"""

import uuid
from django.conf import settings
from django.db import models


class Transaction(models.Model):
    """
    Represents a single financial transaction.
    Uses UUID as primary key for better scalability and security
    (no sequential ID guessing in APIs).
    """

    # ── Category Choices ──────────────────────────────────────────────
    CATEGORY_CHOICES = [
        ('food', 'Food & Dining'),
        ('transport', 'Transport & Fuel'),
        ('shopping', 'Shopping & Lifestyle'),
        ('bills', 'Bills & Utilities'),
        ('health', 'Health & Medical'),
        ('entertainment', 'Entertainment'),
        ('salary', 'Salary & Income'),
        ('freelance', 'Freelance Income'),
        ('investment', 'Investments'),
        ('other', 'Miscellaneous'),
    ]

    # ── Status Choices ────────────────────────────────────────────────
    STATUS_CHOICES = [
        ('spent', 'Spent'),
        ('credited', 'Credited'),
    ]

    # ── Fields ────────────────────────────────────────────────────────
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the transaction"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Owner of this transaction"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Transaction amount (up to 9,999,999,999.99)"
    )
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default='other',
        help_text="Type/category of the transaction"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        help_text="Whether money was spent or credited"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Optional description or notes about the transaction"
    )
    date = models.DateField(
        help_text="Date when the transaction occurred"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def __str__(self):
        return f"{self.get_status_display()} ₹{self.amount} — {self.get_category_display()} ({self.date})"
