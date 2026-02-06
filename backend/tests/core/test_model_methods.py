"""
Tests for model methods and computed properties.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from core.models import Contract


@pytest.mark.django_db
class TestContractMethods:
    """Test Contract model methods."""

    @patch("core.models.contract.date")
    def test_get_elapsed_weeks_before_start_date(self, mock_date):
        """Test get_elapsed_weeks when today is before start_date."""
        # Mock today to be before the contract start
        mock_today = date(2024, 1, 1)
        mock_date.today.return_value = mock_today

        # Create a contract that starts in the future
        future_start = date(2024, 2, 1)  # 1 month in the future
        future_end = date(2024, 12, 31)

        contract = Contract.objects.create(
            start_date=future_start,
            end_date=future_end,
            budget_hours=Decimal("1000.0"),
        )

        # Should return 1 (not started yet)
        assert contract.get_elapsed_weeks() == 1

    def test_get_elapsed_weeks_after_start_date(self):
        """Test get_elapsed_weeks when today is after start_date."""
        # Create a contract that started in the past
        past_start = date.today() - timedelta(days=14)  # 2 weeks ago
        future_end = date.today() + timedelta(days=365)

        contract = Contract.objects.create(
            start_date=past_start,
            end_date=future_end,
            budget_hours=Decimal("1000.0"),
        )

        # Should return at least 3 weeks (2 weeks + current week)
        assert contract.get_elapsed_weeks() >= 3

    def test_get_elapsed_weeks_after_end_date(self):
        """Test get_elapsed_weeks when today is after end_date."""
        # Create a contract that has ended
        past_start = date.today() - timedelta(days=365)
        past_end = date.today() - timedelta(days=30)

        contract = Contract.objects.create(
            start_date=past_start,
            end_date=past_end,
            budget_hours=Decimal("1000.0"),
        )

        # Should use end_date instead of today
        elapsed = contract.get_elapsed_weeks()
        assert elapsed > 1
        # Verify it's using end_date by checking it's less than if we used today
        days_to_end = (past_end - past_start).days + 1
        expected_weeks = max(1, (days_to_end + 6) // 7)  # Ceiling division
        assert elapsed == expected_weeks
