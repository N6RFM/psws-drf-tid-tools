#!/usr/bin/env python3
"""
tid_dashboard.py -- browser-based control panel for the automated
end-to-end TID pipeline (DRF discovery -> Doppler extraction -> DOA ->
Madrigal TEC cross-check).

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 0.9.1
License: MIT (do whatever you want, no warranty).

Change log:
  v0.9.1  Fixed a display-label mismatch: the "Step 1 -- Interactive
          extraction" subheader showed "spline" for wave-only runs,
          matching a real mislabeling bug in tid_spect_click.py's own
          saved method name (also fixed, see that file's v0.9.0).
          Purely cosmetic here -- tsc_method_name isn't used for any
          comparison/matching logic, only display text -- but shown
          "spline" is genuinely wrong for a wave-fit run, since spline
          is a separate, real extraction method.
  v0.9.0  Restored channel-num detection and mandatory visual
          confirmation (KA9Q-radio/WSPRdaemon-style receivers), fixing
          a significant real-world bug found during the first live
          test of the interactive extraction feature: 3 of 4 stations
          in the June 6 2026 event turned out to have real channel-nums
          (up to 9 each), and every part of the pipeline -- overview
          spectrogram, zoomed spectrogram, automated extraction, and
          the interactive tid_spect_click.py launch -- was silently
          defaulting to channel-num 0, which for all 3 affected
          stations was an empty/unused band, not the actual carrier.
          An earlier version of this file had removed channel-num
          handling entirely based on an overgeneralized "PSWS data has
          no channel-nums" assumption; that's true for some station
          types (e.g. plain Grape/N6RFM_5-style single-channel-num
          recorders) but not for KA9Q-radio/WSPRdaemon receivers.
          New "Channel-num selection" step (same mandatory real-
          spectrogram confirmation pattern as the existing Channel
          selection step) reuses tid_workflow.py's own probe_channel_nums/
          best_channel_num selection policy (frequency match to a
          configurable target MHz, else highest SNR). The overview
          spectrogram (used to pick the event window, before per-
          station confirmation happens) uses an unconfirmed best-guess
          for the keystone station only, to avoid a circular UI
          dependency; the real, mandatory-confirmation gate happens
          later, before extraction actually runs.
  v0.8.1  Added a "Doppler axis half-range" control (only shown for
          wave-fit/cwt-prophet), passed as --ylim=-h,h to both the
          zoomed-spectrogram generation and tid_spect_click.py itself.
          Found during the first real (non-synthetic) test of the
          interactive extraction feature: the default ±5 Hz range
          made a real TID signal that only varies over a much smaller
          band look flat and hard to click precisely. Persisted in
          settings like everything else.
  v0.8.0  Added wave-fit and cwt-prophet extraction: the dashboard now
          launches tid_spect_click.py as a native window per station
          (Option A -- spawn the existing, tested tool as a subprocess
          rather than reimplementing spectrogram clicking in-browser).
          Uses --event-json so tid_spect_click.py itself writes the
          exported CSV path into the config on X-export, matched by
          station name -- no output-filename guessing. Only works when
          Streamlit is running locally on the same machine as the
          display (same constraint as the folder-browse button); the
          browser tab blocks while each native window is open, same as
          any other blocking step in the pipeline. Mixing methods
          across stations within one run is not yet supported -- all
          stations in a run use the same method.
  v0.7.0  (see prior entries in PROJECT_STATE.md)

STATUS: v0.9.0. Wraps existing scripts via subprocess -- does not
reimplement any extraction/DOA/TEC logic itself. Automated methods
(autocorr, cwt, fft) run non-interactively; wave-fit and cwt-prophet
launch tid_spect_click.py's own native window per station (see change
log above) rather than reimplementing spectrogram clicking here.

Handles both real multiple DRF *channels* (e.g. wideband receivers like
RX888 recording several carriers as separate ch0/ch1/ch2/... directories)
and multiple *channel-nums* within one channel (KA9Q-radio/WSPRdaemon-style
receivers packing several carriers into one channel's data columns).
An earlier version of this file assumed PSWS data never has channel-nums;
real-world testing (June 6 2026 event) found 3 of 4 stations were
genuine KA9Q-radio receivers with up to 9 channel-nums each, and the
dashboard was silently defaulting to channel-num 0 -- often an empty or
unused band -- producing spectrograms with no visible signal at all.
Both channel and channel-num selection now require the same real-
spectrogram visual confirmation before the pipeline runs -- an SNR
number or frequency label alone isn't good enough to trust blindly.

PREREQUISITES
    pip install streamlit digital_rf madrigalWeb numpy matplotlib scipy

USAGE
    streamlit run tid_dashboard.py

    Then open the printed http://localhost:8501 URL in a browser.

    Everything before the "Run full pipeline" button happens live, as you
    type -- no need to click anything to see it:
      1. Discover stations (digital_rf-readable subdirectories)
      2. Get each station's lat/lon (cache -> DRF metadata -> manual entry)
      3. For any station with more than one DRF channel: show a real
         spectrogram of each candidate and require you to tick a
         confirmation box before the run button will even enable.

    Clicking "Run full pipeline" then does the parts that take real time:
      4. Run drf_to_doppler.py per station (automated method, no clicking)
      5. Write a tid_workflow_event.json-compatible config
      6. Run tid_doa.py, parse speed/azimuth/diagnostics
      7. Compute predicted per-pair lags from the DOA result's own
         geometry, then run fetch_madrigal_tec.py (or the experimental
         fetch_madrigal_tec_closure.py fork) as an independent
         cross-check, auto-filling --doa-speed/--doa-azimuth-from/
         --doa-lags so nothing has to be retyped by hand.

WHY THIS EXISTS
    Today's session hit repeated friction from manually retyping long
    fetch_madrigal_tec.py invocations, running scripts from the wrong
    working directory, and hand-computing predicted DOA lags. This
    wraps those exact steps -- same underlying scripts, same math,
    just orchestrated instead of hand-typed.
"""

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

REPO_DIR = Path(__file__).resolve().parent

# ── Settings autosave ──
# Persists everything except the run button's own state, so re-opening
# the dashboard doesn't require re-typing Madrigal info / re-picking the
# method every time. Same ~/.config/psws/ convention run_madrigal_tools.py
# already uses for Madrigal user info.

SETTINGS_PATH = Path.home() / ".config" / "psws" / "tid_dashboard_settings.json"


def load_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            return {}
    return {}


def save_settings_if_changed(current):
    """Only writes to disk if something actually changed, per the 'autosave
    unless changed, then resave' request -- avoids a disk write on every
    single script rerun (Streamlit reruns the whole script on every widget
    interaction, including ones unrelated to these settings)."""
    existing = load_settings()
    if existing != current:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(current, indent=2))


def browse_for_directory(initial_dir):
    """Open a native OS folder-picker dialog and return the chosen path,
    or None if unavailable/cancelled. Only meaningful when Streamlit is
    running on the SAME machine as the browser viewing it (true for the
    normal local `streamlit run` case this dashboard is built for) --
    the dialog pops up on the server machine's own desktop, not inside
    the browser tab, since browsers cannot grant a web page access to
    arbitrary server-side filesystem paths.

    Requires tkinter (python3-tk on Debian/Ubuntu). Returns None with no
    exception if unavailable (e.g. a headless server) so callers can fall
    back to manual typing rather than crash.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            initialdir=initial_dir if Path(initial_dir).is_dir() else str(Path.home()),
            title="Select event directory",
        )
        root.destroy()
        return selected or None
    except Exception:
        return None

# ── Geometry helpers (same formulas fetch_madrigal_tec.py uses internally,
#    duplicated here so the dashboard can *predict* lags before calling it) ──

def gc_dist_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def bearing_deg(lon1, lat1, lon2, lat2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dlam = np.radians(lon2 - lon1)
    x = np.sin(dlam) * np.cos(phi2)
    y = np.cos(phi1) * np.sin(phi2) - np.sin(phi1) * np.cos(phi2) * np.cos(dlam)
    return np.degrees(np.arctan2(x, y)) % 360


def projected_lag_s(dist_km, az_toward_deg, baseline_bear_deg, speed_ms):
    proj = np.cos(np.radians(az_toward_deg) - np.radians(baseline_bear_deg))
    return (dist_km * 1000 * proj) / speed_ms


# ── Station / channel discovery (mirrors tid_workflow.py's conventions
#    for the parts it already covers; channel selection -- as opposed to
#    channel-num selection -- is new, no existing repo tool does this) ──

def discover_stations(event_dir):
    """Find DRF-readable subdirectories of event_dir. Returns list of Path."""
    stations = []
    try:
        import digital_rf as drf_lib
    except ImportError:
        return None  # signals "digital_rf not installed" to the caller
    for d in sorted(Path(event_dir).iterdir()):
        if not d.is_dir():
            continue
        try:
            r = drf_lib.DigitalRFReader(str(d))
            if r.get_channels():
                stations.append(d)
        except Exception:
            continue
    return stations


def discover_channels(drf_dir):
    """List channel names within a station's DRF directory (e.g. ['ch0'])."""
    try:
        import digital_rf as drf_lib
        r = drf_lib.DigitalRFReader(str(drf_dir))
        return r.get_channels()
    except Exception:
        return []


def probe_channel_frequency(drf_dir, channel):
    """Best-effort center frequency (Hz) for a channel from DRF metadata,
    or None if unavailable. Used only as a label hint; the spectrogram is
    what you should actually trust."""
    try:
        import digital_rf as drf_lib
        r = drf_lib.DigitalRFReader(str(drf_dir))
        props = r.get_properties(channel)
        for key in ["center_frequencies", "center_frequency", "rf_centerfreq", "centerfreq"]:
            val = props.get(key, None)
            if val is not None:
                try:
                    return float(np.atleast_1d(val)[0])
                except Exception:
                    pass
        return None
    except Exception:
        return None


def render_channel_spectrogram(drf_dir, channel, center_dt=None, seconds=600, channel_num=0):
    """Read a short real segment of a channel's IQ data and return a
    matplotlib Figure showing its spectrogram, for visual confirmation.

    center_dt: a UTC datetime to center the preview on (typically the
    middle of the selected event window). Falls back to the middle of
    the whole recording if not given or out of range.

    channel-num: which column to read if this channel's data is
    multi-channel-num (KA9Q-radio/WSPRdaemon-style). Previously
    hardcoded to column 0 regardless of which channel-num was actually
    relevant -- found via real-world testing to silently show an
    empty/wrong-frequency band for any station with real channel-nums.
    """
    try:
        import digital_rf as drf_lib
        from scipy import signal as sp_signal

        r = drf_lib.DigitalRFReader(str(drf_dir))
        props = r.get_properties(channel)
        sr = float(props["samples_per_second"])
        b0, b1 = r.get_bounds(channel)

        if center_dt is not None:
            center_idx = int(center_dt.timestamp() * sr)
            if not (b0 <= center_idx <= b1):
                center_idx = (b0 + b1) // 2
        else:
            center_idx = (b0 + b1) // 2

        block = int(sr * seconds)
        half = block // 2
        start_idx = max(b0, center_idx - half)
        n = min(block, b1 - start_idx)
        iq = r.read_vector(start_idx, n, channel)
        if iq.ndim == 2:
            iq = iq[:, channel_num]

        nperseg = min(1024, max(64, int(sr * 2)))
        f, t, sxx = sp_signal.spectrogram(
            iq, fs=sr, nperseg=nperseg, noverlap=nperseg // 2,
            return_onesided=False, mode="magnitude",
        )
        f = np.fft.fftshift(f)
        sxx = np.fft.fftshift(sxx, axes=0)

        fig, ax = plt.subplots(figsize=(5, 3))
        db = 20 * np.log10(sxx + 1e-12)
        ax.pcolormesh(t, f, db, shading="auto", cmap="viridis")
        ax.set_ylabel("Freq offset (Hz)")
        ax.set_xlabel("Time (s)")
        ax.set_title(f"{Path(drf_dir).name} / {channel}"
                     f"{f' sub{channel_num}' if channel_num else ''}", fontsize=10)
        fig.tight_layout()
        return fig
    except Exception as e:
        fig, ax = plt.subplots(figsize=(5, 2))
        ax.text(0.5, 0.5, f"Preview failed:\n{e}", ha="center", va="center", fontsize=8, wrap=True)
        ax.axis("off")
        return fig


def probe_station_channel_nums(drf_dir, channel, target_mhz=10.0):
    """Probe every channel-num within a specific DRF channel, returning
    (channel_num_idx, snr_db, freq_hz) tuples sorted by SNR descending.

    Channel-aware equivalent of tid_workflow.py's probe_channel_nums(),
    which always hardcodes channel[0] -- needed here since a station
    could have multiple real channels (RX888-style) AND multiple
    channel-nums within whichever one was actually selected.

    Real-world finding (June 6 2026 event): 3 of 4 stations turned out
    to be genuine KA9Q-radio/WSPRdaemon receivers with up to 9
    channel-nums each, and this dashboard previously always silently
    used channel-num 0 -- often an empty/unused band, not the actual
    carrier -- producing spectrograms with no visible signal at all.
    "PSWS data has no channel-nums" (an earlier correction this session)
    turned out to be true only for some station types, not all.
    """
    try:
        import digital_rf as drf_lib
        r = drf_lib.DigitalRFReader(str(drf_dir))
        props = r.get_properties(channel)
        sr = float(props["samples_per_second"])
        b0, b1 = r.get_bounds(channel)
        mid = (b0 + b1) // 2
        block = int(sr * 60)
        try:
            iq = r.read_vector(mid, block, channel)
        except Exception:
            iq = r.read_vector(b0, min(block, b1 - b0), channel)

        if iq.ndim == 1:
            spec = np.abs(np.fft.rfft(iq.real))
            snr = 20 * np.log10(spec.max() / (np.median(spec) + 1e-12))
            freq = None
            for key in ["center_frequencies", "center_frequency", "rf_centerfreq", "centerfreq"]:
                val = props.get(key, None)
                if val is not None:
                    try:
                        freq = float(np.atleast_1d(val)[0])
                    except Exception:
                        pass
                    break
            return [(0, float(snr), freq)]

        n_subs = iq.shape[1]
        freqs = None
        for key in ["center_frequencies", "center_frequency", "rf_centerfreq",
                    "centerfreq", "subchannel_center_frequencies"]:
            val = props.get(key, None)
            if val is not None:
                try:
                    arr = np.atleast_1d(val)
                    if len(arr) == n_subs:
                        freqs = arr
                        break
                    elif len(arr) == 1:
                        freqs = np.full(n_subs, float(arr[0]))
                        break
                except Exception:
                    pass

        results = []
        for sub in range(n_subs):
            col = iq[:, sub]
            spec = np.abs(np.fft.fftshift(np.fft.fft(col))) if np.iscomplexobj(col) else np.abs(np.fft.rfft(col))
            snr = 20 * np.log10(spec.max() / (np.median(spec) + 1e-12))
            freq = float(freqs[sub]) if freqs is not None else None
            results.append((sub, float(snr), freq))
        return sorted(results, key=lambda x: -x[1])
    except Exception:
        return [(0, 0.0, None)]


def best_channel_num_choice(subs, target_mhz=10.0):
    """Same selection policy as tid_workflow.py's best_channel_num(): a
    frequency match within 100 kHz of target_mhz wins; otherwise fall
    back to highest SNR."""
    freq_matches = [(sub, snr, freq) for sub, snr, freq in subs if freq is not None]
    if freq_matches:
        closest = min(freq_matches, key=lambda x: abs(x[2] / 1e6 - target_mhz))
        if abs(closest[2] / 1e6 - target_mhz) < 0.1:
            return closest[0], f"frequency match ({closest[2] / 1e6:.3f} MHz)"
    best = subs[0]
    return best[0], f"highest SNR ({best[1]:.1f} dB)"


def load_coords_cache(event_dir):
    p = Path(event_dir) / "station_coords.json"
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save_coords_cache(event_dir, cache):
    p = Path(event_dir) / "station_coords.json"
    p.write_text(json.dumps(cache, indent=2))


def generate_zoomed_spectrogram(event_path, drf_dir, channel, station_name,
                                 event_start_dt, event_end_dt, ylim_half_range=None,
                                 channel_num=None):
    """Generate a spectrogram zoomed to the actual event window (not the
    full-day overview) -- this is what tid_spect_click.py's wave-fit/
    cwt-prophet clicking is meant to be done against, same as
    tid_workflow.py's own guided-workflow zoomed-spectrogram step.
    Not cached (unlike the overview) since the event window can change
    between runs and this is only generated once per interactive
    extraction attempt, not on every rerun.

    ylim_half_range: if given, passes --ylim=-{h},{h} to drf_spectrogram.py
    to narrow the Doppler axis (default is a wide -5,5 Hz, which can make
    a real TID signal that only varies over a much smaller range look
    flat/squished and hard to click precisely). Uses the --ylim=-2,2
    equals-sign form drf_spectrogram.py's own --help specifically calls
    out as required -- a bare --ylim -2,2 gets misparsed by argparse as
    two separate flags because of the leading minus sign.

    channel-num: which channel-num to plot, for stations where this
    matters (KA9Q-radio/WSPRdaemon-style receivers with several
    carriers packed into one channel). Omitting this previously meant
    silently defaulting to channel-num 0, which for 3 of 4 real stations
    tested this session turned out to be an empty/unused band.

    Returns (png_path, axes_json_path, ok, output_text).
    """
    png_path = event_path / f"{station_name.lower()}_zoomed_spectrogram.png"
    axes_path = png_path.with_name(png_path.stem + "_axes.json")
    args = [
        sys.executable, str(REPO_DIR / "drf_spectrogram.py"),
        str(drf_dir), "--output", str(png_path),
        "--start", event_start_dt.strftime("%H:%M:%S"),
        "--end", event_end_dt.strftime("%H:%M:%S"),
    ]
    if channel:
        args += ["--channel", channel]
    if channel_num is not None:
        args += ["--channel-num", str(channel_num)]
    if ylim_half_range:
        args.append(f"--ylim=-{ylim_half_range},{ylim_half_range}")
    ok, out = run_cmd(args)
    ok = ok and png_path.exists() and axes_path.exists()
    return (png_path if ok else None), (axes_path if ok else None), ok, out


def run_interactive_extraction(config_path, drf_dir, channel, station_name,
                                spectrogram_png, period_hint_s, wave_only,
                                ylim_half_range=None, channel_num=None):
    """Launch tid_spect_click.py's native window for one station and
    block until it's closed. Uses --event-json so the tool itself
    writes the resulting CSV path into our config (matched by station
    name, see tid_spect_click.py's _save_event_json) -- the dashboard
    never has to guess the output filename.

    This is a genuinely blocking subprocess.run, not the byte-streamed
    run_cmd() used elsewhere -- there's no incremental console output
    to show for a GUI app, just "wait for the window to close."

    ylim_half_range: same as generate_zoomed_spectrogram's parameter --
    passed through so the interactive window's own axis matches the
    zoomed preview image exactly, rather than the window silently
    reverting to a wider default range.

    channel-num: the confirmed channel-num index for this station (see
    probe_station_channel_nums/best_channel_num_choice). A previous
    version of this function hardcoded --channel-num 0 unconditionally
    with a comment claiming "PSWS data has no channel-nums" -- true for
    some station types, not all; 3 of 4 real stations tested this
    session turned out to be KA9Q-radio/WSPRdaemon receivers with real
    channel-nums, and channel-num 0 was an empty/unused band for all
    three, meaning this bug silently sent people to click on pure noise.

    Returns (ok, output_text, updated_file_value_or_None). The third
    value is read back from config_path after the process exits, so
    the caller can tell whether the user actually pressed X (exported)
    before closing, versus closing without exporting.
    """
    args = [
        sys.executable, str(REPO_DIR / "tid_spect_click.py"),
        "--spectrogram", str(spectrogram_png),
        "--name", station_name,
        "--event-json", str(config_path),
    ]
    if drf_dir:
        args.append("--drf-dir")
        args.append(str(drf_dir))
    if channel_num is not None:
        args += ["--channel-num", str(channel_num)]
    if period_hint_s:
        args += ["--period-hint", str(int(period_hint_s))]
    if ylim_half_range:
        args.append(f"--ylim=-{ylim_half_range},{ylim_half_range}")
    if wave_only:
        args.append("--wave-only")

    try:
        proc = subprocess.run(args, cwd=REPO_DIR, capture_output=True,
                               text=True, timeout=3600)
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0
    except subprocess.TimeoutExpired as e:
        return False, f"TIMED OUT after 1hr waiting for the window to close\n{e}", None
    except FileNotFoundError as e:
        return False, f"Command not found: {e}", None

    updated_file = None
    try:
        cfg = json.loads(Path(config_path).read_text())
        for s in cfg.get("stations", []):
            if s.get("name", "").upper() == station_name.upper():
                updated_file = s.get("file")
                break
    except Exception:
        pass

    return ok, out, updated_file


def generate_overview_spectrogram(event_path, drf_dir, channel, station_name, channel_num=None):
    """Generate (or reuse a cached) full-window overview spectrogram via the
    repo's own drf_spectrogram.py, so users can visually locate the TID
    before picking a window -- rather than the dashboard reimplementing
    spectrogram rendering from scratch. Cached to disk in event_path
    (same pattern as station_coords.json) since a full-day spectrogram is
    much heavier than the short channel-preview one and shouldn't
    regenerate on every widget interaction.

    channel-num: which channel-num to plot (see generate_zoomed_spectrogram
    for why this matters). Included in the cache filename so switching
    channel-nums correctly invalidates any previously-cached overview
    instead of silently reusing a wrong-band image.

    Also writes/reuses the axes sidecar JSON that drf_spectrogram.py
    produces (the same one tid_spect_click.py consumes) -- needed by
    overlay_selected_window() below to map times to pixel coordinates
    without re-running the spectrogram subprocess.

    Returns (png_path, axes_json_path, ok, output_text).
    """
    suffix = f"_sub{channel_num}" if channel_num is not None else ""
    png_path = event_path / f"{station_name.lower()}_overview_spectrogram{suffix}.png"
    axes_path = png_path.with_name(png_path.stem + "_axes.json")
    if png_path.exists() and axes_path.exists():
        return png_path, axes_path, True, "(using cached overview)"

    args = [
        sys.executable, str(REPO_DIR / "drf_spectrogram.py"),
        str(drf_dir), "--output", str(png_path),
    ]
    if channel:
        args += ["--channel", channel]
    if channel_num is not None:
        args += ["--channel-num", str(channel_num)]
    ok, out = run_cmd(args)
    ok = ok and png_path.exists() and axes_path.exists()
    return (png_path if ok else None), (axes_path if ok else None), ok, out


def overlay_selected_window(png_path, axes_path, event_start_dt, event_end_dt):
    """Draw a translucent highlight band over the currently-selected event
    window, directly on top of the (already-rendered, cached) overview
    spectrogram -- fast, in-process PIL drawing, no subprocess call. This
    is what makes it practical to update the highlight on every slider
    move instead of only on an explicit "regenerate" button click, which
    would mean re-running drf_spectrogram.py (a full DRF read + decimate)
    on every drag.

    Returns a PIL Image, or None if the axes sidecar can't be used.
    """
    try:
        from PIL import Image, ImageDraw

        axes = json.loads(Path(axes_path).read_text())
        date_utc = datetime.strptime(axes["date_utc"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        t_start_h = axes["t_start_utc_hours"]
        t_end_h = axes["t_end_utc_hours"]
        # drf_spectrogram.py's own source defines this as
        # [left, right, bottom, top] (axes bbox corners), NOT
        # [left, bottom, width, height] -- confirmed by reading its
        # _pf_from_mpl construction directly, after an initial version
        # of this function got it backwards and silently drew the
        # highlight in the wrong place (caught by comparing pixels
        # before/after the overlay at known coordinates).
        left, right, bottom, top = axes["plot_fraction"]
        width = right - left
        height = top - bottom

        img = Image.open(png_path).convert("RGBA")
        w, h = img.size

        def hours_since_date(dt):
            return (dt - date_utc).total_seconds() / 3600.0

        sel_start_h = max(t_start_h, hours_since_date(event_start_dt))
        sel_end_h = min(t_end_h, hours_since_date(event_end_dt))
        if sel_end_h <= sel_start_h:
            return img.convert("RGB")  # selection entirely outside this station's range

        def x_for_hour(hr):
            frac = (hr - t_start_h) / (t_end_h - t_start_h) if t_end_h > t_start_h else 0
            return left * w + frac * (width * w)

        x0 = x_for_hour(sel_start_h)
        x1 = x_for_hour(sel_end_h)
        y0 = (1 - top) * h
        y1 = (1 - bottom) * h

        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 0, 70), outline=(255, 200, 0, 220), width=2)
        return Image.alpha_composite(img, overlay).convert("RGB")
    except Exception:
        return None


def get_drf_metadata_coords(drf_dir):
    try:
        import digital_rf as drf_lib
        r = drf_lib.DigitalRFReader(str(drf_dir))
        ch = r.get_channels()[0]
        props = r.get_properties(ch)
        lat, lon = props.get("latitude"), props.get("longitude")
        if lat is not None and lon is not None:
            return float(lat), float(lon)
    except Exception:
        pass
    return None, None


def get_station_time_bounds(drf_dir):
    """Full recorded UTC time range for a station, from DRF sample bounds.
    Returns (start_dt, end_dt) as tz-aware UTC datetimes, or (None, None).
    """
    try:
        import digital_rf as drf_lib
        r = drf_lib.DigitalRFReader(str(drf_dir))
        ch = r.get_channels()[0]
        props = r.get_properties(ch)
        sr = float(props["samples_per_second"])
        b0, b1 = r.get_bounds(ch)
        start_dt = datetime.fromtimestamp(b0 / sr, tz=timezone.utc)
        end_dt = datetime.fromtimestamp(b1 / sr, tz=timezone.utc)
        return start_dt, end_dt
    except Exception:
        return None, None


# ── Subprocess wrappers ──

def run_cmd(args, cwd=None, live_container=None):
    """Run a subprocess. If live_container is given (a Streamlit container
    or st.empty() placeholder), streams combined stdout+stderr into it
    live, byte-by-byte -- important because tools like drf_to_doppler.py
    print progress dots with no trailing newline, so line-buffered
    reading (or subprocess.run's capture_output, which returns nothing
    until the process exits) would show nothing until the whole thing
    finished, even on a fast extraction. Returns (ok, full_output)."""
    if live_container is None:
        try:
            proc = subprocess.run(
                args, cwd=cwd or REPO_DIR, capture_output=True, text=True, timeout=1800,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode == 0, out
        except subprocess.TimeoutExpired as e:
            return False, f"TIMED OUT after 1800s\n{e}"
        except FileNotFoundError as e:
            return False, f"Command not found: {e}"

    placeholder = live_container.empty()
    buf = []
    last_shown_len = 0
    start = time.time()
    try:
        proc = subprocess.Popen(
            args, cwd=cwd or REPO_DIR, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        while True:
            if time.time() - start > 1800:
                proc.kill()
                buf.append("\n[TIMED OUT after 1800s -- process killed]")
                break
            ch = proc.stdout.read(1)
            if ch == "" and proc.poll() is not None:
                break
            if ch:
                buf.append(ch)
                if len(buf) - last_shown_len >= 20:
                    placeholder.code("".join(buf))
                    last_shown_len = len(buf)
        full_output = "".join(buf)
        placeholder.code(full_output if full_output.strip() else "(no output)")
        return (proc.returncode == 0), full_output
    except FileNotFoundError as e:
        return False, f"Command not found: {e}"


def parse_doa_output(text):
    """Extract speed/azimuth/flags/diagnostics from tid_doa.py's printed output."""
    result = {}
    m = re.search(r"Phase speed:\s*([\d.]+) m/s", text)
    if m:
        result["speed_m_s"] = float(m.group(1))
    m = re.search(r"Wave coming from:\s*([\d.]+)", text)
    if m:
        result["azimuth_from_deg"] = float(m.group(1))
    m = re.search(r"Wave heading toward:\s*([\d.]+)", text)
    if m:
        result["azimuth_to_deg"] = float(m.group(1))
    m = re.search(r"(\d+) of 5 diagnostic\(s\) outside typical ranges", text)
    if m:
        result["flags"] = int(m.group(1))
    return result


def extract_interpretation_section(report_text):
    """Pull the DOA CROSS-CHECK INTERPRETATION block straight out of the
    report.txt text produced by fetch_madrigal_tec.py / _closure.py
    (v1.1.0+ / v1.2.0-closure-experimental+). This is a passthrough, not
    a recomputation -- the verdict, per-station numbers, and outlier
    flagging are all computed once, in the CLI script itself, so CLI and
    dashboard usage always show the identical analysis. An earlier
    version of this dashboard had its own separate copy of this logic
    (regex-parsing the cross-correlation table and recomputing the
    verdict independently) -- removed in favor of this, since two
    implementations of the same analysis is a real risk of them quietly
    drifting apart.

    Returns (verdict_word_or_None, full_section_text_or_None).
    """
    lines = report_text.splitlines()
    start = next((i for i, l in enumerate(lines) if "DOA CROSS-CHECK INTERPRETATION" in l), None)
    if start is None:
        return None, None
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() == "" and i > start + 3 and
                (i + 1 >= len(lines) or lines[i + 1].strip().startswith("NOTES:") or lines[i + 1].strip() == "")),
               len(lines))
    section = "\n".join(lines[start:end]).strip()
    m = re.search(r"Verdict:\s*(CONSISTENT|MOSTLY CONSISTENT|INCONSISTENT)", section)
    verdict = m.group(1) if m else None
    return verdict, section


def render_doa_summary(doa):
    """Just the metric row -- factored out so cached results (from a
    prior run, redisplayed after an unrelated widget interaction) look
    identical to a freshly-completed run."""
    c1, c2, c3 = st.columns(3)
    c1.metric("Speed", f"{doa['speed_m_s']:.1f} m/s")
    c2.metric("Coming from", f"{doa.get('azimuth_from_deg', float('nan')):.1f}°")
    c3.metric("Diagnostic flags", f"{doa.get('flags', '?')} / 5")


def render_tec_summary(verdict, interp_section, out_dir):
    """Verdict box + full section + images -- factored out for the same
    cache-and-redisplay reason as render_doa_summary above. out_dir is a
    string (session_state doesn't need to round-trip Path objects)."""
    if interp_section:
        st.subheader("TEC cross-check interpretation")
        verdict_line = next((l.strip() for l in interp_section.splitlines() if l.strip().startswith("Verdict:")), None)
        display_fn = {"CONSISTENT": st.success, "MOSTLY CONSISTENT": st.warning,
                      "INCONSISTENT": st.error}.get(verdict, st.info)
        if verdict_line:
            display_fn(verdict_line)
        st.code(interp_section)
    for img_name in ["madrigal_tec_raw.png", "madrigal_tec_detrended.png", "madrigal_tec_xcorr.png"]:
        img_path = Path(out_dir) / img_name
        if img_path.exists():
            st.image(str(img_path), caption=img_name)


def run_and_display_doa(config_path, live_log_fn, extra_args=None, header="Direction of arrival"):
    """Run tid_doa.py against an existing config, display its result, and
    return the parsed doa dict (or None on failure). Shared by the main
    pipeline and the drop-station re-run section below, so both stay
    consistent instead of each having its own copy of this logic.
    """
    st.subheader(header)
    expander = st.expander("tid_doa.py output", expanded=True)
    args = [sys.executable, str(REPO_DIR / "tid_doa.py"), str(config_path)]
    if extra_args:
        args += extra_args
    ok, out = run_cmd(args, live_container=expander)
    live_log_fn(f"$ {' '.join(args)}\n{out}")
    if not ok:
        st.error("tid_doa.py failed -- see output above / raw subprocess log")
        return None
    doa = parse_doa_output(out)
    if "speed_m_s" not in doa:
        st.error("Could not parse a DOA result from tid_doa.py output -- see output above")
        return None

    render_doa_summary(doa)
    with st.expander("Full tid_doa.py output"):
        st.code(out)
    return doa


def run_and_display_tec(config_path, doa, stations_subset, tec_script, out_dir,
                         user_name, user_email, user_affil, tec_tolerance_min,
                         live_log_fn, header="Madrigal TEC cross-check"):
    """Run the Madrigal TEC cross-check against a specific station subset
    (so a drop-station re-run correctly excludes the dropped station(s)
    from the TEC comparison too, not just from the DOA fit) and display
    the result. stations_subset: list of {"name","lat","lon"} dicts.
    Returns (verdict, interp_section) for caching, or (None, None) on
    failure/no report.
    """
    st.subheader(header)
    speed = doa["speed_m_s"]
    az_from = doa.get("azimuth_from_deg")
    az_toward = (az_from + 180) % 360 if az_from is not None else None

    doa_lags_args = []
    if az_toward is not None:
        for i in range(len(stations_subset)):
            for j in range(i + 1, len(stations_subset)):
                s1, s2 = stations_subset[i], stations_subset[j]
                dist = gc_dist_km(s1["lon"], s1["lat"], s2["lon"], s2["lat"])
                bear = bearing_deg(s1["lon"], s1["lat"], s2["lon"], s2["lat"])
                lag_s = projected_lag_s(dist, az_toward, bear, speed)
                doa_lags_args.append(f"{s1['name']},{s2['name']},{lag_s:.0f}")

    args = [
        sys.executable, str(REPO_DIR / tec_script),
        "--config", str(config_path),
        "--stations"] + [f"{s['name']},{s['lon']},{s['lat']}" for s in stations_subset] + [
        "--user-name", user_name, "--user-email", user_email, "--user-affiliation", user_affil,
        "--doa-speed", str(speed),
        "--output-dir", str(out_dir),
        "--tec-tolerance-min", str(tec_tolerance_min),
    ]
    if az_from is not None:
        args += ["--doa-azimuth-from", str(az_from)]
    if doa_lags_args:
        args += ["--doa-lags"] + doa_lags_args

    st.caption(f"Running {tec_script} on {len(stations_subset)} station(s) -- "
               f"contacts Madrigal over the network, output streams live below.")
    expander = st.expander(f"{tec_script} output", expanded=True)
    ok, out = run_cmd(args, live_container=expander)
    live_log_fn(f"$ {' '.join(args)}\n{out}")
    if not ok:
        st.error(f"{tec_script} failed -- see output above (common cause: TEC experiment not yet on Madrigal for this date)")
        return None, None
    st.success(f"{tec_script} complete -> `{out_dir}`")

    report_path = out_dir / "madrigal_tec_report.txt"
    report_text = report_path.read_text() if report_path.exists() else ""
    verdict, interp_section = extract_interpretation_section(report_text) if report_text else (None, None)
    render_tec_summary(verdict, interp_section, str(out_dir))
    if not interp_section and report_text:
        st.caption("No DOA CROSS-CHECK INTERPRETATION section found in the report.")
    with st.expander("Full report text"):
        st.text(report_text)
    return verdict, interp_section


# ── Streamlit UI ──

DASHBOARD_VERSION = "v0.9.0"

st.set_page_config(page_title="TID Pipeline Dashboard", layout="wide")
st.title("TID Direction-of-Arrival Pipeline")
st.caption(f"Dashboard {DASHBOARD_VERSION} -- if the features described in "
           f"chat aren't showing up, check this matches what you expect; "
           f"it usually means an old copy of the file is still in place.")
st.caption(
    "Automated pipeline: DRF discovery -> Doppler extraction -> DOA -> "
    "Madrigal TEC cross-check. Wraps existing scripts; wave-fit (manual "
    "clicking) is not covered here -- use tid_spect_click.py for that."
)

_settings = load_settings()

if "event_dir" not in st.session_state:
    st.session_state.event_dir = _settings.get(
        "event_dir", str(Path.home() / "Downloads" / "tid_event_YYYYMMDD"))


def _handle_browse_click():
    """Runs as a button on_click callback -- these execute BEFORE the
    script reruns and re-instantiates widgets, which is the only point
    at which it's legal to reassign st.session_state for a key that's
    bound to an already-created widget. Doing this same assignment
    inline in the main script body (after the widget already rendered)
    raises StreamlitAPIException, which is what happened before this fix.
    """
    current = st.session_state.get("event_dir", str(Path.home() / "Downloads"))
    picked = browse_for_directory(current)
    if picked:
        st.session_state.event_dir = picked
        st.session_state["_browse_failed"] = False
    else:
        st.session_state["_browse_failed"] = True


with st.sidebar:
    st.header("Event configuration")
    event_dir = st.text_input(
        "Event directory", key="event_dir",
        help="Directory containing DRF station subdirectories (same "
             "convention as tid_workflow.py --event-dir). Click "
             "Browse below to pick with a folder dialog instead of typing.",
    )
    st.button(
        "Browse...", on_click=_handle_browse_click, width="stretch",
        help="Opens a native folder-picker on this machine (only works "
             "when running streamlit locally, not for a remote/hosted server).",
    )

    if st.session_state.get("_browse_failed"):
        st.caption("Folder dialog unavailable or cancelled -- type the path "
                   "manually above instead. (Needs python3-tk installed and "
                   "a local desktop display -- not available over SSH/remote.)")

    ALL_METHODS = ["autocorr", "cwt", "fft", "wave-fit (interactive)", "cwt-prophet (interactive)"]
    method = st.selectbox(
        "Extraction method",
        ALL_METHODS,
        index=ALL_METHODS.index(_settings.get("method", "autocorr"))
        if _settings.get("method") in ALL_METHODS else 0,
        help="autocorr/cwt/fft run automatically. wave-fit and "
             "cwt-prophet open tid_spect_click.py's native window per "
             "station -- you click, fit, and close it yourself; the "
             "dashboard waits and picks up the result. All stations use "
             "the same method for a given run -- mixing methods across "
             "stations in one run isn't supported yet.",
    )
    is_interactive_method = method in ("wave-fit (interactive)", "cwt-prophet (interactive)")

    ylim_half_range = None
    if is_interactive_method:
        ylim_half_range = st.number_input(
            "Doppler axis half-range for clicking (Hz)",
            min_value=0.1, max_value=10.0,
            value=float(_settings.get("ylim_half_range", 2.0)), step=0.5,
            help="The spectrogram window opened for clicking shows "
                 "±this value on the Doppler axis. Default drf_spectrogram.py "
                 "range is ±5 Hz, which can make a real TID signal that only "
                 "varies over a much smaller range look flat and hard to "
                 "click precisely -- narrow this if that happens. Widen it "
                 "if the signal is being clipped at the edges instead.",
        )

    st.divider()
    st.header("Madrigal TEC cross-check")
    run_madrigal = st.checkbox(
        "Perform Madrigal TEC cross-check", value=_settings.get("run_madrigal", True),
        help="Uncheck to skip this entirely -- the pipeline will stop after "
             "the DOA step. Useful if you just want speed/azimuth quickly, "
             "or Madrigal is unreachable/the TEC data isn't posted yet.",
    )
    if run_madrigal:
        tec_options = ["fetch_madrigal_tec.py (stable)",
                        "fetch_madrigal_tec_closure.py (experimental -- see PROJECT_STATE)"]
        tec_variant = st.radio(
            "Script variant", tec_options,
            index=tec_options.index(_settings.get("tec_variant", tec_options[0]))
            if _settings.get("tec_variant") in tec_options else 0,
        )
        user_name = st.text_input("Madrigal user name", value=_settings.get("user_name", ""))
        user_email = st.text_input("Madrigal user email", value=_settings.get("user_email", ""))
        user_affil = st.text_input("Madrigal affiliation", value=_settings.get("user_affil", "psws-drf-tid-tools"))
        tec_tolerance_min = st.slider(
            "Agreement tolerance (minutes)", min_value=5, max_value=60,
            value=int(_settings.get("tec_tolerance_min", 20)), step=5,
            help="Passed straight to the script's own --tec-tolerance-min flag "
                 "-- how close a GPS-TEC-observed lag needs to be to the "
                 "DOA-predicted lag to count as 'agreeing'. Loose by default: "
                 "MSTID-scale GPS TEC is a blunt cross-check, not exact "
                 "confirmation.",
        )
    else:
        tec_variant = _settings.get("tec_variant", "fetch_madrigal_tec.py (stable)")
        user_name = _settings.get("user_name", "")
        user_email = _settings.get("user_email", "")
        user_affil = _settings.get("user_affil", "psws-drf-tid-tools")
        tec_tolerance_min = _settings.get("tec_tolerance_min", 20)
        st.caption("Skipped -- pipeline will stop after the DOA step.")

    st.divider()
    # Deliberately created here (not disabled, not gated on any slow
    # computation below) so it's visible immediately -- previously it
    # lived after the overview spectrogram generation, so during that
    # step (which can take a while on a real full-day recording) the
    # sidebar looked incomplete/broken, with no run button at all.
    # Prerequisites (channel confirmation, Madrigal fields) are now
    # checked inside the click handler instead of via disabled=.
    run_button = st.button("Run full pipeline", type="primary", width="stretch")

# ── Live: discovery, event window, coords, and channel confirmation ──
# All of this runs on every rerun (not gated behind the run button), so
# by the time you click "Run full pipeline" every choice has already been
# made -- including visually confirming any multi-channel station via a
# real spectrogram, not just an auto-picked SNR number.

event_path = Path(event_dir).expanduser()

if not event_path.is_dir():
    st.info("Enter a valid event directory in the sidebar to continue.")
    st.stop()

stations_preview = discover_stations(event_path)
if stations_preview is None:
    st.error("digital_rf not installed. Run: pip install digital_rf --break-system-packages")
    st.stop()
if len(stations_preview) < 3:
    st.warning(f"Found only {len(stations_preview)} DRF station dir(s) in {event_path} -- "
               f"need at least 3 for a DOA fit.")
if not stations_preview:
    st.stop()

# -- Keystone station: the one whose recording bounds/spectrogram anchor
#    the event-window slider. User-selectable rather than always the
#    first one found in directory listing order (which has no relation
#    to data quality or which station is most useful to orient from). --
station_names = [d.name for d in stations_preview]
_saved_keystone = _settings.get("keystone_station")
default_idx = station_names.index(_saved_keystone) if _saved_keystone in station_names else 0
keystone_name = st.selectbox(
    "Keystone station (used for the overview spectrogram and event-window bounds)",
    station_names, index=default_idx,
)
keystone_station = next(d for d in stations_preview if d.name == keystone_name)

# Provisional (NOT yet user-confirmed) channel-num guess for the keystone
# station, used only to orient the overview spectrogram below so it has
# a reasonable chance of showing the right band before you've picked an
# event window yet. The real, mandatory-confirmation step (with a live
# spectrogram preview) happens later, in the Channel/Channel-num
# selection section, for every station -- this is just enough of a
# guess to avoid the overview defaulting to channel-num 0.
_keystone_chans = discover_channels(keystone_station)
_keystone_channel_guess = _keystone_chans[0] if _keystone_chans else "ch0"
_keystone_subs = probe_station_channel_nums(keystone_station, _keystone_channel_guess)
keystone_channel_num_guess = (
    best_channel_num_choice(_keystone_subs)[0] if len(_keystone_subs) > 1 else None
)

save_settings_if_changed({
    "event_dir": event_dir,
    "method": method,
    "run_madrigal": run_madrigal,
    "tec_tolerance_min": tec_tolerance_min,
    "ylim_half_range": ylim_half_range if ylim_half_range is not None else _settings.get("ylim_half_range", 2.0),
    "tec_variant": tec_variant,
    "user_name": user_name,
    "user_email": user_email,
    "user_affil": user_affil,
    "keystone_station": keystone_name,
})

# -- Overview spectrogram, so the window below is picked with actual
#    visual evidence of where the TID is, not blind -- reuses the repo's
#    own drf_spectrogram.py rather than reimplementing spectrogram
#    rendering. Cached to disk; only regenerated on explicit request. --
# -- Overview spectrogram, so the window below is picked with actual
#    visual evidence of where the TID is, not blind -- reuses the repo's
#    own drf_spectrogram.py rather than reimplementing spectrogram
#    rendering (generated once, cached to disk). The current slider
#    selection is drawn on top live via fast PIL overlay (see
#    overlay_selected_window) -- no re-running the slow subprocess on
#    every drag. A placeholder is used so the image can appear visually
#    ABOVE the slider even though its content depends on the slider's
#    value, which isn't known until the slider is defined below. --
st.subheader("Overview spectrogram")
st.caption(f"Full-window spectrogram for **{keystone_station.name}** with the "
           f"selected window highlighted below -- move the slider and the "
           f"highlight updates.")
spectrogram_placeholder = st.empty()

overview_png, axes_path, overview_ok, overview_out = generate_overview_spectrogram(
    event_path, keystone_station, _keystone_channel_guess, keystone_station.name,
    channel_num=keystone_channel_num_guess)
if not overview_png:
    spectrogram_placeholder.warning("Could not generate overview spectrogram -- see details below.")
    with st.expander("drf_spectrogram.py output"):
        st.code(overview_out)

# -- Event window slider, bounded by the keystone station's real recorded range --
bounds_start, bounds_end = get_station_time_bounds(keystone_station)
if bounds_start is None:
    st.error(f"Could not read recorded time bounds from {keystone_station.name} -- is it a valid DRF directory?")
    st.stop()

st.subheader("Event window")
st.caption(
    f"Full recorded range for **{keystone_station.name}**: "
    f"{bounds_start.isoformat()} to {bounds_end.isoformat()}"
)
window = st.slider(
    "Select the TID event window",
    min_value=bounds_start, max_value=bounds_end,
    value=(bounds_start, bounds_end), format="MM/DD HH:mm",
)
event_start_dt, event_end_dt = window
event_start = event_start_dt.isoformat()
event_end = event_end_dt.isoformat()
event_mid_dt = event_start_dt + (event_end_dt - event_start_dt) / 2
st.caption(f"Selected: **{event_start}** to **{event_end}** "
           f"({(event_end_dt - event_start_dt).total_seconds() / 60:.0f} min)")

# Now that the slider value is known, fill in the placeholder created
# above -- this is what makes the highlight appear to live-update as you
# drag, without ever re-invoking drf_spectrogram.py.
if overview_png:
    overlaid = overlay_selected_window(overview_png, axes_path, event_start_dt, event_end_dt)
    if overlaid is not None:
        spectrogram_placeholder.image(overlaid, caption="Yellow band = currently selected window")
    else:
        spectrogram_placeholder.image(str(overview_png), caption="(could not draw selection overlay -- showing plain spectrogram)")

# -- Coordinates: cache -> DRF metadata -> manual entry --
st.subheader("Station coordinates")
cache = load_coords_cache(event_path)
station_info = []
needs_manual = []
for d in stations_preview:
    name = d.name
    if name.upper() in cache:
        lat, lon = cache[name.upper()]["lat"], cache[name.upper()]["lon"]
    else:
        lat, lon = get_drf_metadata_coords(d)
    if lat is None:
        needs_manual.append(name)
        station_info.append({"name": name, "drf_dir": str(d), "lat": None, "lon": None})
    else:
        station_info.append({"name": name, "drf_dir": str(d), "lat": lat, "lon": lon})
        cache.setdefault(name.upper(), {"lat": lat, "lon": lon})

if needs_manual:
    st.warning(f"No cached/metadata coordinates for: {', '.join(needs_manual)}. Enter manually below.")
    for s in station_info:
        if s["lat"] is None:
            c1, c2 = st.columns(2)
            s["lat"] = c1.number_input(f"{s['name']} latitude", value=0.0, format="%.4f", key=f"lat_{s['name']}")
            s["lon"] = c2.number_input(f"{s['name']} longitude", value=0.0, format="%.4f", key=f"lon_{s['name']}")
    save_coords_cache(event_path, {**cache, **{s["name"].upper(): {"lat": s["lat"], "lon": s["lon"]} for s in station_info}})
else:
    save_coords_cache(event_path, cache)

st.dataframe(
    [{"Station": s["name"], "Lat": s["lat"], "Lon": s["lon"]} for s in station_info],
    width="stretch", hide_index=True,
)

# -- Channel selection: real spectrogram + mandatory visual confirmation
#    for any station with more than one DRF channel (RX888-style). --
st.subheader("Channel selection")
all_confirmed = True
any_multi_channel = False
for s in station_info:
    chans = discover_channels(s["drf_dir"])
    if len(chans) <= 1:
        s["channel"] = chans[0] if chans else None
        continue

    any_multi_channel = True
    st.markdown(f"**{s['name']}** -- {len(chans)} channels found. "
                f"Review the spectrograms below and pick the correct one.")
    cols = st.columns(len(chans))
    freq_labels = {}
    for col, ch in zip(cols, chans):
        freq_hz = probe_channel_frequency(s["drf_dir"], ch)
        freq_labels[ch] = f"{ch} (~{freq_hz/1e6:.3f} MHz)" if freq_hz else ch
        with col:
            fig = render_channel_spectrogram(s["drf_dir"], ch, center_dt=event_mid_dt)
            st.pyplot(fig, clear_figure=True)
            st.caption(freq_labels[ch])

    choice = st.radio(
        f"Correct channel for {s['name']}:",
        chans, format_func=lambda ch: freq_labels.get(ch, ch),
        key=f"chan_{s['name']}", horizontal=True,
    )
    s["channel"] = choice
    confirmed = st.checkbox(
        f"I have reviewed the spectrogram(s) above and confirm "
        f"**{freq_labels.get(choice, choice)}** is the correct channel for {s['name']}.",
        key=f"confirm_{s['name']}",
    )
    if not confirmed:
        all_confirmed = False
    st.divider()

if not any_multi_channel:
    st.caption("All stations have a single channel -- nothing to confirm.")

# -- Channel-num selection: real spectrogram + mandatory visual confirmation
#    for any station with more than one channel-num within its selected
#    channel (KA9Q-radio/WSPRdaemon-style receivers -- confirmed present
#    in 3 of 4 real stations tested this session, contrary to an earlier
#    assumption in this file that PSWS data never has channel-nums). Uses
#    tid_workflow.py's own probe_channel_nums()/best_channel_num() policy
#    (frequency match to target_mhz, else highest SNR), channel-aware
#    (see probe_station_channel_nums above) since the channel confirmed
#    just above might not be channel[0]. --
st.subheader("Channel-num selection")
target_mhz = st.number_input(
    "Target carrier frequency (MHz)", value=10.0, step=0.5,
    help="Used to auto-pick the channel-num closest to this frequency, "
         "for stations recording multiple carriers at once (e.g. WWV "
         "5/10/15/20 MHz). Default 10.0 = WWV 10 MHz, the usual target.",
)
any_multi_channel_num = False
for s in station_info:
    subs = probe_station_channel_nums(s["drf_dir"], s.get("channel"), target_mhz=target_mhz)
    if len(subs) <= 1:
        s["channel_num"] = subs[0][0] if subs else None
        continue

    any_multi_channel_num = True
    auto_idx, reason = best_channel_num_choice(subs, target_mhz=target_mhz)
    st.markdown(f"**{s['name']}** -- {len(subs)} channel-nums found "
                f"(auto-picked via {reason}). Review the preview below "
                f"and confirm, or pick a different one.")

    sub_labels = {}
    for sub, snr, freq in subs:
        sub_labels[sub] = (f"{sub} -- {freq/1e6:.3f} MHz, {snr:.1f} dB"
                            if freq else f"{sub} -- {snr:.1f} dB")
    default_pos = [sub for sub, _, _ in subs].index(auto_idx)
    choice = st.radio(
        f"Channel-num for {s['name']}:",
        [sub for sub, _, _ in subs], index=default_pos,
        format_func=lambda sub: sub_labels.get(sub, str(sub)),
        key=f"subch_{s['name']}", horizontal=True,
    )
    fig = render_channel_spectrogram(s["drf_dir"], s.get("channel"),
                                       center_dt=event_mid_dt, channel_num=choice)
    st.pyplot(fig, clear_figure=True)
    s["channel_num"] = choice
    confirmed = st.checkbox(
        f"I have reviewed the spectrogram above and confirm "
        f"**{sub_labels.get(choice, choice)}** is the correct channel-num "
        f"for {s['name']}.",
        key=f"subch_confirm_{s['name']}",
    )
    if not confirmed:
        all_confirmed = False
    st.divider()

if not any_multi_channel_num:
    st.caption("All stations have a single channel-num -- nothing to confirm.")

if not all_confirmed:
    st.warning("Confirm the channel/channel-num selection for every station flagged above before running -- "
               "the Run full pipeline button (sidebar) will stop with an error if you click it before that.")

log_box = st.expander("Raw subprocess log", expanded=False)


def log(msg):
    with log_box:
        st.code(msg)


config_path = event_path / "tid_workflow_event.json"

if run_button:
    if run_madrigal and not (user_name and user_email and user_affil):
        st.error("Madrigal user name/email/affiliation are required (free registration, no account needed) "
                  "-- or uncheck 'Perform Madrigal TEC cross-check' in the sidebar to skip this step.")
        st.stop()
    if len(station_info) < 3:
        st.error(f"Only {len(station_info)} station(s) -- need at least 3 for a DOA fit.")
        st.stop()
    if not all_confirmed:
        st.error("Confirm the channel/channel-num selection checkbox for every "
                  "station flagged above (see 'Channel selection' and "
                  "'Channel-num selection' sections) before running.")
        st.stop()

    config_path = event_path / "tid_workflow_event.json"

    if is_interactive_method:
        wave_only = method.startswith("wave-fit")
        tsc_method_name = "wave-fit" if wave_only else "cwt-prophet"

        # -- Step 1: write the config FIRST, with stations but no "file"
        #    yet -- tid_spect_click.py's --event-json needs this file to
        #    already exist so it can update the matching station entry
        #    in place when you press X. No guessing output filenames:
        #    the tool writes its own path back into this same file. --
        st.subheader(f"Step 1 -- Interactive extraction ({tsc_method_name})")
        config = {
            "event_start_utc": event_start,
            "event_end_utc": event_end,
            "resample_seconds": 60,
            "use_bandpass": False,
            "use_ipp": True,
            "min_expected_speed_m_s": 100,
            "stations": [
                {"name": s["name"], "lat": s["lat"], "lon": s["lon"]}
                for s in station_info
            ],
        }
        config_path.write_text(json.dumps(config, indent=2))

        st.info("A native window will open per station -- click cycle "
                 "points on the spectrogram, fit, then **press X to "
                 "export** before closing the window. The dashboard "
                 "waits (this tab will look idle, that's expected) until "
                 "you close each window, then moves to the next station.")

        extraction_ok = True
        for i, s in enumerate(station_info):
            st.write(f"**{s['name']}** -- generating zoomed spectrogram for "
                     f"the selected event window...")
            zoom_png, zoom_axes, zoom_ok, zoom_out = generate_zoomed_spectrogram(
                event_path, s["drf_dir"], s.get("channel"), s["name"],
                event_start_dt, event_end_dt, ylim_half_range=ylim_half_range,
                channel_num=s.get("channel_num"))
            log(f"$ drf_spectrogram.py (zoomed, {s['name']})\n{zoom_out}")
            if not zoom_png:
                st.error(f"{s['name']}: could not generate zoomed spectrogram -- "
                          f"see raw subprocess log")
                extraction_ok = False
                continue

            st.write(f"{s['name']}: opening tid_spect_click.py -- waiting for "
                     f"the window to close...")
            ok, out, updated_file = run_interactive_extraction(
                config_path, s["drf_dir"], s.get("channel"), s["name"],
                zoom_png, (event_end_dt - event_start_dt).total_seconds(),
                wave_only, ylim_half_range=ylim_half_range,
                channel_num=s.get("channel_num"))
            log(f"$ tid_spect_click.py ({s['name']})\n{out}")

            if not ok:
                st.error(f"{s['name']}: tid_spect_click.py exited with an "
                          f"error -- see raw subprocess log")
                extraction_ok = False
            elif not updated_file:
                st.warning(f"{s['name']}: window closed but no file was "
                           f"registered -- did you forget to press X "
                           f"before closing? Re-run this station.")
                extraction_ok = False
            else:
                st.success(f"{s['name']}: exported -> `{updated_file}`")
                s["file"] = str((event_path / updated_file).resolve()) \
                    if not Path(updated_file).is_absolute() else updated_file

        if not extraction_ok:
            st.error("Not all stations were successfully extracted -- fix "
                      "the ones flagged above and click Run full pipeline "
                      "again. Stations that already succeeded will reuse "
                      "their exported file (re-running tid_spect_click.py "
                      "on them isn't necessary unless you want to redo one).")
            st.stop()
        st.success("Interactive extraction complete for all stations.")

        # -- Step 2: config already updated in place by tid_spect_click.py
        #    (via --event-json) -- just re-read and display it, nothing
        #    to write ourselves. --
        st.subheader("Step 2 -- Event config")
        config = json.loads(config_path.read_text())
        st.write(f"`{config_path}` already updated by tid_spect_click.py "
                 f"as each station was exported.")
        with st.expander("View config"):
            st.json(config)

    else:
        # ── Step 1: extraction (automated) ──
        st.subheader(f"Step 1 -- Doppler extraction ({method})")
        st.caption("Output streams live below as each station extracts -- this is "
                   "the slow step for a wide event window; a full 24h window at "
                   "10s decimation can genuinely take several minutes per station.")
        prog = st.progress(0.0)
        extraction_ok = True
        for i, s in enumerate(station_info):
            out_csv = event_path / f"{s['name'].lower()}_{method}.csv"
            args = [
                sys.executable, str(REPO_DIR / "drf_to_doppler.py"),
                s["drf_dir"],
                "--start", event_start, "--end", event_end,
                "--method", method,
                "--output", str(out_csv),
            ]
            if s.get("channel"):
                args += ["--channel", s["channel"]]
            if s.get("channel_num") is not None:
                args += ["--channel-num", str(s["channel_num"])]
            station_expander = st.expander(f"{s['name']} -- extracting...", expanded=True)
            ok, out = run_cmd(args, live_container=station_expander)
            log(f"$ {' '.join(args)}\n{out}")
            if not ok:
                st.error(f"{s['name']}: extraction failed -- see log above / raw subprocess log")
                extraction_ok = False
            else:
                st.write(f"{s['name']}: -> `{out_csv.name}`")
                s["file"] = str(out_csv)
            prog.progress((i + 1) / len(station_info))
        if not extraction_ok:
            st.stop()
        st.success("Extraction complete for all stations.")

        # ── Step 2: write event config ──
        st.subheader("Step 2 -- Event config")
        config = {
            "event_start_utc": event_start,
            "event_end_utc": event_end,
            "resample_seconds": 60,
            "use_bandpass": False,
            "use_ipp": True,
            "min_expected_speed_m_s": 100,
            "stations": [
                {"name": s["name"], "file": s["file"], "method": method,
                 "lat": s["lat"], "lon": s["lon"]}
                for s in station_info
            ],
        }
        config_path.write_text(json.dumps(config, indent=2))
        st.write(f"Wrote `{config_path}`")
        with st.expander("View config"):
            st.json(config)

    # ── Step 3: DOA ──
    doa = run_and_display_doa(config_path, log, header="Step 3 -- Direction of arrival")
    if doa is None:
        st.stop()
    st.session_state["cached_doa"] = doa
    st.session_state["cached_tec"] = None  # cleared unless Step 4 below sets it

    # ── Step 4: Madrigal TEC cross-check (optional) ──
    if not run_madrigal:
        st.info("Madrigal TEC cross-check skipped (unchecked in sidebar). "
                "Pipeline complete -- DOA result above is the final output.")
        st.balloons()
    else:
        tec_script = ("fetch_madrigal_tec_closure.py"
                      if "closure" in tec_variant else "fetch_madrigal_tec.py")
        tec_out_dir = event_path / f"evaluation_{tec_script.replace('.py', '')}"
        verdict, interp_section = run_and_display_tec(
            config_path, doa, station_info, tec_script, tec_out_dir,
            user_name, user_email, user_affil, tec_tolerance_min, log,
            header="Step 4 -- Madrigal TEC cross-check",
        )
        st.session_state["cached_tec"] = {"verdict": verdict, "interp_section": interp_section,
                                           "out_dir": str(tec_out_dir)}
        st.balloons()

elif st.session_state.get("cached_doa"):
    # A prior run (this session) completed but the current rerun was
    # triggered by something else (e.g. touching the drop-station
    # multiselect below) -- redisplay the cached results rather than
    # letting them silently vanish, since Streamlit only keeps elements
    # on screen that get re-emitted during the current script execution.
    st.info("Showing results from the last completed run in this session "
            "(this rerun was triggered by something else, e.g. the "
            "'drop station' controls below).")
    st.subheader("Step 3 -- Direction of arrival")
    render_doa_summary(st.session_state["cached_doa"])
    cached_tec = st.session_state.get("cached_tec")
    if cached_tec:
        st.subheader("Step 4 -- Madrigal TEC cross-check")
        render_tec_summary(cached_tec["verdict"], cached_tec["interp_section"], cached_tec["out_dir"])


# ── Investigate further: drop station(s) and re-run DOA/Madrigal ──
# Independent of the run_button flow above -- works off the config file
# on disk, so it's available any time a full run has completed (this
# session or a prior one), without needing to redo the slow extraction
# step. Mirrors the exact `tid_doa.py --drop NAME` workflow used by hand
# earlier for the June 6 2026 event investigation (AC0G_ND exclusion).
if config_path.exists():
    try:
        _cfg = json.loads(config_path.read_text())
        _cfg_stations = _cfg.get("stations", [])
    except Exception:
        _cfg_stations = []

    if len(_cfg_stations) > 3:
        st.divider()
        st.header("Investigate further: drop station(s) and re-run")
        st.caption("Re-runs just the DOA fit (and optionally the Madrigal cross-check) "
                   "excluding the selected station(s) -- extraction isn't redone. Useful "
                   "for checking whether one station (e.g. E-region contamination) is "
                   "skewing the result, the same way AC0G_ND was excluded for the Jan "
                   "2026 event.")
        cfg_names = [s["name"] for s in _cfg_stations]
        drop_names = st.multiselect("Station(s) to drop", cfg_names)
        rerun_madrigal_too = st.checkbox(
            "Also re-run Madrigal TEC cross-check with the reduced station set",
            value=run_madrigal, disabled=not run_madrigal,
            help="Only available if Madrigal is enabled in the sidebar." if not run_madrigal else None,
        )
        rerun_clicked = st.button("Re-run with station(s) dropped", disabled=not drop_names)

        if rerun_clicked:
            if len(_cfg_stations) - len(drop_names) < 3:
                st.error(f"Dropping {len(drop_names)} station(s) would leave fewer than "
                          f"3 -- need at least 3 for a DOA fit.")
            else:
                st.subheader(f"Re-run excluding: {', '.join(drop_names)}")
                extra_args = []
                for name in drop_names:
                    extra_args += ["--drop", name]
                new_doa = run_and_display_doa(
                    config_path, log, extra_args=extra_args,
                    header="Direction of arrival (dropped station re-run)")
                if new_doa is not None and rerun_madrigal_too:
                    remaining = [s for s in _cfg_stations if s["name"] not in drop_names]
                    tec_script_rerun = ("fetch_madrigal_tec_closure.py"
                                        if "closure" in tec_variant else "fetch_madrigal_tec.py")
                    rerun_out_dir = event_path / f"evaluation_{tec_script_rerun.replace('.py', '')}_dropped"
                    run_and_display_tec(
                        config_path, new_doa, remaining, tec_script_rerun, rerun_out_dir,
                        user_name, user_email, user_affil, tec_tolerance_min, log,
                        header="Madrigal TEC cross-check (dropped station re-run)",
                    )
