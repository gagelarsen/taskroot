from rest_framework.filters import BaseFilterBackend


class CanonicalSearchFilter(BaseFilterBackend):
    """
    Implements canonical text search param: ?q=...
    Uses view.search_fields (same idea as DRF SearchFilter), but with 'q' instead of 'search'.
    """

    search_param = "q"

    def filter_queryset(self, request, queryset, view):
        q = request.query_params.get(self.search_param)
        search_fields = getattr(view, "search_fields", None)
        if not q or not search_fields:
            return queryset

        # Build OR query across search_fields using icontains.
        from django.db.models import Q

        conditions = Q()
        for field in search_fields:
            conditions |= Q(**{f"{field}__icontains": q})

        return queryset.filter(conditions)


class CanonicalOrderingFilter(BaseFilterBackend):
    """
    Implements canonical ordering params:
      ?order_by=<field>&order_dir=asc|desc

    The view must declare ordering_fields = {...} or [..]
    Only allows whitelisted fields to avoid exposing arbitrary ordering (stability + safety).
    """

    order_by_param = "order_by"
    order_dir_param = "order_dir"

    def filter_queryset(self, request, queryset, view):
        order_by = request.query_params.get(self.order_by_param)
        if not order_by:
            return queryset

        allowed = getattr(view, "ordering_fields", None)
        if not allowed:
            return queryset

        # allowed can be list/tuple/set or dict mapping aliases -> fields
        if isinstance(allowed, dict):
            order_by = allowed.get(order_by)
            if not order_by:
                return queryset
        else:
            if order_by not in allowed:
                return queryset

        order_dir = request.query_params.get(self.order_dir_param, "asc").lower()
        if order_dir not in ("asc", "desc"):
            order_dir = "asc"

        prefix = "-" if order_dir == "desc" else ""
        return queryset.order_by(f"{prefix}{order_by}")
