r"""
tid_quicklook.py — interactive TID window selector

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 0.1.0
License: MIT (do whatever you want, no warranty).

OVERVIEW
========
First step in the guided TID extraction workflow. Displays a Doppler
spectrogram PNG and lets the user drag a region selector to identify
the time window where a TID is active. Writes a small JSON sidecar
that downstream tools (tid_spect_click.py) use to pre-set the analysis
segment.

WORKFLOW POSITION
=================
    drf_spectrogram.py  →  tid_quicklook.py  →  tid_spect_click.py
                                ↓
                        <png_stem>_window.json
                        {t_start_hours, t_end_hours}

USAGE
=====
    python tid_quicklook.py --spectrogram w7lux_sidecar.png

The sidecar axes JSON (<png_stem>_axes.json) is auto-detected.

KEYBOARD SHORTCUTS
==================
    S     Save selected window to JSON and quit
    Q     Quit without saving

OUTPUT
======
Writes <png_stem>_window.json alongside the spectrogram PNG:
{
  "spectrogram_png": "w7lux_sidecar.png",
  "t_start_utc_hours": 18.0,
  "t_end_utc_hours": 20.0,
  "_note": "TID window selected by tid_quicklook.py"
}

REQUIREMENTS
============
    pip install pyqtgraph PyQt5 Pillow numpy
"""

import argparse
import json
import os
import sys
from pathlib import Path

import os as _os
import numpy as np
from PIL import Image
from PyQt5 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


class QuicklookApp(QtWidgets.QMainWindow):

    def __init__(self, img_path, transform, t_start, t_end):
        super().__init__()
        self.img_path  = Path(img_path)
        self.transform = transform
        self.setWindowTitle(
            f"TID Quicklook — {self.img_path.name} — psws-drf-tid-tools"
        )
        self.resize(1300, 600)
        self._build_ui(t_start, t_end)
        self._install_shortcuts()
        self._update_status()

    def _build_ui(self, t_start, t_end):
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
        self.plot.setLabel("bottom", "Time (UTC hours)")
        self.plot.setLabel("left", "Doppler shift", units="Hz")

        # Load and display spectrogram image
        pil_img = Image.open(self.img_path).convert("RGBA")
        self.img_w, self.img_h = pil_img.size
        arr = np.array(pil_img)
        arr = np.transpose(arr, (1, 0, 2))
        arr = arr[:, ::-1, :]

        self.img_item = pg.ImageItem()
        self.plot.addItem(self.img_item)
        self.img_item.setImage(arr)

        # Set image transform from sidecar
        if self.transform:
            t_lo, d_bot = self.transform.px_to_physical(0, self.img_h)
            t_hi, d_top = self.transform.px_to_physical(self.img_w, 0)
            tr = QtGui.QTransform()
            tr.translate(t_lo, d_bot)
            tr.scale((t_hi - t_lo) / self.img_w,
                     (d_top - d_bot) / self.img_h)
            self.img_item.setTransform(tr)

        # TID window region selector
        self.region = pg.LinearRegionItem(
            values=[t_start, t_end],
            brush=pg.mkBrush(255, 255, 100, 30),
            pen=pg.mkPen(color="#ffff64", width=2),
            movable=True,
        )
        self.plot.addItem(self.region)
        self.region.sigRegionChanged.connect(self._update_status)

    def _update_status(self):
        t0, t1 = self.region.getRegion()

        def fmt(h):
            hh = int(h)
            mm = int(round((h - hh) * 60))
            return f"{hh:02d}:{mm:02d}"

        self.status_label.setText(
            f"Selected TID window: {fmt(t0)} — {fmt(t1)} UTC  "
            f"({t1-t0:.2f} h)   "
            f"[S] save & quit   [Q] quit without saving"
        )

    def _save(self):
        t0, t1 = self.region.getRegion()
        out = self.img_path.parent / (self.img_path.stem + "_window.json")
        data = {
            "spectrogram_png": self.img_path.name,
            "t_start_utc_hours": round(t0, 4),
            "t_end_utc_hours":   round(t1, 4),
            "_note": "TID window selected by tid_quicklook.py — "
                     "used by tid_spect_click.py to pre-set segment"
        }
        with open(out, "w") as f:
            json.dump(data, f, indent=2)

        def fmt(h):
            hh = int(h); mm = int(round((h - hh) * 60))
            return f"{hh:02d}:{mm:02d}"

        msg = (f"Saved: {out.name}  "
               f"({fmt(t0)}–{fmt(t1)} UTC)")
        self.status_label.setText(msg)
        print(f"Written: {out}")
        print(f"  t_start: {t0:.4f} h ({fmt(t0)} UTC)")
        print(f"  t_end:   {t1:.4f} h ({fmt(t1)} UTC)")
        # Check overlap with other station windows in same directory
        self._check_overlap(out, t0, t1)
        QtCore.QTimer.singleShot(800, self.close)

    def _check_overlap(self, this_json, t0, t1):
        """Check overlap with other station window JSONs in same directory."""
        import glob as _glob
        other_windows = _glob.glob(
            str(this_json.parent / "*_window.json")
        )
        other_windows = [f for f in other_windows
                         if f != str(this_json)]
        if not other_windows:
            return
        min_overlap = 60.0  # minutes
        msgs = []
        for f in other_windows:
            try:
                with open(f) as _f:
                    wj = _json.load(_f)
                o0 = wj["t_start_utc_hours"]
                o1 = wj["t_end_utc_hours"]
                overlap = (min(t1, o1) - max(t0, o0)) * 60
                name = _os.path.basename(f)
                if overlap < min_overlap:
                    msgs.append(
                        f"⚠️ Only {overlap:.0f} min overlap with {name} "
                        f"(need ≥{min_overlap:.0f} min)"
                    )
                else:
                    msgs.append(
                        f"✓ {overlap:.0f} min overlap with {name}"
                    )
            except Exception:
                pass
        if msgs:
            print("  Window overlap check:")
            for m in msgs:
                print(f"    {m}")
            self.status_label.setText(
                "  |  ".join(msgs)
            )

    def _install_shortcuts(self):
        for key, cb in [("S", self._save), ("Q", self.close)]:
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(key), self, cb)
            sc.setContext(QtCore.Qt.ApplicationShortcut)


# ---------------------------------------------------------------------------
# Minimal axis transform (same as tid_spect_click.py)
# ---------------------------------------------------------------------------

class AxisTransform:
    def __init__(self, img_w, img_h, tlim, ylim,
                 plot_fraction=(0.0582, 0.8421, 0.3712, 0.9570)):
        lf, rf, bf, tf = plot_fraction
        px_left  = lf * img_w;  px_right = rf * img_w
        py_top   = (1 - tf) * img_h;  py_bot = (1 - bf) * img_h
        t0, t1   = tlim;  d_lo, d_hi = ylim
        self.ax  = (t1 - t0) / (px_right - px_left)
        self.bx  = t0 - self.ax * px_left
        self.ay  = (d_lo - d_hi) / (py_bot - py_top)
        self.by  = d_hi - self.ay * py_top

    def px_to_physical(self, px, py):
        return self.ax * px + self.bx, self.ay * py + self.by


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(
        description="Interactive TID window selector — first step in guided extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--spectrogram", required=True, metavar="PNG",
                   help="Spectrogram PNG (sidecar _axes.json auto-detected)")
    p.add_argument("--plot-fraction", metavar="L,R,B,T",
                   help="Plot area fractions override")
    return p.parse_args()


def main():
    args = _parse_args()
    print("tid_quicklook.py  v0.1.0")

    spec_path = Path(args.spectrogram)
    sidecar   = spec_path.parent / (spec_path.stem + "_axes.json")
    window_f  = spec_path.parent / (spec_path.stem + "_window.json")

    transform = None
    t_start, t_end = 0.25, 0.75   # default fractions until sidecar loaded

    if sidecar.exists():
        with open(sidecar) as f:
            sc = json.load(f)
        t0h = sc["t_start_utc_hours"]
        t1h = sc["t_end_utc_hours"]
        d0  = sc["doppler_lo_hz"]
        d1  = sc["doppler_hi_hz"]
        print(f"  Sidecar: t={t0h}-{t1h} h, doppler={d0}-{d1} Hz")
        pil = Image.open(spec_path)
        w, h = pil.size
        pf = (tuple(float(x) for x in args.plot_fraction.split(","))
              if args.plot_fraction else None)
        transform = AxisTransform(w, h, (t0h, t1h), (d0, d1),
                                  **({"plot_fraction": pf} if pf else {}))
        # Default region: narrow 1-hour window near start
        # User drags to wherever the TID actually is
        t_start = t0h + 1.0
        t_end   = t0h + 2.0
    else:
        print("  No sidecar found — image shown without axis calibration")

    # Pre-load existing window if present
    if window_f.exists():
        with open(window_f) as f:
            wj = json.load(f)
        t_start = wj["t_start_utc_hours"]
        t_end   = wj["t_end_utc_hours"]
        print(f"  Existing window: {t_start:.2f}-{t_end:.2f} h")

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("TID Quicklook")
    win = QuicklookApp(args.spectrogram, transform, t_start, t_end)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
