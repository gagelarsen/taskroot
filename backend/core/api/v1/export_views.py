"""
CSV export views for reporting data.
"""

import csv
from datetime import date

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.v1.permissions import ReadOnlyForStaffOtherwiseManagerAdmin
from core.models import Contract, Deliverable, DeliverableTimeEntry, Initiative, InitiativeWeeklyUpdate, Task


class TimeEntriesCSVExport(APIView):
    """
    Export time entries to CSV format.
    """

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export time entries to CSV",
        description="Export time entries with optional filters (contract_id, deliverable_id, date range)",
        parameters=[
            OpenApiParameter(
                name="contract_id",
                description="Filter by contract ID",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="deliverable_id",
                description="Filter by deliverable ID",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="entry_date_from",
                description="Start date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="entry_date_to",
                description="End date (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        """
        GET /api/v1/exports/time-entries.csv

        Returns CSV file with time entries.
        """
        # Build query
        queryset = (
            DeliverableTimeEntry.objects.all()
            .select_related("deliverable", "deliverable__contract")
            .order_by("entry_date", "id")
        )

        # Apply filters
        contract_id = request.query_params.get("contract_id")
        if contract_id:
            queryset = queryset.filter(deliverable__contract_id=contract_id)

        deliverable_id = request.query_params.get("deliverable_id")
        if deliverable_id:
            queryset = queryset.filter(deliverable_id=deliverable_id)

        entry_date_from = request.query_params.get("entry_date_from")
        if entry_date_from:
            try:
                from_date = date.fromisoformat(entry_date_from)
                queryset = queryset.filter(entry_date__gte=from_date)
            except ValueError:
                return Response(
                    {"error": "Invalid entry_date_from format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )

        entry_date_to = request.query_params.get("entry_date_to")
        if entry_date_to:
            try:
                to_date = date.fromisoformat(entry_date_to)
                queryset = queryset.filter(entry_date__lte=to_date)
            except ValueError:
                return Response(
                    {"error": "Invalid entry_date_to format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="time_entries.csv"'

        writer = csv.writer(response)

        # Write header
        writer.writerow(
            [
                "ID",
                "Entry Date",
                "Hours",
                "Deliverable ID",
                "Deliverable Name",
                "Contract ID",
                "External Source",
                "External ID",
                "Created At",
            ]
        )

        # Write data rows
        for entry in queryset:
            writer.writerow(
                [
                    entry.id,
                    entry.entry_date,
                    entry.hours,
                    entry.deliverable.id,
                    entry.deliverable.name,
                    entry.deliverable.contract.id,
                    entry.external_source or "",
                    entry.external_id or "",
                    entry.created_at.isoformat(),
                ]
            )

        return response


class ContractBurnCSVExport(APIView):
    """
    Export contract burn data to CSV format.
    """

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export contract burn data to CSV",
        description="Export weekly burn data for a contract (requires contract_id parameter)",
        parameters=[
            OpenApiParameter(
                name="contract_id",
                description="Contract ID (required)",
                required=True,
                type=int,
            ),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        """
        GET /api/v1/exports/contract-burn.csv?contract_id=<id>

        Returns CSV file with weekly burn data for a contract.
        """
        contract_id = request.query_params.get("contract_id")
        if not contract_id:
            return Response({"error": "contract_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            contract = Contract.objects.get(pk=contract_id)
        except Contract.DoesNotExist as err:
            raise NotFound("Contract not found") from err

        # Import here to avoid circular dependency
        from datetime import timedelta
        from decimal import Decimal

        from django.db.models import Sum

        from core.api.v1.report_views import generate_weekly_buckets

        # Generate weekly buckets
        buckets = generate_weekly_buckets(contract.start_date, contract.end_date)

        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="contract_{contract.id}_burn.csv"'

        writer = csv.writer(response)

        # Write header
        writer.writerow(
            [
                "Week Ending",
                "Expected Hours",
                "Actual Hours",
                "Cumulative Expected",
                "Cumulative Actual",
                "Variance (Actual - Expected)",
                "Cumulative Variance",
            ]
        )

        # Calculate and write data rows
        cumulative_expected = Decimal("0")
        cumulative_actual = Decimal("0")
        expected_per_bucket = contract.get_assigned_budget_hours() / len(buckets) if buckets else Decimal("0")

        for bucket_end in buckets:
            bucket_start = bucket_end - timedelta(days=6)
            actual_for_bucket = DeliverableTimeEntry.objects.filter(
                deliverable__contract=contract, entry_date__gte=bucket_start, entry_date__lte=bucket_end
            ).aggregate(total=Sum("hours"))["total"] or Decimal("0")

            cumulative_expected += expected_per_bucket
            cumulative_actual += actual_for_bucket

            variance = actual_for_bucket - expected_per_bucket
            cumulative_variance = cumulative_actual - cumulative_expected

            writer.writerow(
                [
                    bucket_end,
                    expected_per_bucket,
                    actual_for_bucket,
                    cumulative_expected,
                    cumulative_actual,
                    variance,
                    cumulative_variance,
                ]
            )

        return response


class ContractsCSVExport(APIView):
    """Export contracts to CSV format."""

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export contracts to CSV",
        description="Export contracts with rollup metrics and tags.",
        parameters=[
            OpenApiParameter(name="status", description="Filter by contract status", required=False, type=str),
            OpenApiParameter(
                name="contract_type",
                description="Filter by contract type",
                required=False,
                type=str,
            ),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        queryset = Contract.objects.all().order_by("id")

        status_value = request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        contract_type = request.query_params.get("contract_type")
        if contract_type:
            queryset = queryset.filter(contract_type=contract_type)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="contracts.csv"'
        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Name",
                "Client",
                "Contract Type",
                "Status",
                "Tags",
                "Start Date",
                "End Date",
                "Budget Hours",
                "Assigned Hours",
                "Spent Hours",
                "Remaining Hours",
                "Percent Complete",
                "Created At",
                "Updated At",
            ]
        )

        for contract in queryset:
            writer.writerow(
                [
                    contract.id,
                    contract.name,
                    contract.client_name,
                    contract.get_contract_type_display(),
                    contract.get_status_display(),
                    "; ".join(contract.tags or []),
                    contract.start_date,
                    contract.end_date,
                    contract.budget_hours,
                    contract.get_assigned_budget_hours(),
                    contract.get_spent_hours(),
                    contract.get_remaining_budget_hours(),
                    contract.get_estimated_percent_complete(),
                    contract.created_at.isoformat(),
                    contract.updated_at.isoformat(),
                ]
            )

        return response


class DeliverablesCSVExport(APIView):
    """Export deliverables to CSV format."""

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export deliverables to CSV",
        description="Export deliverables with rollup metrics and latest status.",
        parameters=[
            OpenApiParameter(name="contract_id", description="Filter by contract ID", required=False, type=int),
            OpenApiParameter(name="status", description="Filter by deliverable status", required=False, type=str),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        queryset = Deliverable.objects.all().select_related("contract").order_by("id")

        contract_id = request.query_params.get("contract_id")
        if contract_id:
            queryset = queryset.filter(contract_id=contract_id)

        status_value = request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="deliverables.csv"'
        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Contract ID",
                "Contract Name",
                "Name",
                "Charge Code",
                "Status",
                "Target Completion Date",
                "Budget Hours",
                "Assigned Hours",
                "Spent Hours",
                "Remaining Hours",
                "Percent Complete",
                "Latest Status",
                "Latest Status Period End",
                "Latest Status Summary",
            ]
        )

        for deliverable in queryset:
            latest_status = deliverable.get_latest_status_update()
            writer.writerow(
                [
                    deliverable.id,
                    deliverable.contract_id,
                    deliverable.contract.name,
                    deliverable.name,
                    deliverable.charge_code,
                    deliverable.get_status_display(),
                    deliverable.target_completion_date or "",
                    deliverable.budget_hours,
                    deliverable.get_assigned_budget_hours(),
                    deliverable.get_spent_hours(),
                    deliverable.get_remaining_budget_hours(),
                    deliverable.get_estimated_percent_complete(),
                    latest_status.get_status_display() if latest_status else "",
                    latest_status.period_end if latest_status else "",
                    latest_status.summary if latest_status else "",
                ]
            )

        return response


class TasksCSVExport(APIView):
    """Export tasks to CSV format."""

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export tasks to CSV",
        description="Export tasks with deliverable/contract context.",
        parameters=[
            OpenApiParameter(name="contract_id", description="Filter by contract ID", required=False, type=int),
            OpenApiParameter(name="deliverable_id", description="Filter by deliverable ID", required=False, type=int),
            OpenApiParameter(name="assignee_id", description="Filter by assignee staff ID", required=False, type=int),
            OpenApiParameter(name="status", description="Filter by task status", required=False, type=str),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        queryset = Task.objects.all().select_related("deliverable", "deliverable__contract", "assignee").order_by("id")

        contract_id = request.query_params.get("contract_id")
        if contract_id:
            queryset = queryset.filter(deliverable__contract_id=contract_id)

        deliverable_id = request.query_params.get("deliverable_id")
        if deliverable_id:
            queryset = queryset.filter(deliverable_id=deliverable_id)

        assignee_id = request.query_params.get("assignee_id")
        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)

        status_value = request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="tasks.csv"'
        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Contract ID",
                "Contract Name",
                "Deliverable ID",
                "Deliverable Name",
                "Title",
                "Assignee ID",
                "Assignee Name",
                "Status",
                "Budget Hours",
                "Percent Complete",
                "Created At",
                "Updated At",
            ]
        )

        for task in queryset:
            assignee_name = f"{task.assignee.first_name} {task.assignee.last_name}" if task.assignee else ""
            writer.writerow(
                [
                    task.id,
                    task.deliverable.contract_id,
                    task.deliverable.contract.name,
                    task.deliverable_id,
                    task.deliverable.name,
                    task.title,
                    task.assignee_id or "",
                    assignee_name,
                    task.get_status_display(),
                    task.budget_hours,
                    task.percent_complete,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ]
            )

        return response


class InitiativesCSVExport(APIView):
    """Export initiatives to CSV format."""

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export initiatives to CSV",
        description="Export initiatives with weekly progress snapshot.",
        parameters=[
            OpenApiParameter(name="status", description="Filter by initiative status", required=False, type=str),
            OpenApiParameter(name="owner_id", description="Filter by owner staff ID", required=False, type=int),
            OpenApiParameter(
                name="tags", description="Filter by tags (comma-separated, matches any)", required=False, type=str
            ),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        queryset = Initiative.objects.all().select_related("owner").prefetch_related("weekly_updates").order_by("id")

        status_value = request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)

        owner_id = request.query_params.get("owner_id")
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        tags_value = request.query_params.get("tags")
        if tags_value:
            raw_tags = [part.strip() for part in tags_value.split(",")]
            requested = {tag.lower() for tag in raw_tags if tag}
            queryset = [
                initiative
                for initiative in queryset
                if {str(tag).strip().lower() for tag in (initiative.tags or []) if str(tag).strip()}.intersection(
                    requested
                )
            ]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="initiatives.csv"'
        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Name",
                "Owner ID",
                "Owner Name",
                "Status",
                "Tags",
                "Target Date",
                "Current Percent Complete",
                "Latest Update Period End",
                "Latest Update Summary",
                "Update Stale",
                "Notes",
                "Created At",
                "Updated At",
            ]
        )

        for initiative in queryset:
            latest = initiative.get_latest_update()
            owner_name = f"{initiative.owner.first_name} {initiative.owner.last_name}" if initiative.owner else ""
            writer.writerow(
                [
                    initiative.id,
                    initiative.name,
                    initiative.owner_id or "",
                    owner_name,
                    initiative.get_status_display(),
                    "; ".join(initiative.tags or []),
                    initiative.target_date or "",
                    initiative.get_current_percent_complete(),
                    latest.period_end if latest else "",
                    latest.summary if latest else "",
                    "Yes" if initiative.is_update_stale(days=7) else "No",
                    initiative.notes,
                    initiative.created_at.isoformat(),
                    initiative.updated_at.isoformat(),
                ]
            )

        return response


class InitiativeWeeklyUpdatesCSVExport(APIView):
    """Export initiative weekly updates to CSV format."""

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export initiative weekly updates to CSV",
        description="Export weekly update history for initiatives.",
        parameters=[
            OpenApiParameter(name="initiative_id", description="Filter by initiative ID", required=False, type=int),
            OpenApiParameter(name="period_end_from", description="Start date (YYYY-MM-DD)", required=False, type=str),
            OpenApiParameter(name="period_end_to", description="End date (YYYY-MM-DD)", required=False, type=str),
        ],
        responses={200: {"type": "string", "format": "binary"}},
    )
    def get(self, request):
        queryset = (
            InitiativeWeeklyUpdate.objects.all().select_related("initiative", "created_by").order_by("period_end", "id")
        )

        initiative_id = request.query_params.get("initiative_id")
        if initiative_id:
            queryset = queryset.filter(initiative_id=initiative_id)

        period_end_from = request.query_params.get("period_end_from")
        if period_end_from:
            try:
                from_date = date.fromisoformat(period_end_from)
                queryset = queryset.filter(period_end__gte=from_date)
            except ValueError:
                return Response(
                    {"error": "Invalid period_end_from format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )

        period_end_to = request.query_params.get("period_end_to")
        if period_end_to:
            try:
                to_date = date.fromisoformat(period_end_to)
                queryset = queryset.filter(period_end__lte=to_date)
            except ValueError:
                return Response(
                    {"error": "Invalid period_end_to format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="initiative_weekly_updates.csv"'
        writer = csv.writer(response)

        writer.writerow(
            [
                "ID",
                "Initiative ID",
                "Initiative Name",
                "Period End",
                "Percent Complete",
                "Summary",
                "Created By ID",
                "Created By Name",
                "Created At",
                "Updated At",
            ]
        )

        for update in queryset:
            created_by_name = (
                f"{update.created_by.first_name} {update.created_by.last_name}" if update.created_by else ""
            )
            writer.writerow(
                [
                    update.id,
                    update.initiative_id,
                    update.initiative.name,
                    update.period_end,
                    update.percent_complete,
                    update.summary,
                    update.created_by_id or "",
                    created_by_name,
                    update.created_at.isoformat(),
                    update.updated_at.isoformat(),
                ]
            )

        return response
