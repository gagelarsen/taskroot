import pytest

from core.models import Task


@pytest.mark.django_db
def test_staff_can_create_task_assigned_to_self(auth_client, staff_user, staff_profile, deliverable):
    client = auth_client(staff_user)

    payload = {
        "title": "Do thing",
        "assignee": staff_profile.id,
        "deliverable": deliverable.id,
    }
    r = client.post("/api/v1/tasks/", payload, format="json")
    assert r.status_code == 201, r.data
    assert r.data["assignee"] == staff_profile.id


@pytest.mark.django_db
def test_staff_can_create_task_unassigned(auth_client, staff_user, staff_profile, deliverable):
    client = auth_client(staff_user)

    payload = {
        "title": "Unassigned",
        "assignee": None,
        "deliverable": deliverable.id,
    }
    r = client.post("/api/v1/tasks/", payload, format="json")
    assert r.status_code == 201, r.data
    assert r.data["assignee"] is None


@pytest.mark.django_db
def test_staff_cannot_create_task_for_other_staff(auth_client, staff_user, other_staff_profile, deliverable):
    client = auth_client(staff_user)

    payload = {
        "title": "Bad",
        "assignee": other_staff_profile.id,
        "deliverable": deliverable.id,
    }
    r = client.post("/api/v1/tasks/", payload, format="json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_staff_can_update_task_if_assigned_to_self(auth_client, staff_user, staff_profile, deliverable):
    task = Task.objects.create(title="Mine", assignee=staff_profile, deliverable=deliverable)
    client = auth_client(staff_user)

    r = client.patch(f"/api/v1/tasks/{task.id}/", {"title": "Mine updated"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["title"] == "Mine updated"


@pytest.mark.django_db
def test_staff_cannot_update_task_if_not_assigned_to_self(auth_client, staff_user, other_staff_profile, deliverable):
    task = Task.objects.create(title="Not mine", assignee=other_staff_profile, deliverable=deliverable)
    client = auth_client(staff_user)

    r = client.patch(f"/api/v1/tasks/{task.id}/", {"title": "Hack"}, format="json")
    assert r.status_code == 403


@pytest.mark.django_db
def test_staff_cannot_reassign_task(auth_client, staff_user, staff_profile, other_staff_profile, deliverable):
    task = Task.objects.create(title="Mine", assignee=staff_profile, deliverable=deliverable)
    client = auth_client(staff_user)

    r = client.patch(
        f"/api/v1/tasks/{task.id}/",
        {"assignee": other_staff_profile.id},
        format="json",
    )
    assert r.status_code == 403
