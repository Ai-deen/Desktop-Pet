# focus_pet_scheduler.py
import os
import sys
import threading
import subprocess
import time
from datetime import datetime, timedelta
import pandas as pd
from dateutil import parser
import tkinter as tk
from tkinter import messagebox, simpledialog

# --- Configuration ----------------
TIMETABLE = "focus_timetable.xlsx"
PET_SCRIPT = "desktop_pet.py"   # must be in same folder or provide full path
WORK_MIN = 25        # default single pomodoro work minutes
BREAK_MIN = 5        # short break minutes
CHECK_INTERVAL = 15  # seconds between schedule checks (low cost)
LAUNCH_PET = True    # if True, spawn your desktop pet script as subprocess
# -----------------------------------

# helper: parse hh:mm into minutes since midnight
def hm_to_minutes(hm: str):
    h, m = map(int, hm.split(":"))
    return h * 60 + m

def minutes_to_timedelta(m):
    return timedelta(minutes=m)

def open_pet_subprocess():
    if not os.path.isfile(PET_SCRIPT):
        print("Pet script not found:", PET_SCRIPT)
        return None
    # Use same python to run
    proc = subprocess.Popen([sys.executable, PET_SCRIPT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Launched pet subprocess (pid {})".format(proc.pid))
    return proc

class Scheduler:
    def __init__(self, timetable_path):
        self.timetable_path = timetable_path
        self.df = None
        self.load_timetable()
        self.current_running = None  # (row_index, end_datetime, pomodoros_total, pomodoros_done)
        self.lock = threading.Lock()

    def load_timetable(self):
        if not os.path.isfile(self.timetable_path):
            raise FileNotFoundError(f"Timetable not found: {self.timetable_path}")
        self.df = pd.read_csv("focus_timetable.csv", dtype=str)
        # ensure needed columns exist
        for col in ["Status", "PomodorosCompleted", "LoggedMinutes", "Comments", "LastUpdated"]:
            if col not in self.df.columns:
                self.df[col] = ""
        # Keep numeric columns typed
        self.df["PomodorosCompleted"] = self.df["PomodorosCompleted"].fillna(0).astype(int)
        print("Timetable loaded, rows:", len(self.df))

    def save_timetable(self):
        # write back to Excel safely
        self.df.to_csv("focus_timetable.csv", index=False)
        print("Timetable saved.")

    def get_todays_slots(self):
        today = datetime.now().date().isoformat()
        # filter by Date column matching today's iso
        rows = self.df[self.df["Date"] == today].copy()
        # convert StartTime/EndTime to minutes
        rows["StartMin"] = rows["StartTime"].apply(hm_to_minutes)
        rows["EndMin"] = rows["EndTime"].apply(hm_to_minutes)
        # handle midnight end (00:00) -> treat as 24:00
        rows.loc[rows["EndTime"] == "00:00", "EndMin"] = 24*60
        return rows.reset_index()

    def find_slot_to_start(self):
        rows = self.get_todays_slots()
        now = datetime.now()
        now_min = now.hour * 60 + now.minute
        # find any slot where StartMin <= now < EndMin and not already marked Done
        for _, r in rows.iterrows():
            idx = r["index"]
            start = int(r["StartMin"])
            end = int(r["EndMin"])
            status = str(self.df.at[idx, "Status"]).strip().lower()
            if start <= now_min < end:
                # if the slot is already marked Done, skip
                if status == "done":
                    continue
                # compute duration in minutes remaining for slot (until end)
                slot_end_dt = datetime.combine(now.date(), datetime.min.time()) + timedelta(minutes=end)
                remaining = (slot_end_dt - now).total_seconds() / 60.0
                return idx, r, remaining
        return None, None, None

    def run_pomodoros_for_slot(self, row_idx, slot_row, remaining_minutes):
        # compute how many full pomodoros fit in remaining slot time
        cycle = WORK_MIN + BREAK_MIN
        pomodoros_possible = int(remaining_minutes // cycle)
        # allow one last partial work period if > WORK_MIN/2 left (configurable; here we ignore partial)
        if pomodoros_possible == 0 and remaining_minutes >= WORK_MIN:
            pomodoros_possible = 1
        if pomodoros_possible == 0:
            print("Not enough time for pomodoro in this slot (remaining {:.1f} min)".format(remaining_minutes))
            return 0

        print(f"Starting {pomodoros_possible} pomodoros for slot '{slot_row['SlotName']}'")
        # run cycles: for each pomodoro, sleep WORK_MIN minutes, then BREAK_MIN minutes (unless it's last)
        pom_done = 0
        for i in range(pomodoros_possible):
            # Work period
            self.show_blocking_popup(f"Start WORK: {slot_row['SlotName']}\nPomodoro {i+1}/{pomodoros_possible}\nFocus for {WORK_MIN} minutes", blocking=False)
            self._sleep_minutes(WORK_MIN)

            pom_done += 1
            self._update_logged_minutes(row_idx, WORK_MIN)

            # small break after every work except last
            if i < pomodoros_possible - 1:
                self.show_blocking_popup(f"Take BREAK: {BREAK_MIN} minutes", blocking=False)
                self._sleep_minutes(BREAK_MIN)
                self._update_logged_minutes(row_idx, BREAK_MIN)

        # mark pomodoros completed in DF temporarily (will finalize after user confirms)
        self.df.at[row_idx, "PomodorosCompleted"] = int(self.df.at[row_idx, "PomodorosCompleted"]) + pom_done
        self.save_timetable()
        return pom_done

    def _sleep_minutes(self, minutes):
        # break into small sleeps to remain responsive
        total = minutes * 60
        step = 5
        elapsed = 0
        while elapsed < total:
            time.sleep(min(step, total - elapsed))
            elapsed += min(step, total - elapsed)

    def _update_logged_minutes(self, row_idx, minutes):
        prev = int(self.df.at[row_idx, "LoggedMinutes"]) if str(self.df.at[row_idx, "LoggedMinutes"]).strip() != "" else 0
        self.df.at[row_idx, "LoggedMinutes"] = prev + int(minutes)

    def show_blocking_popup(self, message, blocking=True):
        """Write messages to the shared message file instead of popup"""
        try:
            with open("focus_ui_message.txt", "w", encoding="utf-8") as f:
                f.write(message)
            print("UI message:", message)
        except Exception as e:
            print("Message write error:", e)

    def ask_task_completion(self, row_idx):
        # ask user to mark Done or Not Done and allow a short comment
        res = {"status": "", "comment": ""}
        def _ask():
            root = tk.Tk()
            root.attributes("-topmost", True)
            root.withdraw()
            ans = messagebox.askyesno("Task Complete?", f"Did you complete: {self.df.at[row_idx, 'SlotName']} ?\n(Yes = Done, No = Not Done)", parent=root)
            comment = ""
            if ans:
                comment = simpledialog.askstring("Comment", "Optional short comment:", parent=root)
                res["status"] = "Done"
                res["comment"] = comment if comment else ""
            else:
                comment = simpledialog.askstring("Why not?", "Short reason (optional):", parent=root)
                res["status"] = "Not Done"
                res["comment"] = comment if comment else ""
            root.destroy()

        t = threading.Thread(target=_ask)
        t.start()
        t.join()
        return res

    def run_loop(self):
        print("Scheduler started run loop.")
        while True:
            try:
                idx, slot_row, remaining = self.find_slot_to_start()
                if idx is not None:
                    # lock while working on this slot
                    with self.lock:
                        # run pomodoros
                        pom_done = self.run_pomodoros_for_slot(idx, slot_row, remaining)
                        # after slot finishes, ask user to mark completion
                        result = self.ask_task_completion(idx)
                        # update dataframe
                        self.df.at[idx, "Status"] = result["status"]
                        self.df.at[idx, "Comments"] = result["comment"]
                        self.df.at[idx, "LastUpdated"] = datetime.now().isoformat(timespec="minutes")
                        # ensure pomodoros logged
                        self.save_timetable()
                        # short cool-off before next check
                        time.sleep(5)
                else:
                    time.sleep(CHECK_INTERVAL)
            except Exception as e:
                print("Scheduler error:", e)
                time.sleep(10)


def open_subprocess(script_name):
    if not os.path.isfile(script_name):
        print("Script not found:", script_name)
        return None
    proc = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    print(f"Launched subprocess {script_name} (pid {proc.pid})")
    return proc


def main():
    pet_proc = None
    timer_proc = None

    # Launch pet and timer UI
    try:
        pet_proc = open_subprocess("desktop_pet.py")
        timer_proc = open_subprocess("focus_pet_timer.py")
    except Exception as e:
        print("Error launching pet or timer:", e)

    # Start scheduler loop
    scheduler = Scheduler(TIMETABLE)
    try:
        scheduler.run_loop()
    except KeyboardInterrupt:
        print("Interrupted, saving and quitting.")
    finally:
        scheduler.save_timetable()
        if pet_proc:
            pet_proc.terminate()
        if timer_proc:
            timer_proc.terminate()
        sys.exit(0)



if __name__ == "__main__":
    main()
