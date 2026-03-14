from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser
from core.exceptions import AccountLockedError, SignatureFailedError


class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials.
    Returns the user object if valid — the view handles token generation.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise AccountLockedError()

        if not user.check_password(password):
            user.increment_failed_attempts()
            raise SignatureFailedError("Invalid credentials.")

        user.reset_failed_attempts()
        data["user"] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    """
    Shapes the user object returned to the frontend after login
    and in user management endpoints.
    """
    class Meta:
        model = CustomUser
        fields = ["id", "email", "full_name", "role", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class CreateUserSerializer(serializers.ModelSerializer):
    """
    Used by admin to create new user accounts.
    Password is write-only — never returned in any response.
    """
    password = serializers.CharField(write_only=True, min_length=12)

    class Meta:
        model = CustomUser
        fields = ["email", "full_name", "role", "password"]

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Used when a user changes their own password.
    Requires current password for verification.
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=12)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value