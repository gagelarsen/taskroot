import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Contract, Deliverable, Staff


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client):
    def _auth(user):
        api_client.force_authenticate(user=user)
        return api_client

    return _auth


@pytest.fixture
def staff_user(db):
    """Create a Django user for staff role."""
    return User.objects.create_user(username="staff_user", password="testpass123")


@pytest.fixture
def staff_profile(db, staff_user):
    """Create a Staff profile with 'staff' role linked to staff_user."""
    return Staff.objects.create(
        user=staff_user, email="staff@example.com", first_name="Staff", last_name="User", role="staff", status="active"
    )


@pytest.fixture
def manager_user(db):
    """Create a Django user for manager role."""
    return User.objects.create_user(username="manager_user", password="testpass123")


@pytest.fixture
def manager_profile(db, manager_user):
    """Create a Staff profile with 'manager' role linked to manager_user."""
    return Staff.objects.create(
        user=manager_user,
        email="manager@example.com",
        first_name="Manager",
        last_name="User",
        role="manager",
        status="active",
    )


@pytest.fixture
def other_staff_profile(db):
    """Create another Staff profile (without a user) for testing permissions."""
    return Staff.objects.create(
        email="other@example.com", first_name="Other", last_name="Staff", role="staff", status="active"
    )


@pytest.fixture
def contract(db):
    """Create a test contract."""
    return Contract.objects.create(
        start_date="2026-01-01", end_date="2026-12-31", budget_hours_total=100.0, status="active"
    )


@pytest.fixture
def deliverable(db, contract):
    """Create a test deliverable."""
    return Deliverable.objects.create(contract=contract, name="Test Deliverable", status="planned")
