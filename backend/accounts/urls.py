"""
URL routing for the Accounts (Auth) API.

Routes:
    POST /api/auth/register/       → Create new account
    POST /api/auth/login/          → Get JWT tokens (SimpleJWT)
    POST /api/auth/token/refresh/  → Refresh access token
    GET  /api/auth/me/             → Current user profile
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import register_view, me_view

urlpatterns = [
    path('register/', register_view, name='auth-register'),
    path('login/', TokenObtainPairView.as_view(), name='auth-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='auth-token-refresh'),
    path('me/', me_view, name='auth-me'),
]
