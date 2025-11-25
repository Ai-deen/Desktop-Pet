import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import sys
import signal

from app.modules import MODULES


# Track running processes per module
running_procs = {}


def start_process(key, start_func, log_fn, status_update_fn):
    """
    Runs the module's start() function and stores the returned Popen process.
    """
    try:
        proc = start_func()
        if proc:
            running_procs[key] = proc
            log_fn(f" Started {MODULES[key]['label']} (PID {proc.pid})")
            status_update_fn(key, True)
        else:
            log_fn(f" {MODULES[key]['label']} did not return a subprocess.")
            status_update_fn(key, False)

    except Exception as e:
        log_fn(f" Failed to start {MODULES[key]['label']}: {e}")
        status_update_fn(key, False)


def stop_process(key, log_fn, status_update_fn):
    """
    Stops a single running module if active.
    """
    proc = running_procs.get(key)
    if not proc:
        log_fn(f"{MODULES[key]['label']} is not running.")
        status_update_fn(key, False)
        return

    log_fn(f"→ Stopping {MODULES[key]['label']}...")

    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=2)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    running_procs.pop(key, None)
    log_fn(f" Stopped {MODULES[key]['label']}")
    status_update_fn(key, False)


def stop_all(log_fn, status_update_fn):
    for key in list(running_procs.keys()):
        stop_process(key, log_fn, status_update_fn)


class ModuleLauncherGUI:
    def __init__(self, root):
        self.root = root
        root.title("Focus System Launcher")
        root.geometry("500x520")
        root.resizable(False, False)

        ttk.Label(root, text="Focus System Launcher",
                  font=("Segoe UI", 18, "bold")).pack(pady=10)

        # container
        self.mod_frame = ttk.Frame(root)
        self.mod_frame.pack(pady=10)

        self.checkbox_vars = {}
        self.status_labels = {}

        # Build module rows
        for key, module in MODULES.items():
            row = ttk.Frame(self.mod_frame)
            row.pack(fill="x", pady=3)

            # checkbox
            var = tk.BooleanVar()
            chk = ttk.Checkbutton(row, text=module["label"], variable=var)
            chk.pack(side="left", padx=5)
            self.checkbox_vars[key] = var

            # status label
            status_lbl = ttk.Label(row, text="Stopped", foreground="red")
            status_lbl.pack(side="left", padx=10)
            self.status_labels[key] = status_lbl

            # start button
            ttk.Button(row, text="Start",
                       command=lambda k=key: self.start_one(k)).pack(side="right", padx=5)

            # stop button
            ttk.Button(row, text="Stop",
                       command=lambda k=key: self.stop_one(k)).pack(side="right")

        # Global buttons
        ttk.Button(root, text="Start Selected Modules",
                   command=self.start_selected).pack(pady=10)

        ttk.Button(root, text="Stop All Modules",
                   command=self.stop_all).pack(pady=5)

        ttk.Button(root, text="Close App",
                   command=self.close_launcher).pack(pady=5)

        # Log window
        self.log = tk.Text(root, width=60, height=10)
        self.log.pack(pady=10)
        self.log.insert("end", "Launcher ready.\n")

        # Window close handling
        root.protocol("WM_DELETE_WINDOW", self.close_launcher)

    def update_status(self, key, running: bool):
        if running:
            self.status_labels[key].config(text="Running", foreground="green")
        else:
            self.status_labels[key].config(text="Stopped", foreground="red")

    def log_msg(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    # ---- Individual actions ----
    def start_one(self, key):
        module = MODULES[key]
        self.log_msg(f"→ Starting {module['label']}...")
        threading.Thread(
            target=start_process,
            args=(key, module["start"], self.log_msg, self.update_status),
            daemon=True
        ).start()

    def stop_one(self, key):
        threading.Thread(
            target=stop_process,
            args=(key, self.log_msg, self.update_status),
            daemon=True
        ).start()

    # ---- Bulk actions ----
    def start_selected(self):
        self.log_msg("\nStarting selected modules...")

        for key, var in self.checkbox_vars.items():
            if var.get():
                self.start_one(key)

    def stop_all(self):
        self.log_msg("\nStopping all modules...")
        threading.Thread(
            target=stop_all,
            args=(self.log_msg, self.update_status),
            daemon=True
        ).start()

    def close_launcher(self):
        self.stop_all()
        self.root.after(500, self.root.destroy)


# ---- MAIN ----
if __name__ == "__main__":
    root = tk.Tk()
    app = ModuleLauncherGUI(root)
    root.mainloop()
