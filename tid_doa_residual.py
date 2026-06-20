#!/usr/bin/env python3
"""
tid_doa_residual.py — Proof of concept: iterative single-wave
subtraction to test for a second superimposed TID.

THIS IS A PROOF OF CONCEPT, NOT YET INTEGRATED INTO THE WORKFLOW.
No CLI polish yet -- edit the CONFIG block below.

Rationale (see PROJECT_STATE.md §70): period-resolved DOA via FFT/
Welch methods does not work on single 2-3 hour event windows (1-2
wave cycles -- not enough for spectral averaging). This POC instead
asks a narrower, more tractable question: "does removing the best-
fit single sinusoid from each station's trace reveal a second,
geometrically coherent wave in the residual?" -- without needing to
resolve a continuous period axis at all.

Method:
  1. Run the existing broadband cross-correlation DOA (reusing
     tid_doa.py's load_station + cross_correlate_lag + the same
     lstsq slowness-vector inversion) on the raw station traces.
     This should reproduce the known, validated result.
  2. Per station, fit a single sinusoid (period, amplitude, phase,
     offset) to the raw Doppler trace via nonlinear least squares.
  3. Subtract the fit from each station's trace -> residual.
  4. Re-run the SAME broadband DOA procedure on the residuals.
  5. Compare: if the residual DOA gives a coherent, physically
     plausible result (reasonable speed, consistent pairwise
     correlation), that's evidence of a second wave. If the residual
     DOA is noisy/inconsistent/unphysical, the single-wave model was
     sufficient and there is no detectable second wave.

Validation target (control case): Jan 2026 event, 3 stations
(AA6BD, N6RFM, W7LUX). Known broadband result: 239 m/s, wave from
~30 deg NNE (1/5 flags), LOW RMS residual (clean single wave).
Expectation: step 1 should reproduce ~239 m/s/30deg; step 4 (residual
DOA) should NOT find a clean second wave, since this event's plane-
wave fit residual was already low in the original tid_doa.py run --
i.e. this is a negative control to confirm the method doesn't
manufacture spurious second waves where none exist.
"""
import sys
import pathlib
import json
import math

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tid_doa import (load_station, latlon_to_local_xy,
                      cross_correlate_lag)  # noqa: E402

# ---------------------------------------------------------------------------
# CONFIG -- edit for your event
# ---------------------------------------------------------------------------
EVENT_JSON = "/home/bob/Downloads/tid_event_20260606/tid_workflow_event.json"
TARGET_DT_S = 60
MAX_LAG_S = 1800  # same as tid_doa.py config for this event
OUTPUT_DIR = "/home/bob/Downloads/tid_event_20260606/runs/residual_poc"
# ---------------------------------------------------------------------------


def sinusoid(t, amp, period_s, phase, offset, slope):
    """Single sinusoid + linear trend (trend absorbs slow drift so the
    fit isolates the oscillatory component)."""
    return amp * np.sin(2 * np.pi * t / period_s + phase) + offset + slope * t


def fit_single_wave(t, y):
    """Fit a single sinusoid to a station's Doppler trace. t in seconds
    from start, y the Doppler series. Returns (fit_curve, params) or
    (None, None) if the fit fails.
    """
    t0 = t - t[0]
    amp0 = (np.max(y) - np.min(y)) / 2
    offset0 = np.mean(y)
    # Try a range of initial period guesses (covers MSTID to LSTID),
    # keep the best fit by SSE
    best = None
    for period_guess_min in [15, 25, 40, 60, 80, 100]:
        p0 = [amp0, period_guess_min * 60, 0.0, offset0, 0.0]
        try:
            popt, _ = curve_fit(sinusoid, t0, y, p0=p0, maxfev=5000)
            fit = sinusoid(t0, *popt)
            sse = np.sum((y - fit) ** 2)
            if best is None or sse < best[0]:
                best = (sse, fit, popt)
        except Exception:
            continue
    if best is None:
        return None, None
    return best[1], best[2]


def run_broadband_doa(sigs, pos, names, fs_hz, max_lag_s, label=""):
    """Same geometry/inversion approach as tid_doa.solve_doa, simplified
    (no candidate-peak selection -- just the top cross-correlation peak
    per pair, which is what tid_doa.py also defaults to before its
    triangle-closure refinement).
    """
    import itertools
    pairs = list(itertools.combinations(names, 2))
    A_rows, b_vals, pair_info = [], [], []

    print(f"\n--- {label} pairwise lags ---")
    for a, b in pairs:
        lag, corr = cross_correlate_lag(sigs[a], sigs[b], fs_hz, max_lag_s)
        dr = pos[b] - pos[a]
        A_rows.append(dr)
        b_vals.append(lag)
        pair_info.append((a, b, lag, corr))
        print(f"  {a} -> {b}   lag={lag:+8.1f}s   corr={corr:+.3f}")

    A = np.array(A_rows)
    bb = np.array(b_vals)
    s_vec, residuals, rank, sv = np.linalg.lstsq(A, bb, rcond=None)
    sx, sy = float(s_vec[0]), float(s_vec[1])
    slow_mag = math.hypot(sx, sy)
    speed_m_s = 1.0 / slow_mag if slow_mag > 0 else float("inf")
    az_rad = math.atan2(sx, sy)
    az_deg = (math.degrees(az_rad) + 360) % 360
    az_from = (az_deg + 180) % 360

    if residuals is not None and len(residuals) > 0:
        sse = float(residuals[0])
    else:
        pred = A.dot(s_vec)
        sse = float(np.sum((bb - pred) ** 2))
    m_pairs = int(A.shape[0])
    rms_resid_s = (sse / m_pairs) ** 0.5 if m_pairs > 0 else float("nan")
    mean_abs_lag = np.mean(np.abs(bb)) if m_pairs > 0 else float("nan")
    resid_pct = 100 * rms_resid_s / mean_abs_lag if mean_abs_lag > 0 else float("nan")

    print(f"  Speed: {speed_m_s:.1f} m/s   From: {az_from:.1f} deg")
    print(f"  RMS lag residual: {rms_resid_s:.1f}s "
          f"({resid_pct:.1f}% of mean abs lag {mean_abs_lag:.1f}s)")
    mean_corr = np.mean([abs(c) for (_, _, _, c) in pair_info])
    print(f"  Mean |corr|: {mean_corr:.3f}")

    return {
        "speed_m_s": speed_m_s, "az_from_deg": az_from,
        "rms_resid_s": rms_resid_s, "resid_pct": resid_pct,
        "mean_corr": mean_corr, "pairs": pair_info,
    }


def main():
    with open(EVENT_JSON) as f:
        cfg = json.load(f)

    t_start = pd.Timestamp(cfg["event_start_utc"])
    t_end = pd.Timestamp(cfg["event_end_utc"])
    names = [s["name"] for s in cfg["stations"]]

    print(f"Loading {len(names)} stations: {', '.join(names)}")
    print(f"Window: {t_start} to {t_end}")

    loaded = {s["name"]: load_station(s, t_start, t_end, TARGET_DT_S)
              for s in cfg["stations"]}
    n = min(len(sd.times) for sd in loaded.values())
    fs_hz = 1.0 / TARGET_DT_S

    mids = np.array([loaded[nm].midpoint for nm in names])
    lat0 = float(np.mean(mids[:, 0]))
    lon0 = float(np.mean(mids[:, 1]))
    pos = {nm: np.array(latlon_to_local_xy(lat, lon, lat0, lon0))
           for nm, (lat, lon) in zip(names, mids)}

    raw_sigs = {nm: loaded[nm].doppler[:n] - np.mean(loaded[nm].doppler[:n])
                for nm in names}
    times_s = loaded[names[0]].times[:n]

    # --- Step 1: broadband DOA on raw signals (should reproduce known result) ---
    result_raw = run_broadband_doa(raw_sigs, pos, names, fs_hz, MAX_LAG_S,
                                    label="RAW (broadband, step 1)")

    # --- Step 2+3: fit single wave per station, subtract -> residual ---
    print("\n--- Single-wave fits per station ---")
    fits = {}
    residual_sigs = {}
    for nm in names:
        fit, params = fit_single_wave(times_s, raw_sigs[nm])
        if fit is None:
            print(f"  {nm}: fit FAILED, using raw signal as residual")
            residual_sigs[nm] = raw_sigs[nm]
            continue
        amp, period_s, phase, offset, slope = params
        print(f"  {nm}: period={period_s/60:.1f}min amp={amp:.3f} "
              f"(fit SSE-reduced trace used as residual)")
        fits[nm] = fit
        residual_sigs[nm] = raw_sigs[nm] - fit

    # --- Residual magnitude guard ---
    # If the single-wave fit absorbed nearly all of the signal, the
    # residual is dominated by fit noise, not a real second wave --
    # a cross-correlation DOA on it is meaningless (the Jun 2026 test
    # run showed exactly this failure mode: near-perfect fits,
    # near-zero residuals, and a DOA result driven by edge-locked
    # lags and correlated numerical noise rather than a real signal).
    RESIDUAL_RATIO_MIN = 0.15  # residual RMS must be >=15% of raw RMS
    print("\n--- Residual magnitude check ---")
    weak_stations = []
    for nm in names:
        raw_rms = np.sqrt(np.mean(raw_sigs[nm] ** 2))
        resid_rms = np.sqrt(np.mean(residual_sigs[nm] ** 2))
        ratio = resid_rms / raw_rms if raw_rms > 0 else 0.0
        flag = "" if ratio >= RESIDUAL_RATIO_MIN else "  << TOO SMALL"
        print(f"  {nm}: raw_rms={raw_rms:.4f}  resid_rms={resid_rms:.4f}  "
              f"ratio={ratio:.3f}{flag}")
        if ratio < RESIDUAL_RATIO_MIN:
            weak_stations.append(nm)

    if weak_stations:
        print(f"\n  >> {len(weak_stations)}/{len(names)} station(s) have "
              f"residual RMS < {RESIDUAL_RATIO_MIN:.0%} of raw signal "
              f"({', '.join(weak_stations)}).")
        print("  The single-wave fit absorbed nearly all of the signal at "
              "these stations.")
        print("  A residual DOA result would be driven by fit noise, not a "
              "real second wave.")
        print("  SKIPPING residual DOA step -- treat this event as "
              "consistent with a SINGLE dominant wave (the high original "
              "RMS lag residual is not explained by a second coherent "
              "wave detectable by this method).")
        print("\n=== COMPARISON ===")
        print(f"{'':20} {'Speed(m/s)':>12} {'From(deg)':>10} "
              f"{'RMS resid %':>12} {'Mean|corr|':>11}")
        print(f"{'Raw (step 1)':20} {result_raw['speed_m_s']:12.1f} "
              f"{result_raw['az_from_deg']:10.1f} "
              f"{result_raw['resid_pct']:12.1f} {result_raw['mean_corr']:11.3f}")
        print(f"{'Residual (step 4)':20} {'SKIPPED':>12} "
              f"{'(residual too small to trust)':>10}")
        return

    # --- Step 4: broadband DOA on residuals ---
    result_resid = run_broadband_doa(residual_sigs, pos, names, fs_hz,
                                      MAX_LAG_S,
                                      label="RESIDUAL (after single-wave "
                                            "subtraction, step 4)")

    # --- Step 5: compare ---
    print("\n=== COMPARISON ===")
    print(f"{'':20} {'Speed(m/s)':>12} {'From(deg)':>10} "
          f"{'RMS resid %':>12} {'Mean|corr|':>11}")
    print(f"{'Raw (step 1)':20} {result_raw['speed_m_s']:12.1f} "
          f"{result_raw['az_from_deg']:10.1f} "
          f"{result_raw['resid_pct']:12.1f} {result_raw['mean_corr']:11.3f}")
    print(f"{'Residual (step 4)':20} {result_resid['speed_m_s']:12.1f} "
          f"{result_resid['az_from_deg']:10.1f} "
          f"{result_resid['resid_pct']:12.1f} {result_resid['mean_corr']:11.3f}")

    print("\nInterpretation guide:")
    print("  If residual mean|corr| is low (<0.4) and/or speed is wildly")
    print("  unphysical -> no detectable second wave (expected for a")
    print("  clean single-wave control event like Jan 2026).")
    print("  If residual mean|corr| is reasonably high (>0.5) AND speed")
    print("  falls in a physically plausible TID range (100-1000 m/s)")
    print("  -> possible evidence of a second wave.")

    # Plot: raw traces, fits, and residuals
    out = pathlib.Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(len(names), 1, figsize=(9, 2.2 * len(names)),
                             sharex=True)
    if len(names) == 1:
        axes = [axes]
    t_min = (times_s - times_s[0]) / 60
    for ax, nm in zip(axes, names):
        ax.plot(t_min, raw_sigs[nm], label="raw (mean-removed)", alpha=0.7)
        if nm in fits:
            ax.plot(t_min, fits[nm], "--", label="single-wave fit",
                    color="tab:orange")
            ax.plot(t_min, residual_sigs[nm], label="residual",
                    color="tab:green", alpha=0.7)
        ax.set_ylabel(nm)
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Minutes from window start")
    fig.suptitle("Single-wave fit and residual per station")
    plt.tight_layout()
    plot_path = out / "residual_fits.png"
    plt.savefig(plot_path, dpi=120)
    print(f"\nPlot saved: {plot_path}")


if __name__ == "__main__":
    main()
