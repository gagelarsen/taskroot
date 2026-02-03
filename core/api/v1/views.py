from rest_framework.viewsets import ModelViewSet

from core.api.v1.serializers import (
    ContractSerializer,
    DeliverableAssignmentSerializer,
    DeliverableSerializer,
    DeliverableStatusUpdateSerializer,
    DeliverableTimeEntrySerializer,
    StaffSerializer,
    TaskSerializer,
)
from core.models import (
    Contract,
    Deliverable,
    DeliverableAssignment,
    DeliverableStatusUpdate,
    DeliverableTimeEntry,
    Staff,
    Task,
)


class StaffViewSet(ModelViewSet):
    queryset = Staff.objects.all().order_by("-id")
    serializer_class = StaffSerializer


class ContractViewSet(ModelViewSet):
    queryset = Contract.objects.all().order_by("-id")
    serializer_class = ContractSerializer


class DeliverableViewSet(ModelViewSet):
    queryset = Deliverable.objects.all().order_by("-id")
    serializer_class = DeliverableSerializer


class TaskViewSet(ModelViewSet):
    queryset = Task.objects.all().order_by("-id")
    serializer_class = TaskSerializer


class DeliverableAssignmentViewSet(ModelViewSet):
    queryset = DeliverableAssignment.objects.all().order_by("-id")
    serializer_class = DeliverableAssignmentSerializer


class DeliverableTimeEntryViewSet(ModelViewSet):
    queryset = DeliverableTimeEntry.objects.all().order_by("-id")
    serializer_class = DeliverableTimeEntrySerializer


class DeliverableStatusUpdateViewSet(ModelViewSet):
    queryset = DeliverableStatusUpdate.objects.all().order_by("-id")
    serializer_class = DeliverableStatusUpdateSerializer
