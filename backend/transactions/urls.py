"""
URL routing for the Transactions API.

Uses DRF's DefaultRouter to auto-generate RESTful URL patterns
from the ViewSet.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, StatementDownloadView

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'statements/<int:year>/<int:month>/download/',
        StatementDownloadView.as_view(),
        name='statement-download',
    ),
]
