r"""
tid_guided_extract.py — interactive guided Doppler CSV correction

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 0.1.0
License: MIT (do whatever you want, no warranty).

OVERVIEW
========
Displays automated Doppler CSV traces (from drf_to_doppler.py) in an
interactive stacked plot and lets the user click ground-truth phase
samples on the TID wave of interest for each station.  A sinusoid is
fitted through the clicks and replaces the automated Doppler values in
the selected time window, producing a higher-quality "guided" CSV.

The tool is intended as a QC/correction layer on top of the existing
automated extraction pipeline, not a replacement for it.

WORKFLOW
========
1. Launch with a tid_doa.py config JSON or a list of NAME:FILE pairs.
2. The tool shows one panel per station, all on a common time axis,
   with the automated Doppler trace in grey.
3. Use the segment selector (drag on any panel) to mark the TID window.
4. Press 1/2/3/... to select the active station, then click 3-7 points
   along the TID wave crest/trough visible in that station's panel.
   Clicks appear as coloured dots.
5. Press F to fit: a sinusoid is computed from the clicks and overlaid
   in the active station's panel.
6. Press A to fit all stations at once (using the same omega derived
   from the reference station, station 1).
7. Press W to write guided CSVs.  Each input file foo.csv is written
   as foo_guided.csv in the same directory.
8. Press R to reset clicks for the active station.
9. Press C to clear all clicks and fits.
10. Press Q to quit.

USAGE
=====
Load from a tid_doa.py config JSON (recommended):

    python tid_guided_extract.py --config event_fft_3stn.json

Or specify stations directly:

    python tid_guided_extract.py \
        --stations W7LUX:w7lux_fft_clean.csv \
                   AC0G_ND:ac0g_nd_fft_clean.csv \
                   N4RVE:n4rve_fft_clean.csv \
        --start 2024-05-17T18:00:00 --end 2024-05-17T20:00:00

OPTIONS
=======
    --config FILE.json        Read station list from tid_doa.py config
    --stations N:F ...        NAME:FILE pairs (alternative to --config)
    --start, --end            Time window override (ISO format)
    --period-hint SECONDS     Hint for TID period (default: auto from clicks)

KEYBOARD SHORTCUTS
==================
    1-9       Select active station (matches panel order top to bottom)
    F         Fit sinusoid for active station from clicks
    A         Fit all stations (enforces common omega from station 1)
    W         Write guided CSVs
    R         Reset clicks for active station
    C         Clear all clicks and fits
    Q         Quit

OUTPUT
======
For each input file foo.csv, writes foo_guided.csv with the same
columns (timestamp_utc, doppler_hz, snr_db).  In the guided window,
doppler_hz is replaced by the fitted sinusoid; outside the window
the original automated values are preserved.  snr_db is unchanged.

REQUIREMENTS
============
    pip install pandas numpy pyqtgraph PyQt5

SEE ALSO
========
    drf_to_doppler.py    produces the input Doppler CSVs
    tid_doa.py           consumes CSVs for DOA analysis
    tid_stack_plot.py    static stacked plot (non-interactive companion)
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg

# ---------------------------------------------------------------------------
# Colour palette — one per station, consistent across panels
# ---------------------------------------------------------------------------
STATION_COLOURS = [
    "#4e9af1",   # blue
    "#f1a14e",   # orange
    "#4ef17a",   # green
    "#f14e4e",   # red
    "#c44ef1",   # purple
    "#f1e24e",   # yellow
    "#4ef1e8",   # cyan
    "#f14ea8",   # pink
]

CLICK_COLOUR   = "#ff4444"
FIT_COLOUR_DIM = "#888888"   # automated trace
FIT_ALPHA      = 180         # alpha for fitted overlay


# ---------------------------------------------------------------------------
# Sinusoid fitting
# ---------------------------------------------------------------------------

def fit_sinusoid_from_clicks(clicks, omega=None):
    """
    Fit  y(t) = A sin(ωt + φ)  from sparse (t, y) samples.

    Parameters
    ----------
    clicks : list of (t_seconds, y_hz)
    omega  : float or None
        Angular frequency in rad/s.  If None, estimated from click spacing.

    Returns
    -------
    amplitude, omega, phase  — or None on failure.
    """
    if len(clicks) < 3:
        return None

    arr = np.array(clicks)
    t, y = arr[:, 0], arr[:, 1]

    if omega is None:
        # Estimate period from mean spacing of sorted click times.
        # Heuristic: assumes clicks sample roughly one full period.
        t_sorted = np.sort(t)
        span = t_sorted[-1] - t_sorted[0]
        if span < 1:
            return None
        # Treat the click span as ~1 period
        omega = 2 * np.pi / span

    # Linearise:  y = a·sin(ωt) + b·cos(ωt)
    A_mat = np.column_stack([np.sin(omega * t), np.cos(omega * t)])
    coeff, *_ = np.linalg.lstsq(A_mat, y, rcond=None)
    a, b = coeff
    amplitude = np.sqrt(a**2 + b**2)
    phase = np.arctan2(b, a)
    return amplitude, omega, phase


def evaluate_sinusoid(t_arr, amplitude, omega, phase):
    """Evaluate fitted sinusoid on a time array."""
    return amplitude * np.sin(omega * t_arr + phase)


# ---------------------------------------------------------------------------
# Station data container
# ---------------------------------------------------------------------------

class StationData:
    def __init__(self, name, filepath, t0=None, t1=None):
        self.name     = name
        self.filepath = Path(filepath)
        self.clicks   = []          # list of (t_seconds, doppler_hz)
        self.fit      = None        # (amplitude, omega, phase) or None
        self.df       = None        # full DataFrame from CSV
        self.t_sec    = None        # numpy array, seconds from epoch
        self.doppler  = None        # numpy array, Hz
        self._load(t0, t1)

    def _load(self, t0, t1):
        df = pd.read_csv(
            self.filepath,
            parse_dates=["timestamp_utc"],
        )
        df["timestamp_utc"] = pd.to_datetime(
            df["timestamp_utc"], utc=True
        )
        df = df.sort_values("timestamp_utc").reset_index(drop=True)

        if t0 is not None:
            df = df[df["timestamp_utc"] >= t0]
        if t1 is not None:
            df = df[df["timestamp_utc"] <= t1]

        self.df      = df
        # Use float seconds from first timestamp as x-axis
        self.t_sec   = (
            df["timestamp_utc"].astype("int64").values / 1e9
        ).astype(float)
        self.doppler = df["doppler_hz"].values.astype(float)

    @property
    def t_rel(self):
        """Seconds relative to t_sec[0] — used for display."""
        if self.t_sec is None or len(self.t_sec) == 0:
            return np.array([])
        return self.t_sec - self.t_sec[0]

    def guided_csv_path(self):
        p = self.filepath
        return p.parent / (p.stem + "_guided" + p.suffix)


# ---------------------------------------------------------------------------
# Main GUI
# ---------------------------------------------------------------------------

class GuidedExtractApp(QtWidgets.QMainWindow):

    def __init__(self, stations, segment_t0=None, segment_t1=None,
                 period_hint=None):
        """
        Parameters
        ----------
        stations      : list of StationData
        segment_t0/t1 : float seconds (relative), pre-set segment bounds
        period_hint   : float seconds, TID period hint
        """
        super().__init__()
        self.stations     = stations
        self.n_stations   = len(stations)
        self.active_idx   = 0
        self.period_hint  = period_hint

        # Segment bounds in relative seconds
        self.seg_t0 = segment_t0
        self.seg_t1 = segment_t1

        self._build_ui()
        self._install_shortcuts()
        self._plot_all()
        self._update_status()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self.setWindowTitle("TID Guided Extraction — psws-drf-tid-tools")
        self.resize(1200, 200 * self.n_stations + 120)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)
        vbox.setContentsMargins(4, 4, 4, 4)
        vbox.setSpacing(2)

        # Status bar at top
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet(
            "font-family: monospace; font-size: 11px; "
            "background: #1a1a2e; color: #e0e0e0; padding: 4px;"
        )
        vbox.addWidget(self.status_label)

        # pyqtgraph graphics layout
        pg.setConfigOption("background", "#0d0d1a")
        pg.setConfigOption("foreground", "#cccccc")

        self.glw = pg.GraphicsLayoutWidget()
        vbox.addWidget(self.glw)

        self.plots  = []   # PlotItem per station
        self.auto_curves  = []   # grey automated trace
        self.fit_curves   = []   # coloured fitted sinusoid
        self.click_scatters = []  # red click dots
        self.seg_regions  = []   # LinearRegionItem per plot

        t_ref = self.stations[0].t_sec[0] if self.stations else 0.0

        for idx, stn in enumerate(self.stations):
            colour = STATION_COLOURS[idx % len(STATION_COLOURS)]

            p = self.glw.addPlot(row=idx, col=0)
            p.setLabel("left", stn.name, units="Hz",
                       **{"font-size": "9pt"})
            if idx == self.n_stations - 1:
                p.setLabel("bottom", "Time (s from start)")
            else:
                p.hideAxis("bottom")

            if idx > 0:
                p.setXLink(self.plots[0])

            # Automated trace (grey)
            auto = p.plot(
                stn.t_rel,
                stn.doppler,
                pen=pg.mkPen(color=FIT_COLOUR_DIM, width=1),
                name="auto",
            )

            # Fitted sinusoid (hidden until fit is computed)
            fit_pen = pg.mkPen(color=colour, width=2)
            fit_curve = p.plot([], [], pen=fit_pen, name="fit")

            # Click scatter
            scatter = pg.ScatterPlotItem(
                size=8,
                brush=pg.mkBrush(CLICK_COLOUR),
                pen=pg.mkPen(None),
            )
            p.addItem(scatter)

            # Segment region (shared across all panels)
            region = pg.LinearRegionItem(
                values=[stn.t_rel[len(stn.t_rel)//4],
                        stn.t_rel[3*len(stn.t_rel)//4]],
                brush=pg.mkBrush(255, 255, 100, 25),
                pen=pg.mkPen(color="#ffff64", width=1),
                movable=True,
            )
            region.sigRegionChanged.connect(self._on_region_changed)
            p.addItem(region)

            # Mouse click handler
            p.scene().sigMouseClicked.connect(
                self._make_click_handler(idx, p)
            )

            self.plots.append(p)
            self.auto_curves.append(auto)
            self.fit_curves.append(fit_curve)
            self.click_scatters.append(scatter)
            self.seg_regions.append(region)

        # Sync all regions to the first one's position
        self._sync_regions()

    # ------------------------------------------------------------------
    # Segment region sync
    # ------------------------------------------------------------------

    def _on_region_changed(self):
        """Keep all segment regions in sync."""
        sender = self.sender()
        bounds = sender.getRegion()
        self._sync_regions(bounds)

    def _sync_regions(self, bounds=None):
        if bounds is None:
            bounds = self.seg_regions[0].getRegion()
        for r in self.seg_regions:
            r.blockSignals(True)
            r.setRegion(bounds)
            r.blockSignals(False)
        self.seg_t0, self.seg_t1 = bounds

    # ------------------------------------------------------------------
    # Mouse click handler factory
    # ------------------------------------------------------------------

    def _make_click_handler(self, idx, plot):
        def handler(event):
            if event.button() != QtCore.Qt.LeftButton:
                return
            if idx != self.active_idx:
                return
            pos = event.scenePos()
            if not plot.sceneBoundingRect().contains(pos):
                return
            mouse = plot.vb.mapSceneToView(pos)
            t_rel = float(mouse.x())
            y     = float(mouse.y())
            self.stations[idx].clicks.append((t_rel, y))
            self._refresh_clicks(idx)
            self._update_status()
        return handler

    # ------------------------------------------------------------------
    # Plotting helpers
    # ------------------------------------------------------------------

    def _plot_all(self):
        for idx in range(self.n_stations):
            self._refresh_clicks(idx)
            self._refresh_fit(idx)

    def _refresh_clicks(self, idx):
        clicks = self.stations[idx].clicks
        if clicks:
            pts = [{"pos": [t, y]} for t, y in clicks]
            self.click_scatters[idx].setData(pts)
        else:
            self.click_scatters[idx].setData([])

    def _refresh_fit(self, idx):
        stn = self.stations[idx]
        if stn.fit is None:
            self.fit_curves[idx].setData([], [])
            return
        amp, omega, phase = stn.fit
        t_arr = stn.t_rel
        y_fit = evaluate_sinusoid(t_arr, amp, omega, phase)
        self.fit_curves[idx].setData(t_arr, y_fit)

    # ------------------------------------------------------------------
    # Fit logic
    # ------------------------------------------------------------------

    def _fit_station(self, idx, omega=None):
        stn = self.stations[idx]
        if len(stn.clicks) < 3:
            self._set_status(
                f"Station {stn.name}: need ≥3 clicks (have {len(stn.clicks)})"
            )
            return None

        if omega is None and self.period_hint is not None:
            omega = 2 * np.pi / self.period_hint

        result = fit_sinusoid_from_clicks(stn.clicks, omega=omega)
        if result is None:
            self._set_status(f"Station {stn.name}: fit failed")
            return None

        stn.fit = result
        self._refresh_fit(idx)
        return result

    def _fit_active(self):
        result = self._fit_station(self.active_idx)
        if result:
            amp, omega, phase = result
            period = 2 * np.pi / omega
            stn = self.stations[self.active_idx]
            self._set_status(
                f"{stn.name}: A={amp:.4f} Hz  T={period:.0f} s  "
                f"φ={np.degrees(phase):.1f}°"
            )
        self._update_status()

    def _fit_all(self):
        """Fit all stations, enforcing common omega from station 0."""
        # Fit reference station first
        ref = self._fit_station(0)
        if ref is None:
            self._set_status("Fit all: reference station (1) fit failed")
            return
        _, omega_ref, _ = ref
        period = 2 * np.pi / omega_ref
        results = [ref]
        for idx in range(1, self.n_stations):
            r = self._fit_station(idx, omega=omega_ref)
            results.append(r)
        n_ok = sum(1 for r in results if r is not None)
        self._set_status(
            f"Fit all: {n_ok}/{self.n_stations} succeeded  "
            f"(shared T={period:.0f} s)"
        )
        self._update_status()

    # ------------------------------------------------------------------
    # Write guided CSVs
    # ------------------------------------------------------------------

    def _write_guided(self):
        if self.seg_t0 is None or self.seg_t1 is None:
            self._set_status("Set segment region before writing")
            return

        written = []
        skipped = []

        for idx, stn in enumerate(self.stations):
            if stn.fit is None:
                skipped.append(stn.name)
                continue

            amp, omega, phase = stn.fit
            df = stn.df.copy()
            t_rel = stn.t_rel

            # Mask for the guided window
            mask = (t_rel >= self.seg_t0) & (t_rel <= self.seg_t1)

            # Replace doppler_hz with fitted sinusoid in window
            df.loc[mask, "doppler_hz"] = evaluate_sinusoid(
                t_rel[mask], amp, omega, phase
            )

            out_path = stn.guided_csv_path()
            df.to_csv(out_path, index=False)
            written.append(str(out_path))

        msg = f"Wrote {len(written)} guided CSV(s)"
        if skipped:
            msg += f"  |  skipped (no fit): {', '.join(skipped)}"
        self._set_status(msg)
        for p in written:
            print(f"  Written: {p}")

    # ------------------------------------------------------------------
    # Reset / clear
    # ------------------------------------------------------------------

    def _reset_active(self):
        idx = self.active_idx
        self.stations[idx].clicks = []
        self.stations[idx].fit = None
        self._refresh_clicks(idx)
        self._refresh_fit(idx)
        self._update_status()

    def _clear_all(self):
        for idx, stn in enumerate(self.stations):
            stn.clicks = []
            stn.fit = None
            self._refresh_clicks(idx)
            self._refresh_fit(idx)
        self._update_status()

    # ------------------------------------------------------------------
    # Status display
    # ------------------------------------------------------------------

    def _set_status(self, msg):
        self.status_label.setText(msg)

    def _update_status(self):
        parts = []
        for idx, stn in enumerate(self.stations):
            marker = "▶ " if idx == self.active_idx else "  "
            n_clicks = len(stn.clicks)
            fitted = "✓fit" if stn.fit is not None else f"{n_clicks}pts"
            parts.append(f"{marker}[{idx+1}] {stn.name}: {fitted}")
        seg = ""
        if self.seg_t0 is not None:
            seg = (f"   segment: {self.seg_t0:.0f}–{self.seg_t1:.0f} s")
        self.status_label.setText(
            "  |  ".join(parts) + seg +
            "   [1-9] station  [F] fit  [A] fit all  "
            "[W] write  [R] reset  [C] clear  [Q] quit"
        )

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _install_shortcuts(self):
        for i in range(min(9, self.n_stations)):
            key = str(i + 1)
            QtWidgets.QShortcut(
                QtGui.QKeySequence(key), self,
                lambda checked=False, idx=i: self._select_station(idx)
            )
        QtWidgets.QShortcut(QtGui.QKeySequence("F"), self, self._fit_active)
        QtWidgets.QShortcut(QtGui.QKeySequence("A"), self, self._fit_all)
        QtWidgets.QShortcut(QtGui.QKeySequence("W"), self, self._write_guided)
        QtWidgets.QShortcut(QtGui.QKeySequence("R"), self, self._reset_active)
        QtWidgets.QShortcut(QtGui.QKeySequence("C"), self, self._clear_all)
        QtWidgets.QShortcut(QtGui.QKeySequence("Q"), self, self.close)

    def _select_station(self, idx):
        self.active_idx = idx
        # Highlight active panel with a brighter left axis label
        for i, p in enumerate(self.plots):
            style = (
                {"color": STATION_COLOURS[i], "font-size": "10pt"}
                if i == idx
                else {"color": "#888888", "font-size": "9pt"}
            )
            p.setLabel("left", self.stations[i].name, units="Hz", **style)
        self._update_status()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(
        description="Interactive guided Doppler CSV correction tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--config", metavar="JSON",
                   help="tid_doa.py config JSON")
    p.add_argument("--stations", nargs="+", metavar="NAME:FILE",
                   help="Station list as NAME:FILE pairs")
    p.add_argument("--start", metavar="ISO",
                   help="Start time (UTC ISO format)")
    p.add_argument("--end", metavar="ISO",
                   help="End time (UTC ISO format)")
    p.add_argument("--period-hint", type=float, metavar="SECONDS",
                   help="TID period hint in seconds (default: auto)")
    return p.parse_args()


def _load_stations(args):
    t0 = pd.Timestamp(args.start, tz="UTC") if args.start else None
    t1 = pd.Timestamp(args.end,   tz="UTC") if args.end   else None

    station_specs = []   # list of (name, filepath)

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        if t0 is None and "event_start_utc" in cfg:
            t0 = pd.Timestamp(cfg["event_start_utc"], tz="UTC")
        if t1 is None and "event_end_utc" in cfg:
            t1 = pd.Timestamp(cfg["event_end_utc"], tz="UTC")
        cfg_dir = Path(args.config).parent
        for s in cfg["stations"]:
            fpath = cfg_dir / s["file"]
            station_specs.append((s["name"], str(fpath)))

    if args.stations:
        for spec in args.stations:
            name, fpath = spec.split(":", 1)
            station_specs.append((name, fpath))

    if not station_specs:
        print("Error: specify --config or --stations", file=sys.stderr)
        sys.exit(1)

    stations = []
    for name, fpath in station_specs:
        print(f"  Loading {name}: {fpath}")
        try:
            stn = StationData(name, fpath, t0=t0, t1=t1)
            stations.append(stn)
        except Exception as e:
            print(f"  WARNING: could not load {fpath}: {e}", file=sys.stderr)

    if not stations:
        print("Error: no stations loaded", file=sys.stderr)
        sys.exit(1)

    return stations


def main():
    args = _parse_args()
    print("tid_guided_extract.py  v0.1.0")
    stations = _load_stations(args)
    print(f"Loaded {len(stations)} station(s)")

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("TID Guided Extract")

    win = GuidedExtractApp(
        stations,
        period_hint=args.period_hint,
    )
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
