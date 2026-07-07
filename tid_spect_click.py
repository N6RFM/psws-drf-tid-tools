r"""
tid_spect_click.py — spectrogram-based guided Doppler phase extraction

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 0.9.0
License: MIT (do whatever you want, no warranty).

Change log:
  v0.9.0  Fixed a real terminology bug found during a documentation
          review, not live testing this time: wave-fit's own accepted
          CSVs were being recorded in the config with "method":
          "spline" -- but spline is a genuinely separate, real
          extraction method (_export_spline_csv, anchor-click + PCHIP
          interpolation directly through the clicks, no sinusoid
          model at all), completely different from wave-fit (fits a
          single sinusoid). Reusing that name caused every wave-fit
          CSV extracted this entire session to be mislabeled in the
          saved config, including tid_doa.py's own "methods_used"
          reporting. Corrected _wave_fit_finalize() to record
          "wave-fit" instead. Verified: confirmed no other code
          anywhere branches on method=="spline" in a way that would
          need updating for this (checked explicitly), and confirmed
          via a real _wave_fit_finalize() run that the saved config
          now correctly shows "method": "wave-fit".
  v0.8.0  Fixed a third real bug in the auto-cycle-estimate, found
          during live testing with 9 real, well-placed clicks (well
          above the 6-point minimum from v0.7.0): the tolerance used
          to decide "is this candidate close enough to the best fit
          to be worth preferring for its simplicity" was 1.5x the
          best residual -- far too loose. For real click data, this
          accepted candidates from 0.2 all the way to 1.1 cycles as
          "good enough" when the true best fit was 0.8, then
          confidently returned 0.2 (the search floor) as if it were a
          precise answer. Tightened to 1.05x. Verified with the exact
          real click coordinates that exposed this (captured via
          temporary debug instrumentation, then removed): the dialog
          now correctly seeds at 0.83, not the old 0.30. Also
          re-verified this doesn't regress the original aliasing test
          the tolerance was built for (still 5/5) and re-ran the
          broader 200-trial synthetic sweep, which improved slightly
          overall (down to 4% failures, most no longer the
          confidently-wrong low-n type this fix specifically targets).
  v0.7.0  Fixed a serious regression in v0.6.0's auto-cycle-estimate,
          found during live testing of a real 4-station event (Jan
          19 2026): with only 3-4 clicked points, the estimator would
          confidently converge to 0.20 (the search grid's own lower
          bound) regardless of the true cycle count, and present it
          with false precision (e.g. "0.20 cycles"). A 3-parameter
          sine fit against only 3-4 points is fundamentally
          underdetermined -- a very long, slowly-varying candidate
          period can always curve through a handful of sparse points
          by coincidence. Measured empirically across 400 synthetic
          trials: 3 clicks failed 100% of the time, 4 clicks 61%, 5
          clicks still 32% (too unreliable), 6+ clicks dropped to
          single digits. Below 6 points, the auto-estimate is no
          longer attempted at all -- falls back honestly to the same
          "1.0" default this feature was built to replace, with a
          clear message explaining why, rather than silently
          presenting an unreliable number with false precision.
          Verified: the exact 0.20 false-positive is gone for 3-5
          clicked points (confirmed via the real _do_wave_fit(),
          not just the estimation logic in isolation), and the
          auto-estimate still works correctly at 6+ points -- though,
          being an inherently hard estimation problem from sparse
          data, it is not and cannot be made 100% reliable even at
          6+ points (measured ~3% residual failure rate there); the
          dialog still shows the number before it's accepted, so a
          human check remains the final safeguard.
  v0.6.0  The wave-fit cycle-count dialog now seeds itself with a
          real, data-driven estimate instead of a blind guess of
          "1.0". Found during live testing of a real event (N6RFM_5,
          June 6 2026): a manually-entered "1.0" cycles answer was
          actually wrong (the true count was 2.0), producing a fitted
          period exactly double what the other two stations in the
          same event independently measured -- which materially
          distorted the resulting TID direction-of-arrival result
          (speed came out non-physical; fixed once the correct cycle
          count was used). The dialog's only prior fallback for a
          data-driven estimate required manually supplying an
          external --period-hint, which virtually nobody does.
          Now fits the sine model at a range of candidate cycle
          counts directly against the user's own clicked points
          (coarse grid search 0.2-6.0, then a finer local refinement)
          and seeds the dialog with whichever fits best -- eliminating
          most of the guessing this dialog previously required, while
          still letting the user override for genuinely ambiguous
          cases. Also fixed a real aliasing vulnerability found while
          testing this: picking the pure global-minimum-residual
          candidate can lock onto a spurious higher-frequency alias
          that fits the same sparse click points just as well by
          coincidence (confirmed: 2 of 5 synthetic test cases failed
          this way before the fix). Fixed by preferring the simplest
          (fewest-cycles) explanation among all candidates whose
          residual is close to the best, the same principle behind
          preferring a fundamental frequency over its harmonic when
          both explain sparse data similarly well. Verified: 5/5
          synthetic cases (0.5, 1.0, 1.5, 2.0, 3.0 true cycles) now
          correctly recovered, and a full end-to-end run through the
          real _do_wave_fit() correctly seeded the dialog at 1.99 for
          a synthetic scenario reproducing the exact real N6RFM_5
          error (clicks spanning 2 true cycles), where the seed used
          to be a blind "1.0".
  v0.5.0  Fixed a real bug found testing v0.4.0 live (N6RFM_5, June 6
          2026): after clicking points and pressing F, the plot
          visibly compressed to a fraction of the window's width.
          Root cause: t_out (used for both the drawn preview curve
          and the exported CSV) was unconditionally overridden with
          the DRF reader's own FULL RECORDING bounds (e.g. the entire
          24-hour day) whenever --drf-dir was provided -- which is
          every real invocation, since that flag is always passed.
          This stretched the preview curve far beyond the zoomed
          segment actually shown on screen; adding that much-wider
          curve to the same plot forced the view to widen dramatically
          to fit it, squeezing the real spectrogram down to a small
          fraction of the window. The comment describing this code
          ("extrapolate beyond clicked region") already correctly
          described the real intent -- extrapolate to the segment,
          not the whole recording -- so the fix simply removes the
          erroneous full-bounds override and keeps the already-correct
          sidecar-derived segment bounds established earlier in the
          same function. Verified end to end: ran the real
          _do_wave_fit() against a synthetic 24-hour recording with a
          ~2.87-hour segment, confirmed both the exported CSV
          (173 rows, 06:04-08:56) and the actual data passed to the
          preview curve widget are correctly bounded to the segment,
          not the full day.
  v0.4.0  Fixed the actual root cause behind a serious bug found
          testing v0.3.0 live (N6RFM_5, June 6 2026): after clicking
          points and pressing F, the window visibly shrank, a stray
          blue cwt-prophet auto-trace appeared, and the app became
          unresponsive -- despite --wave-only being passed. Root
          cause: _wave_only and _no_prophet were hardcoded False in
          __init__, with main() only setting the real values as
          post-construction attributes (win._wave_only = True) AFTER
          the constructor had already finished. Every check inside
          __init__ that read these -- including the auto-run-Prophet-
          on-open guard -- always saw False, so the cwt-prophet pass
          fired unconditionally 500ms after every window opened, even
          in wave-fit mode. Now accepted as real constructor
          parameters (wave_only=, no_prophet=), set correctly before
          anything that depends on them runs. This also let
          _install_shortcuts() branch correctly from the very first
          shortcut installed -- P and E (cwt-prophet-specific keys)
          are no longer bound at all in wave-only mode, and X is bound
          directly to the correct wave-fit accept instead of needing
          the v0.3.0 workaround of binding it wrong first and
          disabling/rebinding it after the fact. Verified: instantiated
          the real class with wave_only=True and wave_only=False,
          confirmed each gets exactly the right key set (no P/E leaking
          into wave-only mode, no W/F/A leaking into normal mode), and
          confirmed X has a single, clean, enabled binding with no
          leftover disabled duplicate from the old approach.
  v0.3.0  Fixed 3 real bugs found during live testing against a real
          event (KV0S_MO, June 6 2026):
          (1) _wave_fit_finalize() never called _save_event_json() --
              unlike the cwt-prophet and plain-spline export paths,
              wave-fit mode's --event-json auto-update silently never
              worked, regardless of which key was used to export.
              Config now correctly gets "file"/"method" (method:
              "spline", the existing documented convention for
              wave-fit-originated CSVs) after accept.
          (2) X was unconditionally bound to _export_spline_csv, the
              wrong export function for wave-fit mode -- pressing X
              while wave-fit clicking silently exported the wrong
              thing rather than the wave-fit result. Properly disabled
              (two QShortcuts on the same key are "ambiguous" to Qt
              and neither fires, so simply adding a second binding
              without disabling the first would have made X do
              nothing) and rebound to the correct wave-fit accept,
              aliasing it to A -- "X = export" is the natural
              expectation in every other mode, no reason for wave-fit
              to be the exception.
          (3) The click-count status bar showed cwt-prophet-mode text
              ("E=accept auto-trace... export spline") while actually
              clicking wave-fit points, because the inline status
              update only checked _no_prophet, never _wave_only --
              overwriting the correct text _update_status() had just
              set moments earlier, on every single click.
          All three verified directly: unit-tested the fixed
          _wave_fit_finalize against a real config file (confirms
          file/method now written correctly), and instantiated the
          real SpectClickApp class to confirm the old X shortcut is
          properly disabled (not left ambiguously bound) and the new
          one correctly targets wave-fit accept.
  v0.2.0  Renamed --subchannel to --channel-num throughout (flag,
          constructor parameter, internal drf_to_doppler.py subprocess
          calls). "Subchannel" incorrectly implied a single combined
          signal demultiplexed into related sub-streams (like ATSC TV
          subchannels); what's actually happening is several
          independent, unrelated frequencies packed into one DRF
          directory's data columns purely for storage convenience.
          No functional change; --subchannel itself no longer exists,
          callers must update.
  v0.1.1  Wave-fit save confirmation now also explains that
          run_tests.py auto-detects and copies the file from here into
          its expected event-directory location -- previously only
          announced where the file was saved, not that a downstream
          tool would relocate it, which caused real confusion in
          practice (the file's --show-commands-described final path
          differs from where it's actually written first). No change
          to the fitting/extraction logic itself.
  v0.1.0  Initial release.

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
                 drf_dir=None, channel_num=0, sgolay_window=21.0,
                 corridor_width=0.4, wave_only=False, no_prophet=False):
        super().__init__()
        self.name        = name
        self.img_path    = img_path
        self.csv_path    = Path(csv_path) if csv_path else None
        self.drf_dir     = drf_dir
        self.channel_num  = channel_num
        self.sgolay_window = sgolay_window
        self.corridor_width = corridor_width
        self._wave_mode = False
        self._wave_done = False
        # REAL BUG FOUND during live testing, root cause of a serious
        # issue: these used to be hardcoded False here, with main()
        # only setting the real values (win._wave_only = True etc.)
        # AFTER the constructor had already finished running. Every
        # check inside __init__ that read self._wave_only -- including
        # the auto-run-Prophet-on-open guard a few lines below --
        # always saw False, regardless of what --wave-only actually
        # requested. This meant the cwt-prophet auto-trace pass fired
        # unconditionally 500ms after every window opened, even in
        # wave-fit mode, producing exactly the symptoms reported live:
        # the window visibly shrinking, a stray blue auto-trace
        # appearing, and the app becoming unresponsive. Now accepted
        # as real constructor parameters, set correctly before
        # anything that depends on them runs.
        self._wave_only = wave_only
        self._no_prophet = no_prophet
        self._wave_candidate = None
        self._wave_final_path = None
        self._wave_clicks_t = []
        self._wave_clicks_d = []
        self._prophet_csv   = None
        self._prophet_done  = False
        self._prophet_curve = None
        self._prophet_pass  = 0     # increments each re-run for color cycling
        self._accepted_csv  = None  # path to last accepted baseline CSV
        self._event_json    = None  # path to event JSON for reproducibility save
        self.period_hint = period_hint   # seconds
        self._period_hint_s = period_hint   # for wave-fit dialog
        self.transform   = transform     # AxisTransform or None
        self.cal_step    = 0 if transform is None else 4
        self.cal_pending = None          # pixel coords waiting for value input
        self.clicks_t    = []            # decimal hours
        self.clicks_d    = []            # doppler Hz
        self._load_image(img_path)
        self._build_ui(seg_start, seg_end)
        self._install_shortcuts()
        self._update_status()
        # Auto-run Prophet on open (Pass 0 — no clicks needed) --
        # this guard now works correctly, since self._wave_only is
        # already the real, caller-provided value by this point.
        if self.drf_dir:
            if not self._wave_only and not self._no_prophet:
                QtCore.QTimer.singleShot(500, self._run_prophet_preview)
        if self._wave_only:
            QtCore.QTimer.singleShot(600, self._wave_fit_start)

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
            # Inset yellow bars 15% from each edge so they're visible
            # and easy to grab -- but t_out still uses full DRF bounds
            t0 = t_start + t_span * 0.15
            t1 = t_start + t_span * 0.85
        else:
            t0, t1 = 0.0, 2.0   # fractions until calibrated

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
        # Store full spectrogram extent for wave-fit extrapolation
        # Add small margin to ensure full right-edge coverage
        self._full_t0 = self.transform.bx
        self._full_t1 = self.transform.bx + self.transform.ax * self.img_w + 1/60
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
            "--channel-num", str(self.channel_num),
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
        if self._no_prophet:
            self._preview_spline()
        self._update_status()
        n = len(self.clicks_t)
        # Real bug, found during live testing: this only checked
        # _no_prophet, never _wave_only, so wave-fit mode showed
        # cwt-prophet-mode status text ("E=accept auto-trace... export
        # spline") while actually clicking wave-fit points -- confusing,
        # and specifically flagged during a real event test.
        if getattr(self, "_wave_only", False):
            self._set_status(
                f"{n} click(s).  F=fit  A=accept  Z=undo  R=reset  Q=quit")
        elif self._no_prophet:
            self._set_status(
                f"{n} anchor(s).  X=export  Z=undo  R=reset  Q=quit")
        else:
            self._set_status(
                f"{n} anchor(s).  E=accept auto-trace  "
                f"X=export spline  Z=undo  R=reset  Q=quit")

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
            "--channel-num", str(self.channel_num),
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
                "Pass 0: running auto-trace... "
                "E=accept auto-trace  X=export clicked trace  Z=undo  R=reset  Q=quit")
        else:
            self._set_status(
                f"Re-running with {n_clicks} anchor(s)...")
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
                f"E=accept auto-trace  X=export clicked trace  Z=undo  R=reset  Q=quit")
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
            # Preview spans FULL spectrogram, not just segment --
            # the fitted sinusoid is extrapolated across all data
            _pv_t0 = getattr(self, '_full_t0', self.seg_t0)
            _pv_t1 = getattr(self, '_full_t1', self.seg_t1)
            t_dense = _np_pv.linspace(_pv_t0, _pv_t1, 500)
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
                f"Exported: {out.name}  ({n_anchors} anchors, {len(df)} rows)  Q to quit")
            print(f"Spline CSV exported: {out}")
            self._save_event_json(str(out), "spline")

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
        self._save_event_json(str(out), "cwt-prophet")

    def _undo_last_click(self):
        """Remove the last clicked anchor point (Z key)."""
        if not self.clicks_t:
            self._set_status("No clicks to undo")
            return
        self.clicks_t.pop()
        self.clicks_d.pop()
        self._refresh_scatter()
        if self._no_prophet:
            if len(self.clicks_t) >= 2:
                self._preview_spline()
            else:
                self.preview_curve.setData([], [])
        n = len(self.clicks_t)
        self._set_status(
            f"Undo — {n} anchor(s) remaining.  "
            f"Z=undo  R=reset")

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
            if getattr(self, "_wave_only", False):
                keys = "[F] fit  [A] accept  [W] redo  [R] reset  [Q] done (close window)"
            elif self._no_prophet:
                keys = "[X] export  [Z] undo  [R] reset  [Q] done (close window)"
            else:
                keys = ("[E] accept auto-trace  "
                        "[X] export clicked trace  "
                        "[Z] undo  [R] reset  [Q] done (close window)")
            msg = f"[{self.name}] {n} click(s){seg}   {keys}"
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
        # Store period hint for wave-fit dialog pre-fill
        if not hasattr(self, '_period_hint_s'):
            self._period_hint_s = None
        self._wave_clicks_t = []
        self._wave_clicks_d = []
        self._wave_mode = True
        self._wave_done = False
        if self._wave_candidate and self._wave_candidate.exists():
            self._wave_candidate.unlink(missing_ok=True)
        self._wave_candidate = None
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

        # Build time grid from segment bounds — no spline CSV needed
        import pathlib as _pl_wf
        # Use sidecar for full window extent if available,
        # otherwise fall back to segment handles
        _sidecar_path = str(self.img_path).replace(".png", "_axes.json")
        # t_out spans the zoomed segment shown on screen -- extrapolate
        # slightly beyond the clicked points to cover the segment, NOT
        # the full day.
        _t_out_start = getattr(self, '_full_t0', self.seg_t0)
        _t_out_end   = getattr(self, '_full_t1', self.seg_t1)
        if _osw.path.exists(_sidecar_path):
            try:
                _sc_tmp = _jsonw.load(open(_sidecar_path))
                _t_out_start = _sc_tmp.get("t_start_utc_hours", _t_out_start)
                # Round t_end up to nearest minute to avoid floating point cutoff
                import math as _math
                _raw_end = _sc_tmp.get("t_end_utc_hours", _t_out_end)
                _t_out_end = _math.ceil(_raw_end * 60) / 60
            except Exception:
                pass
        # REAL BUG FOUND during live testing: this used to unconditionally
        # override the correct sidecar-derived segment bounds above with
        # the DRF reader's own FULL RECORDING bounds (e.g. the entire
        # day) whenever --drf-dir was provided -- which is every real
        # invocation, since that flag is always passed. This stretched
        # both the preview curve drawn on the zoomed spectrogram and the
        # exported CSV across the whole day instead of just the segment
        # actually shown on screen. When that full-day curve got added
        # to the same plot as the (much narrower) zoomed image, the
        # view had to widen dramatically to fit it, visually squeezing
        # the real spectrogram down to a small fraction of the window --
        # confirmed live: "the plot compressed to the right, about 1/3
        # original size" after pressing F. The comment describing this
        # block ("extrapolate beyond clicked region") already correctly
        # described the real intent -- extrapolate to the segment, not
        # the whole recording -- so this block simply rounds the
        # already-correct bounds established above to the nearest
        # minute, matching what used to only happen in the no-drf_dir
        # fallback case.
        import math as _mth
        _t_out_start = _mth.floor(_t_out_start * 60) / 60
        _t_out_end   = _mth.ceil(_t_out_end * 60 + 3) / 60
        t_out = _npw.arange(_t_out_start, _t_out_end, 1/60)
        stem = _pl_wf.Path(self.img_path).stem
        parent = _pl_wf.Path(self.img_path).parent

        # Use click points as the segment
        t_seg = click_t
        d_seg = click_d - click_d.mean()

        # THE ACTUAL FIX: instead of defaulting the dialog to a blind
        # guess of "1.0" (or a guess derived from an external, manually-
        # supplied --period-hint that virtually nobody provides), fit
        # the sine model at a RANGE of candidate cycle counts directly
        # against the user's own clicked points, and seed the dialog
        # with whichever cycle count fits best. This is exactly the
        # kind of automatic estimate the GUI/dashboard workflow already
        # used to avoid pure user guessing -- found missing here during
        # live testing, after a wrong manual "1.0" answer for N6RFM_5
        # (the true count was 2.0) produced a period exactly double the
        # other two stations' independently-measured period, which
        # measurably distorted the resulting TID speed/direction fit.
        _hint_s = getattr(self, '_period_hint_s', None)
        _hint_min = _hint_s / 60.0 if _hint_s else None

        import warnings as _warnings
        t_centre_est = (t0_mark + t1_mark) / 2.0
        A_guess_est   = (click_d.max() - click_d.min()) / 2.0
        off_guess_est = float(_npw.mean(click_d))

        # REAL BUG FOUND during live testing of a real event (Jan 19
        # 2026, 4-station run): with only 3-4 clicked points, this
        # auto-estimate would confidently converge to 0.20 (the search
        # grid's own lower bound) regardless of the true cycle count --
        # a 3-parameter sine fit against only 3-4 points is fundamentally
        # underdetermined, since a very long, slowly-varying candidate
        # period can always curve through a handful of sparse points by
        # coincidence. Measured empirically across 400 synthetic trials:
        # 3 clicks failed 100% of the time, 4 clicks 61%, 5 clicks still
        # 32% (too unreliable), 6+ clicks dropped to single digits. Below
        # 6 points, don't attempt the auto-estimate at all -- fall back
        # honestly to the same "1.0" default this feature was built to
        # replace, with a clear message explaining why, rather than
        # silently presenting an unreliable number with false precision
        # (a value like "0.20" formatted to 2 decimals looks confident
        # even when it's essentially noise).
        _MIN_CLICKS_FOR_AUTO_ESTIMATE = 6
        if len(click_t) < _MIN_CLICKS_FOR_AUTO_ESTIMATE:
            _n_auto = 1.0
            _n_auto_resid = None
            _hint_note = (f"\n  NOTE: only {len(click_t)} points clicked -- "
                          f"auto-estimate needs at least "
                          f"{_MIN_CLICKS_FOR_AUTO_ESTIMATE} to be reliable "
                          f"(tested: fewer points converge to a false "
                          f"answer nearly every time). Falling back to a "
                          f"plain default -- count cycles yourself, or "
                          f"redo with more clicked points.")
        else:
            def _fit_residual_for_n_cycles(n_cyc):
                """RMS residual of the 3-parameter sine fit at this cycle
                count, evaluated only at the actual clicked points."""
                T_h_try = span_h / n_cyc
                def _sine_try(t, A, phi, offset):
                    return A * _npw.sin(2 * _npw.pi / T_h_try * (t - t_centre_est) + phi) + offset
                try:
                    with _warnings.catch_warnings():
                        _warnings.simplefilter("ignore")
                        popt_try, _ = _curve_fit(
                            _sine_try, click_t, click_d,
                            p0=[A_guess_est, 0.0, off_guess_est], maxfev=2000)
                    resid = click_d - _sine_try(click_t, *popt_try)
                    return float(_npw.sqrt(_npw.mean(resid ** 2)))
                except Exception:
                    return float("inf")

            # Coarse grid search, then a finer local refinement around the
            # best coarse candidate -- cheap (a few thousand small curve_fit
            # calls at most) and far more reliable than a single guess for
            # sparse, non-uniformly-sampled click data.
            #
            # Found during testing: picking the pure global-minimum-residual
            # candidate is vulnerable to aliasing -- a spurious higher-
            # frequency candidate can fit the same sparse click points just
            # as well by coincidence, especially with few/evenly-spaced
            # clicks. Fixed by preferring the simplest (fewest-cycles)
            # explanation among all candidates whose residual is close to
            # the best, rather than the pure minimum -- the same principle
            # behind preferring the fundamental over a harmonic when both
            # explain sparse data similarly well.
            #
            # REAL BUG FOUND during live testing with 9 real, well-placed
            # clicks (well above the 6-point minimum): the tolerance of
            # 1.5x the best residual was far too loose, accepting
            # candidates from 0.2 all the way to 1.1 cycles as "good
            # enough" when the true best fit was 0.8 -- then confidently
            # returning 0.2, the search floor, as if it were a precise
            # answer. 1.5x wasn't distinguishing "genuinely near-tied"
            # from "the whole plausible range fits passably." Tightened
            # to 1.05x. Verified this still passes the original aliasing
            # test this tolerance was built for (5/5 synthetic cases) and
            # correctly recovers ~0.8 for the real failing case above,
            # while a broader 200-trial sweep (6-8 clicks) improved
            # slightly overall (4% failures vs more before, and most no
            # longer the confidently-wrong low-n type).
            _coarse = _npw.arange(0.2, 6.01, 0.1)
            _residuals = _npw.array([_fit_residual_for_n_cycles(n) for n in _coarse])
            _best_resid = _residuals.min()
            _tolerance = max(_best_resid * 1.05, 0.005)
            _good_enough = _coarse[_residuals <= _tolerance]
            _best_coarse = float(_good_enough.min()) if len(_good_enough) else _coarse[int(_npw.argmin(_residuals))]
            _fine = _npw.arange(max(0.1, _best_coarse - 0.1), _best_coarse + 0.101, 0.01)
            _fine_residuals = [_fit_residual_for_n_cycles(n) for n in _fine]
            _fine_best_idx = int(_npw.argmin(_fine_residuals))
            _n_auto = float(_fine[_fine_best_idx])
            _n_auto_resid = _fine_residuals[_fine_best_idx]
            _hint_note = (f"\n  Best fit to your clicked points: {_n_auto:.2f} "
                          f"cycles (RMS residual {_n_auto_resid:.3f} Hz)")

        _n_guess = _n_auto
        _n_guess_str = f"{_n_auto:.2f}"
        if _hint_min and _hint_min > 0:
            _n_from_hint = span_s / 60.0 / _hint_min
            _hint_note += (f"\n  (--period-hint {_hint_min:.0f} min would "
                           f"suggest {_n_from_hint:.1f} cycles instead)")
        from PyQt5 import QtWidgets as _QtW
        dlg = _QtW.QInputDialog()
        dlg.setWindowTitle("Wave-fit: how many cycles?")
        dlg.setLabelText(
            f"Your clicked span: {span_s/60:.1f} min\n\n"
            f"How many complete TID cycles did you span?\n"
            f"  Count peak-to-peak or trough-to-trough.\n"
            f"  e.g. 0.5 = half cycle, 1.0 = one full, 1.5 = one and a half"
            f"{_hint_note}\n\n"
            f"Number of cycles:")
        dlg.setTextValue(_n_guess_str)
        dlg.setOkButtonText("OK")
        dlg.setCancelButtonText("Cancel")
        if dlg.exec_() != _QtW.QDialog.Accepted:
            self._set_status("Wave-fit cancelled")
            return
        try:
            n_cycles = float(dlg.textValue().strip())
            if n_cycles <= 0:
                n_cycles = max(_n_guess, 0.5)
        except ValueError:
            n_cycles = max(_n_guess, 0.5)
        T_s = span_s / n_cycles
        T_min = T_s / 60.0
        T_h = T_s / 3600.0

        # Fit A*sin(2π/T * t + φ) to the marked segment
        # Centre time on segment midpoint to make phi well-conditioned
        t_centre = (t0_mark + t1_mark) / 2.0
        def _sine(t, A, phi, offset):
            return A * _npw.sin(2 * _npw.pi / T_h * (t - t_centre) + phi) + offset

        A_guess   = (click_d.max() - click_d.min()) / 2.0
        off_guess = float(_npw.mean(click_d))
        # Warn if too few points for reliable 3-parameter fit
        import warnings as _warnings
        if len(click_t) < 4:
            print(f"  NOTE: only {len(click_t)} click point(s) — "
                  "3-parameter fit may be unreliable. "
                  "Add more points for better accuracy.")
        # Fit ONLY to user click points — they define the wave exactly
        try:
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                popt, _ = _curve_fit(_sine, click_t, click_d,
                                      p0=[A_guess, 0.0, off_guess],
                                      maxfev=4000)
            A_fit, phi_fit, off_fit = popt
        except Exception:
            A_fit   = A_guess
            phi_fit = 0.0
            off_fit = off_guess

        # Reconstruct full window
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

        # Save as a CANDIDATE, not the final output. It only becomes the
        # real <station>_wave_tid.csv on explicit accept (A key), or as
        # a safety net when the window closes with a pending candidate
        # (see closeEvent) -- never silently from F alone.
        out_stem = stem.replace("_tid_zoom_clean", "")
        out_path = parent / f"{out_stem}_wave_tid_candidate.csv"
        out_df.to_csv(out_path, index=False)

        self._wave_done = True
        self._wave_candidate = out_path
        self._wave_final_path = parent / f"{out_stem}_wave_tid.csv"
        self._set_status(
            f"[{self.name}] WAVE-FIT: T={T_s/60:.1f} min  A={abs(A_fit):.3f} Hz  "
            f"phi={phi_fit:.2f} rad   "
            f"[A]=accept  [W]=redo  [Q]=done (auto-accepts if pending)")
        print(f"  Wave-fit candidate: T={T_s/60:.1f} min, A={abs(A_fit):.3f} Hz, "
              f"phi={phi_fit:.3f} rad — press A to accept, W to redo")
        # Draw wave-fit overlay on spectrogram
        try:
            self.preview_curve.setData(list(t_out), list(d_wave))
            self.preview_curve.setPen({"color": "#00BFFF", "width": 2})
        except Exception:
            pass

    def _wave_fit_finalize(self, auto=False):
        """Copy the pending candidate CSV to its real <station>_wave_tid.csv
        path. Shared by explicit accept (A key) and the closeEvent
        safety net (auto=True, when the window closes with a candidate
        still pending)."""
        if not getattr(self, "_wave_done", False) or not self._wave_candidate:
            return None
        candidate = self._wave_candidate
        final = self._wave_final_path
        import shutil as _shutil_wf
        _shutil_wf.copyfile(candidate, final)
        self._wave_candidate = None
        tag = "auto-accepted on close" if auto else "Accepted"
        self._set_status(f"[{self.name}] WAVE-FIT {tag} → {final.name}")
        print(f"  {tag}: {final}")
        print(f"  (If this is for the synthetic test suite, run_tests.py "
              f"looks for exactly this file -- <station>_wave_tid.csv next "
              f"to the spectrogram PNG -- and copies it into the event "
              f"directory automatically. You don't need to move it "
              f"yourself, even though --show-commands describes a "
              f"different final path.)")
        # REAL TERMINOLOGY BUG FOUND: wave-fit's own accepted CSVs were
        # being recorded with method "spline" -- but "spline" is a
        # genuinely separate, real extraction method (_export_spline_csv,
        # anchor-click + PCHIP interpolation directly through the clicks,
        # no sinusoid model at all), completely different from wave-fit
        # (fits a single sinusoid). Reusing that name here caused every
        # wave-fit CSV all session to be mislabeled in the saved config,
        # including tid_doa.py's own "methods_used" reporting. Corrected
        # to record wave-fit's own, correct name.
        self._save_event_json(str(final), "wave-fit")
        return final

    def _wave_fit_accept(self):
        """A key: accept the current wave-fit candidate as final output."""
        final = self._wave_fit_finalize(auto=False)
        if final is None:
            self._set_status(
                f"[{self.name}] No wave-fit candidate to accept — run W+F first")

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _save_event_json(self, csv_path, method):
        """Update the event JSON with the exported CSV path and method.

        Called after X export when --event-json was supplied on the CLI.
        Updates the matching station entry (by name) in-place:
          - "file"   -> relative path to the exported CSV
          - "method" -> "cwt-prophet", "spline", or "wave-fit"
        Also stamps "max_lag_seconds" at top level if not present,
        using the auto-computed value from min_expected_speed_m_s and
        the longest baseline in the station list (rough heuristic —
        user should review and adjust before running tid_doa.py).
        """
        if not self._event_json:
            return
        import json as _ej, math as _math
        ej_path = Path(self._event_json)
        if not ej_path.exists():
            print(f"  [event JSON] not found: {ej_path}")
            return
        try:
            with open(ej_path) as _f:
                cfg = _ej.load(_f)
        except Exception as e:
            print(f"  [event JSON] read error: {e}")
            return

        # Make file path relative to event JSON directory if possible
        try:
            rel = Path(csv_path).resolve().relative_to(ej_path.parent.resolve())
            file_val = str(rel)
        except ValueError:
            file_val = str(csv_path)

        # Update matching station entry
        updated = False
        for stn in cfg.get("stations", []):
            if stn.get("name", "").upper() == self.name.upper():
                stn["file"]   = file_val
                stn["method"] = method
                updated = True
                break

        if not updated:
            print(f"  [event JSON] station '{self.name}' not found in {ej_path.name} — not updated")
            return

        # Stamp max_lag_seconds if absent (rough heuristic)
        if "max_lag_seconds" not in cfg:
            stns = cfg.get("stations", [])
            if len(stns) >= 2:
                lats = [s.get("lat", 0) for s in stns]
                lons = [s.get("lon", 0) for s in stns]
                max_sep_km = 0.0
                for i in range(len(stns)):
                    for j in range(i+1, len(stns)):
                        dlat = _math.radians(lats[i] - lats[j])
                        dlon = _math.radians(lons[i] - lons[j])
                        a = (_math.sin(dlat/2)**2 +
                             _math.cos(_math.radians(lats[i])) *
                             _math.cos(_math.radians(lats[j])) *
                             _math.sin(dlon/2)**2)
                        max_sep_km = max(max_sep_km, 6371 * 2 * _math.asin(_math.sqrt(a)))
                min_spd = cfg.get("min_expected_speed_m_s", 100.0)
                cfg["max_lag_seconds"] = round(max_sep_km * 1000 / min_spd)
                print(f"  [event JSON] max_lag_seconds set to {cfg['max_lag_seconds']} "
                      f"(heuristic — review before running tid_doa.py)")

        with open(ej_path, "w") as _f:
            _ej.dump(cfg, _f, indent=2)
            _f.write("\n")

        print(f"  [event JSON] updated {ej_path.name}: "
              f"{self.name} file={file_val!r} method={method!r}")


    def closeEvent(self, event):
        """Safety net: if a wave-fit candidate is still pending
        (F was pressed but A never was) when the window closes -- by
        any means, not just the Q shortcut -- auto-accept it rather
        than silently losing it. Explicitly pressing A first still
        works exactly as before; this only fires for whatever's left
        unaccepted at close time."""
        if getattr(self, "_wave_only", False) and getattr(self, "_wave_candidate", None):
            self._wave_fit_finalize(auto=True)
        super().closeEvent(event)

    def _install_shortcuts(self):
        # _wave_only is now correctly set before this runs (see the
        # constructor-ordering fix above), so this branches correctly
        # from the very first shortcut installed -- no more need to
        # bind the wrong keys first and patch them later.
        if self._wave_only:
            # P (prophet preview) and E (prophet accept) are for
            # cwt-prophet mode and must not be reachable here --
            # confirmed live that the auto-prophet-timer bug this file
            # just fixed could trigger real, serious problems (the
            # window visibly shrinking, an unrelated blue auto-trace
            # appearing, the app becoming unresponsive) when prophet
            # code ran during wave-fit clicking. X is bound directly
            # to accept (same as A) instead of the wrong
            # _export_spline_csv -- "X = export" is the natural
            # expectation in every other mode, no reason for wave-fit
            # to be the exception.
            keys = [("W", self._wave_fit_start),
                    ("F", self._wave_fit_execute),
                    ("A", self._wave_fit_accept),
                    ("X", self._wave_fit_accept),
                    ("Z", self._undo_last_click),
                    ("R", self._reset_clicks), ("C", self._clear_all),
                    ("Q", self.close)]
        else:
            keys = [("X", self._export_spline_csv),
                    ("E", self._export_prophet_csv),
                    ("P", self._run_prophet_preview),
                    ("Z", self._undo_last_click),
                    ("R", self._reset_clicks), ("C", self._clear_all),
                    ("Q", self.close)]
        self._shortcut_objs = {}
        for key, cb in keys:
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(key), self, cb)
            sc.setContext(QtCore.Qt.ApplicationShortcut)
            self._shortcut_objs[key] = sc


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
    p.add_argument("--channel-num", type=int, default=0, metavar="N",
                   help="DRF column index (for stations packing multiple frequencies into one channel) for sgolay-ridge preview (default 0)")
    p.add_argument("--corridor-width", type=float, default=0.4, metavar="HZ",
                   help="Half-width in Hz of the adaptive corridor centred on "
                        "the Prophet prediction at each time step. CWT peaks "
                        "outside this band are rejected. Default: 0.4 Hz.")
    p.add_argument("--sgolay-window", type=float, default=21.0, metavar="MINUTES",
                   help="SGOLAY smoothing window in minutes for preview (default 21)")
    p.add_argument("--event-json", default=None, metavar="JSON",
                   help="Event JSON config (e.g. event_20260119.json). "
                        "When X is pressed, the matching station entry is "
                        "updated with the exported CSV path and method, "
                        "making the run reproducible from the command line.")
    p.add_argument("--no-prophet", action="store_true",
                   help="Skip Prophet Pass 0 auto-run. Use for pure spline clicking "
                        "or when Prophet is not needed. "
                        "Status bar shows only relevant key bindings.")
    p.add_argument("--wave-only", action="store_true",
                   help="Skip Pass 0. Open directly in wave-fit mode (W).")
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
        channel_num  = args.channel_num,
        sgolay_window = args.sgolay_window,
        corridor_width = args.corridor_width,
        wave_only    = getattr(args, "wave_only", False),
        no_prophet   = args.no_prophet,
    )
    if args.no_prophet:
        print('  Prophet Pass 0: skipped (--no-prophet)')
    if args.event_json:
        win._event_json = args.event_json
        print(f'  Event JSON: {args.event_json} (will update on X export)')
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
