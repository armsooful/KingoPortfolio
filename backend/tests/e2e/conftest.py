import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "/tests/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


def pytest_configure(config):
    """커스텀 마커 등록"""
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "p0: Priority 0 (must pass)")
    config.addinivalue_line("markers", "p1: Priority 1 (should pass)")
