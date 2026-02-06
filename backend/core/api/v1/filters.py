import django_filters
from django.db.models import Exists, OuterRef

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
    Task,
)


def _parse_bool(value: str | None):
    if value is None:
        return None
    v = value.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


class ContractFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")

    start_date_from = django_filters.DateFilter(field_name="start_date", lookup_expr="gte")
    start_date_to = django_filters.DateFilter(field_name="start_date", lookup_expr="lte")
    end_date_from = django_filters.DateFilter(field_name="end_date", lookup_expr="gte")
    end_date_to = django_filters.DateFilter(field_name="end_date", lookup_expr="lte")

    # Health filters
    over_budget = django_filters.CharFilter(method="filter_over_budget")
    over_expected = django_filters.CharFilter(method="filter_over_expected")

    class Meta:
        model = Contract
        fields = [
            "status",
            "start_date_from",
            "start_date_to",
            "end_date_from",
            "end_date_to",
            "over_budget",
            "over_expected",
        ]

    def filter_over_budget(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        # Filter in Python since this is a computed field
        if b:
            return queryset.filter(pk__in=[c.pk for c in queryset if c.is_over_budget()])
        else:
            return queryset.filter(pk__in=[c.pk for c in queryset if not c.is_over_budget()])

    def filter_over_expected(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        # Filter in Python since this is a computed field
        if b:
            return queryset.filter(pk__in=[c.pk for c in queryset if c.is_over_expected()])
        else:
            return queryset.filter(pk__in=[c.pk for c in queryset if not c.is_over_expected()])


class DeliverableFilter(django_filters.FilterSet):
    # Canonical FK params
    contract_id = django_filters.NumberFilter(field_name="contract_id")
    status = django_filters.CharFilter(field_name="status")

    # Canonical date ranges
    target_completion_date_from = django_filters.DateFilter(field_name="target_completion_date", lookup_expr="gte")
    target_completion_date_to = django_filters.DateFilter(field_name="target_completion_date", lookup_expr="lte")

    # Relationship-based filters (custom)
    staff_id = django_filters.NumberFilter(method="filter_staff_id")
    lead_only = django_filters.CharFilter(method="filter_lead_only")
    has_assignments = django_filters.CharFilter(method="filter_has_assignments")

    # Health filters
    over_expected = django_filters.CharFilter(method="filter_over_expected")
    missing_lead = django_filters.CharFilter(method="filter_missing_lead")
    missing_estimate = django_filters.CharFilter(method="filter_missing_estimate")

    class Meta:
        model = Deliverable
        fields = [
            "contract_id",
            "status",
            "target_completion_date_from",
            "target_completion_date_to",
            "staff_id",
            "lead_only",
            "has_assignments",
            "over_expected",
            "missing_lead",
            "missing_estimate",
        ]

    def filter_staff_id(self, queryset, name, value):
        # Deliverables where the given staff member is assigned
        # NumberFilter ensures value is valid or method isn't called
        return queryset.filter(assignments__staff_id=value).distinct()

    def filter_lead_only(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset

        # Use EXISTS to avoid duplicate rows and keep query efficient.
        lead_qs = DeliverableAssignment.objects.filter(deliverable_id=OuterRef("pk"), is_lead=True)
        annotated = queryset.annotate(_has_lead=Exists(lead_qs))
        return annotated.filter(_has_lead=b)

    def filter_has_assignments(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset

        assign_qs = DeliverableAssignment.objects.filter(deliverable_id=OuterRef("pk"))
        annotated = queryset.annotate(_has_assignments=Exists(assign_qs))
        return annotated.filter(_has_assignments=b)

    def filter_over_expected(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        # Filter in Python since this is a computed field
        if b:
            return queryset.filter(pk__in=[d.pk for d in queryset if d.is_over_expected()])
        else:
            return queryset.filter(pk__in=[d.pk for d in queryset if not d.is_over_expected()])

    def filter_missing_lead(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        # Filter in Python since this is a computed field
        if b:
            return queryset.filter(pk__in=[d.pk for d in queryset if d.is_missing_lead()])
        else:
            return queryset.filter(pk__in=[d.pk for d in queryset if not d.is_missing_lead()])

    def filter_missing_estimate(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        # Filter in Python since this is a computed field
        if b:
            return queryset.filter(pk__in=[d.pk for d in queryset if d.is_missing_budget()])
        else:
            return queryset.filter(pk__in=[d.pk for d in queryset if not d.is_missing_budget()])


class TaskFilter(django_filters.FilterSet):
    contract_id = django_filters.NumberFilter(field_name="deliverable__contract_id")
    deliverable_id = django_filters.NumberFilter(field_name="deliverable_id")
    assignee_id = django_filters.NumberFilter(field_name="assignee_id")
    status = django_filters.CharFilter(field_name="status")

    # Canonical boolean filter: unassigned=true|false
    unassigned = django_filters.CharFilter(method="filter_unassigned")

    # Task doesn't necessarily have due_date; filter on deliverable's due_date for now.
    due_date_from = django_filters.DateFilter(field_name="deliverable__due_date", lookup_expr="gte")
    due_date_to = django_filters.DateFilter(field_name="deliverable__due_date", lookup_expr="lte")

    class Meta:
        model = Task
        fields = [
            "contract_id",
            "deliverable_id",
            "assignee_id",
            "unassigned",
            "status",
            "due_date_from",
            "due_date_to",
        ]

    def filter_unassigned(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        if b:
            return queryset.filter(assignee__isnull=True)
        return queryset.filter(assignee__isnull=False)


class DeliverableAssignmentFilter(django_filters.FilterSet):
    contract_id = django_filters.NumberFilter(field_name="deliverable__contract_id")
    deliverable_id = django_filters.NumberFilter(field_name="deliverable_id")
    staff_id = django_filters.NumberFilter(field_name="staff_id")

    lead_only = django_filters.CharFilter(method="filter_lead_only")

    class Meta:
        model = DeliverableAssignment
        fields = ["contract_id", "deliverable_id", "staff_id", "lead_only"]

    def filter_lead_only(self, queryset, name, value):
        b = _parse_bool(value)
        if b is None:
            return queryset
        return queryset.filter(is_lead=b)


class DeliverableTimeEntryFilter(django_filters.FilterSet):
    contract_id = django_filters.NumberFilter(field_name="deliverable__contract_id")
    deliverable_id = django_filters.NumberFilter(field_name="deliverable_id")

    entry_date_from = django_filters.DateFilter(field_name="entry_date", lookup_expr="gte")
    entry_date_to = django_filters.DateFilter(field_name="entry_date", lookup_expr="lte")

    class Meta:
        model = DeliverableTimeEntry
        fields = [
            "contract_id",
            "deliverable_id",
            "entry_date_from",
            "entry_date_to",
        ]


class DeliverableStatusUpdateFilter(django_filters.FilterSet):
    contract_id = django_filters.NumberFilter(field_name="deliverable__contract_id")
    deliverable_id = django_filters.NumberFilter(field_name="deliverable_id")
    status = django_filters.CharFilter(field_name="status")

    period_end_from = django_filters.DateFilter(field_name="period_end", lookup_expr="gte")
    period_end_to = django_filters.DateFilter(field_name="period_end", lookup_expr="lte")

    class Meta:
        model = DeliverableStatusUpdate
        fields = [
            "contract_id",
            "deliverable_id",
            "status",
            "period_end_from",
            "period_end_to",
        ]


class StaffFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="status")
    role = django_filters.CharFilter(field_name="role")

    class Meta:
        model = Staff
        fields = ["status", "role"]
