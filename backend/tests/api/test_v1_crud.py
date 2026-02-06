import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from core.models import Staff


@pytest.fixture()
def admin_user(db):
    """Create an admin user for CRUD tests."""
    user = User.objects.create_user(username="admin", password="testpass123")
    Staff.objects.create(
        user=user, email="admin@example.com", first_name="Admin", last_name="User", role="admin", status="active"
    )
    return user


@pytest.fixture()
def api_client(admin_user):
    """Return an authenticated API client with admin privileges."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture()
def staff_payload():
    return {
        "email": "user@example.com",
        "first_name": "A",
        "last_name": "User",
        "status": "active",
        "role": "staff",
    }


@pytest.fixture()
def contract_payload():
    return {
        "start_date": "2026-01-01",
        "end_date": "2026-12-31",
        "budget_hours": "100.0",
        "status": "active",
    }


@pytest.mark.django_db
class TestV1CrudSmoke:
    def test_staff_create_and_list(self, api_client, staff_payload):
        r = api_client.post("/api/v1/staff/", staff_payload, format="json")
        assert r.status_code == 201, r.data
        staff_id = r.data["id"]

        r = api_client.get("/api/v1/staff/")
        assert r.status_code == 200
        assert "results" in r.data
        assert any(item["id"] == staff_id for item in r.data["results"])

    def test_contract_create_and_list(self, api_client, contract_payload):
        r = api_client.post("/api/v1/contracts/", contract_payload, format="json")
        assert r.status_code == 201, r.data
        contract_id = r.data["id"]

        r = api_client.get("/api/v1/contracts/")
        assert r.status_code == 200
        assert any(item["id"] == contract_id for item in r.data["results"])

    def test_deliverable_create_and_list(self, api_client, contract_payload):
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        r = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        )
        assert r.status_code == 201, r.data
        deliverable_id = r.data["id"]

        r = api_client.get("/api/v1/deliverables/")
        assert r.status_code == 200
        assert any(item["id"] == deliverable_id for item in r.data["results"])

    def test_deliverable_with_charge_code(self, api_client, contract_payload):
        """Test creating and updating deliverable with charge_code field."""
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data

        # Create deliverable with charge_code
        r = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "charge_code": "CC-123", "status": "planned"},
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["charge_code"] == "CC-123"
        deliverable_id = r.data["id"]

        # Update charge_code
        r = api_client.patch(
            f"/api/v1/deliverables/{deliverable_id}/",
            {"charge_code": "CC-456"},
            format="json",
        )
        assert r.status_code == 200, r.data
        assert r.data["charge_code"] == "CC-456"

        # Verify charge_code is returned in list
        r = api_client.get("/api/v1/deliverables/")
        assert r.status_code == 200
        deliverable = next(item for item in r.data["results"] if item["id"] == deliverable_id)
        assert deliverable["charge_code"] == "CC-456"

    def test_task_create_without_assignee_and_list(self, api_client, contract_payload):
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        r = api_client.post(
            "/api/v1/tasks/",
            {"deliverable": deliverable["id"], "title": "T1", "planned_hours": "2.0", "status": "todo"},
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["assignee"] is None

        task_id = r.data["id"]
        r = api_client.get("/api/v1/tasks/")
        assert r.status_code == 200
        assert any(item["id"] == task_id for item in r.data["results"])

    def test_assignment_create_and_list(self, api_client, contract_payload, staff_payload):
        staff = api_client.post("/api/v1/staff/", staff_payload, format="json").data
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        r = api_client.post(
            "/api/v1/deliverable-assignments/",
            {"deliverable": deliverable["id"], "staff": staff["id"], "expected_hours": "5.0", "is_lead": True},
            format="json",
        )
        assert r.status_code == 201, r.data
        assignment_id = r.data["id"]

        r = api_client.get("/api/v1/deliverable-assignments/")
        assert r.status_code == 200
        assert any(item["id"] == assignment_id for item in r.data["results"])

    def test_time_entry_create_and_list(self, api_client, contract_payload, staff_payload):
        _ = api_client.post("/api/v1/staff/", staff_payload, format="json").data
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        r = api_client.post(
            "/api/v1/deliverable-time-entries/",
            {"deliverable": deliverable["id"], "entry_date": "2026-02-01", "hours": "1.5"},
            format="json",
        )
        assert r.status_code == 201, r.data
        time_entry_id = r.data["id"]

        r = api_client.get("/api/v1/deliverable-time-entries/")
        assert r.status_code == 200
        assert any(item["id"] == time_entry_id for item in r.data["results"])

    def test_status_update_create_and_list(self, api_client, contract_payload):
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        r = api_client.post(
            "/api/v1/deliverable-status-updates/",
            {"deliverable": deliverable["id"], "period_end": "2026-02-01", "status": "on_track", "summary": "OK"},
            format="json",
        )
        assert r.status_code == 201, r.data
        status_id = r.data["id"]

        r = api_client.get("/api/v1/deliverable-status-updates/")
        assert r.status_code == 200
        assert any(item["id"] == status_id for item in r.data["results"])


@pytest.mark.django_db
class TestV1Validations:
    def test_staff_email_uniqueness_is_400(self, api_client, staff_payload):
        r = api_client.post("/api/v1/staff/", staff_payload, format="json")
        assert r.status_code == 201, r.data

        r = api_client.post("/api/v1/staff/", staff_payload, format="json")
        assert r.status_code == 400
        assert "email" in r.data

    def test_duplicate_assignment_is_400(self, api_client, contract_payload, staff_payload):
        staff = api_client.post("/api/v1/staff/", staff_payload, format="json").data
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        payload = {"deliverable": deliverable["id"], "staff": staff["id"], "expected_hours": "5.0", "is_lead": False}
        r = api_client.post("/api/v1/deliverable-assignments/", payload, format="json")
        assert r.status_code == 201, r.data

        r = api_client.post("/api/v1/deliverable-assignments/", payload, format="json")
        assert r.status_code == 400
        assert "non_field_errors" in r.data

    def test_duplicate_status_update_is_400(self, api_client, contract_payload):
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        payload = {"deliverable": deliverable["id"], "period_end": "2026-02-01", "status": "on_track", "summary": "OK"}
        r = api_client.post("/api/v1/deliverable-status-updates/", payload, format="json")
        assert r.status_code == 201, r.data

        r = api_client.post("/api/v1/deliverable-status-updates/", payload, format="json")
        assert r.status_code == 400
        assert "non_field_errors" in r.data

    def test_time_entry_hours_leq_zero_is_400(self, api_client, contract_payload, staff_payload):
        _ = api_client.post("/api/v1/staff/", staff_payload, format="json").data
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        r = api_client.post(
            "/api/v1/deliverable-time-entries/",
            {"deliverable": deliverable["id"], "entry_date": "2026-02-01", "hours": "0"},
            format="json",
        )
        assert r.status_code == 400
        assert "hours" in r.data

    def test_task_create_without_assignee_is_201(self, api_client, contract_payload):
        contract = api_client.post("/api/v1/contracts/", contract_payload, format="json").data
        deliverable = api_client.post(
            "/api/v1/deliverables/",
            {"contract": contract["id"], "name": "D1", "status": "planned"},
            format="json",
        ).data

        r = api_client.post(
            "/api/v1/tasks/",
            {"deliverable": deliverable["id"], "title": "T1", "planned_hours": "2.0", "status": "todo"},
            format="json",
        )
        assert r.status_code == 201, r.data
        assert r.data["assignee"] is None
