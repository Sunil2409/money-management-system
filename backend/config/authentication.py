"""
Custom JWT Authentication — Support httpOnly Cookies

Extends DRF's JWTAuthentication to extract JWT tokens from httpOnly cookies
instead of (or in addition to) the Authorization header.

Authentication Flow:
    1. Browser sends request with httpOnly cookie (automatically included)
    2. Our custom auth class extracts token from cookie
    3. DRF validates token and authenticates user
    4. Request proceeds with authenticated user

Fallback: Also supports Bearer token in Authorization header for API testing/clients.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """
    Extend SimpleJWT authentication to support httpOnly cookies.
    
    Tries to extract token from:
    1. HttpOnly cookie (primary, secure method)
    2. Authorization: Bearer header (fallback, for testing/clients)
    """
    
    def authenticate(self, request):
        """
        Extract JWT token from httpOnly cookie or Authorization header.
        
        Args:
            request: DRF request object
            
        Returns:
            (user, token) tuple if authenticated, None if no token found
            
        Raises:
            AuthenticationFailed if token is invalid
        """
        # First, try to get token from httpOnly cookie
        access_token = request.COOKIES.get('access_token')
        
        # If no cookie, try Authorization header (Bearer token)
        if not access_token:
            auth_header = self.get_header(request)
            if auth_header:
                try:
                    access_token = auth_header.split()[-1]
                except IndexError:
                    raise AuthenticationFailed('Invalid Authorization header format')
        
        # If we still don't have a token, return None (let other auth classes try)
        if not access_token:
            return None
        
        # Validate and decode the JWT token using parent class logic
        try:
            validated_token = self.get_validated_token(access_token)
        except AuthenticationFailed:
            raise
        
        # Get user from token
        user = self.get_user(validated_token)
        
        return (user, validated_token)
