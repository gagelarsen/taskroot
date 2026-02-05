import pytest
from rest_framework.test import APIClient

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
    Task,
)


@pytest.fixture()
def client():
    return APIClient()


@pytest.fixture()
def data():
    """
    Minimal dataset that supports all filter tests.
    """
    # Contracts
    c1 = Contract.objects.create(
        start_date="2026-01-01",
        end_date="2026-06-30",
        budget_hours_total="100.0",
        status="active",
    )
    c2 = Contract.objects.create(
        start_date="2026-07-01",
        end_date="2026-12-31",
        budget_hours_total="200.0",
        status="draft",
    )

    # Staff
    s1 = Staff.objects.create(
        email="a@example.com", first_name="Alice", last_name="Able", status="active", role="staff"
    )
    s2 = Staff.objects.create(
        email="b@example.com", first_name="Bob", last_name="Baker", status="inactive", role="manager"
    )

    # Deliverables
    d1 = Deliverable.objects.create(
        contract=c1, name="Alpha", start_date="2026-01-10", due_date="2026-02-10", status="planned"
    )
    d2 = Deliverable.objects.create(
        contract=c1, name="Beta", start_date="2026-02-01", due_date="2026-03-01", status="in_progress"
    )
    d3 = Deliverable.objects.create(
        contract=c2, name="Gamma", start_date="2026-07-10", due_date="2026-08-10", status="planned"
    )

    # Assignments (d1 has lead, d2 has non-lead, d3 none)
    DeliverableAssignment.objects.create(deliverable=d1, staff=s1, expected_hours="10.0", is_lead=True)
    DeliverableAssignment.objects.create(deliverable=d2, staff=s1, expected_hours="5.0", is_lead=False)

    # Tasks (one assigned, one unassigned)
    t1 = Task.objects.create(deliverable=d1, assignee=s1, title="Write report", planned_hours="2.0", status="todo")
    t2 = Task.objects.create(deliverable=d1, assignee=None, title="Unassigned task", planned_hours="1.0", status="todo")
    t3 = Task.objects.create(deliverable=d3, assignee=None, title="Gamma task", planned_hours="1.0", status="blocked")

    # Time entries
    DeliverableTimeEntry.objects.create(deliverable=d1, staff=s1, entry_date="2026-02-01", hours="1.0")
    DeliverableTimeEntry.objects.create(deliverable=d1, staff=s1, entry_date="2026-02-15", hours="2.0")
    DeliverableTimeEntry.objects.create(deliverable=d2, staff=s1, entry_date="2026-02-20", hours="1.0")

    # Status updates
    DeliverableStatusUpdate.objects.create(deliverable=d1, period_end="2026-02-01", status="on_track", summary="ok")
    DeliverableStatusUpdate.objects.create(deliverable=d1, period_end="2026-03-01", status="at_risk", summary="risk")
    DeliverableStatusUpdate.objects.create(deliverable=d2, period_end="2026-03-01", status="on_track", summary="ok")

    return {
        "contracts": (c1, c2),
        "staff": (s1, s2),
        "deliverables": (d1, d2, d3),
        "tasks": (t1, t2, t3),
    }


def _ids(results):
    return {row["id"] for row in results}


@pytest.mark.django_db
def test_deliverables_filter_contract_id(client, data):
    c1, _ = data["contracts"]
    d1, d2, d3 = data["deliverables"]

    r = client.get(f"/api/v1/deliverables/?contract_id={c1.id}")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {d1.id, d2.id}


@pytest.mark.django_db
def test_deliverables_filter_staff_id(client, data):
    s1, _ = data["staff"]
    d1, d2, d3 = data["deliverables"]

    r = client.get(f"/api/v1/deliverables/?staff_id={s1.id}")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {d1.id, d2.id}


@pytest.mark.django_db
def test_deliverables_filter_lead_only_true(client, data):
    d1, d2, d3 = data["deliverables"]

    r = client.get("/api/v1/deliverables/?lead_only=true")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {d1.id}


@pytest.mark.django_db
def test_deliverables_date_range_due_date(client, data):
    d1, d2, d3 = data["deliverables"]

    r = client.get("/api/v1/deliverables/?due_date_from=2026-03-01&due_date_to=2026-12-31")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {d2.id, d3.id}


@pytest.mark.django_db
def test_deliverables_search_q(client, data):
    d1, d2, d3 = data["deliverables"]

    r = client.get("/api/v1/deliverables/?q=Alp")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {d1.id}


@pytest.mark.django_db
def test_deliverables_ordering_due_date_asc(client, data):
    d1, d2, d3 = data["deliverables"]

    r = client.get("/api/v1/deliverables/?order_by=due_date&order_dir=asc")
    assert r.status_code == 200
    ids = [row["id"] for row in r.data["results"]]
    assert ids == [d1.id, d2.id, d3.id]


@pytest.mark.django_db
def test_tasks_filter_contract_id_and_unassigned(client, data):
    c1, c2 = data["contracts"]
    t1, t2, t3 = data["tasks"]

    r = client.get(f"/api/v1/tasks/?contract_id={c1.id}&unassigned=true")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {t2.id}

    r = client.get(f"/api/v1/tasks/?contract_id={c2.id}&unassigned=true")
    assert r.status_code == 200
    assert _ids(r.data["results"]) == {t3.id}


@pytest.mark.django_db
def test_assignments_filter_is_lead(client, data):
    d1, d2, d3 = data["deliverables"]

    r = client.get("/api/v1/deliverable-assignments/?lead_only=true")
    assert r.status_code == 200
    # Only one lead assignment exists in fixture
    assert len(r.data["results"]) == 1
    assert r.data["results"][0]["deliverable"] == d1.id


@pytest.mark.django_db
def test_time_entries_filter_staff_and_date_range(client, data):
    s1, _ = data["staff"]

    r = client.get(
        f"/api/v1/deliverable-time-entries/?staff_id={s1.id}&entry_date_from=2026-02-10&entry_date_to=2026-02-28"
    )
    assert r.status_code == 200
    # Should include 2026-02-15 and 2026-02-20 entries (2 results)
    assert len(r.data["results"]) == 2


@pytest.mark.django_db
def test_status_updates_filter_period_end_range_and_status(client, data):
    r = client.get(
        "/api/v1/deliverable-status-updates/?period_end_from=2026-03-01&period_end_to=2026-03-01&status=on_track"
    )
    assert r.status_code == 200
    assert len(r.data["results"]) == 1
    assert r.data["results"][0]["status"] == "on_track"
    assert r.data["results"][0]["period_end"] == "2026-03-01"
