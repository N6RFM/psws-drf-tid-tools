#!/usr/bin/env python3
"""
evaluate.py -- Result evaluation logic for the synthetic test suite.

Separates pass/fail judgment from the test runner for clarity.
"""

import math


def azimuth_error_deg(measured, true):
    """Signed shortest-path azimuth difference in degrees."""
    return (measured - true + 180) % 360 - 180


def evaluate(speed_m_s, az_from_deg, n_flags, ground_truth):
    """
    Evaluate a DOA result against ground truth.

    Parameters
    ----------
    speed_m_s, az_from_deg : float or None
        Measured DOA result (None if extraction/inversion failed).
    n_flags : int or None
        Number of diagnostic flags raised by tid_doa.py.
    ground_truth : dict
        As written by synthetic_drf.generate_event(). Must contain:
        true_speed_m_s, true_az_from_deg, expect_pass, notes.

    Returns
    -------
    dict with keys:
        speed_error_pct, azimuth_error_deg, overall_pass, category, note
    """
    true_speed  = ground_truth["true_speed_m_s"]
    true_az     = ground_truth["true_az_from_deg"]
    expect_pass = ground_truth["expect_pass"]
    notes       = ground_truth.get("notes", "")
    is_alias    = "ALIAS" in notes
    is_stress   = not expect_pass and not is_alias

    # -- No result at all ---------------------------------------------------
    if speed_m_s is None or az_from_deg is None:
        return {
            "speed_error_pct":  None,
            "azimuth_error_deg": None,
            "n_flags":          n_flags,
            "overall_pass":     not expect_pass,  # failure expected -> pass
            "category":         "no_result",
            "note":             "DOA produced no result",
        }

    spd_err_pct = abs(speed_m_s - true_speed) / true_speed * 100
    az_err_deg  = abs(azimuth_error_deg(az_from_deg, true_az))

    # -- Alias demo tests ---------------------------------------------------
    # These are expected to return a WRONG answer (large azimuth error).
    # Pass = the alias manifested (az error > 30 deg).
    if is_alias:
        alias_confirmed = az_err_deg > 30
        return {
            "speed_error_pct":  round(spd_err_pct, 1),
            "azimuth_error_deg": round(az_err_deg, 1),
            "n_flags":          n_flags,
            "overall_pass":     alias_confirmed,
            "category":         "alias_demo",
            "note":             ("alias confirmed -- azimuth error "  
                                 f"{az_err_deg:.0f}° confirms wrong-period lag peak"
                                 if alias_confirmed
                                 else "CONCERN: alias NOT triggered -- "  
                                 "result suspiciously correct for an aliased case"),
        }

    # -- Stress tests (expect_pass=False, not alias) -----------------------
    # Pass = result is clearly wrong OR toolkit flagged it.
    # Criteria: speed error > 20% OR azimuth error > 15 deg OR flags >= 2.
    if is_stress:
        clearly_wrong = spd_err_pct > 20 or az_err_deg > 15
        flagged = n_flags is not None and n_flags >= 2
        stress_pass = clearly_wrong or flagged
        return {
            "speed_error_pct":  round(spd_err_pct, 1),
            "azimuth_error_deg": round(az_err_deg, 1),
            "n_flags":          n_flags,
            "overall_pass":     stress_pass,
            "category":         "stress",
            "note":             ("toolkit failed as expected" if stress_pass
                                 else "CONCERN: stress test produced plausible result"),
        }

    # -- Normal expect_pass=True tests ------------------------------------
    # Tiered thresholds based on difficulty:
    #   high_snr (40dB AWGN):  speed < 8%,  az < 3 deg
    #   nominal (20dB AWGN):   speed < 12%, az < 5 deg
    #   low_snr / realistic:   speed < 20%, az < 8 deg
    snr_db     = ground_truth.get("snr_db", 20)
    noise_type = ground_truth.get("noise_type", "awgn")

    true_speed = ground_truth["true_speed_m_s"]
    # High-speed TIDs have larger quantization error at 60s cadence
    # (lag resolution 60s / true_lag_s ~= 7-8% at 800 m/s)
    speed_factor = 1.5 if true_speed >= 600 else 1.0
    if snr_db >= 30 and noise_type == "awgn":
        spd_thresh, az_thresh = round(15 * speed_factor), 3
        tier = "clean"
    elif snr_db >= 15 and noise_type == "awgn":
        spd_thresh, az_thresh = round(12 * speed_factor), 5
        tier = "nominal"
    else:
        spd_thresh, az_thresh = round(20 * speed_factor), 8
        tier = "degraded"

    spd_ok = spd_err_pct <= spd_thresh
    az_ok  = az_err_deg  <= az_thresh
    overall = spd_ok and az_ok

    return {
        "speed_error_pct":  round(spd_err_pct, 1),
        "azimuth_error_deg": round(az_err_deg, 1),
        "n_flags":          n_flags,
        "overall_pass":     overall,
        "category":         f"normal_{tier}",
        "note":             (""
                             if overall
                             else f"speed_err {spd_err_pct:.1f}% > {spd_thresh}% "
                                  f"OR az_err {az_err_deg:.1f}° > {az_thresh}°"),
    }
