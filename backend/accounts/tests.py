"""
Unit Tests for Accounts (Authentication) API

Tests covering:
- User registration with validation
- Login with httpOnly cookies
- Token refresh flow
- User profile retrieval
- Logout functionality
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


@pytest.mark.django_db
class TestAuthRegistration:
    """Tests for user registration endpoint."""

    def setup_method(self):
        """Setup test client and ensure no users exist."""
        self.client = APIClient()
        User.objects.all().delete()

    def test_register_valid_credentials(self):
        """Test successful registration with valid data."""
        response = self.client.post('/api/auth/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepass123',
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['user']['username'] == 'testuser'
        assert response.data['user']['email'] == 'test@example.com'
        # Verify user was created in DB
        assert User.objects.filter(username='testuser').exists()

    def test_register_sets_httponly_cookie(self):
        """Test that registration sets httpOnly access token cookie."""
        response = self.client.post('/api/auth/register/', {
            'username': 'cookietest',
            'email': 'cookie@example.com',
            'password': 'securepass123',
        })

        assert response.status_code == status.HTTP_201_CREATED
        # Check that access_token cookie is set
        assert 'access_token' in response.cookies
        assert response.cookies['access_token']['httponly'] is True

    def test_register_duplicate_username(self):
        """Test registration fails with existing username."""
        User.objects.create_user(
            username='duplicate',
            email='old@example.com',
            password='pass'
        )

        response = self.client.post('/api/auth/register/', {
            'username': 'duplicate',
            'email': 'new@example.com',
            'password': 'newpass123',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self):
        """Test registration fails with invalid email format."""
        response = self.client.post('/api/auth/register/', {
            'username': 'testuser',
            'email': 'not-an-email',
            'password': 'securepass123',
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_field(self):
        """Test registration fails with missing required field."""
        response = self.client.post('/api/auth/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            # missing password
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAuthLogin:
    """Tests for login endpoint."""

    def setup_method(self):
        """Setup test client and create test user."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='logintest',
            email='login@example.com',
            password='securepass123'
        )

    def test_login_valid_credentials(self):
        """Test successful login."""
        response = self.client.post('/api/auth/login/', {
            'username': 'logintest',
            'password': 'securepass123',
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'detail' in response.data

    def test_login_sets_httponly_cookies(self):
        """Test that login sets both access and refresh token cookies."""
        response = self.client.post('/api/auth/login/', {
            'username': 'logintest',
            'password': 'securepass123',
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.cookies
        assert 'refresh_token' in response.cookies
        assert response.cookies['access_token']['httponly'] is True
        assert response.cookies['refresh_token']['httponly'] is True

    def test_login_invalid_password(self):
        """Test login fails with wrong password."""
        response = self.client.post('/api/auth/login/', {
            'username': 'logintest',
            'password': 'wrongpassword',
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self):
        """Test login fails with non-existent username."""
        response = self.client.post('/api/auth/login/', {
            'username': 'nonexistent',
            'password': 'anypassword',
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAuthMeEndpoint:
    """Tests for /api/auth/me/ endpoint."""

    def setup_method(self):
        """Setup test client and login."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='metest',
            email='me@example.com',
            password='securepass123'
        )
        # Login
        self.client.post('/api/auth/login/', {
            'username': 'metest',
            'password': 'securepass123',
        })

    def test_get_profile_authenticated(self):
        """Test retrieving user profile when authenticated."""
        response = self.client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == 'metest'
        assert response.data['email'] == 'me@example.com'

    def test_get_profile_unauthenticated(self):
        """Test profile endpoint requires authentication."""
        client = APIClient()
        response = client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAuthLogout:
    """Tests for logout endpoint."""

    def setup_method(self):
        """Setup test client and login."""
        self.client = APIClient()
        User.objects.all().delete()
        self.user = User.objects.create_user(
            username='logouttest',
            password='securepass123'
        )
        self.client.post('/api/auth/login/', {
            'username': 'logouttest',
            'password': 'securepass123',
        })

    def test_logout_clears_cookies(self):
        """Test that logout clears authentication cookies."""
        response = self.client.post('/api/auth/logout/')

        assert response.status_code == status.HTTP_200_OK
        assert response.cookies['access_token']['max_age'] == 0

    def test_logout_requires_auth(self):
        """Test logout endpoint requires authentication."""
        client = APIClient()
        response = client.post('/api/auth/logout/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
