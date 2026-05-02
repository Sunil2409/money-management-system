"""
Root URL configuration for the Money Manager project.

Routes:
    /admin/     → Django Admin panel
    /api/       → Transaction REST API (DRF)
    /api/auth/  → Authentication API (JWT)
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("transactions.urls")),
    path("api/auth/", include("accounts.urls")),
]

