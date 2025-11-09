# focus_pet_timer.py (improved)
import tkinter as tk
import time
import threading
import pandas as pd
from datetime import datetime, timedelta
import os

CSV_PATH = "focus_timetable.csv"
MSG_FILE = "focus_ui_message.txt"

class FocusTimerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FocusPet Timer")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1c1c1c")

        # draggable
        self.offset_x = 0
        self.offset_y = 0
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        # labels
        self.task_label = tk.Label(self.root, text="Waiting for next task...", font=("Segoe UI", 11, "bold"), fg="white", bg="#1c1c1c")
        self.task_label.pack(pady=3, padx=10)

        self.timer_label = tk.Label(self.root, text="--:--:--", font=("Consolas", 18, "bold"), fg="#00ff88", bg="#1c1c1c")
        self.timer_label.pack(pady=2)

        self.time_label = tk.Label(self.root, text="", font=("Segoe UI", 9), fg="#bbbbbb", bg="#1c1c1c")
        self.time_label.pack(pady=2)

        self.msg_label = tk.Label(self.root, text="", font=("Segoe UI", 9, "italic"), fg="#87cefa", bg="#1c1c1c")
        self.msg_label.pack(pady=3)

        # to-do section
        self.todo_label = tk.Label(self.root, text="Today's To-Do:", font=("Segoe UI", 10, "underline"), fg="#ffcc00", bg="#1c1c1c")
        self.todo_label.pack(pady=(8, 0))

        self.todo_text = tk.Text(self.root, height=8, width=34, bg="#2b2b2b", fg="white", font=("Segoe UI", 9))
        self.todo_text.pack(pady=3)
        self.todo_text.configure(state="disabled")

        # threads
        threading.Thread(target=self.update_clock, daemon=True).start()
        threading.Thread(target=self.watch_csv_updates, daemon=True).start()
        threading.Thread(target=self.watch_messages, daemon=True).start()

    def start_move(self, event):
        self.offset_x = event.x
        self.offset_y = event.y

    def do_move(self, event):
        x = self.root.winfo_pointerx() - self.offset_x
        y = self.root.winfo_pointery() - self.offset_y
        self.root.geometry(f"+{x}+{y}")

    def update_clock(self):
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            self.time_label.config(text=f"Current Time: {now}")
            time.sleep(1)

    def format_hms(self, seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def color_for_time(self, remaining):
        if remaining <= 120:  # <2 min
            return "#ff4444"
        elif remaining <= 600:  # <10 min
            return "#ffaa00"
        return "#00ff88"

    def watch_csv_updates(self):
        last_task = ""
        while True:
            try:
                df = pd.read_csv(CSV_PATH, dtype=str)
                df = df.fillna("")  # remove NaN
                today = datetime.now().date().isoformat()
                rows = df[df["Date"] == today]

                # to-do list
                todos = []
                for _, r in rows.iterrows():
                    todos.append(f"- {r['StartTime']}–{r['EndTime']} | {r['SlotName']} [{r.get('Status','')}]")
                todo_str = "\n".join(todos)
                self.todo_text.configure(state="normal")
                self.todo_text.delete(1.0, tk.END)
                self.todo_text.insert(tk.END, todo_str)
                self.todo_text.configure(state="disabled")

                # active task
                now = datetime.now()
                active = None
                for _, r in rows.iterrows():
                    if not r["StartTime"] or not r["EndTime"]:
                        continue
                    start = datetime.strptime(r["StartTime"], "%H:%M").time()
                    end = datetime.strptime(r["EndTime"], "%H:%M").time()
                    start_dt = datetime.combine(now.date(), start)
                    end_dt = datetime.combine(now.date(), end)
                    if start_dt <= now < end_dt:
                        active = (r, start_dt, end_dt)
                        break

                if active:
                    r, start_dt, end_dt = active
                    if last_task != r["SlotName"]:
                        self.task_label.config(text=f"Current: {r['SlotName']}")
                        last_task = r["SlotName"]

                    remaining = (end_dt - now).total_seconds()
                    color = self.color_for_time(remaining)
                    self.timer_label.config(text=self.format_hms(remaining), fg=color)
                else:
                    self.task_label.config(text="No active slot")
                    self.timer_label.config(text="--:--:--", fg="#00ff88")

            except Exception as e:
                print("UI error:", e)
            time.sleep(1)

    def show_message(self, msg, duration=5):
        self.msg_label.config(text=msg)
        self.root.after(duration * 1000, lambda: self.msg_label.config(text=""))

    def watch_messages(self):
        last_message = ""
        while True:
            if os.path.isfile(MSG_FILE):
                with open(MSG_FILE, "r", encoding="utf-8") as f:
                    msg = f.read().strip()
                if msg and msg != last_message:
                    self.show_message(msg)
                    last_message = msg
            time.sleep(1)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FocusTimerUI().run()
