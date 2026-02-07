"""
Tests for bulk import endpoints.
"""

from decimal import Decimal

import pytest

from core.models import Contract, Deliverable, DeliverableTimeEntry, Staff, Task


@pytest.mark.django_db
class TestBulkImportPermissions:
    """Test bulk import permission requirements."""

    def test_bulk_import_requires_authentication(self, api_client):
        """Test that bulk import requires authentication."""
        response = api_client.post("/api/v1/bulk-import/", {}, format="json")
        assert response.status_code == 401

    def test_bulk_import_requires_admin_role(self, auth_client, staff_user, staff_profile):
        """Test that bulk import requires admin role."""
        client = auth_client(staff_user)
        response = client.post("/api/v1/bulk-import/", {}, format="json")
        assert response.status_code == 403

    def test_bulk_import_time_entries_requires_authentication(self, api_client):
        """Test that time entries import requires authentication."""
        response = api_client.post("/api/v1/bulk-import/time-entries/", {}, format="json")
        assert response.status_code == 401

    def test_bulk_import_time_entries_requires_admin_role(self, auth_client, manager_user, manager_profile):
        """Test that time entries import requires admin role."""
        client = auth_client(manager_user)
        response = client.post("/api/v1/bulk-import/time-entries/", {}, format="json")
        assert response.status_code == 403


@pytest.mark.django_db
class TestBulkImportSuccess:
    """Test successful bulk import scenarios."""

    def test_import_staff_only(self, auth_client, admin_user, admin_profile):
        """Test importing only staff data."""
        client = auth_client(admin_user)

        payload = {
            "staff": [
                {
                    "email": "john@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "role": "staff",
                    "status": "active",
                    "expected_hours_per_week": 40.0,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["staff_created"] == 1

        # Verify staff was created
        staff = Staff.objects.get(email="john@example.com")
        assert staff.first_name == "John"
        assert staff.last_name == "Doe"
        assert staff.role == "staff"

    def test_import_contracts_only(self, auth_client, admin_user, admin_profile):
        """Test importing only contract data."""
        client = auth_client(admin_user)

        payload = {
            "contracts": [
                {
                    "name": "Project A",
                    "client_name": "Client X",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "budget_hours": 1000,
                    "status": "active",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["contracts_created"] == 1

        # Verify contract was created
        contract = Contract.objects.get(name="Project A")
        assert contract.client_name == "Client X"
        assert contract.budget_hours == Decimal("1000")

    def test_import_full_data_hierarchy(self, auth_client, admin_user, admin_profile):
        """Test importing complete data hierarchy."""
        client = auth_client(admin_user)

        payload = {
            "staff": [
                {
                    "email": "jane@example.com",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "role": "staff",
                    "status": "active",
                    "expected_hours_per_week": 40.0,
                }
            ],
            "contracts": [
                {
                    "name": "Project B",
                    "client_name": "Client Y",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "budget_hours": 2000,
                    "status": "active",
                }
            ],
            "deliverables": [
                {
                    "contract_name": "Project B",
                    "contract_client_name": "Client Y",
                    "name": "Deliverable 1",
                    "charge_code": "PROJ_B_D1",
                    "budget_hours": 500,
                    "target_completion_date": "2024-06-30",
                    "status": "in_progress",
                }
            ],
            "tasks": [
                {
                    "deliverable_name": "Deliverable 1",
                    "title": "Task 1",
                    "budget_hours": 100,
                    "status": "todo",
                    "assignee_email": "jane@example.com",
                }
            ],
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["staff_created"] == 1
        assert response.data["stats"]["contracts_created"] == 1
        assert response.data["stats"]["deliverables_created"] == 1
        assert response.data["stats"]["tasks_created"] == 1

        # Verify all entities were created
        staff = Staff.objects.get(email="jane@example.com")
        contract = Contract.objects.get(name="Project B")
        deliverable = Deliverable.objects.get(name="Deliverable 1")
        task = Task.objects.get(title="Task 1")

        assert deliverable.contract == contract
        assert task.deliverable == deliverable
        assert task.assignee == staff

    def test_import_task_without_assignee(self, auth_client, admin_user, admin_profile):
        """Test importing task without assignee."""
        client = auth_client(admin_user)

        # Create contract and deliverable first
        contract = Contract.objects.create(
            name="Project C",
            client_name="Client Z",
            start_date="2024-01-01",
            end_date="2024-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable 2",
            status="planned",
        )

        payload = {
            "tasks": [
                {
                    "deliverable_name": "Deliverable 2",
                    "title": "Unassigned Task",
                    "budget_hours": None,
                    "status": "todo",
                    "assignee_email": None,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["tasks_created"] == 1

        task = Task.objects.get(title="Unassigned Task")
        assert task.assignee is None
        assert task.budget_hours == Decimal("0")


@pytest.mark.django_db
class TestBulkImportTimeEntries:
    """Test bulk import of time entries."""

    def test_import_time_entries_success(self, auth_client, admin_user, admin_profile):
        """Test successful import of time entries."""
        client = auth_client(admin_user)

        # Create deliverable first
        contract = Contract.objects.create(
            name="Project D",
            start_date="2024-01-01",
            end_date="2024-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable 3",
            status="in_progress",
        )

        payload = {
            "time_entries": [
                {
                    "deliverable_name": "Deliverable 3",
                    "entry_date": "2024-01-15",
                    "hours": 8.5,
                    "note": "Work completed",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["time_entries_created"] == 1

        # Verify time entry was created
        entry = DeliverableTimeEntry.objects.get(note="Work completed")
        assert entry.hours == Decimal("8.5")
        assert str(entry.entry_date) == "2024-01-15"

    def test_import_multiple_time_entries(self, auth_client, admin_user, admin_profile):
        """Test importing multiple time entries."""
        client = auth_client(admin_user)

        # Create deliverable
        contract = Contract.objects.create(
            name="Project E",
            start_date="2024-01-01",
            end_date="2024-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable 4",
            status="in_progress",
        )

        payload = {
            "time_entries": [
                {
                    "deliverable_name": "Deliverable 4",
                    "entry_date": "2024-01-15",
                    "hours": 8.0,
                    "note": "Day 1",
                },
                {
                    "deliverable_name": "Deliverable 4",
                    "entry_date": "2024-01-16",
                    "hours": 7.5,
                    "note": "Day 2",
                },
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["time_entries_created"] == 2

        assert DeliverableTimeEntry.objects.count() == 2


@pytest.mark.django_db
class TestBulkImportErrors:
    """Test error handling in bulk import."""

    def test_import_deliverable_with_nonexistent_contract(self, auth_client, admin_user, admin_profile):
        """Test that importing deliverable with non-existent contract fails."""
        client = auth_client(admin_user)

        payload = {
            "deliverables": [
                {
                    "contract_name": "Nonexistent Contract",
                    "contract_client_name": "Nonexistent Client",
                    "name": "Deliverable X",
                    "status": "planned",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 400
        assert response.data["success"] is False
        assert "Contract not found" in response.data["error"]

    def test_import_task_with_nonexistent_deliverable(self, auth_client, admin_user, admin_profile):
        """Test that importing task with non-existent deliverable fails."""
        client = auth_client(admin_user)

        payload = {
            "tasks": [
                {
                    "deliverable_name": "Nonexistent Deliverable",
                    "title": "Task X",
                    "status": "todo",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 400
        assert response.data["success"] is False
        assert "Deliverable not found" in response.data["error"]

    def test_import_task_with_nonexistent_assignee(self, auth_client, admin_user, admin_profile):
        """Test that importing task with non-existent assignee fails."""
        client = auth_client(admin_user)

        # Create contract and deliverable
        contract = Contract.objects.create(
            name="Project F",
            start_date="2024-01-01",
            end_date="2024-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable 5",
            status="planned",
        )

        payload = {
            "tasks": [
                {
                    "deliverable_name": "Deliverable 5",
                    "title": "Task Y",
                    "status": "todo",
                    "assignee_email": "nonexistent@example.com",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 400
        assert response.data["success"] is False
        assert "Staff not found" in response.data["error"]

    def test_import_time_entry_with_nonexistent_deliverable(self, auth_client, admin_user, admin_profile):
        """Test that importing time entry with non-existent deliverable fails."""
        client = auth_client(admin_user)

        payload = {
            "time_entries": [
                {
                    "deliverable_name": "Nonexistent Deliverable",
                    "entry_date": "2024-01-15",
                    "hours": 8.0,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 400
        assert response.data["success"] is False
        assert "Deliverable not found" in response.data["error"]


@pytest.mark.django_db
class TestBulkImportIdempotency:
    """Test idempotency of bulk import."""

    def test_reimport_staff_does_not_create_duplicates(self, auth_client, admin_user, admin_profile):
        """Test that re-importing the same staff doesn't create duplicates."""
        client = auth_client(admin_user)

        payload = {
            "staff": [
                {
                    "email": "unique@example.com",
                    "first_name": "Unique",
                    "last_name": "User",
                    "role": "staff",
                    "status": "active",
                    "expected_hours_per_week": 40.0,
                }
            ]
        }

        # First import
        response1 = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response1.status_code == 200
        assert response1.data["stats"]["staff_created"] == 1

        # Second import (should not create duplicate)
        response2 = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response2.status_code == 200
        assert response2.data["stats"]["staff_created"] == 0

        # Verify only one staff exists
        assert Staff.objects.filter(email="unique@example.com").count() == 1

    def test_reimport_contract_does_not_create_duplicates(self, auth_client, admin_user, admin_profile):
        """Test that re-importing the same contract doesn't create duplicates."""
        client = auth_client(admin_user)

        payload = {
            "contracts": [
                {
                    "name": "Unique Project",
                    "client_name": "Unique Client",
                    "start_date": "2024-01-01",
                    "end_date": "2024-12-31",
                    "budget_hours": 1000,
                    "status": "active",
                }
            ]
        }

        # First import
        response1 = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response1.status_code == 200
        assert response1.data["stats"]["contracts_created"] == 1

        # Second import (should not create duplicate)
        response2 = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response2.status_code == 200
        assert response2.data["stats"]["contracts_created"] == 0

        # Verify only one contract exists
        assert Contract.objects.filter(name="Unique Project", client_name="Unique Client").count() == 1

    def test_atomic_rollback_on_error(self, auth_client, admin_user, admin_profile):
        """Test that errors cause complete rollback (atomic transaction)."""
        client = auth_client(admin_user)

        initial_staff_count = Staff.objects.count()

        payload = {
            "staff": [
                {
                    "email": "valid1@example.com",
                    "first_name": "Valid",
                    "last_name": "User1",
                    "role": "staff",
                    "status": "active",
                    "expected_hours_per_week": 40.0,
                }
            ],
            "tasks": [
                {
                    "deliverable_name": "Nonexistent Deliverable",  # This will cause error
                    "title": "Task",
                    "status": "todo",
                }
            ],
        }

        response = client.post("/api/v1/bulk-import/", payload, format="json")
        assert response.status_code == 400

        # Verify no staff was created (rollback occurred)
        assert Staff.objects.count() == initial_staff_count
        assert not Staff.objects.filter(email="valid1@example.com").exists()
