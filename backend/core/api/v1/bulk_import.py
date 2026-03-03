"""
Bulk import API for uploading JSON data files.
"""

import csv
import io
from decimal import Decimal

from django.db import transaction
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from core.api.v1.permissions import IsAdmin
from core.models import Contract, ContractInvoiceUpdate, Deliverable, DeliverableTimeEntry, Staff, Task


def _build_time_entries_from_csv(file_content: str, fallback_entry_date: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(file_content))
    if not reader.fieldnames:
        raise ValueError("CSV file appears to be empty")

    header_map = {
        field_name.strip().upper(): field_name for field_name in reader.fieldnames if field_name and field_name.strip()
    }

    if "CHARGE CODE" not in header_map or "HOURS" not in header_map:
        raise ValueError("CSV must include CHARGE CODE and HOURS columns")

    aggregated_entries: dict[tuple[str, str], dict] = {}
    for row in reader:
        charge_code = (row.get(header_map["CHARGE CODE"], "") or "").strip()
        if not charge_code:
            continue

        if "RESOURCE ID" in header_map:
            resource_id = (row.get(header_map["RESOURCE ID"], "") or "").strip().lower()
            if resource_id == "total":
                continue

        hours_raw = (row.get(header_map["HOURS"], "") or "").strip()
        try:
            hours = Decimal(hours_raw)
        except Exception:
            continue

        if hours <= 0:
            continue

        entry_date = fallback_entry_date
        if "ENTRY DATE" in header_map:
            csv_entry_date = (row.get(header_map["ENTRY DATE"], "") or "").strip()
            entry_date = csv_entry_date or fallback_entry_date

        if not entry_date:
            raise ValueError("entry_date is required for CSV imports when CSV does not contain ENTRY DATE values")

        group = (row.get(header_map["GROUP"], "") or "").strip() if "GROUP" in header_map else ""
        description = (
            (row.get(header_map["CHARGE CODE DESCRIPTION"], "") or "").strip()
            if "CHARGE CODE DESCRIPTION" in header_map
            else ""
        )
        note_parts = [value for value in [group, description] if value]

        aggregate_key = (charge_code, entry_date)
        note = " - ".join(note_parts)

        if aggregate_key not in aggregated_entries:
            aggregated_entries[aggregate_key] = {
                "charge_code": charge_code,
                "entry_date": entry_date,
                "hours": hours,
                "note": note,
            }
            continue

        aggregated_entries[aggregate_key]["hours"] += hours
        if note:
            existing_note = aggregated_entries[aggregate_key]["note"]
            if not existing_note:
                aggregated_entries[aggregate_key]["note"] = note
            elif note not in existing_note.split("; "):
                aggregated_entries[aggregate_key]["note"] = f"{existing_note}; {note}"

    if not aggregated_entries:
        raise ValueError("No importable time entries found in CSV")

    return [
        {
            "charge_code": entry["charge_code"],
            "entry_date": entry["entry_date"],
            "hours": str(entry["hours"]),
            "note": entry["note"],
        }
        for entry in aggregated_entries.values()
    ]


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
    Import time entries from JSON or CSV.

    The JSON format should match the structure in backend/docs/aquaveo-time-entries-data.json.

    For CSV uploads (`multipart/form-data`), provide:
    - `file`: CSV file
    - `entry_date` (optional): fallback date when CSV does not include an `ENTRY DATE` column/value

    CSV must include `CHARGE CODE` and `HOURS` columns.

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
        },
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary"},
                "entry_date": {"type": "string", "format": "date"},
            },
            "required": ["file"],
        },
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
                "imported_entries": {
                    "type": "array",
                    "description": "List of created time entries for verification",
                    "items": {
                        "type": "object",
                        "properties": {
                            "charge_code": {"type": "string"},
                            "entry_date": {"type": "string", "format": "date"},
                            "hours": {"type": "string"},
                            "note": {"type": "string"},
                        },
                    },
                },
            },
        },
        400: {"description": "Unexpected error during import"},
    },
    examples=[
        OpenApiExample(
            "Sample Time Entries JSON Import",
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
            request_only=True,
            media_type="application/json",
        ),
        OpenApiExample(
            "Sample Time Entries CSV Import",
            value={
                "entry_date": "2026-01-15",
            },
            description="Upload a CSV file in the `file` field. `entry_date` is used only when "
            "CSV rows do not include ENTRY DATE.",
            request_only=True,
            media_type="multipart/form-data",
        ),
    ],
)
@api_view(["POST"])
@permission_classes([IsAdmin])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def bulk_import_time_entries_view(request: Request) -> Response:
    """
    Bulk import time entries from JSON payload.

    Processes all entries and reports successes/failures individually.
    Does not fail the entire import if some entries have errors.
    """
    data = request.data

    if "file" in request.FILES:
        uploaded_file = request.FILES["file"]
        fallback_entry_date = (data.get("entry_date", "") or "").strip()

        try:
            file_content = uploaded_file.read().decode("utf-8-sig")
            data = {
                "time_entries": _build_time_entries_from_csv(
                    file_content=file_content, fallback_entry_date=fallback_entry_date
                )
            }
        except UnicodeDecodeError:
            return Response(
                {"success": False, "error": "Unable to decode CSV file. Please use UTF-8 encoding."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    stats = {
        "time_entries_created": 0,
        "time_entries_skipped": 0,
        "time_entries_failed": 0,
    }
    warnings = []
    errors = []
    imported_entries = []

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
                    created_entry = DeliverableTimeEntry.objects.create(
                        deliverable=deliverable,
                        entry_date=entry_date,
                        hours=Decimal(str(hours)),
                        note=entry_data.get("note", ""),
                    )
                    stats["time_entries_created"] += 1
                    imported_entries.append(
                        {
                            "charge_code": charge_code,
                            "entry_date": str(created_entry.entry_date),
                            "hours": str(created_entry.hours),
                            "note": created_entry.note,
                        }
                    )
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

            if imported_entries:
                response_data["imported_entries"] = imported_entries

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
