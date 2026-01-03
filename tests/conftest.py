"""Pytest configuration and fixtures for aws-cost-analyzer tests."""

import pytest
from scanners.base_scanner import BaseScanner


@pytest.fixture(autouse=True)
def clear_cache():
    """
    Automatically clear the class-level cache before each test.
    
    This ensures tests don't interfere with each other when using
    the shared class-level cache in BaseScanner.
    """
    BaseScanner._cache.clear()
    
    yield
    
    BaseScanner._cache.clear()
