#!/usr/bin/env python3
"""
test_pipeline.py -- pytest test cases for psws-drf-tid-tools synthetic
validation suite.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Each parametrized test runs one (test_condition, extraction_method) pair
through the full pipeline: DRF generation → extraction → DOA → evaluation.
"""
import pytest
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from synthetic_drf import generate_event
from run_tests import run_one_test
from evaluate import evaluate
from test_conditions import TEST_CONDITIONS


def pytest_collection_modifyitems(items):
    """Add markers based on test condition metadata."""
    tc_map = {tc[0]: tc for tc in TEST_CONDITIONS}
    for item in items:
        if hasattr(item, "callspec"):
            tc = item.callspec.params.get("test_condition")
            if tc:
                name, *_, expect_pass, notes = tc
                if expect_pass:
                    item.add_marker(pytest.mark.expect_pass)
                elif "ALIAS" in notes:
                    item.add_marker(pytest.mark.alias_demo)
                else:
                    item.add_marker(pytest.mark.stress)


def test_synthetic_pipeline(test_condition, extraction_method, event_root):
    """
    End-to-end pipeline test: generate synthetic DRF, extract Doppler,
    run DOA, evaluate against ground truth.

    Parameters come from conftest.py parametrization.
    """
    result = run_one_test(
        test_condition,
        extraction_method,
        str(event_root),
        verbose=False,
    )

    name       = result["test"]
    expect     = result["expect_pass"]
    overall    = result["overall_pass"]
    category   = result.get("category", "")
    note       = result.get("note", "")
    spd_err    = result.get("speed_error_pct")
    az_err     = result.get("azimuth_error_deg")
    n_flags    = result.get("n_flags")

    # Build a clear failure message
    msg = (
        f"\nTest: {name} / {extraction_method}\n"
        f"  expect_pass={expect}  category={category}\n"
        f"  speed_error={spd_err}%  az_error={az_err}°  flags={n_flags}\n"
        f"  note: {note}"
    )

    assert overall, msg
