"""
Tests for reporting API endpoints.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
)


@pytest.mark.django_db
class TestContractBurnReport:
    """Test contract burn report endpoint."""

    def test_contract_burn_report_basic(self, admin_user, admin_profile):
        """Test basic contract burn report returns correct structure."""
        # Create contract
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 28),  # 4 weeks
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        # Create deliverable with assignment
        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )
        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=admin_profile,
            budget_hours=Decimal("100.00"),
            is_lead=True,
        )

        # Add some time entries
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 5),
            hours=Decimal("25.00"),
        )

        # Call the endpoint
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/reports/contracts/{contract.id}/burn/")

        assert response.status_code == 200
        data = response.data

        # Check structure
        assert "contract_id" in data
        assert "buckets" in data
        assert "budget_hours" in data
        assert "assigned_budget_hours" in data
        assert "spent_hours" in data
        assert "is_over_budget" in data

        # Check values
        assert data["contract_id"] == contract.id
        assert data["budget_hours"] == "1000.00"
        assert data["assigned_budget_hours"] == "100.00"
        assert data["spent_hours"] == "25.00"
        assert data["is_over_budget"] is False

        # Check buckets
        assert len(data["buckets"]) > 0
        first_bucket = data["buckets"][0]
        assert "bucket" in first_bucket
        assert "budget_hours" in first_bucket
        assert "actual_hours" in first_bucket
        assert "cumulative_expected" in first_bucket
        assert "cumulative_actual" in first_bucket


@pytest.mark.django_db
class TestContractDeliverablesReport:
    """Test contract deliverables summary endpoint."""

    def test_contract_deliverables_summary(self, admin_user, admin_profile):
        """Test contract deliverables summary returns all deliverables."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        # Create two deliverables
        d1 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 1",
            status="in_progress",
        )
        d2 = Deliverable.objects.create(
            contract=contract,
            name="Deliverable 2",
            status="planned",
        )

        # Add assignments
        DeliverableAssignment.objects.create(
            deliverable=d1,
            staff=admin_profile,
            budget_hours=Decimal("50.00"),
            is_lead=True,
        )
        DeliverableAssignment.objects.create(
            deliverable=d2,
            staff=admin_profile,
            budget_hours=Decimal("75.00"),
            is_lead=True,
        )

        # Add time entry to d1
        DeliverableTimeEntry.objects.create(
            deliverable=d1,
            entry_date=date(2024, 1, 15),
            hours=Decimal("30.00"),
        )

        # Call the endpoint
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/reports/contracts/{contract.id}/deliverables/")

        assert response.status_code == 200
        data = response.data

        # Check structure
        assert "contract_id" in data
        assert "deliverables" in data
        assert len(data["deliverables"]) == 2

        # Check deliverable data
        deliverables = {d["id"]: d for d in data["deliverables"]}
        assert d1.id in deliverables
        assert d2.id in deliverables

        d1_data = deliverables[d1.id]
        assert d1_data["name"] == "Deliverable 1"
        assert d1_data["assigned_budget_hours"] == "50.00"
        assert d1_data["spent_hours"] == "30.00"
        assert d1_data["variance_hours"] == "-20.00"  # 30 - 50


@pytest.mark.django_db
class TestDeliverableBurnReport:
    """Test deliverable burn report endpoint."""

    def test_deliverable_burn_report(self, admin_user, admin_profile):
        """Test deliverable burn report returns correct structure."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            start_date=date(2024, 1, 1),
            due_date=date(2024, 1, 28),  # 4 weeks
            status="in_progress",
        )

        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=admin_profile,
            budget_hours=Decimal("80.00"),
            is_lead=True,
        )

        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 10),
            hours=Decimal("40.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/reports/deliverables/{deliverable.id}/burn/")

        assert response.status_code == 200
        data = response.data

        assert data["deliverable_id"] == deliverable.id
        assert data["name"] == "Test Deliverable"
        assert data["assigned_budget_hours"] == "80.00"
        assert data["spent_hours"] == "40.00"
        assert data["variance_hours"] == "-40.00"
        assert data["is_over_expected"] is False
        assert len(data["buckets"]) > 0


@pytest.mark.django_db
class TestDeliverableStatusHistory:
    """Test deliverable status history endpoint."""

    def test_status_history_ordered(self, admin_user, admin_profile):
        """Test status history is ordered by period_end."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        # Create status updates out of order
        _ = DeliverableStatusUpdate.objects.create(
            deliverable=deliverable,
            period_end=date(2024, 1, 14),
            status="in_progress",
            summary="Week 2 update",
        )
        _ = DeliverableStatusUpdate.objects.create(
            deliverable=deliverable,
            period_end=date(2024, 1, 7),
            status="in_progress",
            summary="Week 1 update",
        )
        _ = DeliverableStatusUpdate.objects.create(
            deliverable=deliverable,
            period_end=date(2024, 1, 21),
            status="complete",
            summary="Week 3 update - completed",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/reports/deliverables/{deliverable.id}/status-history/")

        assert response.status_code == 200
        data = response.data

        assert data["deliverable_id"] == deliverable.id
        assert len(data["status_history"]) == 3

        # Check ordering
        assert data["status_history"][0]["summary"] == "Week 1 update"
        assert data["status_history"][1]["summary"] == "Week 2 update"
        assert data["status_history"][2]["summary"] == "Week 3 update - completed"


@pytest.mark.django_db
class TestStaffTimeReport:
    """Test staff time report endpoint."""

    def test_staff_time_report_basic(self, admin_user, admin_profile, staff_profile):
        """Test staff time report returns empty results (time entries no longer track staff)."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        # Add time entries across different weeks
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 2),  # Week 1
            hours=Decimal("10.00"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 3),  # Week 1
            hours=Decimal("15.00"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 9),  # Week 2
            hours=Decimal("20.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/reports/staff/{staff_profile.id}/time/")

        assert response.status_code == 200
        data = response.data

        assert data["staff_id"] == staff_profile.id
        assert "buckets" in data
        # Time entries no longer track staff, so buckets should be empty
        assert len(data["buckets"]) == 0


@pytest.mark.django_db
class TestCSVExports:
    """Test CSV export endpoints."""

    def test_time_entries_csv_export(self, admin_user, admin_profile, staff_profile):
        """Test time entries CSV export with filters."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        # Create time entries
        _ = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 5),
            hours=Decimal("10.00"),
        )
        _ = DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 10),
            hours=Decimal("15.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test basic export
        response = client.get("/api/v1/exports/time-entries.csv")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "time_entries.csv" in response["Content-Disposition"]

        # Check CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) >= 3  # Header + 2 entries
        assert "Entry Date" in lines[0]
        assert "Hours" in lines[0]
        # Staff columns should not be in the CSV anymore
        assert "Staff ID" not in lines[0]
        assert "Staff Name" not in lines[0]

    def test_contract_burn_csv_export(self, admin_user, admin_profile):
        """Test contract burn CSV export."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 28),  # 4 weeks
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        DeliverableAssignment.objects.create(
            deliverable=deliverable,
            staff=admin_profile,
            budget_hours=Decimal("100.00"),
            is_lead=True,
        )

        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 5),
            hours=Decimal("25.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test export
        response = client.get(f"/api/v1/exports/contract-burn.csv?contract_id={contract.id}")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert f"contract_{contract.id}_burn.csv" in response["Content-Disposition"]

        # Check CSV content
        content = response.content.decode("utf-8")
        lines = content.strip().split("\n")
        assert len(lines) >= 2  # Header + at least 1 week
        assert "Week Ending" in lines[0]
        assert "Expected Hours" in lines[0]
        assert "Actual Hours" in lines[0]
        assert "Cumulative Expected" in lines[0]
        assert "Cumulative Actual" in lines[0]

    def test_contract_burn_csv_requires_contract_id(self, admin_user):
        """Test that contract burn CSV requires contract_id parameter."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/exports/contract-burn.csv")
        assert response.status_code == 400
        assert "contract_id" in str(response.data)

    def test_time_entries_csv_with_all_filters(self, admin_user, admin_profile):
        """Test time entries CSV with all filter parameters."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 15),
            hours=Decimal("10.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test with contract_id filter
        response = client.get(f"/api/v1/exports/time-entries.csv?contract_id={contract.id}")
        assert response.status_code == 200

        # Test with deliverable_id filter
        response = client.get(f"/api/v1/exports/time-entries.csv?deliverable_id={deliverable.id}")
        assert response.status_code == 200

        # Test with date range filters
        response = client.get("/api/v1/exports/time-entries.csv?entry_date_from=2024-01-01&entry_date_to=2024-01-31")
        assert response.status_code == 200

    def test_time_entries_csv_invalid_date_format(self, admin_user):
        """Test time entries CSV with invalid date format."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test invalid entry_date_from
        response = client.get("/api/v1/exports/time-entries.csv?entry_date_from=invalid-date")
        assert response.status_code == 400
        assert "Invalid entry_date_from format" in str(response.data)

        # Test invalid entry_date_to
        response = client.get("/api/v1/exports/time-entries.csv?entry_date_to=not-a-date")
        assert response.status_code == 400
        assert "Invalid entry_date_to format" in str(response.data)

    def test_contract_burn_csv_not_found(self, admin_user):
        """Test contract burn CSV with non-existent contract."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/exports/contract-burn.csv?contract_id=99999")
        assert response.status_code == 404


@pytest.mark.django_db
class TestReportingErrorCases:
    """Test error cases for reporting endpoints."""

    def test_contract_burn_not_found(self, admin_user):
        """Test contract burn report with non-existent contract."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/reports/contracts/99999/burn/")
        assert response.status_code == 404

    def test_contract_burn_invalid_bucket_type(self, admin_user, admin_profile):
        """Test contract burn report with invalid bucket type."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get(f"/api/v1/reports/contracts/{contract.id}/burn/?bucket=day")
        assert response.status_code == 400
        assert "Only 'week' bucket type is currently supported" in str(response.data)

    def test_contract_deliverables_not_found(self, admin_user):
        """Test contract deliverables report with non-existent contract."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/reports/contracts/99999/deliverables/")
        assert response.status_code == 404

    def test_deliverable_burn_not_found(self, admin_user):
        """Test deliverable burn report with non-existent deliverable."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/reports/deliverables/99999/burn/")
        assert response.status_code == 404

    def test_deliverable_burn_invalid_bucket_type(self, admin_user, admin_profile):
        """Test deliverable burn report with invalid bucket type."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get(f"/api/v1/reports/deliverables/{deliverable.id}/burn/?bucket=month")
        assert response.status_code == 400
        assert "Only 'week' bucket type is currently supported" in str(response.data)

    def test_deliverable_status_history_not_found(self, admin_user):
        """Test deliverable status history with non-existent deliverable."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/reports/deliverables/99999/status-history/")
        assert response.status_code == 404

    def test_staff_time_report_not_found(self, admin_user):
        """Test staff time report with non-existent staff."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/reports/staff/99999/time/")
        assert response.status_code == 404

    def test_staff_time_report_with_filters(self, admin_user, admin_profile, staff_profile):
        """Test staff time report with contract_id filter (returns empty since time entries don't track staff)."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 5),
            hours=Decimal("10.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test with contract_id filter - should return empty since time entries don't track staff
        response = client.get(f"/api/v1/reports/staff/{staff_profile.id}/time/?contract_id={contract.id}")
        assert response.status_code == 200
        assert len(response.data["buckets"]) == 0

    def test_staff_time_report_invalid_date_format(self, admin_user, staff_profile):
        """Test staff time report with invalid date format."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test invalid start_date
        response = client.get(f"/api/v1/reports/staff/{staff_profile.id}/time/?start_date=invalid")
        assert response.status_code == 400
        assert "Invalid start_date format" in str(response.data)

        # Test invalid end_date
        response = client.get(f"/api/v1/reports/staff/{staff_profile.id}/time/?end_date=not-a-date")
        assert response.status_code == 400
        assert "Invalid end_date format" in str(response.data)

    def test_staff_time_report_with_valid_date_filters(self, admin_user, staff_profile):
        """Test staff time report with valid date filters (returns empty since time entries don't track staff)."""
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            budget_hours=Decimal("1000.00"),
            status="active",
        )

        deliverable = Deliverable.objects.create(
            contract=contract,
            name="Test Deliverable",
            status="in_progress",
        )

        # Create entries in different date ranges
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 1, 5),
            hours=Decimal("10.00"),
        )
        DeliverableTimeEntry.objects.create(
            deliverable=deliverable,
            entry_date=date(2024, 2, 15),
            hours=Decimal("15.00"),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Test with start_date filter - should return empty since time entries don't track staff
        response = client.get(f"/api/v1/reports/staff/{staff_profile.id}/time/?start_date=2024-02-01")
        assert response.status_code == 200
        assert len(response.data["buckets"]) == 0

        # Test with end_date filter - should return empty since time entries don't track staff
        response = client.get(f"/api/v1/reports/staff/{staff_profile.id}/time/?end_date=2024-01-31")
        assert response.status_code == 200
        assert len(response.data["buckets"]) == 0


@pytest.mark.django_db
class TestWeekEndingEdgeCases:
    """Test edge cases for week ending date calculation."""

    def test_contract_burn_empty_buckets_fallback(self, admin_user):
        """Test that contract burn handles edge case where end_date is before first week ending."""
        # This tests the fallback in generate_weekly_buckets when
        # get_week_ending_date(start_date) > end_date
        # Example: start_date = Monday Jan 1, end_date = Tuesday Jan 2
        # First week ending would be Sunday Jan 7, which is > Jan 2
        contract = Contract.objects.create(
            start_date=date(2024, 1, 1),  # Monday
            end_date=date(2024, 1, 2),  # Tuesday (before first Sunday)
            budget_hours=Decimal("100.00"),
            status="active",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get(f"/api/v1/reports/contracts/{contract.id}/burn/")
        assert response.status_code == 200
        # Should have exactly one bucket due to fallback
        assert len(response.data["buckets"]) == 1
        # The bucket should be the week ending date for start_date (Sunday Jan 7)
        assert response.data["buckets"][0]["bucket"] == "2024-01-07"
