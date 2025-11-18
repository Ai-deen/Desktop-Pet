# focus_pet_scheduler.py
import os
import sys
import threading
import subprocess
import time
from datetime import datetime, timedelta
import pandas as pd
import tkinter as tk
from tkinter import messagebox, simpledialog

# --- BASE PATH (IMPORTANT) ---
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")

TIMETABLE = os.path.join(DATA_DIR, "focus_timetable.csv")
UI_MESSAGE_FILE = os.path.join(DATA_DIR, "focus_ui_message.txt")

PET_SCRIPT = os.path.join(BASE, "desktop_pet.py")
TIMER_SCRIPT = os.path.join(BASE, "focus_pet_timer.py")

WORK_MIN = 25
BREAK_MIN = 5
CHECK_INTERVAL = 15
# -----------------------------------


def hm_to_minutes(hm: str):
    h, m = map(int, hm.split(":"))
    return h * 60 + m


def open_subprocess(script_path):
    if not os.path.isfile(script_path):
        print("Script not found:", script_path)
        return None

    proc = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"Launched subprocess {script_path} (pid {proc.pid})")
    return proc


class Scheduler:
    def __init__(self, timetable_path):
        self.timetable_path = timetable_path
        self.df = None
        self.lock = threading.Lock()
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
        total = minutes * 60
        step = 5
        elapsed = 0

        while elapsed < total:
            time.sleep(min(step, total - elapsed))
            elapsed += step

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
        while True:
            try:
                idx, row, remaining = self.find_slot_to_start()
                if idx is None:
                    time.sleep(CHECK_INTERVAL)
                    continue

                with self.lock:
                    cycles = (WORK_MIN + BREAK_MIN)
                    pom_count = int(remaining // cycles)

                    if pom_count == 0 and remaining >= WORK_MIN:
                        pom_count = 1

                    if pom_count == 0:
                        continue

                    for i in range(pom_count):
                        self.show_blocking_popup(
                            f"WORK: {row['SlotName']} ({i+1}/{pom_count})"
                        )
                        self._sleep_minutes(WORK_MIN)

                        self._update_logged_minutes(idx, WORK_MIN)

                        if i < pom_count - 1:
                            self.show_blocking_popup(f"BREAK: {BREAK_MIN} minutes")
                            self._sleep_minutes(BREAK_MIN)
                            self._update_logged_minutes(idx, BREAK_MIN)

                    # Ask user to confirm
                    result = self.ask_task_completion(idx)
                    self.df.at[idx, "Status"] = result["status"]
                    self.df.at[idx, "Comments"] = result["comment"]
                    self.df.at[idx, "LastUpdated"] = datetime.now().isoformat()

                    self.save_timetable()
                    time.sleep(5)

            except Exception as e:
                print("Scheduler error:", e)
                time.sleep(5)


def main():
    pet_proc = open_subprocess(PET_SCRIPT)
    timer_proc = open_subprocess(TIMER_SCRIPT)

    scheduler = Scheduler(TIMETABLE)
    scheduler.run_loop()


if __name__ == "__main__":
    main()
