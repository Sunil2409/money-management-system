"""
Root URL configuration for the Money Manager project.

Routes:
    /admin/                  → Django Admin panel
    /api/                    → Transaction REST API (DRF)
    /api/auth/               → Authentication API (JWT)
    /api/health/             → Health check (unauthenticated, for orchestrators)
    /api/docs/               → Swagger UI (interactive API documentation)
    /api/docs/redoc/         → ReDoc (alternative API documentation)
    /api/schema/             → OpenAPI schema (JSON)
"""

from django.contrib import admin
from django.urls import path, include

from config.health import health_check
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("transactions.urls")),
    path("api/auth/", include("accounts.urls")),
    path("api/health/", health_check, name="health-check"),
    
    # API Documentation (drf-spectacular)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

