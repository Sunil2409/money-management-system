"""
URL routing for the Accounts (Auth) API.

Routes:
    POST /api/auth/register/       → Create new account (sets httpOnly cookies)
    POST /api/auth/login/          → Get JWT tokens via httpOnly cookies
    POST /api/auth/token/refresh/  → Refresh access token (uses cookie)
    POST /api/auth/logout/         → Clear auth cookies
    GET  /api/auth/me/             → Current user profile (uses cookie auth)
"""

from django.urls import path

from .views import (
    register_view,
    me_view,
    logout_view,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
)

urlpatterns = [
    path('register/', register_view, name='auth-register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='auth-login'),
    path(
        'token/refresh/',
        CustomTokenRefreshView.as_view(),
        name='auth-token-refresh'
    ),
    path('logout/', logout_view, name='auth-logout'),
    path('me/', me_view, name='auth-me'),
]
