# -*- coding: utf-8 -*-
"""
FOMC Calendar & Options Expiration Utilities

Hardcoded FOMC meeting dates and helper functions for
calculating monthly options expiration (OPEX) dates.
"""

from datetime import date, timedelta
from typing import List, Optional

# FOMC meeting dates (announcement day) for 2025-2026
# Source: Federal Reserve official schedule
FOMC_DATES = [
    # 2025
    date(2025, 1, 29),
    date(2025, 3, 19),
    date(2025, 5, 7),
    date(2025, 6, 18),
    date(2025, 7, 30),
    date(2025, 9, 17),
    date(2025, 10, 29),
    date(2025, 12, 17),
    # 2026
    date(2026, 1, 28),
    date(2026, 3, 18),
    date(2026, 4, 29),
    date(2026, 6, 17),
    date(2026, 7, 29),
    date(2026, 9, 16),
    date(2026, 10, 28),
    date(2026, 12, 16),
]


def get_next_fomc(from_date: Optional[date] = None) -> Optional[date]:
    """
    Get the next FOMC meeting date from a given date.

    Args:
        from_date: Reference date (defaults to today)

    Returns:
        Next FOMC date or None if beyond calendar range
    """
    ref = from_date or date.today()
    for d in FOMC_DATES:
        if d >= ref:
            return d
    return None


def get_upcoming_fomc(from_date: Optional[date] = None, days_ahead: int = 30) -> List[date]:
    """Get all FOMC dates within the next N days."""
    ref = from_date or date.today()
    cutoff = ref + timedelta(days=days_ahead)
    return [d for d in FOMC_DATES if ref <= d <= cutoff]


def get_next_opex(from_date: Optional[date] = None) -> date:
    """
    Get the next monthly options expiration date (3rd Friday of month).

    Args:
        from_date: Reference date (defaults to today)

    Returns:
        Next OPEX date
    """
    ref = from_date or date.today()

    # Start with current month
    year, month = ref.year, ref.month

    for _ in range(3):  # Check up to 3 months ahead
        opex = _third_friday(year, month)
        if opex >= ref:
            return opex
        # Move to next month
        month += 1
        if month > 12:
            month = 1
            year += 1

    return _third_friday(year, month)


def _third_friday(year: int, month: int) -> date:
    """Calculate the 3rd Friday of a given month."""
    # Find the first day of the month
    first_day = date(year, month, 1)
    # Find the first Friday (weekday 4)
    days_until_friday = (4 - first_day.weekday()) % 7
    first_friday = first_day + timedelta(days=days_until_friday)
    # Third Friday is 14 days after first Friday
    third_friday = first_friday + timedelta(days=14)
    return third_friday


def days_until(target: date, from_date: Optional[date] = None) -> int:
    """Calculate business days until a target date (approximate)."""
    ref = from_date or date.today()
    delta = (target - ref).days
    return max(0, delta)
