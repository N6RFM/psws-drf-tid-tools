from pathlib import Path
#!/usr/bin/env python3
"""
conftest.py -- pytest integration for the psws-drf-tid-tools synthetic
test suite.

Usage:
    cd synthetic_tests/
    pytest -v                          # run all 20 conditions x autocorr+cwt
    pytest -v -k "nominal or az_south" # run specific tests
    pytest -v -k "not alias"           # skip alias demos
    pytest --method autocorr           # single method only

Generates synthetic DRF on first run (cached in ~/psws-tools-pr/synthetic_tests/events/
by default; override with --event-root). Subsequent runs reuse cached
DRF files (fast, ~5 min for all tests).

CI note: wave-fit and cwt-prophet require a display (GUI). In headless
CI environments, set PYTEST_METHODS=autocorr,cwt to skip GUI methods.
"""
import os
import pathlib
import pytest

# Allow override via environment variable
DEFAULT_METHODS = os.environ.get("PYTEST_METHODS", "autocorr,cwt").split(",")
DEFAULT_EVENT_ROOT = os.environ.get(
    "PYTEST_EVENT_ROOT", str(Path(__file__).parent / "events"))


def pytest_addoption(parser):
    parser.addoption(
        "--method", action="store", default=None,
        help="Extraction method(s) to test, comma-separated "
             "(default: autocorr,cwt)"
    )
    parser.addoption(
        "--event-root", action="store", default=DEFAULT_EVENT_ROOT,
        help="Root directory for synthetic DRF events "
             f"(default: {DEFAULT_EVENT_ROOT})"
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "expect_pass: mark test as expected to pass (recovers correct result)"
    )
    config.addinivalue_line(
        "markers",
        "alias_demo: mark test as demonstrating period aliasing"
    )
    config.addinivalue_line(
        "markers",
        "stress: mark test as a stress/edge-case expected to fail"
    )


def pytest_generate_tests(metafunc):
    """Parametrize tests over (test_condition, method) pairs."""
    if "test_condition" in metafunc.fixturenames:
        from test_conditions import TEST_CONDITIONS
        metafunc.parametrize(
            "test_condition",
            TEST_CONDITIONS,
            ids=[tc[0] for tc in TEST_CONDITIONS],
        )

    if "extraction_method" in metafunc.fixturenames:
        method_opt = metafunc.config.getoption("--method")
        if method_opt:
            methods = [m.strip() for m in method_opt.split(",")]
        else:
            methods = DEFAULT_METHODS
        metafunc.parametrize("extraction_method", methods)


@pytest.fixture(scope="session")
def event_root(request):
    root = pathlib.Path(request.config.getoption("--event-root"))
    root.mkdir(parents=True, exist_ok=True)
    return root
