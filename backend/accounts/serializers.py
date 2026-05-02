"""
Serializers for user registration, login, and profile.
"""

from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles user registration.
    Accepts username, email, password. Returns user data (no password).
    """
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        read_only_fields = ['id']

    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Create user with hashed password."""
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """Read-only serializer for the current user profile."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'date_joined']
