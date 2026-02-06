from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnTimeEntryOrPrivileged(BasePermission):
    """
    All authenticated staff can edit/delete time entries.
    Time entries no longer track which staff member created them.
    """

    message = "You must be authenticated to modify time entries."

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        staff = getattr(request.user, "staff", None)
        if not staff:
            return False

        # All authenticated staff can edit time entries
        return True


class CanCreateTimeEntryAsStaff(BasePermission):
    """
    All authenticated staff can create time entries.
    Time entries no longer track which staff member created them.
    """

    def has_permission(self, request, view):
        # Allow all authenticated staff to create time entries
        return True


class CanCreateTaskAsStaff(BasePermission):
    """
    Staff can create tasks only if assignee is self or null.
    Managers/admins: allowed (should be handled by outer role permission).
    """

    message = "Staff can only create tasks assigned to themselves or unassigned."

    def has_permission(self, request, view):
        # This permission is only used for POST requests (create action)
        # Staff profile existence is guaranteed by view-level permissions
        staff = request.user.staff

        # Check for 'assignee' field (serializer field name), not 'assignee_id'
        # Handle both missing field and explicit null
        if "assignee" not in request.data:
            # Field not provided - allow (serializer will handle default)
            return True

        assignee_id = request.data.get("assignee")
        if assignee_id is None or assignee_id == "" or assignee_id == 0:
            # Explicitly null/empty - allow unassigned
            return True

        try:
            return int(assignee_id) == staff.id
        except (TypeError, ValueError):
            return False


class CanEditTaskAsStaff(BasePermission):
    """
    Staff can update tasks only if the task is assigned to them.
    """

    message = "Staff can only modify tasks assigned to themselves."

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        staff = getattr(request.user, "staff", None)
        if not staff:
            return False

        return obj.assignee_id == staff.id


def get_staff_role(request):
    """
    Returns the Staff.role for the authenticated user.
    Returns None if user is not authenticated or has no staff profile.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return None
    if not hasattr(request.user, "staff") or request.user.staff is None:
        return None
    return request.user.staff.role


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        role = get_staff_role(request)
        return role == "admin"


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        role = get_staff_role(request)
        return role in {"manager", "admin"}


class IsStaffOrAbove(BasePermission):
    """
    Everyone authenticated with a Staff profile.
    Use this for read access (paired with IsAuthenticated + HasStaffProfile defaults).
    """

    def has_permission(self, request, view):
        return True


class ReadOnlyForStaffOtherwiseManagerAdmin(BasePermission):
    """
    Staff can read only; Manager/Admin can write.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        role = get_staff_role(request)
        return role in {"manager", "admin"}


class HasStaffProfile(BasePermission):
    """
    Authenticated users must have an associated Staff record.
    If missing -> 403 (provisioning issue), with a clear message.
    """

    message = "Authenticated user is not linked to a Staff profile."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            # Let IsAuthenticated handle unauthenticated -> 401
            return True

        # With related_name="staff", this attribute exists only when linked.
        if hasattr(user, "staff") and user.staff is not None:
            return True

        # Raise explicit 403 with a clear message (instead of a silent False)
        raise PermissionDenied(detail=self.message)


class ReadAllWriteAdminOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        role = get_staff_role(request)
        return role == "admin"
