import pytest

from core.models import DeliverableTimeEntry


@pytest.mark.django_db
def test_manager_can_edit_others_time_entry(
    auth_client, manager_user, manager_profile, other_staff_profile, deliverable
):
    entry = DeliverableTimeEntry.objects.create(
        deliverable=deliverable, staff=other_staff_profile, hours=1, entry_date="2026-02-01"
    )
    client = auth_client(manager_user)
    r = client.patch(f"/api/v1/deliverable-time-entries/{entry.id}/", {"hours": "3.0"}, format="json")
    assert r.status_code == 200, r.data
