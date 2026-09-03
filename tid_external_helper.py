#!/usr/bin/env python3
"""
tid_external_helper.py -- setup helper for cross-checking a DOA result
against independent external data sources.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.1.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.1.0  Several real fixes found only by actually running this
          against a real event (19 January 2026), not by review --
          full detail in the main project CHANGELOG.md, summarized
          here:

          - GNSS TEC now calls fetch_madrigal_tec.py directly instead
            of routing through run_madrigal_tools.py --tool gnss,
            which never forwarded --doa-speed/--doa-azimuth-from at
            all -- every DOA-lag comparison column came back blank
            regardless of what was entered above, for every run, not
            just one.
          - lstid_repo_status() now also checks `import polars`, not
            just that the separate hamsci_LSTID_detection repo
            directory exists -- a real run got most of the way through
            a genuinely slow (but working) GNSS TEC step before
            failing on a missing dependency it could have flagged
            up front.
          - The output log went through three iterations before
            working: state="disabled" blocked copy, not just typing;
            a <Key>-binding meant to selectively allow only Ctrl+C/
            Ctrl+A through was confirmed live, twice, to be unreliable;
            settled on a fully normal (never disabled) widget plus an
            explicit right-click Copy/Select-All menu, since stock Tk
            Text widgets have no context menu at all. Still reported
            as clunky in practice, so three visible buttons (Copy All,
            Save to File..., Clear) were added above the log itself.
          - Added a Cancel button -- there was previously no way to
            abort a run in progress short of killing the GUI, even
            once a specific "hang" turned out to just be slow, real
            network I/O rather than actually stuck.

  v1.0.0  Initial version. Deliberately narrow scope, same principle
          as tid_intake_helper.py: this does NOT reimplement Kp/AE
          retrieval, GNSS TEC cross-correlation, or LSTID detection --
          it reads an event's own tid_workflow_event.json and (if
          present) tid_doa_result.json, lets the operator pick which
          of evaluate_external.py / run_madrigal_tools.py's two tools
          to run via checkboxes, and hands off to those real scripts
          exactly as documented in docs/EXTERNAL_EVALUATION.md.

          tid_doa_result.json (tid_doa.py v1.5.1+) means the DOA speed
          and bearing this needs don't have to be retyped by hand --
          restores the one genuine convenience lost when
          tid_dashboard.py was retired (v4.8.0), without bringing back
          the 2,983-line browser app it came attached to.

          The HamSCI LSTID Detection toolkit is a separate GitHub repo
          (https://github.com/HamSCI/hamsci_LSTID_detection), not part
          of this project -- its checkbox is disabled with a plain
          explanation if that repo isn't importable, rather than
          silently failing when "Run Selected" is clicked.

          SuperMAG SME/AE has no API this project uses -- it's browser
          -only per docs/EXTERNAL_EVALUATION.md's own "Manual
          Evaluation Sources" section, so it's a button that opens the
          URL, not a checkbox pretending to fetch anything.
"""

import json
import os
import shlex
import subprocess
import sys
import threading
import queue
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

TOOLS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOLS_DIR))

MADRIGAL_USER_FILE = Path.home() / ".config" / "psws" / "madrigal_user.json"
SUPERMAG_URL = "https://supermag.jhuapl.edu/indices/"


def tool(name):
    return str(TOOLS_DIR / name)


def load_event_config(event_dir):
    """Read tid_workflow_event.json for date/window/stations. Returns
    None if not found or unparseable -- caller falls back to manual
    entry rather than crashing."""
    p = Path(event_dir) / "tid_workflow_event.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def load_doa_result(event_dir):
    """Read tid_doa_result.json (tid_doa.py v1.5.1+). Returns None if
    not found -- an event that hasn't had DOA run yet, or was run
    with an older tid_doa.py, falls back to manual entry."""
    p = Path(event_dir) / "tid_doa_result.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def load_madrigal_user():
    if not MADRIGAL_USER_FILE.exists():
        return {}
    try:
        return json.loads(MADRIGAL_USER_FILE.read_text())
    except Exception:
        return {}


def save_madrigal_user(fullname, email, affiliation):
    MADRIGAL_USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    info = {
        "user_fullname": fullname,
        "user_email": email,
        "user_affiliation": affiliation,
    }
    MADRIGAL_USER_FILE.write_text(json.dumps(info, indent=2))
    return info


def lstid_repo_status():
    """Best-effort check for the separate hamsci_LSTID_detection repo
    AND its own dependencies -- not just that the repo directory
    exists. Found live: the repo can be cloned but missing a real
    dependency (polars) that only surfaces as a mid-run traceback
    after the GNSS TEC step has already spent real time completing --
    checking `import polars` here up front catches exactly that case
    before the operator commits to a run, instead of after.
    Returns (ok: bool, reason: str)."""
    default_repo = Path.home() / "hamsci_LSTID_detection"
    if not (default_repo.exists() and (default_repo / "config").exists()):
        return False, (
            f"Not found at {default_repo} -- see "
            f"docs/EXTERNAL_EVALUATION.md \u00a73 to install it "
            f"(separate repo, not part of this project)."
        )
    try:
        import polars  # noqa: F401
    except ImportError:
        return False, (
            f"Found at {default_repo}, but its 'polars' dependency "
            f"isn't installed in this Python environment. Fix: "
            f"pip install 'polars[rtcompat]' (see "
            f"docs/EXTERNAL_EVALUATION.md \u00a73 for why the "
            f"[rtcompat] variant specifically, on some CPUs)."
        )
    return True, ("Amateur radio spot data (RBN/PSKReporter/WSPRNet), "
                  "several week latency.")


def make_readonly_but_copyable(text_widget):
    """Leave the widget in "normal" state, with NO custom key bindings
    at all. state="disabled" (the usual way to make a Text widget
    read-only) also blocks selection and Ctrl+C, not just typing --
    real friction when the log contains a URL or exact command the
    operator wants to copy out. An earlier version of this tried to
    selectively block only typing via a <Key> binding while explicitly
    allowing Ctrl+C/Ctrl+A through -- confirmed live, twice, that this
    is unreliable: a generic <Key> handler doesn't reliably see
    Control-modified events the way a physical keypress does, and
    separate specific bindings for <Control-c>/<Control-a> didn't
    reliably take precedence either. Rather than ship a third unverified
    guess, this widget simply allows typing too now -- nothing in this
    file ever reads the log widget's own content back for any logic,
    so accidental typing into a passive scrollback log has zero
    functional consequence, only a guaranteed, completely standard,
    zero-custom-code Tk Text widget's selection/copy/navigation
    behavior.

    Still reported as not copyable even with the above fully vanilla --
    the real remaining gap is almost certainly that stock Tk Text
    widgets have NO right-click context menu at all, and right-click
    -> Copy is the single most universal way people expect to copy
    text in any GUI application (more so than Ctrl+C, and far more
    than X11's separate select-to-copy/middle-click-to-paste PRIMARY
    selection convention, which works automatically here but isn't
    what most people reach for first). Explicit right-click menu
    added below so copying doesn't depend on guessing which
    convention the operator expects."""
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


class StreamingRunner:
    """Runs a queue of commands sequentially in a background thread,
    streaming combined stdout/stderr into a Tk text widget. Adapted
    from tid_intake_helper.py's StreamingRunner -- kept as a separate
    copy rather than a shared import, so each GUI tool stays
    independently runnable without cross-file coupling, matching this
    project's existing convention for these small Tkinter helpers.
    """

    def __init__(self, text_widget, on_all_done=None):
        self.text_widget = text_widget
        self.on_all_done = on_all_done
        self._queue = queue.Queue()
        self._proc = None
        self._commands = []
        self._index = 0

    def running(self):
        return self._proc is not None and self._proc.poll() is None

    def cancel(self):
        """Terminate the currently-running subprocess and stop the
        remaining queued commands. Added because a genuinely slow or
        stuck external network call (Madrigal, geomagnetic indices)
        previously had no way to abort short of killing the whole GUI
        -- even once confirmed not actually stuck in one real case,
        that's still a real gap for the next one that IS stuck."""
        self._commands = []  # don't start any further queued commands
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
        self._append("\n[cancelled by user]\n")

    def start(self, commands):
        """commands: list of (label, cmd_list) tuples, run in order."""
        if self.running():
            return False
        self._commands = commands
        self._index = 0
        self.text_widget.delete("1.0", tk.END)
        self._run_next()
        return True

    def _run_next(self):
        if self._index >= len(self._commands):
            if self.on_all_done:
                self.on_all_done()
            return
        label, cmd = self._commands[self._index]
        self._append(f"\n{'='*60}\n{label}\n{'='*60}\n"
                      f"$ {' '.join(shlex.quote(c) for c in cmd)}\n\n")
        thread = threading.Thread(target=self._run, args=(cmd,), daemon=True)
        thread.start()
        self.text_widget.after(100, self._poll)

    def _run(self, cmd):
        try:
            self._proc = subprocess.Popen(
                cmd, cwd=TOOLS_DIR, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            for line in self._proc.stdout:
                self._queue.put(line)
            self._proc.wait()
            self._queue.put(f"\n[exit code {self._proc.returncode}]\n")
        except Exception as e:
            self._queue.put(f"\n[failed to run: {e}]\n")
        finally:
            self._queue.put(None)  # sentinel: this command done

    def _append(self, text):
        # Real bug found live: this used to wrap insert() in
        # configure(state="normal"/"disabled") pairs, which is the
        # standard way to make a Text widget read-only -- but
        # state="disabled" also blocks text SELECTION and copy in Tk,
        # not just typing, which meant there was no way to copy a
        # URL or command straight out of the log. The widget is left
        # permanently in "normal" state instead (see
        # _make_readonly_but_copyable), with typing blocked by a key
        # binding that still allows selection, arrow-key navigation,
        # and Ctrl+C/Ctrl+A.
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
        except queue.Empty:
            pass
        if done:
            self._proc = None
            self._index += 1
            self._run_next()
        else:
            self.text_widget.after(100, self._poll)


class ExternalHelper(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TID External Evaluation Helper -- psws-drf-tid-tools")
        self.geometry("860x780")
        self.event_config = None
        self.doa_result = None
        self._build_ui()

    # ---- UI construction ---------------------------------------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # Event directory
        f1 = ttk.LabelFrame(self, text="1. Event directory")
        f1.pack(fill="x", **pad)
        self.event_dir_var = tk.StringVar()
        row = ttk.Frame(f1)
        row.pack(fill="x", padx=6, pady=4)
        ttk.Entry(row, textvariable=self.event_dir_var).pack(
            side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse...", command=self._browse_event_dir
                   ).pack(side="left", padx=4)
        ttk.Button(row, text="Load", command=self._load_event
                   ).pack(side="left")
        self.event_info_label = ttk.Label(
            f1, text="Not loaded yet.", foreground="#666666",
            wraplength=800, justify="left")
        self.event_info_label.pack(fill="x", padx=6, pady=(0, 6))

        # DOA result
        f2 = ttk.LabelFrame(self, text="2. DOA result (for TEC/Kp/AE comparison)")
        f2.pack(fill="x", **pad)
        self.doa_status_label = ttk.Label(
            f2, text="Load an event directory first.", foreground="#666666",
            wraplength=800, justify="left")
        self.doa_status_label.pack(anchor="w", padx=6, pady=(4, 0), fill="x")
        row2 = ttk.Frame(f2)
        row2.pack(fill="x", padx=6, pady=4)
        ttk.Label(row2, text="Speed (m/s):").pack(side="left")
        self.speed_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.speed_var, width=10).pack(
            side="left", padx=(2, 12))
        ttk.Label(row2, text="Azimuth FROM (deg true):").pack(side="left")
        self.azimuth_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.azimuth_var, width=10).pack(
            side="left", padx=2)

        # Madrigal user info
        f3 = ttk.LabelFrame(
            self, text="3. Madrigal registration (free, required by GNSS "
                        "TEC + LSTID -- saved for reuse)")
        f3.pack(fill="x", **pad)
        grid = ttk.Frame(f3)
        grid.pack(fill="x", padx=6, pady=4)
        self.mad_name_var = tk.StringVar()
        self.mad_email_var = tk.StringVar()
        self.mad_affil_var = tk.StringVar()
        for i, (label, var) in enumerate([
            ("Full name:", self.mad_name_var),
            ("Email:", self.mad_email_var),
            ("Affiliation:", self.mad_affil_var),
        ]):
            ttk.Label(grid, text=label, width=12).grid(
                row=i, column=0, sticky="w", pady=2)
            ttk.Entry(grid, textvariable=var, width=40).grid(
                row=i, column=1, sticky="w", pady=2)
        self._load_madrigal_fields()
        ttk.Button(f3, text="Save for future use",
                   command=self._save_madrigal_fields
                   ).pack(anchor="e", padx=6, pady=(0, 6))

        # Checkboxes
        f4 = ttk.LabelFrame(self, text="4. Which sources to check")
        f4.pack(fill="x", **pad)
        self.want_kpae = tk.BooleanVar(value=True)
        self.want_gnss = tk.BooleanVar(value=True)
        self.want_lstid = tk.BooleanVar(value=False)
        self.want_download = tk.BooleanVar(value=False)

        def _checkbox_with_note(parent, var, short, note, enabled=True):
            row = ttk.Frame(parent)
            row.pack(fill="x", padx=6, pady=(4, 0))
            cb = ttk.Checkbutton(row, text=short, variable=var,
                                  state="normal" if enabled else "disabled")
            cb.pack(anchor="w")
            ttk.Label(row, text=f"    {note}", foreground="#666666",
                      wraplength=780, justify="left"
                      ).pack(anchor="w", pady=(0, 4))
            return row

        _checkbox_with_note(
            f4, self.want_kpae,
            "Kp + AE geomagnetic indices (evaluate_external.py)",
            "Open data, no registration, no upload delay.")

        _checkbox_with_note(
            f4, self.want_gnss,
            "GNSS TEC cross-correlation (fetch_madrigal_tec.py)",
            "2\u20134 week upload latency -- check availability before "
            "expecting results.")

        lstid_ok, lstid_reason = lstid_repo_status()
        lstid_row = _checkbox_with_note(
            f4, self.want_lstid,
            "HamSCI LSTID Detection (run_madrigal_tools.py --tool lstid)",
            lstid_reason,
            enabled=lstid_ok)
        if not lstid_ok:
            for child in lstid_row.winfo_children():
                if isinstance(child, ttk.Label):
                    child.configure(foreground="#a04040")

        _checkbox_with_note(
            f4, self.want_download,
            "Download missing HF spot / TEC data if needed (--download)",
            "Slower -- only matters for GNSS TEC / LSTID, ignored by Kp/AE.")

        # SuperMAG (manual, browser-only)
        f5 = ttk.LabelFrame(self, text="5. SuperMAG SME/AE (manual, browser only)")
        f5.pack(fill="x", **pad)
        row5 = ttk.Frame(f5)
        row5.pack(fill="x", padx=6, pady=4)
        ttk.Label(
            row5, text="No API used by this project -- opens the site; "
                       "check SME/SML, event date \u22126h to +3h.",
            foreground="#666666", wraplength=600, justify="left"
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(row5, text="Open SuperMAG",
                   command=lambda: webbrowser.open(SUPERMAG_URL)
                   ).pack(side="right")

        # Run
        run_row = ttk.Frame(self)
        run_row.pack(fill="x", **pad)
        self.run_button = ttk.Button(
            run_row, text="Run Selected", command=self._run_selected)
        self.run_button.pack(side="left")
        self.cancel_button = ttk.Button(
            run_row, text="Cancel", command=self._cancel_run,
            state="disabled")
        self.cancel_button.pack(side="left", padx=(6, 0))
        ttk.Label(
            run_row, text="Runs sequentially; each tool's own real output "
                          "streams below. Real network calls (Madrigal, "
                          "geomagnetic indices) can legitimately take a "
                          "while -- that's not necessarily stuck.",
            foreground="#666666", wraplength=500, justify="left"
        ).pack(side="left", padx=8)

        # Log pane
        f6 = ttk.LabelFrame(self, text="Output")
        f6.pack(fill="both", expand=True, **pad)

        log_buttons = ttk.Frame(f6)
        log_buttons.pack(fill="x", padx=6, pady=(6, 0))
        ttk.Button(log_buttons, text="Copy All",
                   command=self._copy_log).pack(side="left")
        ttk.Button(log_buttons, text="Save to File...",
                   command=self._save_log).pack(side="left", padx=(6, 0))
        ttk.Button(log_buttons, text="Clear",
                   command=self._clear_log).pack(side="left", padx=(6, 0))
        ttk.Label(log_buttons, text="(or right-click in the box below for "
                                     "Copy / Select All)",
                  foreground="#666666").pack(side="left", padx=8)

        self.log_widget = scrolledtext.ScrolledText(
            f6, height=18, font=("Courier", 10))
        make_readonly_but_copyable(self.log_widget)
        self.log_widget.pack(fill="both", expand=True, padx=6, pady=6)
        self.runner = StreamingRunner(self.log_widget, self._on_all_done)

    def _copy_log(self):
        content = self.log_widget.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(content)

    def _save_log(self):
        content = self.log_widget.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("Nothing to save", "The output is empty.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="tid_external_helper_output.txt")
        if path:
            Path(path).write_text(content)

    def _clear_log(self):
        self.log_widget.delete("1.0", "end")

    # ---- Event / DOA loading ------------------------------------------

    def _browse_event_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.event_dir_var.set(d)
            self._load_event()

    def _load_event(self):
        event_dir = self.event_dir_var.get().strip()
        if not event_dir:
            return
        self.event_config = load_event_config(event_dir)
        if self.event_config is None:
            self.event_info_label.configure(
                text=f"No tid_workflow_event.json found in {event_dir} -- "
                     f"run tid_workflow.py through at least Step 8 first.",
                foreground="#a04040")
        else:
            stations = [s.get("name", "?")
                        for s in self.event_config.get("stations", [])]
            self.event_info_label.configure(
                text=f"Event window: {self.event_config.get('event_start_utc')} "
                     f"to {self.event_config.get('event_end_utc')}\n"
                     f"Stations: {', '.join(stations)}",
                foreground="#206020")

        self.doa_result = load_doa_result(event_dir)
        if self.doa_result is None:
            self.doa_status_label.configure(
                text="No tid_doa_result.json found -- enter speed/azimuth "
                     "manually below, or run tid_doa.py first "
                     "(v1.5.1+ writes this automatically).",
                foreground="#a04040")
        else:
            self.speed_var.set(f"{self.doa_result['speed_m_s']:.1f}")
            self.azimuth_var.set(f"{self.doa_result['azimuth_from_deg']:.1f}")
            computed_at = self.doa_result.get("computed_at_utc", "?")
            self.doa_status_label.configure(
                text=f"Auto-filled from tid_doa_result.json "
                     f"(computed {computed_at}). Edit below if you want "
                     f"to compare against a different combination's result.",
                foreground="#206020")

    def _load_madrigal_fields(self):
        info = load_madrigal_user()
        self.mad_name_var.set(info.get("user_fullname", ""))
        self.mad_email_var.set(info.get("user_email", ""))
        self.mad_affil_var.set(info.get("user_affiliation", ""))

    def _save_madrigal_fields(self):
        name = self.mad_name_var.get().strip()
        email = self.mad_email_var.get().strip()
        affil = self.mad_affil_var.get().strip()
        if not name or not email:
            messagebox.showwarning(
                "Missing info", "Full name and email are required by the "
                                "Madrigal API.")
            return
        save_madrigal_user(name, email, affil)
        messagebox.showinfo(
            "Saved", f"Saved to {MADRIGAL_USER_FILE} for reuse next time.")

    # ---- Running selected tools -----------------------------------------

    def _run_selected(self):
        event_dir = self.event_dir_var.get().strip()
        if not event_dir or self.event_config is None:
            messagebox.showwarning(
                "No event loaded", "Load a valid event directory first.")
            return

        commands = []

        if self.want_kpae.get():
            speed = self.speed_var.get().strip()
            azimuth = self.azimuth_var.get().strip()
            if not speed or not azimuth:
                messagebox.showwarning(
                    "Missing DOA result",
                    "Speed and azimuth are required for the Kp/AE check "
                    "-- enter them manually or run tid_doa.py first.")
                return
            out_dir = str(Path(event_dir) / "runs" / "external_evaluations")
            commands.append((
                "Kp + AE geomagnetic indices",
                ["python3", tool("evaluate_external.py"),
                 "--date", self.event_config["event_start_utc"][:10],
                 "--event-start", self.event_config["event_start_utc"],
                 "--event-end", self.event_config["event_end_utc"],
                 "--speed-m-s", speed,
                 "--azimuth-from", azimuth,
                 "--output-dir", out_dir],
            ))

        if self.want_gnss.get() or self.want_lstid.get():
            name = self.mad_name_var.get().strip()
            email = self.mad_email_var.get().strip()
            affil = self.mad_affil_var.get().strip() or "Independent"
            if not name or not email:
                messagebox.showwarning(
                    "Missing Madrigal registration",
                    "Full name and email are required for GNSS TEC / "
                    "LSTID -- fill in section 3 and click 'Save for "
                    "future use' first.")
                return

            if self.want_gnss.get():
                # Called directly, NOT via run_madrigal_tools.py --tool
                # gnss. Real gap found live: run_madrigal_tools.py's own
                # run_gnss_tec() never forwards --doa-speed/
                # --doa-azimuth-from to fetch_madrigal_tec.py at all --
                # confirmed directly in its source, not guessed from the
                # symptom -- so every DOA-lag comparison column in the
                # report came back "---" regardless of what was entered
                # above. Calling the real script directly here, with the
                # values this GUI already collected, is what actually
                # wires that comparison through.
                speed = self.speed_var.get().strip()
                azimuth = self.azimuth_var.get().strip()
                gnss_cmd = [
                    "python3", tool("fetch_madrigal_tec.py"),
                    "--config", str(Path(event_dir) / "tid_workflow_event.json"),
                    "--user-name", name,
                    "--user-email", email,
                    "--user-affiliation", affil,
                    "--output-dir", str(Path(event_dir) / "gnss_tec"),
                ]
                if speed and azimuth:
                    gnss_cmd += ["--doa-speed", speed,
                                 "--doa-azimuth-from", azimuth]
                    gnss_label = "GNSS TEC cross-correlation"
                else:
                    gnss_label = (
                        "GNSS TEC cross-correlation (no DOA speed/azimuth "
                        "entered -- DOA lag comparison columns will be "
                        "blank; the TEC cross-correlation itself still runs)")
                commands.append((gnss_label, gnss_cmd))

            if self.want_lstid.get():
                lstid_cmd = ["python3", tool("run_madrigal_tools.py"),
                             "--event", event_dir, "--tool", "lstid"]
                if self.want_download.get():
                    lstid_cmd.append("--download")
                commands.append(("HamSCI LSTID Detection", lstid_cmd))

        if not commands:
            messagebox.showinfo("Nothing selected",
                                 "Check at least one source above.")
            return

        self.run_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.runner.start(commands)

    def _cancel_run(self):
        self.runner.cancel()
        self.cancel_button.configure(state="disabled")
        self.run_button.configure(state="normal")

    def _on_all_done(self):
        self.run_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")


def main():
    app = ExternalHelper()
    app.mainloop()


if __name__ == "__main__":
    main()
