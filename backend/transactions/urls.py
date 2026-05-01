"""
URL routing for the Transactions API.

Uses DRF's DefaultRouter to auto-generate RESTful URL patterns
from the ViewSet.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
]
