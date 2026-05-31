"""
Pytest configuration and fixtures for all tests.

Disables rate limiting during tests to prevent 429 errors.
"""

import pytest
from rest_framework.throttling import SimpleRateThrottle


@pytest.fixture(autouse=True)
def disable_throttle(monkeypatch):
    """Disable all throttling during tests."""
    # Patch allow_request to always return True
    monkeypatch.setattr(
        SimpleRateThrottle,
        'allow_request',
        lambda self, request, view: True
    )
