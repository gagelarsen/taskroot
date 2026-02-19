"""
Reporting API views for time series and burn reports.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from core.api.v1.permissions import ReadOnlyForStaffOtherwiseManagerAdmin
from core.api.v1.report_serializers import (
    ContractBurnReportSerializer,
    ContractDeliverablesReportSerializer,
    ContractTMBurnReportSerializer,
    DeliverableBurnReportSerializer,
    DeliverableStatusHistoryReportSerializer,
    StaffTimeReportSerializer,
)
from core.models import Contract, Deliverable, DeliverableTimeEntry, Staff


def get_week_ending_date(d: date) -> date:
    """
    Get the week ending date (Sunday) for a given date.
    If the date is already Sunday, return it. Otherwise, return the next Sunday.
    """
    # 6 = Sunday in Python's weekday() (0=Monday, 6=Sunday)
    # days_until_sunday will be 0 if already Sunday, otherwise 1-6
    days_until_sunday = (6 - d.weekday()) % 7
    return d + timedelta(days=days_until_sunday)


def generate_weekly_buckets(start_date: date, end_date: date):
    """
    Generate weekly bucket ending dates from start to end.
    Returns list of week-ending dates (Sundays).
    """
    buckets = []
    current = get_week_ending_date(start_date)

    while current <= end_date:
        buckets.append(current)
        current += timedelta(days=7)

    # Ensure we have at least one bucket
    if not buckets:
        buckets.append(get_week_ending_date(start_date))

    return buckets


class ContractReportViewSet(ViewSet):
    """
    Reporting endpoints for contracts.
    """

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Contract burn report",
        description="Get weekly burn data (expected vs actual) for a contract with budget signals",
        responses={200: ContractBurnReportSerializer},
        parameters=[
            OpenApiParameter(
                name="bucket",
                description="Time bucket size (week, day, month). Default: week",
                required=False,
                type=str,
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_path="burn")
    def burn(self, request, pk=None):
        """
        GET /api/v1/reports/contracts/{contract_id}/burn/

        Returns weekly buckets with expected vs actual hours and budget signals.
        """
        try:
            contract = Contract.objects.get(pk=pk)
        except Contract.DoesNotExist as err:
            raise NotFound("Contract not found") from err

        # For now, only support weekly buckets
        bucket_type = request.query_params.get("bucket", "week")
        if bucket_type != "week":
            return Response(
                {"error": "Only 'week' bucket type is currently supported"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Generate weekly buckets
        buckets = generate_weekly_buckets(contract.start_date, contract.end_date)

        # Get all deliverables for this contract
        _ = contract.deliverables.all()

        # Build bucket data
        bucket_data = []
        cumulative_expected = Decimal("0")
        cumulative_actual = Decimal("0")

        for bucket_end in buckets:
            # Calculate expected hours for this bucket
            # For simplicity, distribute expected hours evenly across weeks
            expected_for_bucket = contract.get_assigned_budget_hours() / len(buckets)

            # Calculate actual hours for this bucket
            # Sum all time entries with entry_date <= bucket_end and > previous bucket
            bucket_start = bucket_end - timedelta(days=6)
            actual_for_bucket = DeliverableTimeEntry.objects.filter(
                deliverable__contract=contract, entry_date__gte=bucket_start, entry_date__lte=bucket_end
            ).aggregate(total=Sum("hours"))["total"] or Decimal("0")

            cumulative_expected += expected_for_bucket
            cumulative_actual += actual_for_bucket

            bucket_data.append(
                {
                    "bucket": bucket_end,
                    "budget_hours": expected_for_bucket,
                    "actual_hours": actual_for_bucket,
                    "cumulative_expected": cumulative_expected,
                    "cumulative_actual": cumulative_actual,
                }
            )

        report_data = {
            "contract_id": contract.id,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
            "budget_hours": contract.budget_hours,
            "assigned_budget_hours": contract.get_assigned_budget_hours(),
            "spent_hours": contract.get_spent_hours(),
            "remaining_budget_hours": contract.get_unspent_budget_hours(),
            "is_over_budget": contract.is_over_budget(),
            "is_over_expected": contract.is_over_expected(),
            "buckets": bucket_data,
        }

        serializer = ContractBurnReportSerializer(report_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Contract deliverables summary",
        description="Get table-style summary of all deliverables in a contract",
        responses={200: ContractDeliverablesReportSerializer},
    )
    @action(detail=True, methods=["get"], url_path="deliverables")
    def deliverables_summary(self, request, pk=None):
        """
        GET /api/v1/reports/contracts/{contract_id}/deliverables/

        Returns summary of all deliverables with expected, actual, variance, and latest status.
        """
        try:
            contract = Contract.objects.get(pk=pk)
        except Contract.DoesNotExist as err:
            raise NotFound("Contract not found") from err

        deliverables_data = []
        for deliverable in contract.deliverables.all():
            latest_status_update = deliverable.get_latest_status_update()

            deliverables_data.append(
                {
                    "id": deliverable.id,
                    "name": deliverable.name,
                    "status": deliverable.status,
                    "assigned_budget_hours": deliverable.get_assigned_budget_hours(),
                    "spent_hours": deliverable.get_spent_hours(),
                    "variance_hours": deliverable.get_variance_hours(),
                    "latest_status": latest_status_update.summary if latest_status_update else None,
                }
            )

        report_data = {
            "contract_id": contract.id,
            "deliverables": deliverables_data,
        }

        serializer = ContractDeliverablesReportSerializer(report_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Time and materials burn report",
        description=("Get weekly invoice burndown and hours trend data for a time-and-materials contract."),
        responses={200: ContractTMBurnReportSerializer},
    )
    @action(detail=True, methods=["get"], url_path="tm-burn")
    def tm_burn(self, request, pk=None):
        try:
            contract = Contract.objects.get(pk=pk)
        except Contract.DoesNotExist as err:
            raise NotFound("Contract not found") from err

        if contract.contract_type != Contract.ContractType.TIME_AND_MATERIALS:
            return Response(
                {"error": "This endpoint is only available for time-and-materials contracts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if contract.contract_amount is None:
            return Response(
                {"error": "Contract amount is required for time-and-materials burn reporting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        buckets = generate_weekly_buckets(contract.start_date, contract.end_date)

        invoice_updates = contract.invoice_updates.filter(
            invoice_date__gte=contract.start_date,
            invoice_date__lte=contract.end_date,
        )
        weekly_invoice_amounts: dict[date, Decimal] = {}
        for update in invoice_updates:
            week_end = get_week_ending_date(update.invoice_date)
            weekly_invoice_amounts[week_end] = weekly_invoice_amounts.get(week_end, Decimal("0")) + update.amount

        time_entries = DeliverableTimeEntry.objects.filter(
            deliverable__contract=contract,
            entry_date__gte=contract.start_date,
            entry_date__lte=contract.end_date,
        )
        weekly_hours: dict[date, Decimal] = {}
        for entry in time_entries:
            week_end = get_week_ending_date(entry.entry_date)
            weekly_hours[week_end] = weekly_hours.get(week_end, Decimal("0")) + entry.hours

        bucket_data = []
        cumulative_invoiced = Decimal("0")
        cumulative_hours = Decimal("0")

        for bucket_end in buckets:
            invoice_amount = weekly_invoice_amounts.get(bucket_end, Decimal("0"))
            hours_for_week = weekly_hours.get(bucket_end, Decimal("0"))

            cumulative_invoiced += invoice_amount
            cumulative_hours += hours_for_week

            bucket_data.append(
                {
                    "bucket": bucket_end,
                    "invoice_amount": invoice_amount,
                    "cumulative_invoiced": cumulative_invoiced,
                    "remaining_contract_amount": contract.contract_amount - cumulative_invoiced,
                    "weekly_hours": hours_for_week,
                    "cumulative_hours": cumulative_hours,
                }
            )

        report_data = {
            "contract_id": contract.id,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
            "contract_amount": contract.contract_amount,
            "invoiced_amount": contract.get_invoiced_amount(),
            "remaining_contract_amount": contract.get_remaining_contract_amount(),
            "spent_hours": contract.get_spent_hours(),
            "buckets": bucket_data,
        }

        serializer = ContractTMBurnReportSerializer(report_data)
        return Response(serializer.data)


class DeliverableReportViewSet(ViewSet):
    """
    Reporting endpoints for deliverables.
    """

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Deliverable burn report",
        description="Get weekly burn data (expected vs actual) for a deliverable",
        responses={200: DeliverableBurnReportSerializer},
        parameters=[
            OpenApiParameter(
                name="bucket",
                description="Time bucket size (week, day, month). Default: week",
                required=False,
                type=str,
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_path="burn")
    def burn(self, request, pk=None):
        """
        GET /api/v1/reports/deliverables/{deliverable_id}/burn/

        Returns weekly buckets with expected vs actual hours.
        """
        try:
            deliverable = Deliverable.objects.get(pk=pk)
        except Deliverable.DoesNotExist as err:
            raise NotFound("Deliverable not found") from err

        # For now, only support weekly buckets
        bucket_type = request.query_params.get("bucket", "week")
        if bucket_type != "week":
            return Response(
                {"error": "Only 'week' bucket type is currently supported"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Use contract dates for deliverable burn report
        start = deliverable.contract.start_date
        end = deliverable.contract.end_date

        # Generate weekly buckets
        buckets = generate_weekly_buckets(start, end)

        # Build bucket data
        bucket_data = []
        cumulative_expected = Decimal("0")
        cumulative_actual = Decimal("0")

        for bucket_end in buckets:
            # Distribute expected hours evenly across weeks
            expected_for_bucket = deliverable.get_assigned_budget_hours() / len(buckets)

            # Calculate actual hours for this bucket
            bucket_start = bucket_end - timedelta(days=6)
            actual_for_bucket = DeliverableTimeEntry.objects.filter(
                deliverable=deliverable, entry_date__gte=bucket_start, entry_date__lte=bucket_end
            ).aggregate(total=Sum("hours"))["total"] or Decimal("0")

            cumulative_expected += expected_for_bucket
            cumulative_actual += actual_for_bucket

            bucket_data.append(
                {
                    "bucket": bucket_end,
                    "budget_hours": expected_for_bucket,
                    "actual_hours": actual_for_bucket,
                    "cumulative_expected": cumulative_expected,
                    "cumulative_actual": cumulative_actual,
                }
            )

        report_data = {
            "deliverable_id": deliverable.id,
            "name": deliverable.name,
            "assigned_budget_hours": deliverable.get_assigned_budget_hours(),
            "spent_hours": deliverable.get_spent_hours(),
            "variance_hours": deliverable.get_variance_hours(),
            "is_over_expected": deliverable.is_over_expected(),
            "buckets": bucket_data,
        }

        serializer = DeliverableBurnReportSerializer(report_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Deliverable status history",
        description="Get ordered status history for a deliverable",
        responses={200: DeliverableStatusHistoryReportSerializer},
    )
    @action(detail=True, methods=["get"], url_path="status-history")
    def status_history(self, request, pk=None):
        """
        GET /api/v1/reports/deliverables/{deliverable_id}/status-history/

        Returns status updates ordered by period_end.
        """
        try:
            deliverable = Deliverable.objects.get(pk=pk)
        except Deliverable.DoesNotExist as err:
            raise NotFound("Deliverable not found") from err

        # Get all status updates ordered by period_end
        status_updates = deliverable.status_updates.all().order_by("period_end")

        status_history_data = [
            {
                "period_end": update.period_end,
                "status": update.status,
                "summary": update.summary,
                "created_at": update.created_at,
            }
            for update in status_updates
        ]

        report_data = {
            "deliverable_id": deliverable.id,
            "name": deliverable.name,
            "status_history": status_history_data,
        }

        serializer = DeliverableStatusHistoryReportSerializer(report_data)
        return Response(serializer.data)


class StaffReportViewSet(ViewSet):
    """
    Reporting endpoints for staff utilization.
    """

    permission_classes = [ReadOnlyForStaffOtherwiseManagerAdmin]

    @extend_schema(
        summary="Staff time report",
        description="Get weekly time report for a staff member, optionally filtered by contract",
        responses={200: StaffTimeReportSerializer},
        parameters=[
            OpenApiParameter(
                name="contract_id",
                description="Filter by contract ID",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="start_date",
                description="Start date for report (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="end_date",
                description="End date for report (YYYY-MM-DD)",
                required=False,
                type=str,
            ),
        ],
    )
    @action(detail=True, methods=["get"], url_path="time")
    def time_report(self, request, pk=None):
        """
        GET /api/v1/reports/staff/{staff_id}/time/

        Returns weekly time buckets grouped by deliverable/contract.

        NOTE: Time entries no longer track staff, so this endpoint returns empty results.
        Consider using deliverable assignments for staff utilization reporting.
        """
        try:
            staff_member = Staff.objects.get(pk=pk)
        except Staff.DoesNotExist as err:
            raise NotFound("Staff member not found") from err

        # Time entries no longer track staff, so return empty result
        # Validate query parameters for backwards compatibility
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if start_date_str:
            try:
                date.fromisoformat(start_date_str)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )

        if end_date_str:
            try:
                date.fromisoformat(end_date_str)
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST
                )

        # Return empty buckets since time entries no longer track staff
        report_data = {
            "staff_id": staff_member.id,
            "staff_name": f"{staff_member.first_name} {staff_member.last_name}".strip() or staff_member.email,
            "buckets": [],
        }

        serializer = StaffTimeReportSerializer(report_data)
        return Response(serializer.data)
