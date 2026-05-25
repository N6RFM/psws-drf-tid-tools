r"""
tid_spect_click.py — spectrogram-based guided Doppler phase extraction

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 0.1.0
License: MIT (do whatever you want, no warranty).

OVERVIEW
========
Displays a Doppler spectrogram PNG and lets the user click directly on
the carrier track to mark phase samples for the TID of interest.
A sinusoid is fitted to the clicks and the result is used to produce a
corrected "guided" Doppler CSV, replacing the automated extraction in
the selected time window.

This is complementary to tid_guided_extract.py (which works on the
extracted Doppler trace). Clicking on the spectrogram is more intuitive
because the TID wave is directly visible as the carrier track.

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
4. Click 4-7 points along the carrier track (TID wave) in the segment.
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
    F     Fit sinusoid from clicks
    W     Write guided CSV
    R     Reset phase clicks (keeps calibration)
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
# Sinusoid fitting
# ---------------------------------------------------------------------------

def fit_sinusoid(clicks_hours, doppler_vals, omega=None, period_hint_s=None):
    """
    Fit y(t) = A sin(ωt + φ) from sparse (t_hours, dop_hz) samples.
    Returns (amplitude, omega_rad_per_s, phase_rad) or None.
    """
    if len(clicks_hours) < 3:
        return None
    t_s = np.array(clicks_hours) * 3600.0   # convert hours → seconds
    y   = np.array(doppler_vals)

    if omega is None:
        if period_hint_s is not None:
            omega = 2 * np.pi / period_hint_s
        else:
            span = t_s[-1] - t_s[0]
            if span < 1:
                return None
            omega = 2 * np.pi / span

    A_mat = np.column_stack([np.sin(omega * t_s), np.cos(omega * t_s)])
    coeff, *_ = np.linalg.lstsq(A_mat, y, rcond=None)
    a, b = coeff
    amplitude = np.sqrt(a**2 + b**2)
    phase = np.arctan2(b, a)
    return amplitude, omega, phase


def evaluate_sinusoid_hours(t_hours_arr, amplitude, omega, phase):
    """Evaluate sinusoid on array of times in decimal hours."""
    t_s = np.array(t_hours_arr) * 3600.0
    return amplitude * np.sin(omega * t_s + phase)


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
                 drf_dir=None, subchannel=0, sgolay_window=21.0):
        super().__init__()
        self.name        = name
        self.csv_path    = Path(csv_path)
        self.drf_dir     = drf_dir
        self.subchannel  = subchannel
        self.sgolay_window = sgolay_window
        self.period_hint = period_hint   # seconds
        self.transform   = transform     # AxisTransform or None
        self.cal_step    = 0 if transform is None else 4
        self.cal_pending = None          # pixel coords waiting for value input
        self.clicks_t    = []            # decimal hours
        self.clicks_d    = []            # doppler Hz
        self.fit         = None          # (amp, omega, phase)

        self._load_csv()
        self._load_image(img_path)
        self._build_ui(seg_start, seg_end)
        self._install_shortcuts()
        self._update_status()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_csv(self):
        df = pd.read_csv(self.csv_path, parse_dates=["timestamp_utc"])
        df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
        df = df.sort_values("timestamp_utc").reset_index(drop=True)
        self.df = df
        # Convert timestamps to decimal UTC hours for plotting
        self.csv_t_hours = (
            df["timestamp_utc"].dt.hour +
            df["timestamp_utc"].dt.minute / 60 +
            df["timestamp_utc"].dt.second / 3600
        ).values
        self.csv_doppler = df["doppler_hz"].values.astype(float)

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
        self.plot.setLabel("bottom", "Time (UTC hours)")
        self.plot.setLabel("left", "Doppler shift", units="Hz")

        # Spectrogram image
        self.img_item = pg.ImageItem()
        self.plot.addItem(self.img_item)
        self.img_item.setImage(self.img_arr)

        # Set image scale/position based on transform if available
        self._update_image_transform()

        # Automated Doppler CSV overlay (grey)
        self.csv_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#888888", width=1),
            name="auto",
        )
        self._csv_visible = False  # hidden by default — press V to toggle

        # Fitted sinusoid (inside segment — bright)
        self.fit_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#4e9af1", width=2),
            name="fit",
        )
        # Fitted sinusoid (outside segment — dim dotted)
        self.fit_dim_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#4e9af1", width=1,
                         style=QtCore.Qt.DotLine),
            name="fit_dim",
        )

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
        self.corridor_hi_curve.setData([], [])
        self.corridor_lo_curve.setData([], [])
        self.fit_curve.setData([], [])
        self.fit_dim_curve.setData([], [])
        self.preview_curve.setData([], [])
        # Delete stale output files from previous sessions
        import os as _os_clean
        for _suffix in ["_corridor.json", "_corridor_preview.csv"]:
            _stale = str(self.csv_path).replace(".csv", _suffix)
            if _os_clean.path.exists(_stale):
                _os_clean.remove(_stale)
                print(f"  Removed stale file: {_os_clean.path.basename(_stale)}")

        # SGOLAY-ridge preview curve (shown after X if --drf-dir provided)
        self.preview_curve = self.plot.plot(
            [], [],
            pen=pg.mkPen(color="#00ff88", width=2),
            name="sgolay_preview",
        )

        # Phase click scatter
        self.scatter = pg.ScatterPlotItem(
            size=9,
            brush=pg.mkBrush("#ff4444"),
            pen=pg.mkPen(None),
        )
        self.plot.addItem(self.scatter)

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
            t0 = self.csv_t_hours[len(self.csv_t_hours)//4]
            t1 = self.csv_t_hours[3*len(self.csv_t_hours)//4]
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
        self._refresh_fit()
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

        # Get date from CSV
        try:
            df_tmp = _pd2.read_csv(self.csv_path, parse_dates=["timestamp_utc"], nrows=1)
            date_str = str(df_tmp["timestamp_utc"].iloc[0])[:10]
        except Exception:
            date_str = "2024-05-17"

        def _h_to_iso(h):
            hh = int(h); rem = (h-hh)*60; mm = int(rem); ss = int((rem-mm)*60)
            return f"{date_str}T{hh:02d}:{mm:02d}:{ss:02d}"

        t0_h, t1_h = self.seg_t0, self.seg_t1
        out_csv = _os2.path.splitext(str(corridor_json_path))[0] + "_preview.csv"

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
                self._replot_csv()
                self._set_status(
                    "Calibration complete! Now click phase samples on the carrier track."
                )

        self.cal_step += 1
        self._update_status()

    def _replot_csv(self):
        """Replot CSV overlay in calibrated coordinates (already in hours)."""
        self.csv_curve.setData(self.csv_t_hours, self.csv_doppler)

    def _add_cal_marker(self, vx, vy):
        pts = [{"pos": [p["pos"][0], p["pos"][1]]}
               for p in (self.cal_scatter.data or [])]
        pts.append({"pos": [vx, vy]})
        self.cal_scatter.setData(pts)

    def _handle_phase_click(self, vx, vy):
        """Store a phase sample click in physical coordinates."""
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

    def _refresh_scatter(self):
        if self.clicks_t:
            pts = [{"pos": [t, d]}
                   for t, d in zip(self.clicks_t, self.clicks_d)]
            self.scatter.setData(pts)
        else:
            self.scatter.setData([])

    # ------------------------------------------------------------------
    # Fit
    # ------------------------------------------------------------------

    def _fit(self):
        if len(self.clicks_t) < 3:
            self._set_status(f"Need ≥3 clicks (have {len(self.clicks_t)})")
            return
        result = fit_sinusoid(
            self.clicks_t, self.clicks_d,
            period_hint_s=self.period_hint
        )
        if result is None:
            self._set_status("Fit failed")
            return
        self.fit = result
        amp, omega, phase = result
        period_s = 2 * np.pi / omega
        self._set_status(
            f"Fit: A={amp:.4f} Hz  T={period_s:.0f} s  "
            f"φ={np.degrees(phase):.1f}°  — press W to write CSV"
        )
        self._refresh_fit()

    def _refresh_fit(self):
        if self.fit is None:
            self.fit_curve.setData([], [])
            self.fit_dim_curve.setData([], [])
            return
        amp, omega, phase = self.fit
        t_arr = self.csv_t_hours
        y_fit = evaluate_sinusoid_hours(t_arr, amp, omega, phase)
        t0, t1 = self.seg_t0, self.seg_t1
        seg_mask = (t_arr >= t0) & (t_arr <= t1)
        self.fit_curve.setData(t_arr[seg_mask], y_fit[seg_mask])
        self.fit_dim_curve.setData(t_arr[~seg_mask], y_fit[~seg_mask])

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def _write(self):
        if not self.clicks_t:
            # Guard against spurious W keypress on launch before any interaction
            return
        if self.fit is None:
            self._set_status("No fit yet — press F first")
            return
        amp, omega, phase = self.fit
        df = self.df.copy()
        t_arr = self.csv_t_hours
        t0, t1 = self.seg_t0, self.seg_t1
        mask = (t_arr >= t0) & (t_arr <= t1)
        df.loc[mask, "doppler_hz"] = evaluate_sinusoid_hours(
            t_arr[mask], amp, omega, phase
        )
        out = self.csv_path.parent / (self.csv_path.stem + "_guided" + self.csv_path.suffix)
        df.to_csv(out, index=False)
        self._set_status(f"Written: {out}")
        print(f"Written: {out}")

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
        out = self.csv_path.parent / (self.csv_path.stem + "_corridor.json")
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
        # Consistency check: xcorr corridor centres vs automated CSV
        # to detect phase offset (>60s = likely tracking different feature)
        try:
            import numpy as _np
            from scipy.signal import correlate as _corr, correlation_lags as _lags
            t_arr = _np.array([c["t_utc_hours"] for c in corridor["clicks"]])
            d_arr = _np.array([c["doppler_hz"]   for c in corridor["clicks"]])
            csv_t = self.csv_t_hours
            csv_d = self.csv_doppler.copy()
            # Interpolate corridor centres onto CSV time grid
            corr_centres = _np.interp(csv_t, t_arr, d_arr)
            # Only compare within clicked time range
            in_range = (csv_t >= t_arr[0]) & (csv_t <= t_arr[-1])
            if in_range.sum() > 10:
                x = corr_centres[in_range] - corr_centres[in_range].mean()
                y = csv_d[in_range] - csv_d[in_range].mean()
                cc = _corr(y, x, mode="full") / (
                    (_np.std(x) * _np.std(y) * in_range.sum()) + 1e-12)
                lag_steps = _lags(in_range.sum(), in_range.sum(), mode="full")
                dt_h = (csv_t[1] - csv_t[0]) if len(csv_t) > 1 else (1/60)
                lag_s = lag_steps * dt_h * 3600
                peak_idx = int(_np.argmax(cc))
                offset_s = float(lag_s[peak_idx])
                peak_r   = float(cc[peak_idx])
                if abs(offset_s) > 60:
                    warn = (f"⚠️ WARNING: corridor offset {offset_s:+.0f}s vs "
                            f"automated CSV (r={peak_r:.2f}) — "
                            f"may be tracking different carrier feature")
                    self._set_status(warn)
                    print(warn)
                else:
                    ok = (f"✓ Consistency OK: offset {offset_s:+.0f}s "
                          f"(r={peak_r:.2f}) — corridor tracks same carrier")
                    self._set_status(
                        f"Corridor written: {out.name}  "
                        f"({len(self.clicks_t)} points, ±{half_bw} Hz)  {ok}"
                    )
                    print(ok)
                    self._run_sgolay_preview(out)
                    return
        except Exception as _e:
            print(f"  Consistency check failed: {_e}")

        self._set_status(
            f"Corridor written: {out.name}  "
            f"({len(self.clicks_t)} points, ±{half_bw} Hz)"
        )
        print(f"Corridor written: {out}")
        # Run sgolay-ridge preview if DRF dir provided
        self._run_sgolay_preview(out)

    def _toggle_csv_overlay(self):
        """Toggle automated CSV overlay on/off (V key)."""
        self._csv_visible = not self._csv_visible
        if self._csv_visible:
            self.csv_curve.setData(self.csv_t_hours, self.csv_doppler)
            self._set_status("CSV overlay ON (grey) — press V to hide")
        else:
            self.csv_curve.setData([], [])
            self._set_status("CSV overlay OFF — press V to show")

    def _reset_clicks(self):
        self.clicks_t = []
        self.clicks_d = []
        self.fit = None
        self._refresh_scatter()
        self._refresh_fit()
        self._update_status()

    def _clear_all(self):
        self.clicks_t = []
        self.clicks_d = []
        self.fit = None
        self.transform = None
        self.cal_step = 0
        self.cal_scatter.setData([])
        self._refresh_scatter()
        self._refresh_fit()
        self.corridor_hi_curve.setData([], [])
        self.corridor_lo_curve.setData([], [])
        self.preview_curve.setData([], [])
        self.csv_curve.setData([], [])
        self._csv_visible = False
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
            fit_str = "✓fit" if self.fit else f"{n} click(s)"
            seg = f"  seg: {self.seg_t0:.2f}–{self.seg_t1:.2f} h"
            msg = (
                f"[{self.name}] {fit_str}{seg}   "
                "[F] fit  [W] write  [X] export corridor  "
                "[R] reset  [C] clear  [Q] quit"
            )
        self.status_label.setText(msg)

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _install_shortcuts(self):
        for key, cb in [("F", self._fit), ("W", self._write),
                        ("X", self._write_corridor),
                ("V", self._toggle_csv_overlay),
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
    p.add_argument("--csv", required=True, metavar="FILE",
                   help="Automated Doppler CSV")
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
    )
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
