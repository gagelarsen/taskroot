from django.contrib import admin

from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
    Task,
)


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "status", "role")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("status", "role")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "start_date", "end_date", "budget_hours", "status")
    list_filter = ("status",)
    search_fields = ("id", "name", "client_name")


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
    list_display = ("id", "name", "contract", "start_date", "due_date", "status")
    list_filter = ("status",)
    search_fields = ("name", "id")
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
