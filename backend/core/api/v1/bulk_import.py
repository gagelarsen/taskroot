"""
Bulk import API for uploading JSON data files.
"""

from decimal import Decimal

from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.v1.permissions import IsAdmin
from core.models import Contract, Deliverable, DeliverableTimeEntry, Staff, Task


@extend_schema(
    summary="Bulk import data from JSON",
    description="""
    Import staff, contracts, deliverables, tasks, and time entries from a JSON file.
    
    The JSON format should match the structure in backend/docs/aquaveo-contracts-data.json.
    
    All imports are atomic - if any error occurs, the entire import is rolled back.
    
    Requires admin role.
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "staff": {"type": "array"},
                "contracts": {"type": "array"},
                "deliverables": {"type": "array"},
                "tasks": {"type": "array"},
            },
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "stats": {
                    "type": "object",
                    "properties": {
                        "staff_created": {"type": "integer"},
                        "contracts_created": {"type": "integer"},
                        "deliverables_created": {"type": "integer"},
                        "tasks_created": {"type": "integer"},
                    },
                },
            },
        },
        400: {"description": "Invalid data"},
    },
    examples=[
        OpenApiExample(
            "Sample Import",
            value={
                "version": "1.0",
                "staff": [{"email": "user@example.com", "first_name": "John", "last_name": "Doe"}],
                "contracts": [{"name": "Project A", "client_name": "Client X", "start_date": "2024-01-01"}],
            },
        )
    ],
)
@api_view(["POST"])
@permission_classes([IsAdmin])
def bulk_import_view(request: Request) -> Response:
    """
    Bulk import data from JSON payload.
    """
    data = request.data

    try:
        with transaction.atomic():
            stats = {
                "staff_created": 0,
                "contracts_created": 0,
                "deliverables_created": 0,
                "tasks_created": 0,
            }

            # Import staff first (no dependencies)
            staff_map = {}  # email -> Staff instance
            for staff_data in data.get("staff", []):
                staff, created = Staff.objects.get_or_create(
                    email=staff_data["email"],
                    defaults={
                        "first_name": staff_data.get("first_name", ""),
                        "last_name": staff_data.get("last_name", ""),
                        "role": staff_data.get("role", "staff"),
                        "status": staff_data.get("status", "active"),
                        "expected_hours_per_week": Decimal(str(staff_data.get("expected_hours_per_week", 40.0))),
                    },
                )
                staff_map[staff_data["email"]] = staff
                if created:
                    stats["staff_created"] += 1

            # Import contracts (no dependencies)
            contract_map = {}  # (name, client_name) -> Contract instance
            for contract_data in data.get("contracts", []):
                contract, created = Contract.objects.get_or_create(
                    name=contract_data["name"],
                    client_name=contract_data.get("client_name", ""),
                    defaults={
                        "start_date": contract_data.get("start_date"),
                        "end_date": contract_data.get("end_date"),
                        "budget_hours": Decimal(str(contract_data.get("budget_hours", 0))),
                        "status": contract_data.get("status", "draft"),
                    },
                )
                contract_map[(contract_data["name"], contract_data.get("client_name", ""))] = contract
                if created:
                    stats["contracts_created"] += 1

            # Import deliverables (depends on contracts)
            deliverable_map = {}  # name -> Deliverable instance
            for deliv_data in data.get("deliverables", []):
                contract_key = (deliv_data["contract_name"], deliv_data.get("contract_client_name", ""))
                contract = contract_map.get(contract_key)
                if not contract:
                    raise ValueError(
                        f"Contract not found: {deliv_data['contract_name']} "
                        f"({deliv_data.get('contract_client_name', '')})"
                    )

                deliverable, created = Deliverable.objects.get_or_create(
                    name=deliv_data["name"],
                    contract=contract,
                    defaults={
                        "charge_code": deliv_data.get("charge_code", ""),
                        "budget_hours": Decimal(str(deliv_data.get("budget_hours", 0))),
                        "target_completion_date": deliv_data.get("target_completion_date"),
                        "status": deliv_data.get("status", "planned"),
                    },
                )
                deliverable_map[deliv_data["name"]] = deliverable
                if created:
                    stats["deliverables_created"] += 1

            # Import tasks (depends on deliverables and staff)
            for task_data in data.get("tasks", []):
                # Try to get deliverable from map first, then from database
                deliverable = deliverable_map.get(task_data["deliverable_name"])
                if not deliverable:
                    try:
                        deliverable = Deliverable.objects.get(name=task_data["deliverable_name"])
                    except Deliverable.DoesNotExist as err:
                        raise ValueError(f"Deliverable not found: {task_data['deliverable_name']}") from err

                assignee = None
                if task_data.get("assignee_email"):
                    # Try to get staff from map first, then from database
                    assignee = staff_map.get(task_data["assignee_email"])
                    if not assignee:
                        try:
                            assignee = Staff.objects.get(email=task_data["assignee_email"])
                        except Staff.DoesNotExist as err:
                            raise ValueError(f"Staff not found: {task_data['assignee_email']}") from err

                task, created = Task.objects.get_or_create(
                    deliverable=deliverable,
                    title=task_data["title"],
                    defaults={
                        "assignee": assignee,
                        "budget_hours": (
                            Decimal(str(task_data.get("budget_hours", 0)))
                            if task_data.get("budget_hours")
                            else Decimal("0")
                        ),
                        "status": task_data.get("status", "todo"),
                    },
                )
                if created:
                    stats["tasks_created"] += 1

            return Response(
                {
                    "success": True,
                    "message": "Data imported successfully",
                    "stats": stats,
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(
    summary="Bulk import time entries from JSON",
    description="""
    Import time entries from a JSON file.

    The JSON format should match the structure in backend/docs/aquaveo-time-entries-data.json.

    Time entries are matched to deliverables by their charge_code field.

    All imports are atomic - if any error occurs, the entire import is rolled back.

    Requires admin role.
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "time_entries": {"type": "array"},
            },
        }
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message": {"type": "string"},
                "stats": {
                    "type": "object",
                    "properties": {
                        "time_entries_created": {"type": "integer"},
                    },
                },
            },
        },
        400: {"description": "Invalid data"},
    },
    examples=[
        OpenApiExample(
            "Sample Time Entries Import",
            value={
                "time_entries": [
                    {
                        "charge_code": "RD_T_NSF",
                        "entry_date": "2024-01-15",
                        "hours": 8.5,
                        "note": "Work completed",
                    }
                ]
            },
        )
    ],
)
@api_view(["POST"])
@permission_classes([IsAdmin])
def bulk_import_time_entries_view(request: Request) -> Response:
    """
    Bulk import time entries from JSON payload.
    """
    data = request.data

    try:
        with transaction.atomic():
            stats = {"time_entries_created": 0}

            # Import time entries (depends on deliverables)
            for entry_data in data.get("time_entries", []):
                # Find deliverable by charge_code
                try:
                    deliverable = Deliverable.objects.get(charge_code=entry_data["charge_code"])
                except Deliverable.DoesNotExist as err:
                    raise ValueError(f"Deliverable not found with charge_code: {entry_data['charge_code']}") from err

                # Create time entry
                time_entry, created = DeliverableTimeEntry.objects.get_or_create(
                    deliverable=deliverable,
                    entry_date=entry_data["entry_date"],
                    hours=Decimal(str(entry_data["hours"])),
                    defaults={
                        "note": entry_data.get("note", ""),
                    },
                )
                if created:
                    stats["time_entries_created"] += 1

            return Response(
                {
                    "success": True,
                    "message": "Time entries imported successfully",
                    "stats": stats,
                },
                status=status.HTTP_200_OK,
            )

    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_400_BAD_REQUEST,
        )
