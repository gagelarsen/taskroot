"""
Tests for bulk import endpoints.
"""

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from core.models import Contract, ContractInvoiceUpdate, Deliverable, DeliverableTimeEntry, Staff, Task


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

    def test_bulk_import_invoices_requires_authentication(self, api_client):
        """Test that invoice updates import requires authentication."""
        response = api_client.post("/api/v1/bulk-import/invoices/", {}, format="json")
        assert response.status_code == 401

    def test_bulk_import_invoices_requires_admin_role(self, auth_client, manager_user, manager_profile):
        """Test that invoice updates import requires admin role."""
        client = auth_client(manager_user)
        response = client.post("/api/v1/bulk-import/invoices/", {}, format="json")
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
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
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
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
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
                    "target_completion_date": "2026-06-30",
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
            start_date="2026-01-01",
            end_date="2026-12-31",
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
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable 3",
            charge_code="TEST_CHARGE_CODE",
            status="in_progress",
        )

        payload = {
            "time_entries": [
                {
                    "charge_code": "TEST_CHARGE_CODE",
                    "entry_date": "2026-01-15",
                    "hours": 8.5,
                    "note": "Work completed",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["time_entries_created"] == 1
        assert response.data["stats"]["time_entries_skipped"] == 0
        assert response.data["stats"]["time_entries_failed"] == 0

        # Verify time entry was created
        entry = DeliverableTimeEntry.objects.get(note="Work completed")
        assert entry.hours == Decimal("8.5")
        assert str(entry.entry_date) == "2026-01-15"

    def test_import_time_entries_with_duplicate_date(self, auth_client, admin_user, admin_profile):
        """Test that duplicate entries (same charge_code + date) are skipped with warning."""
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Project E",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 4",
            charge_code="DUP_TEST",
            status="in_progress",
        )

        # Create existing time entry
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date="2026-01-15",
            hours=Decimal("5.0"),
            note="Existing entry",
        )

        payload = {
            "time_entries": [
                {
                    "charge_code": "DUP_TEST",
                    "entry_date": "2026-01-15",
                    "hours": 8.5,
                    "note": "Duplicate entry",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True  # Success because no failures
        assert response.data["stats"]["time_entries_created"] == 0
        assert response.data["stats"]["time_entries_skipped"] == 1
        assert response.data["stats"]["time_entries_failed"] == 0
        assert "warnings" in response.data
        assert len(response.data["warnings"]) == 1
        assert "already exists" in response.data["warnings"][0]

        # Verify only the original entry exists
        assert DeliverableTimeEntry.objects.filter(deliverable=deliverable).count() == 1
        entry = DeliverableTimeEntry.objects.get(deliverable=deliverable)
        assert entry.hours == Decimal("5.0")
        assert entry.note == "Existing entry"

    def test_import_time_entries_with_nonexistent_charge_code(self, auth_client, admin_user, admin_profile):
        """Test that entries with non-existent charge codes are skipped with warning."""
        client = auth_client(admin_user)

        payload = {
            "time_entries": [
                {
                    "charge_code": "NONEXISTENT_CODE",
                    "entry_date": "2026-01-15",
                    "hours": 8.5,
                    "note": "Invalid charge code",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True  # Success because no failures
        assert response.data["stats"]["time_entries_created"] == 0
        assert response.data["stats"]["time_entries_skipped"] == 1
        assert response.data["stats"]["time_entries_failed"] == 0
        assert "warnings" in response.data
        assert len(response.data["warnings"]) == 1
        assert "not found" in response.data["warnings"][0]
        assert "NONEXISTENT_CODE" in response.data["warnings"][0]

    def test_import_time_entries_mixed_valid_and_invalid(self, auth_client, admin_user, admin_profile):
        """Test that valid entries are imported even when some are invalid."""
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Project F",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 5",
            charge_code="MIXED_TEST",
            status="in_progress",
        )

        # Create existing entry for duplicate test
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date="2026-01-10",
            hours=Decimal("3.0"),
            note="Existing",
        )

        payload = {
            "time_entries": [
                {
                    "charge_code": "MIXED_TEST",
                    "entry_date": "2026-01-15",
                    "hours": 8.5,
                    "note": "Valid entry 1",
                },
                {
                    "charge_code": "NONEXISTENT",
                    "entry_date": "2026-01-16",
                    "hours": 5.0,
                    "note": "Invalid charge code",
                },
                {
                    "charge_code": "MIXED_TEST",
                    "entry_date": "2026-01-10",
                    "hours": 7.0,
                    "note": "Duplicate date",
                },
                {
                    "charge_code": "MIXED_TEST",
                    "entry_date": "2026-01-17",
                    "hours": 6.0,
                    "note": "Valid entry 2",
                },
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["time_entries_created"] == 2  # Two valid entries
        assert response.data["stats"]["time_entries_skipped"] == 2  # One nonexistent, one duplicate
        assert response.data["stats"]["time_entries_failed"] == 0
        assert "warnings" in response.data
        assert len(response.data["warnings"]) == 2

        # Verify the valid entries were created
        assert DeliverableTimeEntry.objects.filter(deliverable=deliverable).count() == 3  # 1 existing + 2 new
        assert DeliverableTimeEntry.objects.filter(note="Valid entry 1").exists()
        assert DeliverableTimeEntry.objects.filter(note="Valid entry 2").exists()

    def test_import_multiple_time_entries(self, auth_client, admin_user, admin_profile):
        """Test importing multiple time entries."""
        client = auth_client(admin_user)

        # Create deliverable
        contract = Contract.objects.create(
            name="Project E",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable 4",
            status="in_progress",
            charge_code="MULTI_TEST",
        )

        payload = {
            "time_entries": [
                {
                    "charge_code": "MULTI_TEST",
                    "entry_date": "2026-01-15",
                    "hours": 8.0,
                    "note": "Day 1",
                },
                {
                    "charge_code": "MULTI_TEST",
                    "entry_date": "2026-01-16",
                    "hours": 7.5,
                    "note": "Day 2",
                },
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["stats"]["time_entries_created"] == 2

        assert DeliverableTimeEntry.objects.count() == 2

    def test_import_time_entries_from_csv_success(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="CSV Project",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="CSV Deliverable",
            charge_code="CSV_CODE",
            status="in_progress",
        )

        csv_content = (
            "GROUP,RESOURCE ID,CHARGE CODE,CHARGE CODE DESCRIPTION,HOURS\n"
            "Administration,,CSV_CODE,Admin tasks,2.5\n"
            "Administration,Total,CSV_CODE,Summary row,10.0\n"
            "Administration,,CSV_CODE,Invalid value,not-a-number\n"
            "Administration,,CSV_CODE,Zero hours,0\n"
            ",,,Missing charge,5\n"
        )
        csv_file = SimpleUploadedFile("charge_codes.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file, "entry_date": "2026-02-01"},
            format="multipart",
        )

        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["time_entries_created"] == 1
        assert response.data["stats"]["time_entries_skipped"] == 0
        assert response.data["stats"]["time_entries_failed"] == 0

        entry = DeliverableTimeEntry.objects.get(deliverable=deliverable)
        assert str(entry.entry_date) == "2026-02-01"
        assert entry.hours == Decimal("2.5")
        assert entry.note == "Administration - Admin tasks"

    def test_import_time_entries_from_csv_uses_entry_date_column(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="CSV Date Project",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="CSV Date Deliverable",
            charge_code="CSV_DATE_CODE",
            status="in_progress",
        )

        csv_content = "CHARGE CODE,ENTRY DATE,HOURS\n" "CSV_DATE_CODE,2026-03-05,3.0\n"
        csv_file = SimpleUploadedFile(
            "charge_codes_with_dates.csv", csv_content.encode("utf-8"), content_type="text/csv"
        )

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file},
            format="multipart",
        )

        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["time_entries_created"] == 1
        assert DeliverableTimeEntry.objects.filter(entry_date="2026-03-05", hours=Decimal("3.0")).exists()

    def test_import_time_entries_from_csv_missing_required_columns(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        csv_content = "GROUP,RESOURCE ID,HOURS\nAdministration,,3.0\n"
        csv_file = SimpleUploadedFile("invalid_columns.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file, "entry_date": "2026-02-01"},
            format="multipart",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "CHARGE CODE and HOURS" in response.data["error"]

    def test_import_time_entries_from_csv_requires_entry_date_when_not_in_file(
        self, auth_client, admin_user, admin_profile
    ):
        client = auth_client(admin_user)

        csv_content = "CHARGE CODE,HOURS\nCODE_A,2.0\n"
        csv_file = SimpleUploadedFile("missing_entry_date.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file},
            format="multipart",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "entry_date is required" in response.data["error"]

    def test_import_time_entries_from_csv_rejects_invalid_encoding(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        csv_file = SimpleUploadedFile("bad_encoding.csv", b"\x80\x81\x82", content_type="text/csv")

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file, "entry_date": "2026-02-01"},
            format="multipart",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "UTF-8" in response.data["error"]

    def test_import_time_entries_from_csv_rejects_empty_file(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        csv_file = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file, "entry_date": "2026-02-01"},
            format="multipart",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "empty" in response.data["error"].lower()

    def test_import_time_entries_from_csv_rejects_when_no_rows_are_importable(
        self, auth_client, admin_user, admin_profile
    ):
        client = auth_client(admin_user)

        csv_content = "CHARGE CODE,HOURS\n" "CODE_A,0\n" "CODE_A,not-a-number\n"
        csv_file = SimpleUploadedFile("no_importable_rows.csv", csv_content.encode("utf-8"), content_type="text/csv")

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            {"file": csv_file, "entry_date": "2026-02-01"},
            format="multipart",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "No importable time entries" in response.data["error"]


@pytest.mark.django_db
class TestBulkImportInvoiceUpdates:
    """Test bulk import of contract invoice updates."""

    def test_import_invoice_updates_success(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Invoice Contract",
            contract_number="TM-INV-001",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            contract_amount=Decimal("50000.00"),
            contract_type="time_and_materials",
            status="active",
        )

        payload = {
            "invoice_updates": [
                {
                    "contract_number": "TM-INV-001",
                    "invoice_date": "2026-01-31",
                    "amount": 12500,
                    "note": "January invoice",
                },
                {
                    "contract_id": contract.id,
                    "invoice_date": "2026-02-28",
                    "amount": 10000,
                    "note": "February invoice",
                },
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["invoice_updates_created"] == 2
        assert response.data["stats"]["invoice_updates_skipped"] == 0
        assert response.data["stats"]["invoice_updates_failed"] == 0

        assert ContractInvoiceUpdate.objects.filter(contract=contract).count() == 2

    def test_import_invoice_updates_skips_missing_contract(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        payload = {
            "invoice_updates": [
                {
                    "contract_number": "DOES-NOT-EXIST",
                    "invoice_date": "2026-01-31",
                    "amount": 12500,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["invoice_updates_created"] == 0
        assert response.data["stats"]["invoice_updates_skipped"] == 1
        assert response.data["stats"]["invoice_updates_failed"] == 0
        assert "warnings" in response.data

    def test_import_invoice_updates_skips_duplicates(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Dup Contract",
            contract_number="TM-INV-DUP",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            contract_amount=Decimal("50000.00"),
            contract_type="time_and_materials",
            status="active",
        )

        ContractInvoiceUpdate.objects.create(
            contract=contract,
            invoice_date="2026-01-31",
            amount=Decimal("1000.00"),
            note="Existing",
        )

        payload = {
            "invoice_updates": [
                {
                    "contract_number": "TM-INV-DUP",
                    "invoice_date": "2026-01-31",
                    "amount": 1000,
                    "note": "Duplicate",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["invoice_updates_created"] == 0
        assert response.data["stats"]["invoice_updates_skipped"] == 1
        assert response.data["stats"]["invoice_updates_failed"] == 0
        assert ContractInvoiceUpdate.objects.filter(contract=contract).count() == 1

    def test_import_invoice_updates_reports_validation_errors(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        payload = {
            "invoice_updates": [
                {
                    "contract_number": "TM-INV-001",
                    "amount": 100,
                },
                {
                    "contract_number": "TM-INV-001",
                    "invoice_date": "2026-01-31",
                    "amount": 0,
                },
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is False
        assert response.data["stats"]["invoice_updates_created"] == 0
        assert response.data["stats"]["invoice_updates_failed"] == 2
        assert "errors" in response.data


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
            start_date="2026-01-01",
            end_date="2026-12-31",
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
                    "entry_date": "2026-01-15",
                    "hours": 8.0,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200


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
                    "start_date": "2026-01-01",
                    "end_date": "2026-12-31",
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


@pytest.mark.django_db
class TestBulkImportCoverageEdges:
    """Target edge branches to maximize coverage for bulk import endpoints."""

    def test_time_entries_import_missing_required_fields(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        payload = {
            "time_entries": [
                {"entry_date": "2026-01-15", "hours": 2.5, "note": "Missing charge code"},
                {"charge_code": "SOME_CODE", "hours": 1.5, "note": "Missing entry date"},
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is False
        assert response.data["stats"]["time_entries_failed"] == 2
        assert "errors" in response.data
        assert any("Missing charge_code" in error for error in response.data["errors"])
        assert any("Missing entry_date" in error for error in response.data["errors"])

    def test_time_entries_import_create_exception_is_reported(
        self, auth_client, admin_user, admin_profile, monkeypatch
    ):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Project Coverage",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )
        Deliverable.objects.create(
            contract=contract,
            name="Deliverable Coverage",
            charge_code="COVERAGE_CODE",
            status="in_progress",
        )

        def raise_create_error(*args, **kwargs):
            raise RuntimeError("forced create failure")

        monkeypatch.setattr(DeliverableTimeEntry.objects, "create", raise_create_error)

        payload = {
            "time_entries": [
                {
                    "charge_code": "COVERAGE_CODE",
                    "entry_date": "2026-01-20",
                    "hours": 4,
                    "note": "Will fail",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/time-entries/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is False
        assert response.data["stats"]["time_entries_failed"] == 1
        assert "errors" in response.data
        assert "forced create failure" in response.data["errors"][0]

    def test_time_entries_import_non_mapping_payload_hits_outer_exception(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        response = client.post(
            "/api/v1/bulk-import/time-entries/",
            ["not", "a", "mapping"],
            format="json",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "Unexpected error" in response.data["error"]

    def test_invoice_updates_import_finds_contract_by_name_and_client(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Named Contract",
            client_name="Client Lookup",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )

        payload = {
            "invoice_updates": [
                {
                    "contract_name": "Named Contract",
                    "contract_client_name": "Client Lookup",
                    "invoice_date": "2026-03-01",
                    "amount": 2500,
                    "note": "Lookup path",
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["invoice_updates_created"] == 1
        assert ContractInvoiceUpdate.objects.filter(contract=contract, amount=Decimal("2500")).exists()

    def test_invoice_updates_import_reports_missing_and_invalid_amount(self, auth_client, admin_user, admin_profile):
        client = auth_client(admin_user)

        payload = {
            "invoice_updates": [
                {
                    "contract_number": "TM-INV-001",
                    "invoice_date": "2026-01-31",
                },
                {
                    "contract_number": "TM-INV-001",
                    "invoice_date": "2026-01-31",
                    "amount": "not-a-number",
                },
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is False
        assert response.data["stats"]["invoice_updates_failed"] == 2
        assert any("Missing amount" in error for error in response.data["errors"])
        assert any("Invalid amount" in error for error in response.data["errors"])

    def test_invoice_updates_import_missing_contract_identifiers_returns_not_found_warning(
        self, auth_client, admin_user, admin_profile
    ):
        client = auth_client(admin_user)

        payload = {
            "invoice_updates": [
                {
                    "invoice_date": "2026-01-31",
                    "amount": 100,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert response.data["stats"]["invoice_updates_created"] == 0
        assert response.data["stats"]["invoice_updates_skipped"] == 1
        assert "warnings" in response.data

    def test_invoice_updates_import_create_exception_is_reported(
        self, auth_client, admin_user, admin_profile, monkeypatch
    ):
        client = auth_client(admin_user)

        contract = Contract.objects.create(
            name="Invoice Create Failure",
            contract_number="INV-FAIL",
            start_date="2026-01-01",
            end_date="2026-12-31",
            budget_hours=1000,
            status="active",
        )

        def raise_create_error(*args, **kwargs):
            raise RuntimeError("forced invoice create failure")

        monkeypatch.setattr(ContractInvoiceUpdate.objects, "create", raise_create_error)

        payload = {
            "invoice_updates": [
                {
                    "contract_id": contract.id,
                    "invoice_date": "2026-03-15",
                    "amount": 1200,
                }
            ]
        }

        response = client.post("/api/v1/bulk-import/invoices/", payload, format="json")
        assert response.status_code == 200
        assert response.data["success"] is False
        assert response.data["stats"]["invoice_updates_failed"] == 1
        assert "forced invoice create failure" in response.data["errors"][0]

    def test_invoice_updates_import_non_mapping_payload_hits_outer_exception(
        self, auth_client, admin_user, admin_profile
    ):
        client = auth_client(admin_user)

        response = client.post(
            "/api/v1/bulk-import/invoices/",
            ["not", "a", "mapping"],
            format="json",
        )

        assert response.status_code == 400
        assert response.data["success"] is False
        assert "Unexpected error" in response.data["error"]
