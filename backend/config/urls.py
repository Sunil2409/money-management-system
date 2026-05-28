"""
Root URL configuration for the Money Manager project.

Routes:
    /admin/       → Django Admin panel
    /api/         → Transaction REST API (DRF)
    /api/auth/    → Authentication API (JWT)
    /api/health/  → Health check (unauthenticated, for orchestrators)
"""

from django.contrib import admin
from django.urls import path, include

from config.health import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("transactions.urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/health/", health_check, name="health-check"),
]

