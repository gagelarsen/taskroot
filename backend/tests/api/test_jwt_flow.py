"""
Tests for JWT authentication flow.

Covers:
- Obtaining JWT tokens with valid credentials
- Refreshing JWT tokens
- Verifying JWT tokens
- Unauthenticated requests return 401
- Invalid credentials return 401
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Staff


@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    return APIClient()


@pytest.fixture
def test_user_with_staff(db):
    """Create a test user with a staff profile."""
    user = User.objects.create_user(username="testuser", password="testpass123")
    Staff.objects.create(
        user=user, email="testuser@example.com", first_name="Test", last_name="User", role="staff", status="active"
    )
    return user


@pytest.mark.django_db
class TestJWTFlow:
    """Test JWT authentication flow."""

    def test_obtain_token_with_valid_credentials(self, api_client, test_user_with_staff):
        """Test obtaining JWT token with valid username and password."""
        response = api_client.post(
            "/api/v1/auth/token/", {"username": "testuser", "password": "testpass123"}, format="json"
        )

        assert response.status_code == 200, response.data
        assert "access" in response.data
        assert "refresh" in response.data
        assert isinstance(response.data["access"], str)
        assert isinstance(response.data["refresh"], str)
        assert len(response.data["access"]) > 0
        assert len(response.data["refresh"]) > 0

    def test_obtain_token_with_invalid_credentials(self, api_client, test_user_with_staff):
        """Test that invalid credentials return 401."""
        response = api_client.post(
            "/api/v1/auth/token/", {"username": "testuser", "password": "wrongpassword"}, format="json"
        )

        assert response.status_code == 401, response.data

    def test_obtain_token_with_nonexistent_user(self, api_client):
        """Test that nonexistent user returns 401."""
        response = api_client.post(
            "/api/v1/auth/token/", {"username": "nonexistent", "password": "testpass123"}, format="json"
        )

        assert response.status_code == 401, response.data

    def test_refresh_token(self, api_client, test_user_with_staff):
        """Test refreshing JWT token with valid refresh token."""
        # First, obtain tokens
        token_response = api_client.post(
            "/api/v1/auth/token/", {"username": "testuser", "password": "testpass123"}, format="json"
        )
        refresh_token = token_response.data["refresh"]

        # Now refresh
        refresh_response = api_client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_token}, format="json")

        assert refresh_response.status_code == 200, refresh_response.data
        assert "access" in refresh_response.data
        assert isinstance(refresh_response.data["access"], str)
        assert len(refresh_response.data["access"]) > 0

    def test_refresh_token_with_invalid_token(self, api_client):
        """Test that invalid refresh token returns 401."""
        response = api_client.post("/api/v1/auth/token/refresh/", {"refresh": "invalid.token.here"}, format="json")

        assert response.status_code == 401, response.data

    def test_verify_token(self, api_client, test_user_with_staff):
        """Test verifying a valid JWT token."""
        # First, obtain tokens
        token_response = api_client.post(
            "/api/v1/auth/token/", {"username": "testuser", "password": "testpass123"}, format="json"
        )
        access_token = token_response.data["access"]

        # Now verify
        verify_response = api_client.post("/api/v1/auth/token/verify/", {"token": access_token}, format="json")

        assert verify_response.status_code == 200, verify_response.data

    def test_verify_invalid_token(self, api_client):
        """Test that invalid token verification returns 401."""
        response = api_client.post("/api/v1/auth/token/verify/", {"token": "invalid.token.here"}, format="json")

        assert response.status_code == 401, response.data

    def test_unauthenticated_request_returns_401(self, api_client):
        """Test that unauthenticated POST requests to protected endpoints return 401."""
        # Try to POST to a protected endpoint without authentication
        # POST requests require authentication even if GET is allowed
        response = api_client.post("/api/v1/tasks/", {}, format="json")

        assert response.status_code == 401, response.data
        assert "detail" in response.data

    def test_authenticated_request_with_valid_token(self, api_client, test_user_with_staff):
        """Test that authenticated requests with valid token succeed."""
        # Obtain token
        token_response = api_client.post(
            "/api/v1/auth/token/", {"username": "testuser", "password": "testpass123"}, format="json"
        )
        access_token = token_response.data["access"]

        # Make authenticated request
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get("/api/v1/staff/")

        assert response.status_code == 200, response.data

    def test_authenticated_request_with_invalid_token(self, api_client):
        """Test that requests with invalid token return 401."""
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid.token.here")
        response = api_client.get("/api/v1/staff/")

        assert response.status_code == 401, response.data
