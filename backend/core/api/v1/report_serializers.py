"""
Serializers for reporting endpoints.

These serializers define the "shapes" (API contracts) for time series and reporting data.
"""

from rest_framework import serializers


class BurnBucketSerializer(serializers.Serializer):
    """
    Represents a single time bucket in a burn report.

    Used for weekly/daily/monthly burn data showing expected vs actual hours.
    """

    bucket = serializers.DateField(help_text="The ending date of this time bucket (e.g., week ending date)")
    expected_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Expected hours for this bucket"
    )
    actual_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Actual hours logged for this bucket"
    )
    cumulative_expected = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Cumulative expected hours up to and including this bucket"
    )
    cumulative_actual = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Cumulative actual hours up to and including this bucket"
    )


class ContractBurnReportSerializer(serializers.Serializer):
    """
    Contract burn report with weekly buckets and budget signals.
    """

    contract_id = serializers.IntegerField(help_text="Contract ID")
    start_date = serializers.DateField(help_text="Contract start date")
    end_date = serializers.DateField(help_text="Contract end date")
    budget_hours_total = serializers.DecimalField(max_digits=10, decimal_places=2, help_text="Total budget hours")
    expected_hours_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Total expected hours from all deliverables"
    )
    actual_hours_total = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Total actual hours logged"
    )
    remaining_budget_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Remaining budget hours (budget - actual)"
    )
    is_over_budget = serializers.BooleanField(help_text="True if actual hours exceed budget")
    is_over_expected = serializers.BooleanField(help_text="True if actual hours exceed expected")
    buckets = BurnBucketSerializer(many=True, help_text="Time series data buckets (weekly by default)")


class DeliverableSummarySerializer(serializers.Serializer):
    """
    Summary of a deliverable for contract reporting.
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    expected_hours_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    actual_hours_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    variance_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2, help_text="Difference between actual and expected (actual - expected)"
    )
    latest_status = serializers.CharField(allow_null=True, help_text="Latest status update summary")


class ContractDeliverablesReportSerializer(serializers.Serializer):
    """
    Table-style summary of all deliverables in a contract.
    """

    contract_id = serializers.IntegerField()
    deliverables = DeliverableSummarySerializer(many=True)


class DeliverableBurnReportSerializer(serializers.Serializer):
    """
    Deliverable burn report with weekly buckets.
    """

    deliverable_id = serializers.IntegerField()
    name = serializers.CharField()
    start_date = serializers.DateField(allow_null=True)
    due_date = serializers.DateField(allow_null=True)
    expected_hours_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    actual_hours_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    variance_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    is_over_expected = serializers.BooleanField()
    buckets = BurnBucketSerializer(many=True)


class StatusHistoryEntrySerializer(serializers.Serializer):
    """
    Single status history entry for a deliverable.
    """

    period_end = serializers.DateField()
    status = serializers.CharField()
    summary = serializers.CharField()
    created_at = serializers.DateTimeField()


class DeliverableStatusHistoryReportSerializer(serializers.Serializer):
    """
    Deliverable status history report.
    """

    deliverable_id = serializers.IntegerField()
    name = serializers.CharField()
    status_history = StatusHistoryEntrySerializer(many=True)


class StaffTimeReportSerializer(serializers.Serializer):
    """
    Staff time report grouped by week.
    """

    staff_id = serializers.IntegerField()
    staff_name = serializers.CharField()
    buckets = serializers.ListField(
        child=serializers.DictField(), help_text="Weekly time buckets with hours by deliverable/contract"
    )
