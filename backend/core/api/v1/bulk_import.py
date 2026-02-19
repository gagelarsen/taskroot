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
from core.models import Contract, ContractInvoiceUpdate, Deliverable, DeliverableTimeEntry, Staff, Task


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
                "contracts": [{"name": "Project A", "client_name": "Client X", "start_date": "2026-01-01"}],
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

    **Smart Import Behavior:**
    - Entries with non-existent charge codes are **skipped** with a warning
    - Duplicate entries (same charge_code + date) are **skipped** with a warning
    - Valid entries are imported successfully
    - The import continues processing all entries even if some fail
    - Returns detailed stats showing created/skipped/failed counts

    The entire import is atomic - either all valid entries are created or none are.

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
                        "time_entries_skipped": {"type": "integer"},
                        "time_entries_failed": {"type": "integer"},
                    },
                },
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of warnings for skipped entries",
                },
                "errors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of errors for failed entries",
                },
            },
        },
        400: {"description": "Unexpected error during import"},
    },
    examples=[
        OpenApiExample(
            "Sample Time Entries Import",
            value={
                "time_entries": [
                    {
                        "charge_code": "RD_T_NSF",
                        "entry_date": "2026-01-15",
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

    Processes all entries and reports successes/failures individually.
    Does not fail the entire import if some entries have errors.
    """
    data = request.data

    stats = {
        "time_entries_created": 0,
        "time_entries_skipped": 0,
        "time_entries_failed": 0,
    }
    warnings = []
    errors = []

    try:
        with transaction.atomic():
            # Import time entries (depends on deliverables)
            for idx, entry_data in enumerate(data.get("time_entries", []), start=1):
                charge_code = entry_data.get("charge_code", "")
                entry_date = entry_data.get("entry_date", "")
                hours = entry_data.get("hours", 0)

                # Validate required fields
                if not charge_code:
                    errors.append(f"Entry #{idx}: Missing charge_code")
                    stats["time_entries_failed"] += 1
                    continue

                if not entry_date:
                    errors.append(f"Entry #{idx}: Missing entry_date")
                    stats["time_entries_failed"] += 1
                    continue

                # Find deliverable by charge_code
                try:
                    deliverable = Deliverable.objects.get(charge_code=charge_code)
                except Deliverable.DoesNotExist:
                    warnings.append(f"Entry #{idx}: Deliverable not found with charge_code '{charge_code}' - skipped")
                    stats["time_entries_skipped"] += 1
                    continue

                # Check if entry already exists for this deliverable and date
                existing_entry = DeliverableTimeEntry.objects.filter(
                    deliverable=deliverable,
                    entry_date=entry_date,
                ).first()

                if existing_entry:
                    warnings.append(
                        f"Entry #{idx}: Time entry already exists for charge_code '{charge_code}' "
                        f"on {entry_date} ({existing_entry.hours}h) - skipped"
                    )
                    stats["time_entries_skipped"] += 1
                    continue

                # Create time entry
                try:
                    DeliverableTimeEntry.objects.create(
                        deliverable=deliverable,
                        entry_date=entry_date,
                        hours=Decimal(str(hours)),
                        note=entry_data.get("note", ""),
                    )
                    stats["time_entries_created"] += 1
                except Exception as e:
                    errors.append(f"Entry #{idx}: Failed to create - {str(e)}")
                    stats["time_entries_failed"] += 1

            # Determine overall success
            success = stats["time_entries_created"] > 0 or (
                stats["time_entries_failed"] == 0 and stats["time_entries_skipped"] > 0
            )

            message_parts = []
            if stats["time_entries_created"] > 0:
                message_parts.append(f"{stats['time_entries_created']} entries created")
            if stats["time_entries_skipped"] > 0:
                message_parts.append(f"{stats['time_entries_skipped']} entries skipped")
            if stats["time_entries_failed"] > 0:
                message_parts.append(f"{stats['time_entries_failed']} entries failed")

            message = ", ".join(message_parts) if message_parts else "No entries processed"

            response_data = {
                "success": success,
                "message": message,
                "stats": stats,
            }

            if warnings:
                response_data["warnings"] = warnings

            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"success": False, "error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(
    summary="Bulk import contract invoice updates from JSON",
    description="""
    Import contract invoice updates from a JSON payload.

    **Contract matching priority:**
    1. `contract_id`
    2. `contract_number`
    3. (`contract_name`, optional `contract_client_name`)

    **Smart Import Behavior:**
    - Missing/invalid contract references are **skipped** with warnings
    - Duplicate entries (same contract + invoice_date + amount) are **skipped**
    - Valid entries are created
    - Processing continues across all rows

    Requires admin role.
    """,
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "invoice_updates": {"type": "array"},
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
                        "invoice_updates_created": {"type": "integer"},
                        "invoice_updates_skipped": {"type": "integer"},
                        "invoice_updates_failed": {"type": "integer"},
                    },
                },
                "warnings": {"type": "array", "items": {"type": "string"}},
                "errors": {"type": "array", "items": {"type": "string"}},
            },
        },
        400: {"description": "Unexpected error during import"},
    },
    examples=[
        OpenApiExample(
            "Sample Invoice Update Import",
            value={
                "invoice_updates": [
                    {
                        "contract_number": "TM-2026-001",
                        "invoice_date": "2026-02-15",
                        "amount": 12500.0,
                        "note": "Milestone invoice",
                    }
                ]
            },
        )
    ],
)
@api_view(["POST"])
@permission_classes([IsAdmin])
def bulk_import_invoice_updates_view(request: Request) -> Response:
    """
    Bulk import contract invoice updates from JSON payload.
    """
    data = request.data

    stats = {
        "invoice_updates_created": 0,
        "invoice_updates_skipped": 0,
        "invoice_updates_failed": 0,
    }
    warnings = []
    errors = []

    def _find_contract(entry_data: dict):
        contract_id = entry_data.get("contract_id")
        if contract_id is not None:
            return Contract.objects.filter(id=contract_id).first()

        contract_number = str(entry_data.get("contract_number", "")).strip()
        if contract_number:
            return Contract.objects.filter(contract_number=contract_number).first()

        contract_name = str(entry_data.get("contract_name", "")).strip()
        if contract_name:
            contract_client_name = str(entry_data.get("contract_client_name", "")).strip()
            return Contract.objects.filter(name=contract_name, client_name=contract_client_name).first()

        return None

    try:
        with transaction.atomic():
            for idx, entry_data in enumerate(data.get("invoice_updates", []), start=1):
                invoice_date = entry_data.get("invoice_date", "")
                amount_raw = entry_data.get("amount")
                note = entry_data.get("note", "")

                if not invoice_date:
                    errors.append(f"Entry #{idx}: Missing invoice_date")
                    stats["invoice_updates_failed"] += 1
                    continue

                if amount_raw in (None, ""):
                    errors.append(f"Entry #{idx}: Missing amount")
                    stats["invoice_updates_failed"] += 1
                    continue

                try:
                    amount = Decimal(str(amount_raw))
                except Exception:
                    errors.append(f"Entry #{idx}: Invalid amount '{amount_raw}'")
                    stats["invoice_updates_failed"] += 1
                    continue

                if amount <= 0:
                    errors.append(f"Entry #{idx}: Amount must be > 0")
                    stats["invoice_updates_failed"] += 1
                    continue

                contract = _find_contract(entry_data)
                if not contract:
                    warnings.append(
                        f"Entry #{idx}: Contract not found (provide contract_id, contract_number, "
                        "or contract_name + contract_client_name) - skipped"
                    )
                    stats["invoice_updates_skipped"] += 1
                    continue

                existing = ContractInvoiceUpdate.objects.filter(
                    contract=contract,
                    invoice_date=invoice_date,
                    amount=amount,
                ).first()

                if existing:
                    warnings.append(
                        f"Entry #{idx}: Invoice update already exists for contract '{contract.id}' "
                        f"on {invoice_date} amount {amount} - skipped"
                    )
                    stats["invoice_updates_skipped"] += 1
                    continue

                try:
                    ContractInvoiceUpdate.objects.create(
                        contract=contract,
                        invoice_date=invoice_date,
                        amount=amount,
                        note=note,
                    )
                    stats["invoice_updates_created"] += 1
                except Exception as e:
                    errors.append(f"Entry #{idx}: Failed to create - {str(e)}")
                    stats["invoice_updates_failed"] += 1

            success = stats["invoice_updates_created"] > 0 or (
                stats["invoice_updates_failed"] == 0 and stats["invoice_updates_skipped"] > 0
            )

            message_parts = []
            if stats["invoice_updates_created"] > 0:
                message_parts.append(f"{stats['invoice_updates_created']} entries created")
            if stats["invoice_updates_skipped"] > 0:
                message_parts.append(f"{stats['invoice_updates_skipped']} entries skipped")
            if stats["invoice_updates_failed"] > 0:
                message_parts.append(f"{stats['invoice_updates_failed']} entries failed")

            message = ", ".join(message_parts) if message_parts else "No entries processed"

            response_data = {
                "success": success,
                "message": message,
                "stats": stats,
            }

            if warnings:
                response_data["warnings"] = warnings

            if errors:
                response_data["errors"] = errors

            return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"success": False, "error": f"Unexpected error: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )
