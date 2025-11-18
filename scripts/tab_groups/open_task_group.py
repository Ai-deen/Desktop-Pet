# open_task_group.py
import requests
import sys

SERVER = "http://127.0.0.1:5050"

def open_group(name):
    payload = {"action": "open_group", "payload": {"name": name}}
    r = requests.post(SERVER + "/set_command", json=payload, timeout=2)
    print("server response:", r.json())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python open_task_group.py \"Slot Name\"")
    else:
        open_group(sys.argv[1])
