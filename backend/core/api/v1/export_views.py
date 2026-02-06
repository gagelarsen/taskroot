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
from core.models import Contract, DeliverableTimeEntry


class TimeEntriesCSVExport(APIView):
    """
    Export time entries to CSV format.
    """

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Export time entries to CSV",
        description="Export time entries with optional filters (contract_id, deliverable_id, staff_id, date range)",
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
                name="staff_id",
                description="Filter by staff ID",
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
            .select_related("deliverable", "deliverable__contract", "staff")
            .order_by("entry_date", "id")
        )

        # Apply filters
        contract_id = request.query_params.get("contract_id")
        if contract_id:
            queryset = queryset.filter(deliverable__contract_id=contract_id)

        deliverable_id = request.query_params.get("deliverable_id")
        if deliverable_id:
            queryset = queryset.filter(deliverable_id=deliverable_id)

        staff_id = request.query_params.get("staff_id")
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

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
                "Staff ID",
                "Staff Name",
                "Staff Email",
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
            staff_name = f"{entry.staff.first_name} {entry.staff.last_name}".strip() or entry.staff.email
            writer.writerow(
                [
                    entry.id,
                    entry.entry_date,
                    entry.hours,
                    entry.staff.id,
                    staff_name,
                    entry.staff.email,
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
