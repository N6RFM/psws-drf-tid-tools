r"""
tid_spect_click.py — spectrogram-based guided Doppler phase extraction

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 0.1.0
License: MIT (do whatever you want, no warranty).

OVERVIEW
========
Displays a Doppler spectrogram PNG and lets the user click directly on
the F-region carrier track — the slow sinusoidal oscillation near 0 Hz that represents the TID.
A sinusoid is fitted to the clicks and the result is used to produce a
corrected "guided" Doppler CSV, replacing the automated extraction in
the selected time window.

This is complementary to tid_guided_extract.py (which works on the
extracted Doppler trace). Clicking on the spectrogram is more intuitive
because the TID is directly visible as the slow F-region carrier oscillation.

WORKFLOW
========
1. Launch with a spectrogram PNG and its corresponding Doppler CSV.
2. The tool shows the spectrogram. Before clicking phase samples, you
   must calibrate the pixel→physical coordinate transform using 4 clicks:

   CALIBRATION (done once per spectrogram, guided by on-screen prompts):
     Cal click 1: click on a known time gridline at Doppler = 0 Hz
                  then type the time value when prompted (e.g. 18.0 for 18:00 UTC)
     Cal click 2: click on a DIFFERENT known time gridline at Doppler = 0 Hz
                  then type the time value when prompted (e.g. 20.0)
     Cal click 3: click on any point at a known Doppler shift
                  (e.g. the +1 Hz gridline) at any time
                  then type the Doppler value when prompted (e.g. 1.0)
     Cal click 4: click on the 0 Hz line at the same time position as click 3
                  (establishes the y-scale)

   After 4 calibration clicks the pixel→(time, Hz) transform is defined.

3. Mark the analysis segment: drag the yellow region handles.
4. Click 2+ points along the F-region carrier (slow oscillation near 0 Hz; avoid fast E-region loops) in the segment.
5. Press F to fit sinusoid, W to write guided CSV.
6. Press R to reset clicks, C to clear all, Q to quit.

USAGE
=====
Single station (most common):

    python tid_spect_click.py \
        --spectrogram w7lux_hires_600.png \
        --csv w7lux_fft_clean.csv \
        --name W7LUX

With a pre-known axis range (skips interactive calibration):

    python tid_spect_click.py \
        --spectrogram w7lux_hires_600.png \
        --csv w7lux_fft_clean.csv \
        --name W7LUX \
        --tlim 16,22 --ylim -5,5

OPTIONS
=======
    --spectrogram PNG     Spectrogram image file
    --csv FILE            Automated Doppler CSV (from drf_to_doppler.py)
    --name NAME           Station name label
    --tlim T0,T1          Known time axis limits in decimal UTC hours
    --ylim LO,HI          Known Doppler axis limits in Hz
    --tref ISO            Reference time for t=0 on the spectrogram
                          (default: midnight of the spectrogram date)
    --seg-start HOURS     Pre-set segment start (decimal UTC hours)
    --seg-end HOURS       Pre-set segment end (decimal UTC hours)
    --period-hint SECS    TID period hint in seconds

KEYBOARD SHORTCUTS
==================
    V     Toggle automated CSV overlay
    X     Export corridor JSON + run sgolay-ridge preview
    R     Reset clicks (keeps calibration)
    C     Clear everything (calibration + clicks)
    Q     Quit

OUTPUT
======
Writes <input_stem>_guided.csv alongside the input CSV.
In the segment window, doppler_hz is replaced by the fitted sinusoid;
outside the window the original automated values are preserved.

REQUIREMENTS
============
    pip install pandas numpy pyqtgraph PyQt5 Pillow
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------

class AxisTransform:
    """
    Maps image pixel coordinates → physical (time_hours, doppler_hz).

    Calibrated from two time points (at doppler=0) and two doppler points
    (at any fixed time), giving a full affine transform.
    """

    def __init__(self):
        self.cal_points = []   # list of (px, py, t_hours, dop_hz)
        self.ready = False
        # Transform coefficients: t = ax*px + bx,  d = ay*py + by
        self.ax = self.bx = self.ay = self.by = None

    def add_cal_point(self, px, py, t_hours, dop_hz):
        self.cal_points.append((px, py, t_hours, dop_hz))
        self._try_fit()

    def _try_fit(self):
        """Fit once we have ≥2 time points and ≥2 doppler points."""
        t_pts = [(px, t) for px, py, t, d in self.cal_points if t is not None]
        d_pts = [(py, d) for px, py, t, d in self.cal_points if d is not None]
        if len(t_pts) >= 2 and len(d_pts) >= 2:
            # Time: t = ax*px + bx
            px0, t0 = t_pts[0]; px1, t1 = t_pts[1]
            self.ax = (t1 - t0) / (px1 - px0) if px1 != px0 else 1.0
            self.bx = t0 - self.ax * px0
            # Doppler: d = ay*py + by  (note: image y may be inverted)
            py0, d0 = d_pts[0]; py1, d1 = d_pts[1]
            self.ay = (d1 - d0) / (py1 - py0) if py1 != py0 else 1.0
            self.by = d0 - self.ay * py0
            self.ready = True

    def px_to_physical(self, px, py):
        """Returns (t_hours, dop_hz) or None if not calibrated."""
        if not self.ready:
            return None
        return self.ax * px + self.bx, self.ay * py + self.by

    def physical_to_px(self, t_hours, dop_hz):
        """Inverse transform."""
        if not self.ready:
            return None
        px = (t_hours - self.bx) / self.ax
        py = (dop_hz   - self.by) / self.ay
        return px, py

    @classmethod
    def from_limits(cls, img_w, img_h, tlim, ylim, plot_fraction=None):
        """
        Build transform from known axis limits and image size.

        plot_fraction: (left, right, bottom, top) as fractions of image
                       size occupied by the plot area (excluding margins).
                       Default assumes matplotlib standard margins.
        """
        # Typical matplotlib figure margins (rough defaults)
        if plot_fraction is None:
            # Defaults measured from drf_spectrogram.py output at 600 dpi
            # (left, right, bottom, top) as fractions of image dimensions
            plot_fraction = (0.0582, 0.8421, 0.3712, 0.9570)
        lf, rf, bf, tf = plot_fraction
        px_left  = lf * img_w
        px_right = rf * img_w
        py_top   = (1 - tf) * img_h   # image y=0 at top
        py_bot   = (1 - bf) * img_h

        t0, t1 = tlim
        d_lo, d_hi = ylim

        obj = cls()
        obj.ax = (t1 - t0) / (px_right - px_left)
        obj.bx = t0 - obj.ax * px_left
        # Image y increases downward; doppler increases upward
        obj.ay = (d_lo - d_hi) / (py_bot - py_top)
        obj.by = d_hi - obj.ay * py_top
        obj.ready = True
        return obj



# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

class SpectClickApp(QtWidgets.QMainWindow):

    CAL_SEQUENCE = [
        "CAL 1/4: Click a known TIME gridline at Doppler = 0 Hz",
        "CAL 2/4: Click a DIFFERENT time gridline at Doppler = 0 Hz",
        "CAL 3/4: Click any point at a known non-zero Doppler (e.g. +1 Hz line)",
        "CAL 4/4: Click Doppler = 0 Hz at the same horizontal position as CAL 3",
    ]

    def __init__(self, img_path, csv_path, name,
                 transform=None, period_hint=None,
                 seg_start=None, seg_end=None,
                 drf_dir=None, subchannel=0, sgolay_window=21.0,
                 corridor_width=0.4):
        super().__init__()
        self.name        = name
        self.img_path    = img_path
        self.csv_path    = Path(csv_path) if csv_path else None
        self.drf_dir     = drf_dir
        self.subchannel  = subchannel
        self.sgolay_window = sgolay_window
        self.corridor_width = corridor_width
        self._wave_mode = False
        self._wave_done = False
        self._wave_clicks_t = []
        self._wave_clicks_d = []
        self._prophet_csv   = None
        self._prophet_done  = False
        self._prophet_curve = None
        self._prophet_pass  = 0     # increments each re-run for color cycling
        self._accepted_csv  = None  # path to last accepted baseline CSV
        self.period_hint = period_hint   # seconds
        self.transform   = transform     # AxisTransform or None
        self.cal_step    = 0 if transform is None else 4
        self.cal_pending = None          # pixel coords waiting for value input
        self.clicks_t    = []            # decimal hours
        self.clicks_d    = []            # doppler Hz
        self._load_image(img_path)
        self._build_ui(seg_start, seg_end)
        self._install_shortcuts()
        self._update_status()
        # Auto-run Prophet on open (Pass 0 — no clicks needed)
        if self.drf_dir:
            QtCore.QTimer.singleShot(500, self._run_prophet_preview)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------


    def _load_image(self, img_path):
        """Load PNG and convert to format pyqtgraph can display."""
        pil_img = Image.open(img_path).convert("RGBA")
        self.img_w, self.img_h = pil_img.size
        arr = np.array(pil_img)
        # pyqtgraph ImageItem expects (width, height, channels) with y=0 at bottom.
        # PIL gives (height, width, channels); transpose axes 0 and 1, then flip y.
        arr = np.transpose(arr, (1, 0, 2))   # → (width, height, channels)
        self.img_arr = arr[:, ::-1, :]        # flip y so bottom=low doppler

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, seg_start, seg_end):
        self.setWindowTitle(
            f"TID Spectrogram Click — {self.name} — psws-drf-tid-tools"
        )
        self.resize(1400, 800)

        pg.setConfigOption("background", "#0a0a14")
        pg.setConfigOption("foreground", "#cccccc")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)
        vbox.setContentsMargins(2, 2, 2, 2)
        vbox.setSpacing(2)

        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet(
            "font-family: monospace; font-size: 11px; "
            "background: #12122a; color: #e8e8e8; padding: 4px;"
        )
        vbox.addWidget(self.status_label)

        self.glw = pg.GraphicsLayoutWidget()
        vbox.addWidget(self.glw)

        self.plot = self.glw.addPlot()
        self.plot.setMouseEnabled(x=False, y=False)
        # Hide pyqtgraph axes — the spectrogram PNG has its own baked-in axes
        self.plot.hideAxis("bottom")
        self.plot.hideAxis("left")

        # Spectrogram image
        self.img_item = pg.ImageItem()
        self.plot.addItem(self.img_item)
        self.img_item.setImage(self.img_arr)

        # Set image scale/position based on transform if available
        self._update_image_transform()


        # Corridor boundary curves (shown after X is pressed)
        self.corridor_hi_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#ffff00", width=1,
                         style=QtCore.Qt.DashLine),
            name="corridor_hi",
        )
        self.corridor_lo_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#ffff00", width=1,
                         style=QtCore.Qt.DashLine),
            name="corridor_lo",
        )

        # SGOLAY-ridge preview curve (shown after X if --drf-dir provided)
        self.preview_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#00ff88", width=2),
            name="sgolay_preview",
        )

        # Ensure all curves start empty — clean launch every time
        self.corridor_hi_curve.setData([], [])
        self.corridor_lo_curve.setData([], [])
        self.preview_curve.setData([], [])

        # Delete stale output files from previous sessions
        import os as _os_clean
        for _suffix in ["_corridor.json", "_corridor_preview.csv"]:
            _stale = str(Path(self.img_path).parent / (Path(self.img_path).stem + _suffix))
            if _os_clean.path.exists(_stale):
                _os_clean.remove(_stale)
                print(f"  Removed stale: {_os_clean.path.basename(_stale)}")

        # Phase click scatter
        self.scatter = pg.ScatterPlotItem(
            size=9,
            brush=pg.mkBrush("#000000"),
            pen=pg.mkPen(color="#ffffff", width=1),
        )
        self.plot.addItem(self.scatter)
        # Brown diamond markers for wave-fit click points
        self.wave_scatter = pg.ScatterPlotItem(
            size=14,
            symbol="d",
            brush=pg.mkBrush(139, 69, 19, 220),
            pen=pg.mkPen(color="#ffffff", width=1.5),
        )
        self.plot.addItem(self.wave_scatter)

        # Calibration click scatter (cyan crosses)
        self.cal_scatter = pg.ScatterPlotItem(
            size=12,
            symbol="+",
            brush=pg.mkBrush("#00ffff"),
            pen=pg.mkPen(color="#00ffff", width=2),
        )
        self.plot.addItem(self.cal_scatter)

        # Segment region
        if self.transform and self.transform.ready:
            t_span = self.transform.ax * self.img_w  # total time width
            t_start = self.transform.bx
            t0 = t_start + t_span * 0.25
            t1 = t_start + t_span * 0.75
        else:
            t0, t1 = 0.25, 0.75   # fractions until calibrated

        if seg_start is not None: t0 = seg_start
        if seg_end   is not None: t1 = seg_end

        self.region = pg.LinearRegionItem(
            values=[t0, t1],
            brush=pg.mkBrush(255, 255, 100, 20),
            pen=pg.mkPen(color="#ffff64", width=1),
            movable=True,
        )
        self.plot.addItem(self.region)
        self.seg_t0, self.seg_t1 = self.region.getRegion()
        self.region.sigRegionChanged.connect(self._on_region)

        # Mouse click
        self.plot.scene().sigMouseClicked.connect(self._on_click)

    def _update_image_transform(self):
        """Position the image in data coordinates using the transform."""
        if self.transform is None or not self.transform.ready:
            return
        # Map pixel corners to physical coordinates
        t_left, d_bot_left = self.transform.px_to_physical(0, self.img_h)
        t_right, d_top = self.transform.px_to_physical(self.img_w, 0)
        width_t  = t_right - t_left
        height_d = d_top   - d_bot_left
        tr = QtGui.QTransform()
        tr.translate(t_left, d_bot_left)
        tr.scale(width_t / self.img_w, height_d / self.img_h)
        self.img_item.setTransform(tr)

    # ------------------------------------------------------------------
    # Region
    # ------------------------------------------------------------------

    def _on_region(self):
        self.seg_t0, self.seg_t1 = self.region.getRegion()
        self._update_status()

    # ------------------------------------------------------------------
    # Click handler
    # ------------------------------------------------------------------

    def _on_click(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        pos = event.scenePos()
        if not self.plot.sceneBoundingRect().contains(pos):
            return
        mouse = self.plot.vb.mapSceneToView(pos)
        vx, vy = float(mouse.x()), float(mouse.y())

        if self.cal_step < 4:
            self._handle_cal_click(vx, vy)
        else:
            self._handle_phase_click(vx, vy)

    def _refresh_corridor(self, t_arr, d_arr, half_bw):
        """Draw corridor bounds on the spectrogram after X export."""
        if len(t_arr) < 2:
            self.corridor_hi_curve.setData([], [])
            self.corridor_lo_curve.setData([], [])
            return
        import numpy as _np
        # Build dense time array across clicked range
        t_dense = _np.linspace(t_arr[0], t_arr[-1], 300)
        centre   = _np.interp(t_dense, t_arr, d_arr)
        self.corridor_hi_curve.setData(t_dense, centre + half_bw)
        self.corridor_lo_curve.setData(t_dense, centre - half_bw)

    def _run_sgolay_preview(self, corridor_json_path):
        """Run sgolay-ridge extraction and overlay result on spectrogram."""
        if not self.drf_dir:
            return
        import subprocess as _sp, os as _os2, threading as _threading
        import pandas as _pd2

        # Get date from sidecar, img filename, or DRF dir name
        import re as _re, json as _json2
        date_str = None
        # Try sidecar JSON first
        _sidecar = str(self.img_path).replace(".png", "_axes.json")
        if not date_str and _os2.path.exists(_sidecar):
            try:
                _sc = _json2.load(open(_sidecar))
                date_str = _sc.get("date_utc")
            except Exception:
                pass
        # Try filename or drf_dir for YYYY-MM-DD
        if not date_str:
            for _s in [str(self.img_path), str(self.drf_dir)]:
                _m = _re.search(r"(\d{4}-\d{2}-\d{2})", _s)
                if _m:
                    date_str = _m.group(1)
                    break
        if not date_str:
            date_str = "2024-05-17"  # last resort fallback
            print(f"  WARNING: could not determine date, using {date_str}")

        def _h_to_iso(h):
            hh = int(h); rem = (h-hh)*60; mm = int(rem); ss = int((rem-mm)*60)
            return f"{date_str}T{hh:02d}:{mm:02d}:{ss:02d}"

        # Use corridor click extent as extraction window
        t0_h = min(self.clicks_t) if self.clicks_t else self.seg_t0
        t1_h = max(self.clicks_t) if self.clicks_t else self.seg_t1
        out_csv = str(corridor_json_path).replace(".json", "_preview.csv")

        cmd = [
            "python3",
            _os2.path.join(_os2.path.dirname(_os2.path.abspath(__file__)),
                          "drf_to_doppler.py"),
            self.drf_dir,
            "--subchannel", str(self.subchannel),
            "--start", _h_to_iso(t0_h),
            "--end",   _h_to_iso(t1_h),
            "--decim-seconds", "60",
            "--method", "sgolay-ridge",
            "--corridor", str(corridor_json_path),
            "--sgolay-window", str(self.sgolay_window),
            "--output", out_csv,
        ]
        self._set_status("Running sgolay-ridge preview... (may take 10-30s)")
        self._preview_done = False
        self._preview_csv  = out_csv

        def _run():
            try:
                _sp.run(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE, timeout=120)
            except Exception as _e:
                print(f"  Preview exception: {_e}")
            finally:
                self._preview_done = True

        _threading.Thread(target=_run, daemon=True).start()

        # Poll from main Qt thread using a method
        self._start_preview_poll()

    def _start_preview_poll(self):
        """Called from main thread — polls until preview CSV is ready."""
        if not self._preview_done:
            QtCore.QTimer.singleShot(1000, self._start_preview_poll)
            return
        import pandas as _pd3, os as _os3
        if not _os3.path.exists(self._preview_csv):
            self._set_status("Preview failed — no output CSV")
            return
        try:
            df_prev = _pd3.read_csv(self._preview_csv, parse_dates=["timestamp_utc"])
            df_prev["t_h"] = (df_prev["timestamp_utc"].dt.hour +
                              df_prev["timestamp_utc"].dt.minute/60 +
                              df_prev["timestamp_utc"].dt.second/3600)
            t_arr = df_prev["t_h"].values
            d_arr = df_prev["doppler_hz"].values
            self.preview_curve.setData(list(t_arr), list(d_arr))
            self._set_status(
                f"✓ Preview: sgolay-ridge {d_arr.min():.2f} to "
                f"{d_arr.max():.2f} Hz [green] — R to re-click, Q to accept"
            )
        except Exception as _e:
            self._set_status(f"Preview display error: {_e}")
            print(f"  Preview display error: {_e}")

    def _handle_cal_click(self, vx, vy):
        """Handle calibration clicks — prompt user for physical value."""
        step = self.cal_step

        if step in (0, 1):
            # Time calibration: user clicked at Doppler=0, need time value
            t_str, ok = QtWidgets.QInputDialog.getText(
                self, "Calibration",
                f"Cal {step+1}/4: Enter the UTC hour for this gridline\n"
                f"(e.g. 18.0 for 18:00 UTC, 18.5 for 18:30):"
            )
            if not ok or not t_str.strip():
                return
            try:
                t_val = float(t_str.strip())
            except ValueError:
                self._set_status("Invalid value — enter a number like 18.0")
                return
            # Store as (view_x, view_y, t_hours, dop=0)
            # At this point view coords = physical if transform ready,
            # else we store pixel-equivalent view coords
            if self.transform is None:
                self.transform = AxisTransform()
            # We need pixel coords; vx,vy are view coords
            # Before calibration, view coords = pixel coords (no transform set)
            self.transform.add_cal_point(vx, vy, t_val, 0.0)
            self._add_cal_marker(vx, vy)

        elif step == 2:
            # Doppler calibration: user clicked at known doppler value
            d_str, ok = QtWidgets.QInputDialog.getText(
                self, "Calibration",
                f"Cal 3/4: Enter the Doppler value (Hz) at this point\n"
                f"(e.g. 1.0 if you clicked the +1 Hz gridline):"
            )
            if not ok or not d_str.strip():
                return
            try:
                d_val = float(d_str.strip())
            except ValueError:
                self._set_status("Invalid value")
                return
            self._cal3_px = (vx, vy)
            self._cal3_d  = d_val
            self.transform.add_cal_point(vx, vy, None, d_val)
            self._add_cal_marker(vx, vy)

        elif step == 3:
            # Cal 4: user clicks 0 Hz at same time as cal 3 → gives y scale
            self.transform.add_cal_point(vx, vy, None, 0.0)
            self._add_cal_marker(vx, vy)
            if self.transform.ready:
                self._update_image_transform()
                self._set_status(
                    "Calibration complete! Now click phase samples on the carrier track."
                )

        self.cal_step += 1
        self._update_status()


    def _add_cal_marker(self, vx, vy):
        pts = [{"pos": [p["pos"][0], p["pos"][1]]}
               for p in (self.cal_scatter.data or [])]
        pts.append({"pos": [vx, vy]})
        self.cal_scatter.setData(pts)

    def _handle_phase_click(self, vx, vy):
        """Store a phase sample click in physical coordinates."""
        # Wave-fit mode intercepts clicks
        if getattr(self, "_wave_mode", False):
            if self.transform and self.transform.ready:
                self._wave_fit_click(vx, vy)
            return
        # Ignore clicks while wave-fit result is displayed
        if getattr(self, "_wave_done", False):
            self._set_status(
                "Wave-fit done — press W to redo, X to export spline, Q to quit")
            return
        if self.transform and self.transform.ready:
            # vx, vy are already in physical coords after image transform
            t_hours, dop_hz = vx, vy
        else:
            self._set_status("Calibrate first (4 clicks needed)")
            return
        self.clicks_t.append(t_hours)
        self.clicks_d.append(dop_hz)
        self._refresh_scatter()
        self._update_status()
        n = len(self.clicks_t)
        self._set_status(
            f"{n} anchor(s).  P=re-run Prophet  X=export  W=wave-fit  R=reset  Q=quit")

    def _refresh_scatter(self):
        if self.clicks_t:
            pts = [{"pos": [t, d]}
                   for t, d in zip(self.clicks_t, self.clicks_d)]
            self.scatter.setData(pts)
        else:
            self.scatter.setData([])



    # ------------------------------------------------------------------
    # Reset / clear
    # ------------------------------------------------------------------

    def _write_corridor(self, half_bw=0.5):
        """Export corridor JSON for drf_to_doppler.py --corridor."""
        if not self.clicks_t:
            self._set_status("No clicks yet — click points first")
            return
        import json as _json
        corridor = {
            "station": self.name,
            "half_bandwidth_hz": half_bw,
            "clicks": [
                {"t_utc_hours": t, "doppler_hz": d}
                for t, d in zip(self.clicks_t, self.clicks_d)
            ],
            "_note": (
                "Generated by tid_spect_click.py for use with "
                "drf_to_doppler.py --corridor"
            ),
        }
        out = Path(self.img_path).parent / (Path(self.img_path).stem + "_corridor.json")
        with open(out, "w") as _f:
            _json.dump(corridor, _f, indent=2)

        # Warn if clicks don't cover the full segment window
        import numpy as _npw
        t_arr_w = _npw.array([c["t_utc_hours"] for c in corridor["clicks"]])
        gap_start = t_arr_w[0] - self.seg_t0
        gap_end   = self.seg_t1 - t_arr_w[-1]
        warn_msgs = []
        if gap_start > 0.25:  # >15 min gap at start
            warn_msgs.append(f"start gap {gap_start*60:.0f} min")
        if gap_end > 0.25:    # >15 min gap at end
            warn_msgs.append(f"end gap {gap_end*60:.0f} min")
        if warn_msgs:
            print(f"  ⚠️ Corridor coverage gaps: {', '.join(warn_msgs)} "
                  f"— add clicks near segment edges for better coverage")

        # Show corridor bounds on spectrogram
        import numpy as _np2
        t_arr = _np2.array([c["t_utc_hours"] for c in corridor["clicks"]])
        d_arr = _np2.array([c["doppler_hz"]   for c in corridor["clicks"]])
        self._refresh_corridor(t_arr, d_arr, half_bw)

        self._set_status(
            f"Corridor written: {out.name}  "
            f"({len(self.clicks_t)} points, ±{half_bw} Hz)"
        )
        print(f"Corridor written: {out}")
        # Run sgolay-ridge preview if DRF dir provided
        self._run_sgolay_preview(out)



    def _run_prophet_preview(self):
        """Run cwt-prophet extraction using current clicks as anchors.
        Triggered automatically on open and after each user click.
        """
        if not self.drf_dir:
            return
        import subprocess as _sp, os as _os2, threading as _threading
        import json as _json2, re as _re2

        # Determine date string
        date_str = None
        _sidecar = str(self.img_path).replace(".png", "_axes.json")
        if _os2.path.exists(_sidecar):
            try:
                _sc = _json2.load(open(_sidecar))
                date_str = _sc.get("date_utc")
            except Exception:
                pass
        if not date_str:
            for _s in [str(self.img_path), str(self.drf_dir)]:
                _m = _re2.search(r"(\d{4}-\d{2}-\d{2})", _s)
                if _m:
                    date_str = _m.group(1)
                    break
        if not date_str:
            date_str = "2026-01-19"

        def _h_to_iso(h):
            hh = int(h); rem = (h-hh)*60; mm = int(rem); ss = int((rem-mm)*60)
            return f"{date_str}T{hh:02d}:{mm:02d}:{ss:02d}"

        t0_h = self.seg_t0
        t1_h = self.seg_t1
        out_csv = str(Path(self.img_path).parent /
                      (Path(self.img_path).stem + "_prophet_preview.csv"))
        self._prophet_csv = out_csv

        # Write anchors JSON if user has clicked points
        anchors_json = None
        if self.clicks_t:
            anchors = {
                "station": self.name,
                "corridor_width_hz": self.corridor_width,
                "anchors": [
                    {"t_utc_hours": t, "doppler_hz": d}
                    for t, d in zip(self.clicks_t, self.clicks_d)
                ]
            }
            anchors_path = str(Path(self.img_path).parent /
                               (Path(self.img_path).stem + "_anchors.json"))
            with open(anchors_path, "w") as _af:
                _json2.dump(anchors, _af, indent=2)
            anchors_json = anchors_path

        cmd = [
            "python3",
            _os2.path.join(_os2.path.dirname(_os2.path.abspath(__file__)),
                          "drf_to_doppler.py"),
            self.drf_dir,
            "--subchannel", str(self.subchannel),
            "--start", _h_to_iso(t0_h),
            "--end",   _h_to_iso(t1_h),
            "--decim-seconds", "60",
            "--method", "cwt-prophet",
            "--corridor-width", str(self.corridor_width),
            "--output", out_csv,
        ]
        if anchors_json:
            cmd += ["--anchors", anchors_json]

        self._prophet_pass += 1
        # Clear old trace while Prophet runs
        self.preview_curve.setData([], [])
        n_clicks = len(self.clicks_t)
        if n_clicks == 0:
            self._set_status(
                "Pass 0: running Prophet automatically... "
                "Click excursions to add anchors, P to re-run, X to export, R to reset, Q to quit")
        else:
            self._set_status(
                f"Re-running Prophet with {n_clicks} anchor(s)...")
        self._prophet_done = False

        def _run():
            try:
                _sp.run(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE, timeout=180)
            except Exception as _e:
                print(f"  Prophet preview exception: {_e}")
            finally:
                self._prophet_done = True

        _threading.Thread(target=_run, daemon=True).start()
        self._start_prophet_poll()

    def _start_prophet_poll(self):
        """Poll for prophet preview completion and update overlay."""
        import os as _os3
        if self._prophet_done:
            self._load_prophet_overlay()
            return
        QtCore.QTimer.singleShot(500, self._start_prophet_poll)

    def _load_prophet_overlay(self):
        """Load prophet CSV and draw overlay on spectrogram."""
        if not self._prophet_csv or not Path(self._prophet_csv).exists():
            self._set_status("Pass 0 complete — no output CSV found (check DRF path)")
            return
        try:
            import pandas as _pd3
            df = _pd3.read_csv(self._prophet_csv,
                               parse_dates=["timestamp_utc"])
            df["t_h"] = (df["timestamp_utc"].dt.hour +
                         df["timestamp_utc"].dt.minute / 60 +
                         df["timestamp_utc"].dt.second / 3600)
            t_arr = df["t_h"].values
            d_arr = df["doppler_hz"].values
            # Alternate color each pass so user can see the update
            import pyqtgraph as _pg2
            colors = ["#00ff88", "#00ccff", "#ffff00", "#ff88ff"]
            color = colors[self._prophet_pass % len(colors)]
            self.preview_curve.setPen(_pg2.mkPen(color=color, width=2))
            self.preview_curve.setData(t_arr, d_arr)
            n = len(self.clicks_t)
            import datetime as _dt
            ts = _dt.datetime.now().strftime("%H:%M:%S")
            self._set_status(
                f"[{ts}] Pass {self._prophet_pass} — {n} anchor(s).  "
                f"Click F-region carrier to add anchors  P=re-run Prophet  X=export  W=wave-fit  R=reset  Q=quit")
        except Exception as _e:
            self._set_status(f"Prophet overlay failed: {_e}")


    def _preview_spline(self):
        """Show live spline preview through current anchor clicks."""
        if len(self.clicks_t) < 2:
            return
        try:
            import numpy as _np_pv
            from scipy.interpolate import PchipInterpolator as _Pchip_pv
            pairs = sorted(zip(self.clicks_t, self.clicks_d))
            t_arr = _np_pv.array([p[0] for p in pairs])
            d_arr = _np_pv.array([p[1] for p in pairs])
            t_min_pv = t_arr[0]; t_max_pv = t_arr[-1]
            spline = _Pchip_pv(t_arr, d_arr)
            t_dense = _np_pv.linspace(self.seg_t0, self.seg_t1, 500)
            d_dense = []
            for _t in t_dense:
                if t_min_pv <= _t <= t_max_pv:
                    d_dense.append(float(spline(_t)))
                else:
                    d_dense.append(float(d_arr[0] if _t < t_min_pv else d_arr[-1]))
            self.preview_curve.setData(list(t_dense), d_dense)
        except Exception:
            pass

    def _accept_spline(self):
        """Accept current spline as new baseline. Clears clicks for next region."""
        if len(self.clicks_t) < 2:
            self._set_status("Need at least 2 clicks to accept — click on the F-region carrier first")
            return
        import tempfile as _tmp
        tmp = _tmp.NamedTemporaryFile(suffix="_accepted.csv", delete=False)
        tmp.close()
        self._export_spline_csv(_accept_path=tmp.name)
        self._accepted_csv = tmp.name
        self.clicks_t = []
        self.clicks_d = []
        # Force full scatter redraw by hiding then showing
        self.scatter.setData(x=[-999], y=[-999])
        self.scatter.setData(x=[], y=[])
        self.scatter.update()
        self.preview_curve.setData([], [])
        self._set_status(
            "Accepted ✓  Clicks cleared — click next problem region, X to export final")
        print(f"  Accepted spline as new baseline: {tmp.name}")

    def _export_spline_csv(self, _accept_path=None):
        """Export spline interpolated through anchor clicks as final CSV.
        Blocked during wave-fit mode to prevent accidental interruption.
        """
        if getattr(self, "_wave_mode", False):
            self._set_status(
                f"[{self.name}] WAVE-FIT in progress — "
                "press F to fit or W to cancel first")
            return
        """Export spline interpolated through anchor clicks as final CSV.
        No CWT or DRF processing — the spline IS the extracted Doppler.
        Requires at least 2 anchor clicks spanning the segment window.
        """
        if len(self.clicks_t) < 2:
            if _accept_path is None:
                self._set_status("Need at least 2 anchor clicks to export spline")
            return
        import numpy as _np_sp
        import pandas as _pd_sp
        from scipy.interpolate import PchipInterpolator as _Pchip_sp
        import json as _json_sp, re as _re_sp

        # Get date from sidecar
        import os as _os_sp
        date_str = None
        _sidecar = str(self.img_path).replace(".png", "_axes.json")
        if _os_sp.path.exists(_sidecar):
            try:
                _sc = _json_sp.load(open(_sidecar))
                date_str = _sc.get("date_utc")
            except Exception:
                pass
        if not date_str:
            for _s in [str(self.img_path), str(self.drf_dir or "")]:
                _m = _re_sp.search(r"(\d{4}-\d{2}-\d{2})", _s)
                if _m:
                    date_str = _m.group(1)
                    break
        if not date_str:
            date_str = "2026-01-19"

        # Sort anchors by time
        pairs = sorted(zip(self.clicks_t, self.clicks_d))
        t_arr = _np_sp.array([p[0] for p in pairs])
        d_arr = _np_sp.array([p[1] for p in pairs])

        # Outside anchor range: blend with prophet preview (Pass 0 result)
        # Use last accepted CSV as baseline, else prophet preview
        _auto_path = self._accepted_csv or str(
            Path(self.img_path).parent /
            (Path(self.img_path).stem + "_prophet_preview.csv"))
        auto_df = None
        if _auto_path and Path(_auto_path).exists():
            try:
                auto_df = _pd_sp.read_csv(_auto_path, parse_dates=["timestamp_utc"])
                auto_df["t_h"] = (auto_df["timestamp_utc"].dt.hour +
                                  auto_df["timestamp_utc"].dt.minute/60.0 +
                                  auto_df["timestamp_utc"].dt.second/3600.0)
            except Exception:
                auto_df = None

        # Build dense time grid at decim_seconds resolution
        decim = 60.0  # seconds
        t0_sec = self.seg_t0 * 3600
        t1_sec = self.seg_t1 * 3600
        t_seconds = _np_sp.arange(t0_sec, t1_sec + decim, decim)
        t_hours = t_seconds / 3600.0

        # Spline interpolation — only in anchor range
        # Sort anchor arrays (already sorted but safety check)
        sort_idx = _np_sp.argsort(t_arr)
        t_arr = t_arr[sort_idx]; d_arr = d_arr[sort_idx]
        spline = _Pchip_sp(t_arr, d_arr)
        t_min = t_arr[0]; t_max = t_arr[-1]

        # Build output: spline in anchor range, auto elsewhere
        doppler = _np_sp.zeros(len(t_hours))
        for i, th in enumerate(t_hours):
            if t_min <= th <= t_max:
                doppler[i] = float(spline(th))
            elif auto_df is not None:
                # Use nearest auto value outside anchor range
                idx = _np_sp.argmin(_np_sp.abs(auto_df["t_h"].values - th))
                doppler[i] = float(auto_df["doppler_hz"].iloc[idx])
            else:
                # No auto — clamp to nearest anchor
                doppler[i] = float(d_arr[0] if th < t_min else d_arr[-1])

        # Build timestamps
        base = _pd_sp.Timestamp(f"{date_str}T00:00:00+00:00")
        timestamps = [base + _pd_sp.Timedelta(seconds=float(s)) for s in t_seconds]

        df = _pd_sp.DataFrame({
            "timestamp_utc": timestamps,
            "doppler_hz": doppler,
            "snr_db": [50.0] * len(doppler)  # placeholder SNR
        })

        if _accept_path:
            df.to_csv(_accept_path, index=False)
        else:
            out = Path(self.img_path).parent / (
                Path(self.img_path).stem.replace("_tid_zoom_clean", "")
                + "_spline_tid.csv")
            df.to_csv(out, index=False)
            # Use exported file as new baseline for further editing
            self._accepted_csv = str(out)
            # Update preview curve with final trace
            self.preview_curve.setData(list(t_hours), list(doppler))
            # Clear all clicks
            self.clicks_t = []
            self.clicks_d = []
            self._refresh_scatter()
            n_anchors = len(pairs)
            self._set_status(
                f"Exported: {out.name}  ({n_anchors} anchors, {len(df)} rows) — W=wave-fit  Q to quit")
            print(f"Spline CSV exported: {out}")

    def _export_prophet_csv(self):
        """Export the current prophet CSV as the final output."""
        if not self._prophet_csv or not Path(self._prophet_csv).exists():
            self._set_status("No prophet trace yet — wait for Pass 0 to complete")
            return
        import shutil as _sh
        stem = Path(self.img_path).stem
        # Remove _prophet_preview suffix, replace with _prophet_tid
        out = Path(self.img_path).parent / (
            stem.replace("_tid_zoom_clean", "") + "_prophet_tid.csv")
        _sh.copy(self._prophet_csv, out)
        self._set_status(f"Exported: {out.name}  ({len(self.clicks_t)} anchors used)")
        print(f"Prophet CSV exported: {out}")

    def _reset_clicks(self):
        self.clicks_t = []
        self.clicks_d = []
        self._refresh_scatter()
        self._update_status()

    def _clear_all(self):
        self.clicks_t = []
        self.clicks_d = []
        self.transform = None
        self.cal_step = 0
        self.cal_scatter.setData([])
        self._refresh_scatter()
        self.corridor_hi_curve.setData([], [])
        self.corridor_lo_curve.setData([], [])
        self.preview_curve.setData([], [])
        self._update_status()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _set_status(self, msg):
        self.status_label.setText(msg)

    def _update_status(self):
        if self.cal_step < 4:
            msg = self.CAL_SEQUENCE[self.cal_step]
        else:
            n = len(self.clicks_t)
            seg = f"  seg: {self.seg_t0:.2f}–{self.seg_t1:.2f} h"
            msg = (
                f"[{self.name}] {n} click(s){seg}   "
                "[X] export  [W] wave-fit  "
                "[R] reset  [C] clear  [Q] quit"
            )
        self.status_label.setText(msg)


    # ------------------------------------------------------------------
    # Wave-fit reconstruction  (W key)
    # ------------------------------------------------------------------
    # User marks ≥ half a cycle on the spline by clicking two points.
    # The tool fits period T, amplitude A, phase φ from that segment,
    # then reconstructs the full window by mirroring/tiling the fitted
    # waveform. Each station uses its own T/A/φ — no shared period
    # assumption. Exports {stn}_wave_tid.csv alongside the spline CSV.
    # ------------------------------------------------------------------

    def _refresh_wave_scatter(self):
        """Update brown diamond markers for wave-fit click points."""
        try:
            if self._wave_clicks_t:
                pts = [{"pos": [t, d]}
                       for t, d in zip(self._wave_clicks_t, self._wave_clicks_d)]
                self.wave_scatter.setData(pts)
            else:
                self.wave_scatter.setData([])
        except Exception:
            pass

    def _wave_fit_start(self):
        """Enter wave-fit mode: next 2 clicks mark the half-cycle."""
        if self.cal_step < 4:
            self._set_status("Calibrate first before using wave-fit")
            return
        self._wave_clicks_t = []
        self._wave_clicks_d = []
        self._wave_mode = True
        self._wave_done = False
        self._refresh_wave_scatter()
        self._set_status(
            f"[{self.name}] WAVE-FIT: click points along the wave  "
            "[F]=fit  [W]=cancel")

    def _wave_fit_click(self, t_h, d_hz):
        """Accumulate wave-fit click points. F key triggers the fit."""
        self._wave_clicks_t.append(t_h)
        self._wave_clicks_d.append(d_hz)
        n = len(self._wave_clicks_t)
        self._refresh_wave_scatter()
        self._set_status(
            f"[{self.name}] WAVE-FIT: {n} point(s) — keep clicking or "
            "[F]=fit now  [W]=cancel")

    def _wave_fit_execute(self):
        """F key: trigger wave-fit from accumulated clicks."""
        if not getattr(self, "_wave_mode", False):
            return
        if len(self._wave_clicks_t) < 2:
            self._set_status(
                f"[{self.name}] WAVE-FIT: need at least 2 points — keep clicking")
            return
        self._wave_mode = False
        self._do_wave_fit()

    def _do_wave_fit(self):
        """Fit waveform to marked half-cycle and reconstruct full window."""
        import numpy as _npw
        import pandas as _pdw
        from scipy.interpolate import PchipInterpolator as _Pchipw
        from scipy.optimize import curve_fit as _curve_fit
        import json as _jsonw, re as _rew, os as _osw

        t0_mark = min(self._wave_clicks_t)
        t1_mark = max(self._wave_clicks_t)
        span_h  = t1_mark - t0_mark        # marked span in hours
        span_s  = span_h * 3600.0          # in seconds
        # Click points used to constrain phase
        click_t = _npw.array(self._wave_clicks_t)
        click_d = _npw.array(self._wave_clicks_d)

        # Load spline CSV as the signal source
        spline_csv = None
        import pathlib as _pl_wf
        stem = _pl_wf.Path(self.img_path).stem
        parent = _pl_wf.Path(self.img_path).parent
        for candidate in [
            parent / (stem.replace("_tid_zoom_clean", "") + "_spline_tid.csv"),
            parent / (stem + "_spline_tid.csv"),
        ]:
            if candidate.exists():
                spline_csv = candidate
                break

        if spline_csv is None:
            self._set_status("WAVE-FIT: no spline CSV found — export spline first (X)")
            return

        try:
            df = _pdw.read_csv(spline_csv, parse_dates=["timestamp_utc"])
            df["t_h"] = (df["timestamp_utc"].dt.hour +
                         df["timestamp_utc"].dt.minute / 60.0 +
                         df["timestamp_utc"].dt.second / 3600.0)
            df = df.sort_values("t_h")
        except Exception as _e:
            self._set_status(f"WAVE-FIT: could not load spline CSV: {_e}")
            return

        # Extract signal segment within marked window
        mask = (df["t_h"] >= t0_mark) & (df["t_h"] <= t1_mark)
        seg = df[mask].copy()
        if len(seg) < 4:
            self._set_status("WAVE-FIT: marked segment too short — mark more of the wave")
            return

        t_seg = seg["t_h"].values
        d_seg = seg["doppler_hz"].values
        d_seg -= d_seg.mean()

        # Ask user what fraction of the cycle they marked
        from PyQt5 import QtWidgets as _QtW
        dlg = _QtW.QInputDialog()
        dlg.setWindowTitle("Wave-fit: period")
        dlg.setLabelText(
            f"Marked span: {span_s/60:.1f} min\n\n"
            "What did you mark?\n"
            "  1 = half cycle  (trough→peak or peak→trough)  T = span × 2\n"
            "  2 = full cycle  (trough→trough or peak→peak)  T = span × 1\n"
            "  Or enter any multiplier (e.g. 1.5 = ⅔ cycle):\n")
        dlg.setTextValue("1")
        dlg.setOkButtonText("OK")
        dlg.setCancelButtonText("Cancel")
        if dlg.exec_() != _QtW.QDialog.Accepted:
            self._set_status("Wave-fit cancelled")
            return
        try:
            multiplier = float(dlg.textValue().strip())
            if multiplier <= 0:
                multiplier = 1.0
        except ValueError:
            multiplier = 1.0
        T_s = span_s * multiplier * 2 if multiplier == 1 else span_s / (1.0 / (multiplier * 2) if multiplier != 1 else 0.5)
        # Simplified: multiplier maps as follows:
        #   1 → half cycle → T = span * 2
        #   2 → full cycle → T = span * 1
        #   other → T = span * (2 / multiplier)
        T_s = span_s * 2.0 / multiplier
        T_h = T_s / 3600.0

        # Fit A*sin(2π/T * t + φ) to the marked segment
        # Centre time on segment midpoint to make phi well-conditioned
        t_centre = (t0_mark + t1_mark) / 2.0
        def _sine(t, A, phi, offset):
            return A * _npw.sin(2 * _npw.pi / T_h * (t - t_centre) + phi) + offset

        A_guess  = (d_seg.max() - d_seg.min()) / 2.0
        off_guess = float(_npw.mean(d_seg))
        # Fit using raw signal + click points (click points weighted heavily)
        n_repeats = max(1, len(t_seg) // max(1, len(click_t)))
        t_fit = _npw.concatenate([t_seg] + [click_t] * n_repeats)
        d_fit = _npw.concatenate([d_seg]  + [click_d] * n_repeats)
        try:
            popt, _ = _curve_fit(_sine, t_fit, d_fit,
                                  p0=[A_guess, 0.0, off_guess],
                                  maxfev=4000)
            A_fit, phi_fit, off_fit = popt
        except Exception:
            A_fit   = A_guess
            phi_fit = 0.0
            off_fit = off_guess

        # Reconstruct full window
        t_out = df["t_h"].values
        d_wave = A_fit * _npw.sin(2 * _npw.pi / T_h * (t_out - t_centre) + phi_fit) + off_fit

        # Get date string
        date_str = None
        sidecar = str(self.img_path).replace(".png", "_axes.json")
        if _osw.path.exists(sidecar):
            try:
                sc = _jsonw.load(open(sidecar))
                date_str = sc.get("date_utc")
            except Exception:
                pass
        if not date_str:
            for _s in [str(self.img_path), str(self.drf_dir or "")]:
                _m = _rew.search(r"(\d{4}-\d{2}-\d{2})", _s)
                if _m:
                    date_str = _m.group(1)
                    break
        if not date_str:
            date_str = "2026-01-01"

        # Build timestamps
        import datetime as _dt
        base = _dt.datetime.strptime(date_str, "%Y-%m-%d").replace(
            tzinfo=_dt.timezone.utc)
        timestamps = [base + _dt.timedelta(hours=float(h)) for h in t_out]

        out_df = _pdw.DataFrame({
            "timestamp_utc": timestamps,
            "doppler_hz":    d_wave,
            "snr_db":        50.0,
        })

        # Save
        out_stem = stem.replace("_tid_zoom_clean", "")
        out_path = parent / f"{out_stem}_wave_tid.csv"
        out_df.to_csv(out_path, index=False)

        self._wave_done = True
        self._set_status(
            f"[{self.name}] WAVE-FIT: T={T_s/60:.1f} min  A={abs(A_fit):.3f} Hz  "
            f"phi={phi_fit:.2f} rad  → {out_path.name}   "
            f"[W]=redo  [Q]=quit")
        print(f"  Wave-fit: T={T_s/60:.1f} min, A={abs(A_fit):.3f} Hz, "
              f"phi={phi_fit:.3f} rad")
        print(f"  Saved: {out_path}")
        # Draw wave-fit overlay on spectrogram
        try:
            self.preview_curve.setData(list(t_out), list(d_wave))
            self.preview_curve.setPen({"color": "#00BFFF", "width": 2})
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------
    def _install_shortcuts(self):
        for key, cb in [("X", self._export_spline_csv),
                        ("P", self._run_prophet_preview),
                        ("W", self._wave_fit_start),
                        ("F", self._wave_fit_execute),
                        ("R", self._reset_clicks), ("C", self._clear_all),
                        ("Q", self.close)]:
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(key), self, cb)
            sc.setContext(QtCore.Qt.ApplicationShortcut)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(
        description="Spectrogram-based guided Doppler phase extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--spectrogram", required=True, metavar="PNG",
                   help="Spectrogram image file")
    p.add_argument("--csv", default=None, metavar="FILE",
                   help="Automated Doppler CSV (optional, unused)")
    p.add_argument("--name", default="Station", metavar="NAME",
                   help="Station name label")
    p.add_argument("--tlim", metavar="T0,T1",
                   help="Known time axis limits in decimal UTC hours (e.g. 16,22)")
    p.add_argument("--ylim", metavar="LO,HI",
                   help="Known Doppler axis limits in Hz (e.g. -5,5)")
    p.add_argument("--sidecar", metavar="JSON",
                   help="Axis metadata JSON written by drf_spectrogram.py "
                        "(auto-detected as <png_stem>_axes.json if present)")
    p.add_argument("--plot-fraction", metavar="L,R,B,T",
                   help="Plot area fractions (left,right,bottom,top) "
                        "default: 0.0582,0.8421,0.3712,0.9570 "
                        "(measured from drf_spectrogram.py 600dpi output)")
    p.add_argument("--seg-start", type=float, metavar="HOURS",
                   help="Pre-set segment start (decimal UTC hours)")
    p.add_argument("--seg-end", type=float, metavar="HOURS",
                   help="Pre-set segment end (decimal UTC hours)")
    p.add_argument("--period-hint", type=float, metavar="SECONDS",
                   help="TID period hint in seconds")
    p.add_argument("--drf-dir", default=None, metavar="DIR",
                   help="DRF data directory for sgolay-ridge preview after X. "
                        "If provided, runs sgolay-ridge extraction after corridor "
                        "export and overlays result on spectrogram.")
    p.add_argument("--subchannel", type=int, default=0, metavar="N",
                   help="DRF subchannel index for sgolay-ridge preview (default 0)")
    p.add_argument("--corridor-width", type=float, default=0.4, metavar="HZ",
                   help="Half-width in Hz of the adaptive corridor centred on "
                        "the Prophet prediction at each time step. CWT peaks "
                        "outside this band are rejected. Default: 0.4 Hz.")
    p.add_argument("--sgolay-window", type=float, default=21.0, metavar="MINUTES",
                   help="SGOLAY smoothing window in minutes for preview (default 21)")
    return p.parse_args()


def main():
    args = _parse_args()
    print("tid_spect_click.py  v0.1.0")


    import os as _os, json as _json
    transform = None
    sidecar_path = args.sidecar
    if sidecar_path is None:
        auto = _os.path.splitext(args.spectrogram)[0] + "_axes.json"
        if _os.path.exists(auto):
            sidecar_path = auto
            print(f"  Auto-detected sidecar: {auto}")

    pil = Image.open(args.spectrogram)
    w, h = pil.size
    pf = tuple(float(x) for x in args.plot_fraction.split(",")) if args.plot_fraction else None

    if sidecar_path:
        with open(sidecar_path) as _f:
            sc = _json.load(_f)
        t0, t1 = sc["t_start_utc_hours"], sc["t_end_utc_hours"]
        d0, d1 = sc["doppler_lo_hz"], sc["doppler_hi_hz"]
        print(f"  Sidecar axes: t={t0}-{t1} h, doppler={d0}-{d1} Hz")
        pf = pf or (tuple(sc["plot_fraction"]) if "plot_fraction" in sc else None)
        transform = AxisTransform.from_limits(w, h, (t0, t1), (d0, d1), plot_fraction=pf)
    elif args.tlim and args.ylim:
        t0, t1 = (float(x) for x in args.tlim.split(","))
        d0, d1 = (float(x) for x in args.ylim.split(","))
        print(f"  Using known axes: t={t0}-{t1} h, doppler={d0}-{d1} Hz")
        transform = AxisTransform.from_limits(w, h, (t0, t1), (d0, d1), plot_fraction=pf)

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("TID Spectrogram Click")

    # Auto-detect window JSON from tid_quicklook.py
    seg_start = args.seg_start
    seg_end   = args.seg_end
    window_f  = _os.path.splitext(args.spectrogram)[0] + "_window.json"
    if seg_start is None and seg_end is None and _os.path.exists(window_f):
        with open(window_f) as _f:
            wj = _json.load(_f)
        seg_start = wj["t_start_utc_hours"]
        seg_end   = wj["t_end_utc_hours"]
        print(f"  Auto-detected window: {seg_start:.2f}-{seg_end:.2f} h "
              f"(from {_os.path.basename(window_f)})")

    win = SpectClickApp(
        img_path     = args.spectrogram,
        csv_path     = args.csv,
        name         = args.name,
        transform    = transform,
        period_hint  = args.period_hint,
        seg_start    = seg_start,
        seg_end      = seg_end,
        drf_dir      = args.drf_dir,
        subchannel   = args.subchannel,
        sgolay_window = args.sgolay_window,
        corridor_width = args.corridor_width,
    )
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
