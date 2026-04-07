# focus_pet_timer.py (defensive, logs exceptions, keeps mainloop alive)
import tkinter as tk
import time
import threading
import pandas as pd
from datetime import datetime
import os
import traceback
import logging
import ctypes
import ctypes.wintypes
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
from app.utils.log_file import log_file


# --- Base Paths ---
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")

CSV_PATH = os.path.join(DATA_DIR, "focus_timetable.csv")
MSG_FILE = os.path.join(DATA_DIR, "focus_ui_message.txt")
LOG_PATH = log_file("focus_timer_debug.log")


# --- Logging setup ---
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def log_exc(prefix="Uncaught exception"):
    logging.error(prefix)
    logging.error(traceback.format_exc())

class FocusTimerUI:
    def __init__(self):
        # Create root
        self.root = tk.Tk()
        self.root.title("FocusPet Timer")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1c1c1c")

        # Replace Tk's exception handler so after-callback errors don't kill the app
        def tk_report_callback_exception(exc, val, tb):
            logging.error("Exception in Tk callback:\n%s", "".join(traceback.format_exception(exc, val, tb)))
            # show a brief message in UI without raising
            try:
                self.safe(lambda: self.msg_label.config(text="(Error in UI — check logs)"))
            except Exception:
                pass
        # assign handler
        self.root.report_callback_exception = tk_report_callback_exception

        self.is_mini = False
        self.full_geometry = None

        # drag logic
        self.offset_x = 0
        self.offset_y = 0
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        # double-click toggle
        self.root.bind("<Double-1>", self.toggle_mini_mode)

        # ---------------- UI ELEMENTS ------------------
        self.task_label = tk.Label(self.root, text="Waiting for next task...",
                                   font=("Segoe UI", 11, "bold"),
                                   fg="white", bg="#1c1c1c")
        self.task_label.pack(pady=3, padx=10)

        self.timer_label = tk.Label(self.root, text="--:--:--",
                                    font=("Consolas", 18, "bold"),
                                    fg="#00ff88", bg="#1c1c1c")
        self.timer_label.pack(pady=2)

        self.time_label = tk.Label(self.root, text="",
                                   font=("Segoe UI", 9),
                                   fg="#bbbbbb", bg="#1c1c1c")
        self.time_label.pack(pady=2)

        self.msg_label = tk.Label(self.root, text="",
                                  font=("Segoe UI", 9, "italic"),
                                  fg="#87cefa", bg="#1c1c1c")
        self.msg_label.pack(pady=3)

        self.todo_label = tk.Label(self.root, text="Today's To-Do:",
                                   font=("Segoe UI", 10, "underline"),
                                   fg="#ffcc00", bg="#1c1c1c")
        self.todo_label.pack(pady=(8, 0))

        self.todo_text = tk.Text(self.root, height=8, width=34,
                                 bg="#2b2b2b", fg="white",
                                 font=("Segoe UI", 9))
        self.todo_text.pack(pady=3)
        self.todo_text.configure(state="disabled")

        # -------------- Threads (safe) ---------------
        # start threads as daemon so they won't block exit, but they are all protected with try/except
        threading.Thread(target=self.thread_clock, daemon=True).start()
        threading.Thread(target=self.thread_watch_csv, daemon=True).start()
        threading.Thread(target=self.thread_watch_messages, daemon=True).start()

        # small watchdog that logs if mainloop terminates unexpectedly (runs in background)
        threading.Thread(target=self._watchdog_thread, daemon=True).start()

    # ============= DRAG HANDLERS ===================
    def start_move(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def do_move(self, event):
        try:
            x = self.root.winfo_pointerx() - self.offset_x
            y = self.root.winfo_pointery() - self.offset_y
            self.root.geometry(f"+{x}+{y}")
        except Exception:
            log_exc("Error during do_move")

    # ================ UI SAFE UPDATE HELPERS ==================
    def safe(self, func):
        """Run UI update on Tk main thread (non-throwing)."""
        try:
            self.root.after(0, func)
        except Exception:
            log_exc("safe() scheduling failed")

    # =============== CLOCK THREAD ======================
    def thread_clock(self):
        try:
            while True:
                now = datetime.now().strftime("%H:%M:%S")
                try:
                    self.safe(lambda: self.time_label.config(text=f"Current Time: {now}"))
                except Exception:
                    log_exc("Error scheduling clock update")
                time.sleep(1)
        except Exception:
            log_exc("thread_clock crashed")

    def format_hms(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def color_for_time(self, remaining):
        if remaining <= 120:
            return "#ff4444"
        elif remaining <= 600:
            return "#ffaa00"
        return "#00ff88"

    # ============ CSV WATCHER THREAD ====================
    def thread_watch_csv(self):
        last_task = ""
        try:
            while True:
                try:
                    if not os.path.isfile(CSV_PATH):
                        # if file missing, show helpful note and wait
                        logging.debug("CSV not found at %s", CSV_PATH)
                        self.safe(lambda: self.task_label.config(text="No timetable found"))
                        time.sleep(1)
                        continue

                    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
                    today = datetime.now().date().isoformat()
                    rows = df[df["Date"] == today]

                    # --- To-do list ---
                    todos = []
                    for _, r in rows.iterrows():
                        s = r.get("StartTime", "") or ""
                        e = r.get("EndTime", "") or ""
                        name = r.get("SlotName", "") or ""
                        status = r.get("Status", "") or ""
                        todos.append(f"- {s}–{e} | {name} [{status}]")
                    todo_str = "\n".join(todos)

                    def apply_todo():
                        try:
                            self.todo_text.configure(state="normal")
                            self.todo_text.delete(1.0, tk.END)
                            self.todo_text.insert(tk.END, todo_str)
                            self.todo_text.configure(state="disabled")
                        except Exception:
                            log_exc("apply_todo failed")

                    self.safe(apply_todo)

                    # --- Active slot detection ---
                    now = datetime.now()
                    active = None

                    for _, r in rows.iterrows():
                        st = r.get("StartTime", "") or ""
                        et = r.get("EndTime", "") or ""
                        if not st or not et:
                            continue
                        try:
                            start = datetime.strptime(st, "%H:%M").time()
                            end = datetime.strptime(et, "%H:%M").time()
                        except Exception:
                            continue

                        start_dt = datetime.combine(now.date(), start)
                        end_dt = datetime.combine(now.date(), end)

                        if start_dt <= now < end_dt:
                            active = (r, start_dt, end_dt)
                            break

                    if active:
                        r, start_dt, end_dt = active
                        remaining = (end_dt - now).total_seconds()

                        if last_task != r.get("SlotName", ""):
                            self.safe(lambda: self.task_label.config(text=f"Current: {r.get('SlotName','')}"))
                            last_task = r.get("SlotName", "")

                        color = self.color_for_time(remaining)
                        self.safe(lambda: self.timer_label.config(text=self.format_hms(remaining), fg=color))
                    else:
                        self.safe(lambda: self.task_label.config(text="No active slot"))
                        self.safe(lambda: self.timer_label.config(text="--:--:--", fg="#00ff88"))

                except Exception:
                    log_exc("thread_watch_csv inner loop error")

                time.sleep(1)
        except Exception:
            log_exc("thread_watch_csv crashed")

    # ========= MESSAGE WATCHER THREAD =====================
    def show_message(self, msg, duration=5):
        def apply():
            try:
                self.msg_label.config(text=msg)
                self.root.after(duration * 1000, lambda: self.msg_label.config(text=""))
            except Exception:
                log_exc("show_message apply failed")
        self.safe(apply)

    def thread_watch_messages(self):
        last_message = ""
        try:
            while True:
                try:
                    if os.path.isfile(MSG_FILE):
                        with open(MSG_FILE, "r", encoding="utf-8") as f:
                            msg = f.read().strip()
                        if msg and msg != last_message:
                            self.show_message(msg)
                            last_message = msg
                except Exception:
                    log_exc("thread_watch_messages inner error")
                time.sleep(1)
        except Exception:
            log_exc("thread_watch_messages crashed")

    # =============== MINI MODE ALWAYS ON TOP============================
    def force_above_taskbar(self,hwnd):
        HWND_TOPMOST = -1
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_SHOWWINDOW = 0x0040

        ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )

    # =============== MINI MODE ============================
    def toggle_mini_mode(self, event=None):
        try:
            if not self.is_mini:
                self.is_mini = True
                self.full_geometry = self.root.geometry()

                self.task_label.pack_forget()
                self.time_label.pack_forget()
                self.msg_label.pack_forget()
                self.todo_label.pack_forget()
                self.todo_text.pack_forget()

                self.root.geometry("150x40")

                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                self.root.geometry(f"150x40+{0}+{sh - 85}")
                self.root.update_idletasks()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                self.force_above_taskbar(hwnd)

                self.timer_label.config(font=("Consolas", 20, "bold"))

            else:
                self.is_mini = False

                self.task_label.pack(pady=3, padx=10)
                self.timer_label.pack(pady=2)
                self.time_label.pack(pady=2)
                self.msg_label.pack(pady=3)
                self.todo_label.pack(pady=(8, 0))
                self.todo_text.pack(pady=3)

                if self.full_geometry:
                    self.root.geometry(self.full_geometry)

                self.timer_label.config(font=("Consolas", 18, "bold"))
        except Exception:
            log_exc("toggle_mini_mode failed")

    # simple watchdog to detect if mainloop died unexpectedly (logs periodically)
    def _watchdog_thread(self):
        try:
            while True:
                # if root window exists, do nothing; this thread mainly writes to log occasionally
                logging.debug("watchdog: ui alive")
                time.sleep(30)
        except Exception:
            log_exc("watchdog crashed")

    # ======================================================
    def run(self):
        try:
            logging.info("FocusTimerUI starting mainloop")
            self.root.mainloop()
            logging.info("FocusTimerUI mainloop exited")
        except Exception:
            log_exc("mainloop raised exception")

if __name__ == "__main__":
    # Ensure log file exists and print a small startup message to stdout (so running in terminal shows it)
    print("Starting FocusTimer (logs -> {})".format(LOG_PATH))
    logging.info("Starting FocusTimer (standalone run)")
    ui = FocusTimerUI()
    ui.run()
