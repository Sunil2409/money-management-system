"""
Auth API Views — JWT httpOnly cookies, register, login, profile.

Authentication Flow:
    1. POST /api/auth/register/  → Create account → httpOnly cookies
    2. POST /api/auth/login/     → JWT tokens in httpOnly cookies
    3. GET  /api/auth/me/        → Returns current user profile
    4. POST /api/auth/token/refresh/ → Refresh token using cookie
    5. POST /api/auth/logout/    → Clear auth cookies

Security:
    - Access token: httpOnly, Secure, SameSite cookie (JS-inaccessible)
    - Refresh token: httpOnly, Secure, SameSite cookie
    - Rate-limited: 5 requests/minute per IP (brute-force protection)
    - Prevents XSS attacks from stealing tokens via localStorage
"""

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.throttling import AnonRateThrottle

from .serializers import RegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)

# Cookie configuration
ACCESS_TOKEN_COOKIE = 'access_token'
REFRESH_TOKEN_COOKIE = 'refresh_token'


# ── Rate Limiting for Brute Force Protection ──────────────────────────
class LoginRateThrottle(AnonRateThrottle):
    """
    Stricter rate limiting for login/register endpoints.
    Prevents brute-force attacks: max 5 requests per minute per IP.
    """
    scope = 'login'  # Rate limit scope name
    THROTTLE_RATES = {'login': '5/minute'}  # Can be overridden via settings


def _set_auth_cookies(response, access_token, refresh_token):
    """
    Helper function to set JWT tokens in httpOnly cookies.

    Args:
        response: Django Response object
        access_token: JWT access token string
        refresh_token: JWT refresh token string
    """
    # Access token cookie: short-lived (1 day), expires when browser closes
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=str(access_token),
        max_age=60 * 60 * 24,  # 1 day
        httponly=settings.HTTPONLY_COOKIES_ENABLED,
        secure=settings.SECURE_COOKIE_ENABLED,
        samesite='None' if settings.SECURE_COOKIE_ENABLED else 'Lax',
        path='/',
    )

    # Refresh token cookie: long-lived (7 days)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=str(refresh_token),
        max_age=60 * 60 * 24 * 7,  # 7 days
        httponly=settings.HTTPONLY_COOKIES_ENABLED,
        secure=settings.SECURE_COOKIE_ENABLED,
        samesite='None' if settings.SECURE_COOKIE_ENABLED else 'Lax',
        path='/',
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def register_view(request):
    """
    Register a new user.

    POST /api/auth/register/
    Body: { "username": "...", "email": "...", "password": "..." }
    Returns: 201 with user data. Auth tokens set in httpOnly cookies.

    Rate limited to 5 requests per minute per IP (brute-force protection).
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Auto-generate JWT tokens on registration
        refresh = RefreshToken.for_user(user)
        logger.info(
            "User registered: username=%s email=%s",
            user.username, user.email,
        )
        response = Response(
            {
                'user': UserSerializer(user).data,
                'detail': (
                    'Registration successful. '
                    'Tokens set in httpOnly cookies.'
                )
            },
            status=status.HTTP_201_CREATED
        )
        _set_auth_cookies(response, refresh.access_token, refresh)
        return response
    logger.warning(
        "Registration failed: errors=%s",
        serializer.errors,
    )
    return Response(
        serializer.errors, status=status.HTTP_400_BAD_REQUEST
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom login view that sets JWT in httpOnly cookies.

    Rate limited to 5 requests per minute per IP (brute-force protection).

    POST /api/auth/login/
    Body: { "username": "...", "password": "..." }
    Returns: 200 with user data. Tokens set in httpOnly cookies.
    """
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        """Override to set tokens in cookies and return user data."""
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.pop('access', None)
            refresh_token = response.data.pop('refresh', None)

            # Return user data instead of tokens
            response.data = {
                'detail': 'Login successful. Tokens set in httpOnly cookies.',
            }

            # If we have tokens, set them in cookies
            if access_token and refresh_token:
                _set_auth_cookies(response, access_token, refresh_token)

            username = request.data.get('username')
            logger.info("User logged in: username=%s", username)

        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view using httpOnly cookies.

    POST /api/auth/token/refresh/
    Cookie: refresh_token (automatically sent by browser)
    Returns: 200 with new access token set in httpOnly cookie.
    """

    def post(self, request, *args, **kwargs):
        """Override to use cookie for refresh and set new token in cookie."""
        # Extract refresh token from cookie
        refresh_token = request.COOKIES.get(REFRESH_TOKEN_COOKIE)

        if not refresh_token:
            msg = "Token refresh attempted without refresh token cookie"
            logger.warning(msg)
            return Response(
                {'detail': 'Refresh token not found in cookies.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Add refresh token to request data for parent class
        request.data._mutable = True
        request.data['refresh'] = refresh_token

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.pop('access', None)

            # Set new access token in cookie
            if access_token:
                response.set_cookie(
                    key=ACCESS_TOKEN_COOKIE,
                    value=str(access_token),
                    max_age=60 * 60 * 24,  # 1 day
                    httponly=settings.HTTPONLY_COOKIES_ENABLED,
                    secure=settings.SECURE_COOKIE_ENABLED,
                    samesite=(
                        'None'
                        if settings.SECURE_COOKIE_ENABLED
                        else 'Lax'
                    ),
                    path='/',
                )

            msg = 'Token refreshed. New access token set in cookie.'
            response.data = {'detail': msg}
            logger.info("Token refreshed successfully")

        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout the user by clearing authentication cookies.

    POST /api/auth/logout/
    Returns: 200 with cookies cleared
    """
    response = Response(
        {'detail': 'Logout successful. Cookies cleared.'},
        status=status.HTTP_200_OK
    )
    # Clear both tokens
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path='/')
    response.delete_cookie(REFRESH_TOKEN_COOKIE, path='/')

    logger.info("User logged out: username=%s", request.user.username)
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Get current authenticated user's profile.

    GET /api/auth/me/
    Auth: httpOnly cookie (automatically sent by browser)
    Returns: user data
    """
    logger.debug("Profile accessed: user=%s", request.user.username)
    return Response(UserSerializer(request.user).data)
