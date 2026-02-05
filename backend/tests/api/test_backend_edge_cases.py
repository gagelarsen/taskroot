"""
Tests for backend edge cases to achieve 100% coverage.
"""

import pytest
from rest_framework.request import Request

from core.api.v1.backends import CanonicalOrderingFilter
from core.models import Contract


@pytest.mark.django_db
class TestCanonicalOrderingFilter:
    """Test CanonicalOrderingFilter edge cases."""

    def test_ordering_with_no_ordering_fields_attribute(self, request_factory, staff_user):
        """Test ordering when view has no ordering_fields attribute (line 47)."""
        backend = CanonicalOrderingFilter()

        # Create a mock view without ordering_fields
        class MockView:
            pass

        view = MockView()
        queryset = Contract.objects.all()

        # Create request with ordering parameters
        django_request = request_factory.get("/api/v1/contracts/", {"order_by": "start_date", "order_dir": "asc"})
        django_request.user = staff_user
        request = Request(django_request)

        # Should return queryset unchanged (no ordering applied)
        result = backend.filter_queryset(request, queryset, view)
        assert result.query.order_by == queryset.query.order_by

    def test_ordering_with_dict_ordering_fields_valid(self, request_factory, staff_user):
        """Test ordering with dict-based ordering_fields (lines 51-53)."""
        backend = CanonicalOrderingFilter()

        # Create a mock view with dict ordering_fields
        class MockView:
            ordering_fields = {
                "start": "start_date",
                "end": "end_date",
            }

        view = MockView()
        queryset = Contract.objects.all()

        # Create request with valid alias
        django_request = request_factory.get("/api/v1/contracts/", {"order_by": "start", "order_dir": "asc"})
        django_request.user = staff_user
        request = Request(django_request)

        # Should apply ordering using the mapped field
        result = backend.filter_queryset(request, queryset, view)
        assert "start_date" in str(result.query.order_by)

    def test_ordering_with_dict_ordering_fields_invalid(self, request_factory, staff_user):
        """Test ordering with dict-based ordering_fields and invalid field (line 52-53)."""
        backend = CanonicalOrderingFilter()

        # Create a mock view with dict ordering_fields
        class MockView:
            ordering_fields = {
                "start": "start_date",
                "end": "end_date",
            }

        view = MockView()
        queryset = Contract.objects.all()

        # Create request with invalid alias
        django_request = request_factory.get("/api/v1/contracts/", {"order_by": "invalid_field", "order_dir": "asc"})
        django_request.user = staff_user
        request = Request(django_request)

        # Should return queryset unchanged (no ordering applied)
        result = backend.filter_queryset(request, queryset, view)
        assert result.query.order_by == queryset.query.order_by

    def test_ordering_without_order_by_param(self, request_factory, staff_user):
        """Test ordering when no order_by parameter is provided."""
        backend = CanonicalOrderingFilter()

        class MockView:
            ordering_fields = ["start_date", "end_date"]

        view = MockView()
        queryset = Contract.objects.all()

        # Create request without order_by parameter
        django_request = request_factory.get("/api/v1/contracts/")
        django_request.user = staff_user
        request = Request(django_request)

        # Should return queryset unchanged
        result = backend.filter_queryset(request, queryset, view)
        assert result.query.order_by == queryset.query.order_by

    def test_ordering_with_invalid_field_in_list(self, request_factory, staff_user):
        """Test ordering with invalid field when ordering_fields is a list."""
        backend = CanonicalOrderingFilter()

        class MockView:
            ordering_fields = ["start_date", "end_date"]

        view = MockView()
        queryset = Contract.objects.all()

        # Create request with field not in allowed list
        django_request = request_factory.get("/api/v1/contracts/", {"order_by": "invalid_field", "order_dir": "asc"})
        django_request.user = staff_user
        request = Request(django_request)

        # Should return queryset unchanged
        result = backend.filter_queryset(request, queryset, view)
        assert result.query.order_by == queryset.query.order_by

    def test_ordering_with_valid_field_in_list(self, request_factory, staff_user):
        """Test ordering with valid field when ordering_fields is a list."""
        backend = CanonicalOrderingFilter()

        class MockView:
            ordering_fields = ["start_date", "end_date"]

        view = MockView()
        queryset = Contract.objects.all()

        # Create request with valid field
        django_request = request_factory.get("/api/v1/contracts/", {"order_by": "start_date", "order_dir": "desc"})
        django_request.user = staff_user
        request = Request(django_request)

        # Should apply ordering
        result = backend.filter_queryset(request, queryset, view)
        assert "-start_date" in str(result.query.order_by)
