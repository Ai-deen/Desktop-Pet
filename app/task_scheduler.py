import csv
import datetime
import time
import json
import requests

CSV_PATH = "data\focus_timetable.csv"
URLS_PATH = "task_urls.json"
CONTROL_SERVER = "http://127.0.0.1:5050/set_command"


def load_urls():
    with open(URLS_PATH, "r") as f:
        return json.load(f)


def load_tasks():
    tasks = []
    with open(CSV_PATH, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 5:
                continue
            date, _day, task, start, end = row[:5]
            tasks.append({
                "date": date.strip(),
                "task": task.strip(),
                "start": start.strip(),
                "end": end.strip(),
            })
    return tasks


def send_command(action, payload):
    """Send the action to your existing control server."""
    try:
        requests.post(CONTROL_SERVER, json={
            "action": action,
            "payload": payload
        }, timeout=2)
    except:
        print("[WARN] Control server unreachable.")


def scheduler_loop():
    tasks = load_tasks()
    urls_dict = load_urls()
    active_task = None

    print("Scheduler running...")

    while True:
        now = datetime.datetime.now()
        now_date = now.strftime("%Y-%m-%d")
        now_time = now.strftime("%H:%M")

        for t in tasks:
            if t["date"] != now_date:
                continue

            task_name = t["task"]
            start = t["start"]
            end = t["end"]

            # ---- START ----
            if now_time == start and active_task != task_name:
                urls = urls_dict.get(task_name, [])

                print(f"[START] Opening {task_name}: {urls}")
                send_command("open_tabs", {
                    "group_name": task_name,
                    "urls": urls
                })
                active_task = task_name

            # ---- END ----
            if now_time == end and active_task == task_name:
                print(f"[END] Closing {task_name}")
                send_command("close_tabs", {
                    "group_name": task_name
                })
                active_task = None

        time.sleep(60)  # check every 1 minute


if __name__ == "__main__":
    scheduler_loop()
