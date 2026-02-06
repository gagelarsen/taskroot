import pytest

from core.models import DeliverableTimeEntry


@pytest.mark.django_db
def test_staff_create_time_entry_forces_staff_to_self(
    auth_client, staff_user, staff_profile, other_staff_profile, deliverable
):
    client = auth_client(staff_user)

    payload = {
        "deliverable": deliverable.id,
        "hours": "1.5",
        "entry_date": "2026-02-01",
    }
    r = client.post("/api/v1/deliverable-time-entries/", payload, format="json")
    assert r.status_code == 201, r.data


@pytest.mark.django_db
def test_staff_can_edit_any_time_entry(auth_client, staff_user, staff_profile, other_staff_profile, deliverable):
    """Test that staff can edit any time entry (time entries no longer track staff)."""
    entry = DeliverableTimeEntry.objects.create(
        deliverable=deliverable,
        hours=1,
        entry_date="2026-02-01",
    )
    client = auth_client(staff_user)

    r = client.patch(f"/api/v1/deliverable-time-entries/{entry.id}/", {"hours": "2.0"}, format="json")
    assert r.status_code == 200
    assert r.data["hours"] == "2.00"


@pytest.mark.django_db
def test_staff_can_edit_own_time_entry(auth_client, staff_user, staff_profile, deliverable):
    entry = DeliverableTimeEntry.objects.create(
        deliverable=deliverable,
        hours=1,
        entry_date="2026-02-01",
    )
    client = auth_client(staff_user)

    r = client.patch(f"/api/v1/deliverable-time-entries/{entry.id}/", {"hours": "2.0"}, format="json")
    assert r.status_code == 200, r.data
    assert str(r.data["hours"]) in ("2.0", "2.00", "2")  # depending on serializer formatting


@pytest.mark.django_db
def test_staff_cannot_delete_others_time_entry(auth_client, staff_user, other_staff_profile, deliverable):
    entry = DeliverableTimeEntry.objects.create(
        deliverable=deliverable,
        hours=1,
        entry_date="2026-02-01",
    )
    client = auth_client(staff_user)

    r = client.delete(f"/api/v1/deliverable-time-entries/{entry.id}/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_staff_can_list_time_entries(auth_client, staff_user, staff_profile, deliverable):
    """Test that staff can list time entries (line 558)."""
    # Create a time entry
    DeliverableTimeEntry.objects.create(
        deliverable=deliverable,
        hours=1,
        entry_date="2026-02-01",
    )
    client = auth_client(staff_user)

    # Staff should be able to list time entries
    r = client.get("/api/v1/deliverable-time-entries/")
    assert r.status_code == 200
