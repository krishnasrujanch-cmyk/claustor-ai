"""Unit tests for alert service thresholds."""
import pytest
from app.services.alert_service import RENEWAL_ALERT_DAYS, OBLIGATION_ALERT_DAYS


def test_renewal_alert_days_defined():
    assert len(RENEWAL_ALERT_DAYS) > 0
    assert 30 in RENEWAL_ALERT_DAYS
    assert 7 in RENEWAL_ALERT_DAYS


def test_obligation_alert_days_defined():
    assert len(OBLIGATION_ALERT_DAYS) > 0
    assert 1 in OBLIGATION_ALERT_DAYS  # day before


def test_renewal_days_sorted_descending():
    assert RENEWAL_ALERT_DAYS == sorted(RENEWAL_ALERT_DAYS, reverse=True)


def test_obligation_days_sorted_descending():
    assert OBLIGATION_ALERT_DAYS == sorted(OBLIGATION_ALERT_DAYS, reverse=True)


def test_earliest_renewal_alert():
    assert max(RENEWAL_ALERT_DAYS) >= 90  # at least 90 days advance notice


def test_last_obligation_alert():
    assert min(OBLIGATION_ALERT_DAYS) == 1  # always alert day before
