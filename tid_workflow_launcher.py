#!/usr/bin/env python3
"""
tid_workflow_launcher.py -- configure and launch tid_workflow.py against
an already-set-up event directory, without retyping the command by hand.

Part of psws-drf-tid-tools (https://github.com/N6RFM/psws-drf-tid-tools)
Created by N6RFM with help from Claude AI.
Version: 1.3.0
License: MIT (do whatever you want, no warranty).

Change log:
  v1.3.0  Echoes a real user@host:dir$ prompt line (bash's own default
          PS1 format, built from the operator's actual username,
          hostname, and directory) before running the command --
          jumping straight into a program's own output with no
          visible context of what's running or from where felt
          unsettling compared to a normal terminal session.

  v1.2.0  Fixed the launched terminal closing the instant
          tid_workflow.py finished -- whether it succeeded, failed, or
          crashed -- making any error message or the final DOA result
          impossible to actually read. Now runs the command through
          `bash -c`, then prints a clear "finished, press Enter to
          close" message and pauses on `read` before the shell exits.

  v1.1.0  Fixed "Launch in New Terminal" opening a visibly different,
          unstyled terminal (bare xterm) instead of the operator's
          actual default -- found live: the hardcoded candidate list
          didn't include mate-terminal (Linux Mint's default), so it
          fell all the way through to xterm as the last resort. Now
          checks the Debian/Ubuntu/Mint "alternatives" system first
          (x-terminal-emulator, a symlink to whatever the operator has
          actually configured as their default terminal) before
          falling back to the hardcoded list, which also now includes
          mate-terminal.

  v1.0.0  Initial version. Deliberately does NOT try to run
          tid_workflow.py captured/piped through a log pane the way
          tid_external_helper.py's batch tools are -- tid_workflow.py
          is fully interactive (input() prompts, tid_quicklook.py's
          drag-select window, tid_spect_click.py's wave-fit clicking),
          and piping its stdout/stdin through Python would break all
          of that. Follows the same deliberate pattern already
          established in tid_intake_helper.py: generate the correct
          command and copy it to the clipboard, rather than attempt a
          captured subprocess. A best-effort "Launch in New Terminal"
          button is offered alongside as a convenience -- tries common
          terminal emulators and says plainly if none are found,
          rather than failing silently.

          Reuses tid_workflow.py's own discover_stations() directly
          (same principle as tid_intake_helper.py importing
          KNOWN_STATIONS from it) so the detected station list is
          guaranteed to match what tid_workflow.py itself will find
          when actually launched, not a second, potentially-drifting
          implementation of the same directory-scanning logic.

          Built specifically because --my-station is easy to forget
          as a bare CLI flag, and forgetting it doesn't fail loudly --
          tid_workflow.py silently falls back to alphabetical
          directory order for the keystone instead, a real bug found
          and documented earlier in this same project. Making keystone
          selection an explicit, visible, always-populated GUI choice
          removes that failure mode entirely.
"""

import os
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

TOOLS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(TOOLS_DIR))

try:
    from tid_workflow import discover_stations
except Exception:
    # Helper should still be usable even if tid_workflow.py can't be
    # imported for some reason -- falls back to a plain directory
    # listing instead of the real DRF-validated discovery.
    discover_stations = None


def tool(name):
    return str(TOOLS_DIR / name)


def fallback_discover_stations(event_dir):
    """Plain directory listing, used only if importing the real
    discover_stations() from tid_workflow.py failed above."""
    p = Path(event_dir)
    if not p.is_dir():
        return []
    return sorted(d for d in p.iterdir() if d.is_dir())


def find_terminal_emulator():
    """Best-effort search for a terminal emulator to launch into.
    Returns (name, argv_prefix) or None if none found -- callers must
    handle None explicitly rather than assume one exists.

    Checks the Debian/Ubuntu/Mint "alternatives" system first --
    x-terminal-emulator is a symlink to whatever the user has actually
    configured as their default terminal, carrying their real theme
    and profile. Found live: without this, the hardcoded candidate
    list below (which didn't include mate-terminal, Linux Mint's
    default) fell all the way through to a bare xterm -- a genuinely
    different, unstyled console instead of matching the one the
    operator already has open. x-terminal-emulator's own convention is
    `-e`, same as most of the hardcoded fallbacks."""
    if shutil.which("x-terminal-emulator"):
        return "x-terminal-emulator", ["x-terminal-emulator", "-e"]
    candidates = [
        ("gnome-terminal", ["gnome-terminal", "--"]),
        ("mate-terminal", ["mate-terminal", "-e"]),
        ("konsole", ["konsole", "-e"]),
        ("xfce4-terminal", ["xfce4-terminal", "-e"]),
        ("xterm", ["xterm", "-e"]),
    ]
    for name, prefix in candidates:
        if shutil.which(name):
            return name, prefix
    return None


class WorkflowLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TID Workflow Launcher -- psws-drf-tid-tools")
        self.geometry("820x680")
        self.station_vars = {}   # name -> BooleanVar
        self.keystone_var = tk.StringVar()
        self._build_ui()

    # ---- UI construction ---------------------------------------------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # Event directory
        f1 = ttk.LabelFrame(self, text="1. Event directory (already set up)")
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
            wraplength=780, justify="left")
        self.event_info_label.pack(fill="x", padx=6, pady=(0, 6))

        # Stations + keystone
        f2 = ttk.LabelFrame(
            self, text="2. Stations to include, and which one is the keystone")
        f2.pack(fill="both", **pad)
        ttk.Label(
            f2, text="The keystone is processed first -- its window sets "
                     "what every other station is measured against. "
                     "Usually your own station.",
            foreground="#666666", wraplength=780, justify="left"
        ).pack(anchor="w", padx=6, pady=(4, 0))
        self.stations_frame = ttk.Frame(f2)
        self.stations_frame.pack(fill="x", padx=6, pady=6)
        self.no_stations_label = ttk.Label(
            self.stations_frame, text="Load an event directory to see "
                                       "detected stations.",
            foreground="#666666")
        self.no_stations_label.pack(anchor="w")

        # Options
        f3 = ttk.LabelFrame(self, text="3. Options")
        f3.pack(fill="x", **pad)
        row3 = ttk.Frame(f3)
        row3.pack(fill="x", padx=6, pady=4)
        ttk.Label(row3, text="--max-lag (minutes):").pack(side="left")
        self.max_lag_var = tk.StringVar(value="30")
        ttk.Entry(row3, textvariable=self.max_lag_var, width=6).pack(
            side="left", padx=(4, 12))
        ttk.Label(row3, text="~1/3 of the expected TID period "
                             "(e.g. 30 for a ~90 min LSTID).",
                  foreground="#666666").pack(side="left")

        self.resume_var = tk.BooleanVar(value=False)
        self.resume_check = ttk.Checkbutton(
            f3, text="--resume (continue from saved progress)",
            variable=self.resume_var)
        self.resume_check.pack(anchor="w", padx=6, pady=(0, 4))
        self.resume_note = ttk.Label(
            f3, text="", foreground="#206020", wraplength=780, justify="left")
        self.resume_note.pack(anchor="w", padx=6, pady=(0, 4))

        # Command preview
        f4 = ttk.LabelFrame(self, text="4. Command")
        f4.pack(fill="both", expand=True, **pad)
        self.command_widget = scrolledtext.ScrolledText(
            f4, height=6, font=("Courier", 10))
        self.command_widget.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        btn_row = ttk.Frame(f4)
        btn_row.pack(fill="x", padx=6, pady=6)
        ttk.Button(btn_row, text="Update Command",
                   command=self._update_command).pack(side="left")
        ttk.Button(btn_row, text="Copy Command",
                   command=self._copy_command).pack(side="left", padx=(6, 0))
        ttk.Button(btn_row, text="Launch in New Terminal",
                   command=self._launch_in_terminal
                   ).pack(side="left", padx=(6, 0))
        ttk.Label(
            btn_row, text="Copy is the reliable option everywhere. Launch "
                          "is best-effort and depends on a terminal "
                          "emulator being found on this system.",
            foreground="#666666", wraplength=380, justify="left"
        ).pack(side="left", padx=8)

    # ---- Event loading --------------------------------------------------

    def _browse_event_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.event_dir_var.set(d)
            self._load_event()

    def _load_event(self):
        event_dir = self.event_dir_var.get().strip()
        if not event_dir or not Path(event_dir).is_dir():
            messagebox.showwarning("Not found", "Enter or browse to a "
                                                 "real directory first.")
            return

        finder = discover_stations if discover_stations else fallback_discover_stations
        try:
            dirs = finder(event_dir) or []
        except Exception as e:
            messagebox.showerror("Discovery failed", str(e))
            return

        for child in self.stations_frame.winfo_children():
            child.destroy()
        self.station_vars = {}

        if not dirs:
            ttk.Label(
                self.stations_frame,
                text="No DRF station directories found here.",
                foreground="#a04040").pack(anchor="w")
        else:
            for d in dirs:
                name = d.name.upper()
                var = tk.BooleanVar(value=True)
                self.station_vars[name] = var
                ttk.Checkbutton(
                    self.stations_frame, text=name, variable=var,
                    command=self._refresh_keystone_options
                ).pack(anchor="w")

        self.event_info_label.configure(
            text=f"Found {len(dirs)} station folder(s) in {event_dir}.",
            foreground="#206020" if dirs else "#a04040")

        self._refresh_keystone_options()

        state_file = Path(event_dir) / "tid_workflow_state.json"
        if state_file.exists():
            self.resume_var.set(True)
            self.resume_note.configure(
                text=f"Found {state_file.name} -- a prior session exists "
                     f"here. --resume checked by default.")
        else:
            self.resume_var.set(False)
            self.resume_note.configure(text="")

        self._update_command()

    def _refresh_keystone_options(self):
        # Rebuild the keystone radio list whenever which stations are
        # checked changes -- the keystone must always be one of the
        # currently-checked stations, never an unchecked or removed one.
        if not hasattr(self, "_keystone_frame"):
            self._keystone_label = ttk.Label(
                self.stations_frame, text="Keystone:",
                font=("TkDefaultFont", 10, "bold"))
            self._keystone_frame = ttk.Frame(self.stations_frame)
        self._keystone_label.pack(anchor="w", pady=(8, 0))
        self._keystone_frame.pack(anchor="w")
        for child in self._keystone_frame.winfo_children():
            child.destroy()

        checked = [name for name, var in self.station_vars.items() if var.get()]
        if not checked:
            ttk.Label(self._keystone_frame, text="(check at least one "
                                                  "station above)",
                      foreground="#a04040").pack(anchor="w")
            self.keystone_var.set("")
            return

        if self.keystone_var.get() not in checked:
            self.keystone_var.set(checked[0])
        for name in checked:
            ttk.Radiobutton(
                self._keystone_frame, text=name, value=name,
                variable=self.keystone_var,
                command=self._update_command
            ).pack(side="left", padx=(0, 12))

    # ---- Command construction -------------------------------------------

    def _build_command(self):
        event_dir = self.event_dir_var.get().strip()
        checked = [name for name, var in self.station_vars.items() if var.get()]
        keystone = self.keystone_var.get()
        max_lag = self.max_lag_var.get().strip()

        if not event_dir or not checked or not keystone:
            return None
        try:
            float(max_lag)
        except ValueError:
            return None

        cmd = [
            "python3", tool("tid_workflow.py"),
            "--event-dir", event_dir,
            "--stations", ",".join(checked),
            "--my-station", keystone,
            "--max-lag", max_lag,
        ]
        if self.resume_var.get():
            cmd.append("--resume")
        return cmd

    def _format_command(self, cmd):
        """Format as one flag+value pair per line, matching how every
        other command example in this project's own docs is shown --
        found live that joining every individual token with its own
        line break (the first version of this) produced an ugly,
        unfamiliar wall of single-word lines instead."""
        lines = [cmd[0], cmd[1]]  # "python3", the script path
        i = 2
        while i < len(cmd):
            if cmd[i].startswith("--") and i + 1 < len(cmd) and \
                    not cmd[i + 1].startswith("--"):
                lines.append(f"{cmd[i]} {shlex.quote(cmd[i + 1])}")
                i += 2
            else:
                lines.append(cmd[i])
                i += 1
        return " \\\n    ".join(lines)

    def _update_command(self):
        cmd = self._build_command()
        self.command_widget.delete("1.0", "end")
        if cmd is None:
            self.command_widget.insert(
                "1.0", "(load an event directory, check at least one "
                       "station, and pick a keystone first)")
        else:
            self.command_widget.insert("1.0", self._format_command(cmd))

    def _copy_command(self):
        cmd = self._build_command()
        if cmd is None:
            messagebox.showwarning("Not ready", "Load an event directory, "
                                    "check at least one station, and pick "
                                    "a keystone first.")
            return
        text = " ".join(shlex.quote(c) for c in cmd)
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Command copied to clipboard -- "
                                       "paste it into a terminal to run.")

    def _launch_in_terminal(self):
        cmd = self._build_command()
        if cmd is None:
            messagebox.showwarning("Not ready", "Load an event directory, "
                                    "check at least one station, and pick "
                                    "a keystone first.")
            return
        found = find_terminal_emulator()
        if not found:
            messagebox.showwarning(
                "No terminal emulator found",
                "Couldn't find gnome-terminal, konsole, xfce4-terminal, "
                "or xterm on this system. Use 'Copy Command' instead and "
                "paste it into whatever terminal you normally use.")
            return
        name, prefix = found
        # Run through bash explicitly, then pause with a visible
        # prompt before the shell exits -- without this, the terminal
        # closes the instant tid_workflow.py finishes, whether it
        # succeeded, failed, or crashed, making any error message or
        # the final DOA result impossible to actually read. Passing
        # bash/-c/the-full-string as three separate argv elements
        # (not one shell-joined string) keeps this working regardless
        # of how the specific terminal emulator's own -e/-- parsing
        # differs.
        #
        # Also echoes a real user@host:dir$ prompt line before running
        # the command -- jumping straight into a program's own output
        # with no visible context of what's running or from where felt
        # unsettling compared to a normal terminal session. Built from
        # the operator's actual username/hostname/directory (bash's
        # own default PS1 format), not a placeholder.
        user = os.environ.get("USER") or os.environ.get("LOGNAME") or "user"
        host = socket.gethostname().split(".")[0]
        home = str(Path.home())
        cwd_display = str(TOOLS_DIR)
        if cwd_display.startswith(home):
            cwd_display = "~" + cwd_display[len(home):]
        prompt_line = f"{user}@{host}:{cwd_display}$"
        inner = " ".join(shlex.quote(c) for c in cmd)
        shell_cmd = (
            f"echo {shlex.quote(prompt_line + ' ' + inner)}; "
            f"{inner}; "
            f"echo; "
            f"echo '--- tid_workflow.py finished. Press Enter to close this window. ---'; "
            f"read"
        )
        try:
            subprocess.Popen(prefix + ["bash", "-c", shell_cmd], cwd=TOOLS_DIR)
        except Exception as e:
            messagebox.showerror(
                "Launch failed", f"Tried {name}, but it failed: {e}\n\n"
                                  f"Use 'Copy Command' instead.")


def main():
    app = WorkflowLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
