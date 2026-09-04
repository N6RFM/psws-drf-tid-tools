#!/usr/bin/env python3
"""
mock_server_gui.py -- guided GUI for mock_psws_server.py: pick a
scenario, start/stop the server, and download example data for
subsequent analysis, without needing a second terminal or a manual
`export PSWS_BASE_URL=...`.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.1.0  Fixed the same stdout-buffering bug already found and fixed
          in tid_external_helper.py one round earlier: both subprocess
          launches (the server itself, and download_companions.py)
          now run with `python3 -u`. Without it, real progress output
          -- the server's own per-station generation lines, its full
          startup banner -- can sit invisible in Python's default
          block buffer when piped, making a scenario that's actually
          generating normally look like it's hung or taking far
          longer than it really is. This should have been applied
          proactively when this file was first written, having just
          learned the identical lesson in a sibling tool -- worth
          being direct about that rather than presenting this as a
          fresh discovery. Also worth noting: this sandbox's own
          PYTHONUNBUFFERED=1 environment variable means testing here
          could never have caught this bug even by re-checking, since
          every subprocess run in this environment is secretly
          unbuffered regardless of the flag -- real verification
          needs a real, differently-configured machine.

  v1.0.0  Initial version. Same design principle as
          tid_intake_helper.py / tid_external_helper.py /
          tid_workflow_launcher.py: deliberately narrow, hands off to
          the real tools (mock_psws_server.py, download_companions.py)
          rather than reimplementing their logic. Reuses
          mock_psws_server.py's own RECOMMENDED_SCENARIOS list
          directly, so the curated 6 shown here can never drift from
          what --list-scenarios itself reports.

          Different lifecycle than the other three GUIs, worth being
          explicit about: mock_psws_server.py is a long-running
          background process, not a batch script that finishes --
          this manages Start/Stop rather than run-to-completion, and
          sets PSWS_BASE_URL directly in download_companions.py's own
          subprocess environment (not the GUI's own process, and not
          by asking the operator to export it in a separate terminal),
          scoped to exactly the port the managed server is actually
          listening on.

          Real bug found live, not just code-reviewed: the initial
          scenario-info callback was wired to run during section 1's
          own widget construction, but it referenced out_dir_var --
          not created until section 3, built later. Fixed by moving
          that initial call to the end of _build_ui(), after every
          widget and variable actually exists.
"""

import os
import queue
import re
import shlex
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

TOOLS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOLS_DIR))

try:
    from mock_psws_server import RECOMMENDED_SCENARIOS
    _HAVE_SCENARIOS = True
except Exception as e:
    _HAVE_SCENARIOS = False
    _SCENARIOS_IMPORT_ERROR = e
    RECOMMENDED_SCENARIOS = []

try:
    sys.path.insert(0, str(TOOLS_DIR / "synthetic_tests"))
    from test_conditions import TEST_CONDITIONS
    _HAVE_TEST_CONDITIONS = True
except Exception:
    _HAVE_TEST_CONDITIONS = False
    TEST_CONDITIONS = []


def tool(name):
    return str(TOOLS_DIR / name)


def make_readonly_but_copyable(text_widget):
    """Same conclusion reached in tid_external_helper.py after two
    failed attempts at something cleverer: leave the widget in
    "normal" state with no custom key bindings. Nothing here reads
    the log widget's own content back for logic, so accidental typing
    into a passive scrollback log has zero functional consequence."""
    text_widget.configure(state="normal")

    menu = tk.Menu(text_widget, tearoff=0)
    menu.add_command(
        label="Copy",
        command=lambda: text_widget.event_generate("<<Copy>>"))
    menu.add_command(
        label="Select All",
        command=lambda: (text_widget.tag_add("sel", "1.0", "end"),
                          text_widget.mark_set("insert", "end")))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)
        return "break"

    text_widget.bind("<Button-3>", show_menu)


class StreamReader:
    """Reads a subprocess's combined stdout/stderr continuously in a
    background thread, feeding a Tk text widget via .after() polling
    -- the same queue-based pattern used by tid_external_helper.py's
    StreamingRunner, generalized here to also support a *long-running*
    process (the mock server itself) rather than only one that's
    expected to finish. on_line, if given, is called with each raw
    line for callers that want to react to specific output (e.g.
    detecting "Listening on ..." to know the server is ready)."""

    def __init__(self, text_widget, on_line=None, on_exit=None):
        self.text_widget = text_widget
        self.on_line = on_line
        self.on_exit = on_exit
        self._queue = queue.Queue()
        self.proc = None

    def start(self, cmd, env=None):
        self.proc = subprocess.Popen(
            cmd, cwd=TOOLS_DIR, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1, env=env,
        )
        thread = threading.Thread(target=self._read, daemon=True)
        thread.start()
        self.text_widget.after(100, self._poll)

    def _read(self):
        try:
            for line in self.proc.stdout:
                self._queue.put(line)
            self.proc.wait()
            self._queue.put(f"\n[exit code {self.proc.returncode}]\n")
        except Exception as e:
            self._queue.put(f"\n[failed: {e}]\n")
        finally:
            self._queue.put(None)

    def _append(self, text):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, text)
        self.text_widget.see(tk.END)

    def _poll(self):
        done = False
        try:
            while True:
                line = self._queue.get_nowait()
                if line is None:
                    done = True
                    break
                self._append(line)
                if self.on_line:
                    self.on_line(line)
        except queue.Empty:
            pass
        if done:
            if self.on_exit:
                self.on_exit()
        else:
            self.text_widget.after(100, self._poll)

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if self.running():
            self.proc.terminate()


class MockServerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mock PSWS Server -- psws-drf-tid-tools")
        self.geometry("880x760")
        self.server_reader = None
        self.server_port = None
        self.scenario_stations = []
        self.scenario_date = None
        self.station_vars = {}
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    # ---- UI construction ---------------------------------------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # Scenario selection
        f1 = ttk.LabelFrame(self, text="1. Choose a scenario")
        f1.pack(fill="x", **pad)
        row1 = ttk.Frame(f1)
        row1.pack(fill="x", padx=6, pady=4)
        ttk.Label(row1, text="Scenario:").pack(side="left")
        self.scenario_var = tk.StringVar(
            value=RECOMMENDED_SCENARIOS[0] if RECOMMENDED_SCENARIOS else "")
        self.scenario_combo = ttk.Combobox(
            row1, textvariable=self.scenario_var,
            values=RECOMMENDED_SCENARIOS, state="readonly", width=20)
        self.scenario_combo.pack(side="left", padx=(4, 12))
        self.scenario_combo.bind("<<ComboboxSelected>>", self._on_scenario_pick)
        self.show_all_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="Show all 30 (not just the 6 recommended)",
                         variable=self.show_all_var,
                         command=self._toggle_all_scenarios).pack(side="left")
        ttk.Label(row1, text="Port:").pack(side="left", padx=(16, 0))
        self.port_var = tk.StringVar(value="8765")
        ttk.Entry(row1, textvariable=self.port_var, width=6).pack(
            side="left", padx=4)

        self.scenario_info_label = ttk.Label(
            f1, text="", foreground="#206020", wraplength=820,
            justify="left")
        self.scenario_info_label.pack(fill="x", padx=6, pady=(0, 6))

        # Server control
        f2 = ttk.LabelFrame(self, text="2. Start the mock server")
        f2.pack(fill="x", **pad)
        row2 = ttk.Frame(f2)
        row2.pack(fill="x", padx=6, pady=4)
        self.start_button = ttk.Button(
            row2, text="Start Server", command=self._start_server)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            row2, text="Stop Server", command=self._stop_server,
            state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))
        self.server_status_label = ttk.Label(
            row2, text="Not running.", foreground="#666666")
        self.server_status_label.pack(side="left", padx=12)
        ttk.Label(
            f2, text="Generation can take anywhere from a few seconds to "
                     "over a minute the first time a scenario is used -- "
                     "let it finish rather than clicking Stop early.",
            foreground="#666666", wraplength=820, justify="left"
        ).pack(fill="x", padx=6, pady=(0, 6))

        # Download
        f3 = ttk.LabelFrame(self, text="3. Download example data")
        f3.pack(fill="x", **pad)
        row3 = ttk.Frame(f3)
        row3.pack(fill="x", padx=6, pady=4)
        ttk.Label(row3, text="Save to:").pack(side="left")
        self.out_dir_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.out_dir_var).pack(
            side="left", fill="x", expand=True, padx=4)
        ttk.Button(row3, text="Browse...", command=self._browse_out_dir
                   ).pack(side="left")

        self.stations_frame = ttk.Frame(f3)
        self.stations_frame.pack(fill="x", padx=6, pady=4)
        ttk.Label(self.stations_frame,
                  text="(start the server first to see this scenario's "
                       "real station list)",
                  foreground="#666666").pack(anchor="w")

        row3b = ttk.Frame(f3)
        row3b.pack(fill="x", padx=6, pady=(0, 6))
        self.download_button = ttk.Button(
            row3b, text="Download", command=self._download,
            state="disabled")
        self.download_button.pack(side="left")
        self.download_status_label = ttk.Label(
            row3b, text="", foreground="#206020")
        self.download_status_label.pack(side="left", padx=12)

        # Next step
        f4 = ttk.LabelFrame(self, text="4. Next step")
        f4.pack(fill="x", **pad)
        self.next_step_label = ttk.Label(
            f4, text="After downloading, run tid_workflow_launcher.py "
                     "(or tid_workflow.py directly) pointed at the "
                     "directory above.",
            foreground="#666666", wraplength=820, justify="left")
        self.next_step_label.pack(fill="x", padx=6, pady=6)
        ttk.Button(f4, text="Open tid_workflow_launcher.py",
                   command=self._launch_workflow_launcher
                   ).pack(anchor="w", padx=6, pady=(0, 6))

        # Log
        f5 = ttk.LabelFrame(self, text="Output")
        f5.pack(fill="both", expand=True, **pad)
        log_buttons = ttk.Frame(f5)
        log_buttons.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Button(log_buttons, text="Copy All",
                   command=self._copy_log).pack(side="left")
        ttk.Button(log_buttons, text="Clear",
                   command=self._clear_log).pack(side="left", padx=(6, 0))
        ttk.Label(log_buttons, text="(or right-click below for Copy / "
                                     "Select All)",
                  foreground="#666666").pack(side="left", padx=8)
        self.log_widget = scrolledtext.ScrolledText(
            f5, height=16, font=("Courier", 10))
        make_readonly_but_copyable(self.log_widget)
        self.log_widget.pack(fill="both", expand=True, padx=6, pady=6)

        self._on_scenario_pick()

    # ---- Scenario selection --------------------------------------------

    def _toggle_all_scenarios(self):
        if self.show_all_var.get() and _HAVE_TEST_CONDITIONS:
            values = [tc[0] for tc in TEST_CONDITIONS]
        else:
            values = RECOMMENDED_SCENARIOS
        self.scenario_combo.configure(values=values)
        if self.scenario_var.get() not in values and values:
            self.scenario_var.set(values[0])
            self._on_scenario_pick()

    def _on_scenario_pick(self, event=None):
        name = self.scenario_var.get()
        if not _HAVE_TEST_CONDITIONS:
            self.scenario_info_label.configure(
                text=f"Could not import test_conditions.py.",
                foreground="#a04040")
            return
        by_name = {tc[0]: tc for tc in TEST_CONDITIONS}
        tc = by_name.get(name)
        if not tc:
            return
        _, speed, az, period, amp, snr, noise, array, expect_pass, notes = tc
        self.scenario_info_label.configure(
            text=f"Ground truth: {speed} m/s from {az}\u00b0, "
                 f"{period} min period, {snr} dB SNR ({noise}), "
                 f"array={array}, expect_pass={expect_pass}. {notes}")
        self.out_dir_var.set(str(Path.home() / "Downloads" /
                                  f"tid_event_synthetic_{name}"))

    # ---- Server control --------------------------------------------------

    def _start_server(self):
        if self.server_reader and self.server_reader.running():
            messagebox.showinfo("Already running",
                                 "Stop the current server first.")
            return
        name = self.scenario_var.get()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showwarning("Bad port", "Port must be a number.")
            return

        self.server_port = port
        self.scenario_stations = []
        self.scenario_date = None
        cmd = ["python3", "-u", tool("mock_psws_server.py"),
               "--port", str(port), "--scenario", name]
        self._append_log(f"\n$ {' '.join(shlex.quote(c) for c in cmd)}\n\n")
        self.server_reader = StreamReader(
            self.log_widget, on_line=self._on_server_line,
            on_exit=self._on_server_exit)
        self.server_reader.start(cmd)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.server_status_label.configure(
            text="Starting -- generating scenario data...",
            foreground="#a06000")

    def _stop_server(self):
        if self.server_reader:
            self.server_reader.stop()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.server_status_label.configure(text="Stopped.",
                                            foreground="#666666")
        self.download_button.configure(state="disabled")

    def _on_server_line(self, line):
        # Parse the server's own startup banner rather than guess at
        # timing or re-derive station names independently -- these are
        # the exact strings mock_psws_server.py itself prints.
        m = re.search(r"Fake stations:\s*(.+)", line)
        if m:
            self.scenario_stations = [s.strip() for s in m.group(1).split(",")]
            self._populate_station_checkboxes()
        m = re.search(r"Test date:\s*(\S+)", line)
        if m:
            self.scenario_date = m.group(1)
        if "Listening on" in line:
            self.server_status_label.configure(
                text=f"Running on port {self.server_port}.",
                foreground="#206020")
            if self.scenario_stations:
                self.download_button.configure(state="normal")

    def _on_server_exit(self):
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.download_button.configure(state="disabled")
        self.server_status_label.configure(
            text="Stopped (process exited).", foreground="#666666")

    # ---- Station checkboxes ------------------------------------------

    def _populate_station_checkboxes(self):
        for child in self.stations_frame.winfo_children():
            child.destroy()
        self.station_vars = {}
        for name in self.scenario_stations:
            var = tk.BooleanVar(value=True)
            self.station_vars[name] = var
            ttk.Checkbutton(self.stations_frame, text=name, variable=var
                             ).pack(side="left", padx=(0, 10))

    # ---- Download --------------------------------------------------------

    def _browse_out_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.out_dir_var.set(d)

    def _download(self):
        if not self.server_reader or not self.server_reader.running():
            messagebox.showwarning("Server not running",
                                    "Start the server first.")
            return
        checked = [n for n, v in self.station_vars.items() if v.get()]
        if not checked:
            messagebox.showwarning("No stations", "Check at least one "
                                                    "station above.")
            return
        out_dir = self.out_dir_var.get().strip()
        if not out_dir:
            messagebox.showwarning("No directory", "Choose a save "
                                                     "location first.")
            return
        date = self.scenario_date or ""
        cmd = ["python3", "-u", tool("download_companions.py"),
               "--date", date, "--stations", *checked,
               "--out-dir", out_dir, "--no-cache"]
        env = dict(os.environ)
        env["PSWS_BASE_URL"] = f"http://127.0.0.1:{self.server_port}"
        self._append_log(f"\n$ export PSWS_BASE_URL={env['PSWS_BASE_URL']}\n"
                          f"$ {' '.join(shlex.quote(c) for c in cmd)}\n\n")
        self.download_button.configure(state="disabled")
        self.download_status_label.configure(text="Downloading...",
                                              foreground="#a06000")
        reader = StreamReader(self.log_widget, on_exit=self._on_download_done)
        self._download_reader = reader
        reader.start(cmd, env=env)

    def _on_download_done(self):
        self.download_button.configure(state="normal")
        self.download_status_label.configure(text="Done.",
                                              foreground="#206020")
        self.next_step_label.configure(
            text=f"Downloaded to: {self.out_dir_var.get()}\n"
                 f"Next: python3 tid_workflow_launcher.py -- browse to "
                 f"that directory there, or run tid_workflow.py directly "
                 f"with --event-dir {self.out_dir_var.get()} "
                 f"--my-station {self.scenario_stations[0] if self.scenario_stations else '<NAME>'}.")

    # ---- Misc --------------------------------------------------------

    def _launch_workflow_launcher(self):
        try:
            subprocess.Popen(["python3", tool("tid_workflow_launcher.py")],
                              cwd=TOOLS_DIR)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))

    def _append_log(self, text):
        self.log_widget.configure(state="normal")
        self.log_widget.insert(tk.END, text)
        self.log_widget.see(tk.END)

    def _copy_log(self):
        content = self.log_widget.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)

    def _clear_log(self):
        self.log_widget.delete("1.0", "end")

    def _on_close(self):
        # A left-running mock server is an orphaned background process
        # once this window closes -- stop it explicitly rather than
        # leaving it silently bound to the port.
        if self.server_reader and self.server_reader.running():
            self.server_reader.stop()
        self.destroy()


def main():
    if not _HAVE_SCENARIOS:
        print(f"WARNING: could not import mock_psws_server.py's "
              f"RECOMMENDED_SCENARIOS ({_SCENARIOS_IMPORT_ERROR}). "
              f"The scenario dropdown will be empty.")
    app = MockServerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
