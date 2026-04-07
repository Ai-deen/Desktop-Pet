#!/usr/bin/env python3
# focus_pet_scheduler.py
# Minimal, backward-compatible scheduler + controller for your GUI.
# Small changes from original:
# - scheduler.run_loop uses `self.running` so it can be stopped
# - _sleep_minutes checks self.running and returns early
# - SchedulerController class added to start/stop pet+timer + scheduler thread
# - start_timer_pet() now returns a SchedulerController instance (GUI expects this)

import os
import sys
import threading
import subprocess
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
import tkinter as tk
from tkinter import messagebox, simpledialog
from app.utils.log_file import log_file
from app.summariser import AutoLogger

# --- BASE PATH (IMPORTANT) ---
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")

TIMETABLE = os.path.join(DATA_DIR, "focus_timetable.csv")
UI_MESSAGE_FILE = os.path.join(DATA_DIR, "focus_ui_message.txt")

PET_SCRIPT = os.path.join(BASE, "desktop_pet.py")
TIMER_SCRIPT = os.path.join(BASE, "focus_pet_timer.py")
SCHEDULER_LOG = log_file("scheduler.log")

WORK_MIN = 25

BREAK_MIN = 5
CHECK_INTERVAL = 15
# -----------------------------------


def hm_to_minutes(hm: str):
    h, m = map(int, hm.split(":"))
    return h * 60 + m

def log_service(*msg):
    with open(SCHEDULER_LOG, "a", encoding="utf-8") as f:
        f.write(" ".join(str(m) for m in msg) + "\n")

print = log_service
def open_subprocess(script_path):
    if not os.path.isfile(script_path):
        print("Script not found:", script_path)
        return None

    proc = subprocess.Popen(
        [sys.executable, script_path],
        stdout=open(SCHEDULER_LOG, "a", encoding="utf-8"),
        stderr=open(SCHEDULER_LOG, "a", encoding="utf-8")
    )
    print(f"Launched subprocess {script_path} (pid {proc.pid})")
    return proc



class Scheduler:
    """
    Original scheduler with minimal changes:
    - self.running flag to allow external stop
    - _sleep_minutes breaks early if running becomes False
    """

    def __init__(self, timetable_path):
        self.timetable_path = timetable_path
        self.df = None
        self.lock = threading.Lock()
        self.running = True     # <-- new: set True by default
        self.load_timetable()

    def load_timetable(self):
        if not os.path.isfile(self.timetable_path):
            raise FileNotFoundError(f"Timetable not found: {self.timetable_path}")

        self.df = pd.read_csv(self.timetable_path, dtype=str)

        # ensure needed columns exist
        for col in ["Status", "PomodorosCompleted", "LoggedMinutes", "Comments", "LastUpdated"]:
            if col not in self.df.columns:
                self.df[col] = ""

        self.df["PomodorosCompleted"] = self.df["PomodorosCompleted"].fillna(0).astype(int)
        print("Timetable loaded, rows:", len(self.df))

    def save_timetable(self):
        self.df.to_csv(self.timetable_path, index=False)
        print("Timetable saved.")

    def get_todays_slots(self):
        today = datetime.now().date().isoformat()
        rows = self.df[self.df["Date"] == today].copy()

        rows["StartMin"] = rows["StartTime"].apply(hm_to_minutes)
        rows["EndMin"] = rows["EndTime"].apply(hm_to_minutes)

        rows.loc[rows["EndTime"] == "00:00", "EndMin"] = 1440
        return rows.reset_index()

    def find_slot_to_start(self):
        rows = self.get_todays_slots()
        now = datetime.now()
        now_min = now.hour * 60 + now.minute

        for _, r in rows.iterrows():
            idx = r["index"]
            start = int(r["StartMin"])
            end = int(r["EndMin"])
            status = str(self.df.at[idx, "Status"]).strip().lower()

            if start <= now_min < end and status != "done":
                slot_end = datetime.combine(now.date(), datetime.min.time()) + timedelta(minutes=end)
                remaining = (slot_end - now).total_seconds() / 60
                return idx, r, remaining

        return None, None, None

    def _sleep_minutes(self, minutes):
        """
        Sleep in small chunks so we can break out early when self.running becomes False.
        """
        total = minutes * 60
        step = 5
        elapsed = 0

        while elapsed < total:
            if not self.running:
                # stop requested
                return False
            time.sleep(min(step, total - elapsed))
            elapsed += step
        return True

    def _update_logged_minutes(self, row_idx, minutes):
        prev = int(self.df.at[row_idx, "LoggedMinutes"] or 0)
        self.df.at[row_idx, "LoggedMinutes"] = prev + int(minutes)

    def show_blocking_popup(self, message):
        try:
            with open(UI_MESSAGE_FILE, "w", encoding="utf-8") as f:
                f.write(message)
        except:
            pass

    def ask_task_completion(self, row_idx):
        res = {"status": "", "comment": ""}

        def _ask():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            ans = messagebox.askyesno(
                "Task Complete?",
                f"Completed: {self.df.at[row_idx, 'SlotName']} ?",
                parent=root
            )

            if ans:
                c = simpledialog.askstring("Comment", "Optional comment:", parent=root)
                res["status"] = "Done"
                res["comment"] = c or ""
            else:
                c = simpledialog.askstring("Reason", "Why not?", parent=root)
                res["status"] = "Not Done"
                res["comment"] = c or ""

            root.destroy()

        t = threading.Thread(target=_ask)
        t.start()
        t.join()
        return res

    def run_loop(self):
        print("Scheduler running...")
        # loop is now controllable via self.running
        while self.running:
            try:
                idx, row, remaining = self.find_slot_to_start()
                if idx is None:
                    # if stop requested while idle, break quickly
                    for _ in range(CHECK_INTERVAL):
                        if not self.running:
                            break
                        time.sleep(1)
                    continue

                with self.lock:
                    cycles = (WORK_MIN + BREAK_MIN)
                    pom_count = int(remaining // cycles)

                    if pom_count == 0 and remaining >= WORK_MIN:
                        pom_count = 1

                    if pom_count == 0:
                        continue

                    for i in range(pom_count):
                        if not self.running:
                            print("Scheduler stopping mid-cycle.")
                            return
                        
                        if hasattr(self, "controller") and self.controller.autologger is None:
                            self.controller.autologger = AutoLogger(interval_minutes=5)
                            self.controller.autologger.start()
                            print("AutoLogger started for this slot.")

                        self.show_blocking_popup(
                            f"WORK: {row['SlotName']} ({i+1}/{pom_count})"
                        )
                        ok = self._sleep_minutes(WORK_MIN)
                        if not ok:
                            print("Sleep interrupted (stop requested).")
                            return

                        self._update_logged_minutes(idx, WORK_MIN)

                        if i < pom_count - 1:
                            self.show_blocking_popup(f"BREAK: {BREAK_MIN} minutes")
                            ok = self._sleep_minutes(BREAK_MIN)
                            if not ok:
                                print("Break interrupted (stop requested).")
                                return
                            self._update_logged_minutes(idx, BREAK_MIN)

                    # --- STOP AUTOLOGGER (slot finished) ---
                    if hasattr(self, "controller") and self.controller.autologger:
                        try:
                            self.controller.autologger.stop()
                            print("AutoLogger stopped for this slot.")
                        except Exception as e:
                            print("Error stopping AutoLogger:", e)
                        self.controller.autologger = None
                    # ---------------------------------------
                    # Mark session start only ONCE
                    if hasattr(self, "controller") and self.controller.session_start is None:
                        self.controller.session_start = datetime.now(timezone.utc)
                        print("Session start marked:", self.controller.session_start.isoformat())



                    # Ask user to confirm
                    result = self.ask_task_completion(idx)
                    # Session END time
                    if hasattr(self, "controller"):
                        self.controller.session_end = datetime.now(timezone.utc)
                        print("Session end marked:", self.controller.session_end.isoformat())

                    self.df.at[idx, "Status"] = result["status"]
                    self.df.at[idx, "Comments"] = result["comment"]
                    self.df.at[idx, "LastUpdated"] = datetime.now().isoformat()

                    self.save_timetable()
                    # short pause allowing stop requests to be handled quickly
                    for _ in range(5):
                        if not self.running:
                            break
                        time.sleep(1)

            except Exception as e:
                print("Scheduler error:", e)
                for _ in range(5):
                    if not self.running:
                        break
                    time.sleep(1)

        print("Scheduler stopped.")


# -----------------------
# Minimal controller used by GUI
# -----------------------
class SchedulerController:
    """
    Lightweight controller that:
      - spawns desktop_pet.py and focus_pet_timer.py
      - runs the Scheduler.run_loop() in a background thread
      - exposes .pid and terminate()/wait() so the GUI launcher can manage it like a Popen
    """

    def __init__(self):
        self.pet_proc = None
        self.timer_proc = None
        self.scheduler = None
        self.thread = None
        self.pid = None
        self._started = False
        self.autologger = None
        self.session_start = None
        self.session_end = None
        self.session_log_path = log_file("task_session_log.jsonl")



    def start(self):
        if self._started:
            return self
        # spawn subprocesses
        self.pet_proc = open_subprocess(PET_SCRIPT)
        self.timer_proc = open_subprocess(TIMER_SCRIPT)

        # create scheduler instance and run in thread
        self.scheduler = Scheduler(TIMETABLE)
        self.scheduler.controller = self   
        self.scheduler.running = True
        self.thread = threading.Thread(target=self.scheduler.run_loop, daemon=True)
        self.thread.start()

        # GUI expects .pid attribute (use timer pid if available)
        self.pid = self.timer_proc.pid if self.timer_proc else (self.pet_proc.pid if self.pet_proc else None)
        self._started = True
        return self

    # Popen-like terminate
    def terminate(self):
        # stop scheduler loop
        try:
            if self.scheduler:
                self.scheduler.running = False
        except Exception:
            pass

        # terminate child processes
        for p in (self.pet_proc, self.timer_proc):
            if p and p.poll() is None:
                try:
                    p.terminate()
                except Exception:
                    pass

        # wait briefly, then force kill if needed
        time.sleep(0.5)
        for p in (self.pet_proc, self.timer_proc):
            if p and p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass

    def wait(self, timeout=None):
        # wait for scheduler thread and children; returns True if all exited
        start = time.time()
        if self.thread:
            remaining = None if timeout is None else max(0, timeout - (time.time() - start))
            try:
                self.thread.join(timeout=remaining)
            except Exception:
                pass

        # wait for child procs
        for p in (self.timer_proc, self.pet_proc):
            if p:
                remaining = None if timeout is None else max(0, timeout - (time.time() - start))
                try:
                    p.wait(timeout=remaining)
                except Exception:
                    pass

        alive = any(p and p.poll() is None for p in (self.pet_proc, self.timer_proc))
        return not alive

    def kill(self):
        # force kill everything
        try:
            if self.scheduler:
                self.scheduler.running = False
        except Exception:
            pass
        for p in (self.pet_proc, self.timer_proc):
            if p and p.poll() is None:
                try:
                    p.kill()
                except Exception:
                    pass


def start_timer_pet():
    """
    Backward-compatible entry point imported by modules.py.
    Returns a SchedulerController instance (Popen-like).
    """
    ctrl = SchedulerController()
    return ctrl.start()


if __name__ == "__main__":
    # preserve old behavior when launched directly from CLI:
    start_timer_pet()
