from django.contrib import admin

from core.models import (
    ChargeCode,
    Contract,
    ContractInvoiceUpdate,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
    Task,
    UnmappedChargeCodeEntry,
)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "status", "role")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("status", "role")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "contract_number",
        "start_date",
        "end_date",
        "budget_hours",
        "contract_amount",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("id", "name", "contract_number", "client_name")


@admin.register(ContractInvoiceUpdate)
class ContractInvoiceUpdateAdmin(admin.ModelAdmin):
    list_display = ("id", "contract", "invoice_date", "amount")
    list_filter = ("invoice_date",)
    search_fields = ("contract__name", "contract__contract_number")
    autocomplete_fields = ("contract",)


class UnmappedChargeCodeEntryInline(admin.TabularInline):
    model = UnmappedChargeCodeEntry
    extra = 0
    fields = ("entry_date", "hours", "note", "source_file", "created_at")
    readonly_fields = ("created_at",)


@admin.register(ChargeCode)
class ChargeCodeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "description", "allotted_hours", "deliverable", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "description", "deliverable__name")
    autocomplete_fields = ("deliverable",)
    inlines = (UnmappedChargeCodeEntryInline,)


@admin.register(UnmappedChargeCodeEntry)
class UnmappedChargeCodeEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "charge_code", "entry_date", "hours", "source_file", "created_at")
    list_filter = ("entry_date", "created_at")
    search_fields = ("charge_code__code", "note", "source_file")
    autocomplete_fields = ("charge_code",)


class DeliverableAssignmentInline(admin.TabularInline):
    model = DeliverableAssignment
    extra = 0
    autocomplete_fields = ("staff",)


class DeliverableTimeEntryInline(admin.TabularInline):
    model = DeliverableTimeEntry
    extra = 0


class DeliverableStatusUpdateInline(admin.TabularInline):
    model = DeliverableStatusUpdate
    extra = 0
    autocomplete_fields = ("created_by",)


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    autocomplete_fields = ("assignee",)


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "charge_code", "contract", "target_completion_date", "status")
    list_filter = ("status",)
    search_fields = ("name", "charge_code", "id")
    autocomplete_fields = ("contract",)
    inlines = (DeliverableAssignmentInline, DeliverableTimeEntryInline, DeliverableStatusUpdateInline, TaskInline)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "deliverable", "assignee", "budget_hours", "status")
    list_filter = ("status",)
    search_fields = ("title",)
    autocomplete_fields = ("deliverable", "assignee")


@admin.register(DeliverableAssignment)
class DeliverableAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "deliverable", "staff", "budget_hours", "is_lead")
    list_filter = ("is_lead",)
    autocomplete_fields = ("deliverable", "staff")


@admin.register(DeliverableTimeEntry)
class DeliverableTimeEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "deliverable", "entry_date", "hours")
    autocomplete_fields = ("deliverable",)
    list_filter = ("entry_date",)


@admin.register(DeliverableStatusUpdate)
class DeliverableStatusUpdateAdmin(admin.ModelAdmin):
    list_display = ("id", "deliverable", "period_end", "status", "created_by", "created_at")
    list_filter = ("status", "period_end")
    autocomplete_fields = ("deliverable", "created_by")
