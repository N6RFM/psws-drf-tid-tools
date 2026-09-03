#!/usr/bin/env python3
"""
tid_intake_helper.py -- lightweight setup helper for the TID pipeline.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.0.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.0.0  Initial version. Deliberately narrow scope: this is NOT a
          smaller tid_dashboard.py. tid_dashboard.py (Streamlit) does
          the full end-to-end pipeline including the interactive
          extraction steps. This tool only covers the front end --
          discover companion stations, download data, organize it into
          a correctly-named event directory -- then hands off to the
          real interactive tool (tid_workflow.py) rather than trying
          to embed it. Built with Tkinter specifically so it adds zero
          new dependencies to requirements.txt and doesn't open a
          second browser-based app alongside the dashboard.

          find_event_stations.py has no JSON output option, and its
          own header row and data row column widths don't actually
          match (confirmed by reading its print() calls directly --
          e.g. the header's "Path" column is 5 chars wide but the data
          rows print a 4-char number + "km" = 6 chars), so this
          deliberately does NOT try to parse its table output into
          clickable rows -- that would be a fragile parser dressed up
          as a feature. Instead its raw output is just shown verbatim,
          and station selection is a manual text-entry field.

OVERVIEW
========
Three sections, top to bottom:
  1. Find companion stations for an event (wraps find_event_stations.py)
  2. Download + organize data (wraps download_companions.py)
  3. Hand off to tid_workflow.py (generates and copies the command;
     does not launch the interactive session itself)

USAGE
=====
    python3 tid_intake_helper.py
"""

import queue
import shlex
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

TOOLS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOLS_DIR))

try:
    from tid_workflow import KNOWN_STATIONS
except Exception:
    # Helper should still be usable even if tid_workflow.py can't be
    # imported for some reason (e.g. missing an unrelated dependency
    # it needs at import time) -- coordinate auto-fill just won't work.
    KNOWN_STATIONS = {}


def tool(name):
    return str(TOOLS_DIR / name)


class StreamingRunner:
    """Runs a subprocess, streaming its stdout/stderr into a Tk Text
    widget without blocking the GUI thread. One instance per button
    that launches a long-running command."""

    def __init__(self, text_widget, on_done=None):
        self.text_widget = text_widget
        self.on_done = on_done
        self._queue = queue.Queue()
        self._proc = None

    def running(self):
        return self._proc is not None and self._proc.poll() is None

    def start(self, cmd, cwd=None):
        if self.running():
            return False
        self.text_widget.configure(state="normal")
        self.text_widget.delete("1.0", tk.END)
        self.text_widget.insert(tk.END, f"$ {' '.join(shlex.quote(c) for c in cmd)}\n\n")
        self.text_widget.configure(state="disabled")
        thread = threading.Thread(
            target=self._run, args=(cmd, cwd), daemon=True
        )
        thread.start()
        self.text_widget.after(100, self._poll)
        return True

    def _run(self, cmd, cwd):
        try:
            self._proc = subprocess.Popen(
                cmd, cwd=cwd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                self._queue.put(line)
            self._proc.wait()
            self._queue.put(f"\n[exit code {self._proc.returncode}]\n")
        except Exception as e:
            self._queue.put(f"\n[failed to run: {e}]\n")
        finally:
            self._queue.put(None)  # sentinel: done

    def _poll(self):
        done = False
        try:
            while True:
                line = self._queue.get_nowait()
                if line is None:
                    done = True
                    break
                self.text_widget.configure(state="normal")
                self.text_widget.insert(tk.END, line)
                self.text_widget.see(tk.END)
                self.text_widget.configure(state="disabled")
        except queue.Empty:
            pass
        if done:
            returncode = self._proc.returncode if self._proc else -1
            self._proc = None
            if self.on_done:
                self.on_done(returncode)
        else:
            self.text_widget.after(100, self._poll)


class IntakeHelper(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PSWS TID Intake Helper")
        self.geometry("880x820")
        self._build_ui()

    # ---------------------------------------------------------- UI ---
    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ---- Section 0: your station ----
        frm0 = ttk.LabelFrame(self, text="Your station")
        frm0.pack(fill="x", **pad)

        ttk.Label(frm0, text="Callsign:").grid(row=0, column=0, sticky="e", **pad)
        self.call_var = tk.StringVar()
        call_entry = ttk.Entry(frm0, textvariable=self.call_var, width=14)
        call_entry.grid(row=0, column=1, sticky="w", **pad)
        call_entry.bind("<FocusOut>", self._maybe_autofill_coords)
        call_entry.bind("<Return>", self._maybe_autofill_coords)

        ttk.Label(frm0, text="Lat:").grid(row=0, column=2, sticky="e", **pad)
        self.lat_var = tk.StringVar()
        ttk.Entry(frm0, textvariable=self.lat_var, width=10).grid(
            row=0, column=3, sticky="w", **pad)

        ttk.Label(frm0, text="Lon:").grid(row=0, column=4, sticky="e", **pad)
        self.lon_var = tk.StringVar()
        ttk.Entry(frm0, textvariable=self.lon_var, width=10).grid(
            row=0, column=5, sticky="w", **pad)

        self.coords_hint = ttk.Label(frm0, text="", foreground="#666")
        self.coords_hint.grid(row=1, column=0, columnspan=6, sticky="w", padx=8)

        ttk.Label(frm0, text="Event date (YYYY-MM-DD):").grid(
            row=2, column=0, sticky="e", **pad)
        self.date_var = tk.StringVar(value=datetime.utcnow().strftime("%Y-%m-%d"))
        date_entry = ttk.Entry(frm0, textvariable=self.date_var, width=14)
        date_entry.grid(row=2, column=1, sticky="w", **pad)
        date_entry.bind("<FocusOut>", lambda e: self._update_event_dir())
        date_entry.bind("<Return>", lambda e: self._update_event_dir())

        ttk.Label(frm0, text="Frequency (MHz):").grid(
            row=2, column=2, sticky="e", **pad)
        self.freq_var = tk.StringVar(value="10.000")
        ttk.Entry(frm0, textvariable=self.freq_var, width=10).grid(
            row=2, column=3, sticky="w", **pad)

        # ---- Section 1: find companions ----
        frm1 = ttk.LabelFrame(self, text="1. Find companion stations")
        frm1.pack(fill="both", expand=True, **pad)

        self.find_btn = ttk.Button(
            frm1, text="Find Companion Stations", command=self._run_find
        )
        self.find_btn.pack(anchor="w", padx=8, pady=4)

        self.find_output = scrolledtext.ScrolledText(
            frm1, height=14, state="disabled", wrap="none", font=("Courier", 10)
        )
        self.find_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.find_runner = StreamingRunner(self.find_output)

        # ---- Section 2: download + organize ----
        frm2 = ttk.LabelFrame(self, text="2. Download and organize data")
        frm2.pack(fill="both", expand=True, **pad)

        ttk.Label(
            frm2,
            text="Stations to download (comma-separated, include your "
                 "own callsign — read candidates off the table above):",
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(4, 0))
        self.stations_var = tk.StringVar()
        ttk.Entry(frm2, textvariable=self.stations_var, width=60).grid(
            row=1, column=0, columnspan=3, sticky="we", padx=8, pady=4
        )

        ttk.Label(frm2, text="Event directory:").grid(
            row=2, column=0, sticky="e", padx=8, pady=4)
        self.event_dir_var = tk.StringVar()
        ttk.Entry(frm2, textvariable=self.event_dir_var, width=50).grid(
            row=2, column=1, sticky="we", padx=8, pady=4)
        self._update_event_dir()

        self.download_btn = ttk.Button(
            frm2, text="Download Data", command=self._run_download
        )
        self.download_btn.grid(row=2, column=2, sticky="w", padx=8, pady=4)

        self.download_output = scrolledtext.ScrolledText(
            frm2, height=12, state="disabled", wrap="word", font=("Courier", 10)
        )
        self.download_output.grid(
            row=3, column=0, columnspan=3, sticky="nsew", padx=8, pady=(0, 8)
        )
        frm2.grid_columnconfigure(1, weight=1)
        frm2.grid_rowconfigure(3, weight=1)
        self.download_runner = StreamingRunner(
            self.download_output, on_done=self._on_download_done
        )

        # ---- Section 3: hand off ----
        frm3 = ttk.LabelFrame(self, text="3. Ready to analyze")
        frm3.pack(fill="both", **pad)

        ttk.Label(
            frm3,
            text="This does not launch the interactive session itself "
                 "(that's a separate PyQt5 process) -- copy this command "
                 "into your own terminal (with your venv activated) to begin:",
        ).pack(anchor="w", padx=8, pady=(4, 0))

        self.command_box = scrolledtext.ScrolledText(
            frm3, height=6, state="disabled", wrap="word", font=("Courier", 10)
        )
        self.command_box.pack(fill="x", padx=8, pady=4)

        btn_row = ttk.Frame(frm3)
        btn_row.pack(anchor="w", padx=8, pady=(0, 8))
        ttk.Button(
            btn_row, text="Generate Command", command=self._generate_command
        ).pack(side="left")
        ttk.Button(
            btn_row, text="Copy to Clipboard", command=self._copy_command
        ).pack(side="left", padx=(8, 0))
        self.terminal_btn = ttk.Button(
            btn_row, text="Open Terminal Here (best effort)",
            command=self._try_open_terminal
        )
        self.terminal_btn.pack(side="left", padx=(8, 0))

    # ------------------------------------------------------ helpers ---
    def _maybe_autofill_coords(self, event=None):
        call = self.call_var.get().strip().upper()
        if call in KNOWN_STATIONS:
            lat, lon, grid = KNOWN_STATIONS[call]
            self.lat_var.set(str(lat))
            self.lon_var.set(str(lon))
            self.coords_hint.configure(
                text=f"Found in built-in station database: {grid}"
            )
        elif call:
            self.coords_hint.configure(
                text="Not in the built-in database -- enter lat/lon manually."
            )
        else:
            self.coords_hint.configure(text="")

    def _update_event_dir(self):
        date_str = self.date_var.get().strip()
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            suggested = str(Path.home() / "Downloads" / f"tid_event_{d.strftime('%Y%m%d')}")
        except ValueError:
            suggested = str(Path.home() / "Downloads" / "tid_event_YYYYMMDD")
        self.event_dir_var.set(suggested)

    def _validate_date(self):
        try:
            datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d")
            return True
        except ValueError:
            messagebox.showerror(
                "Invalid date", "Event date must be in YYYY-MM-DD format."
            )
            return False

    # -------------------------------------------------- section 1 -----
    def _run_find(self):
        call = self.call_var.get().strip().upper()
        lat, lon = self.lat_var.get().strip(), self.lon_var.get().strip()
        if not (call and lat and lon):
            messagebox.showerror(
                "Missing info", "Callsign, latitude, and longitude are all required."
            )
            return
        if not self._validate_date():
            return
        cmd = [
            "python3", tool("find_event_stations.py"),
            "--date", self.date_var.get().strip(),
            "--my-lat", lat, "--my-lon", lon, "--my-call", call,
            "--frequency", self.freq_var.get().strip() or "10.000",
        ]
        if self.find_runner.start(cmd):
            self.find_btn.configure(state="disabled")
            self._reenable_after(self.find_runner, self.find_btn)

    def _reenable_after(self, runner, btn):
        def check():
            if runner.running():
                self.after(200, check)
            else:
                btn.configure(state="normal")
        self.after(200, check)

    # -------------------------------------------------- section 2 -----
    def _run_download(self):
        if not self._validate_date():
            return
        stations_raw = self.stations_var.get().strip()
        if not stations_raw:
            messagebox.showerror(
                "Missing stations",
                "Enter at least one station callsign (comma-separated)."
            )
            return
        stations = [s.strip().upper() for s in stations_raw.split(",") if s.strip()]
        event_dir = self.event_dir_var.get().strip()
        if not event_dir:
            messagebox.showerror("Missing directory", "Event directory can't be empty.")
            return
        Path(event_dir).mkdir(parents=True, exist_ok=True)
        cmd = [
            "python3", tool("download_companions.py"),
            "--date", self.date_var.get().strip(),
            "--stations", *stations,
            "--out-dir", event_dir,
        ]
        if self.download_runner.start(cmd):
            self.download_btn.configure(state="disabled")
            self._reenable_after(self.download_runner, self.download_btn)

    def _on_download_done(self, returncode):
        if returncode == 0:
            self._generate_command()

    # -------------------------------------------------- section 3 -----
    def _generate_command(self):
        call = self.call_var.get().strip().upper()
        stations_raw = self.stations_var.get().strip()
        stations = [s.strip().upper() for s in stations_raw.split(",") if s.strip()]
        event_dir = self.event_dir_var.get().strip()
        if not (call and stations and event_dir):
            messagebox.showinfo(
                "Not ready yet",
                "Fill in your callsign, station list, and event directory first."
            )
            return
        if call not in stations:
            stations = [call] + stations
        cmd_str = (
            f"python3 tid_workflow.py \\\n"
            f"    --event-dir {event_dir} \\\n"
            f"    --stations {','.join(stations)} \\\n"
            f"    --my-station {call} \\\n"
            f"    --max-lag 30"
        )
        self.command_box.configure(state="normal")
        self.command_box.delete("1.0", tk.END)
        self.command_box.insert(tk.END, cmd_str)
        self.command_box.configure(state="disabled")

    def _copy_command(self):
        text = self.command_box.get("1.0", tk.END).strip()
        if not text:
            self._generate_command()
            text = self.command_box.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Copied", "Command copied to clipboard.")

    def _try_open_terminal(self):
        """Best-effort only. Cross-desktop terminal launching is
        inherently unreliable -- if none of these work or are found,
        fails visibly rather than pretending to succeed, and the
        Copy to Clipboard button remains the dependable path."""
        event_dir = self.event_dir_var.get().strip() or str(Path.home())
        candidates = [
            ("x-terminal-emulator", []),
            ("gnome-terminal", ["--working-directory", event_dir]),
            ("konsole", ["--workdir", event_dir]),
            ("xterm", []),
        ]
        for exe, extra_args in candidates:
            path = shutil.which(exe)
            if path:
                try:
                    subprocess.Popen([path] + extra_args, cwd=TOOLS_DIR)
                    return
                except Exception:
                    continue
        messagebox.showwarning(
            "No terminal found",
            "Couldn't find a terminal emulator to launch automatically. "
            "Use the Copy to Clipboard button and paste into your own terminal."
        )


if __name__ == "__main__":
    app = IntakeHelper()
    app.mainloop()
