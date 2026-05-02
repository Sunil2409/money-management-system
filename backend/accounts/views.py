"""
Auth API Views — Register, Login (JWT), and current user profile.

Authentication Flow:
    1. POST /api/auth/register/  → Create account → returns user data
    2. POST /api/auth/login/     → Returns JWT access + refresh tokens
    3. GET  /api/auth/me/        → Returns current user profile (requires token)
    4. POST /api/auth/token/refresh/ → Refresh expired access token
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    Register a new user.
    
    POST /api/auth/register/
    Body: { "username": "...", "email": "...", "password": "..." }
    Returns: 201 with user data + JWT tokens
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        # Auto-generate JWT tokens on registration
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Get current authenticated user's profile.
    
    GET /api/auth/me/
    Headers: Authorization: Bearer <access_token>
    Returns: user data
    """
    return Response(UserSerializer(request.user).data)
