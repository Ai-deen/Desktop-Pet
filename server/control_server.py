from flask import Flask, request, jsonify
import threading
import uuid
import time
import logging
import os
import signal
import json
import pandas as pd
from datetime import datetime
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)
from app.utils.log_file import log_file


# ==========================================================
# FLASK APP
# ==========================================================
app = Flask(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = log_file("control_server.log")
URLS_PATH = os.path.join(BASE, "..", "data",  "task_urls.json")
TIMETABLE = os.path.join(BASE, "..", "data", "focus_timetable.csv")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [CONTROL_SERVER] %(levelname)s: %(message)s"
)


# ==========================================================
# THREAD-SAFE PENDING COMMAND STORAGE
# ==========================================================
_pending_lock = threading.Lock()
_pending = None     # {id, action, payload, created_at}


def set_pending(action, payload):
    """Create a new command for Chrome extension to execute."""
    global _pending
    with _pending_lock:
        _pending = {
            "id": str(uuid.uuid4()),
            "action": action,
            "payload": payload,
            "created_at": time.time()
        }
        logging.info(f"SET COMMAND: {action} | Payload={payload}")
        return _pending


def get_pending():
    with _pending_lock:
        return _pending


def clear_pending(cmd_id=None):
    global _pending
    with _pending_lock:
        if _pending is None:
            return False

        if cmd_id is None or str(_pending["id"]) == str(cmd_id):
            logging.info(f"CLEAR COMMAND: {cmd_id}")
            _pending = None
            return True
        return False


# ==========================================================
# BASIC ROUTES (Chrome extension)
# ==========================================================
@app.route("/command", methods=["GET"])
def command_get():
    return jsonify({"ok": True, "pending": get_pending()})


@app.route("/set_command", methods=["POST"])
def command_set():
    data = request.get_json(force=True)
    action = data.get("action")
    payload = data.get("payload", {})

    if not action:
        return jsonify({"ok": False, "error": "missing action"}), 400

    cmd = set_pending(action, payload)
    return jsonify({"ok": True, "pending": cmd})


@app.route("/ack", methods=["POST"])
def command_ack():
    data = request.get_json(force=True)
    cmd_id = data.get("id")
    ok = clear_pending(cmd_id)
    return jsonify({"ok": ok})


@app.route("/presence", methods=["POST"])
def presence():
    data = request.get_json(force=True)
    logging.info(f"PRESENCE: {data}")
    return jsonify({"ok": True})


# ==========================================================
# AUTO-SAVE TABS → PC STORAGE (called from Chrome)
# ==========================================================
@app.route("/save_urls", methods=["POST"])
def save_urls():
    data = request.get_json(force=True)
    task = data.get("group_name")
    urls = data.get("urls", [])

    if not task:
        return jsonify({"ok": False, "error": "missing group_name"}), 400

    try:
        if os.path.isfile(URLS_PATH):
            with open(URLS_PATH, "r") as f:
                db = json.load(f)
        else:
            db = {}

        db[task] = urls

        with open(URLS_PATH, "w") as f:
            json.dump(db, f, indent=2)

        logging.info(f"Saved {len(urls)} URLs for task {task}")
        return jsonify({"ok": True})

    except Exception as e:
        logging.error(f"save_urls error: {e}")
        return jsonify({"ok": False, "error": str(e)})


# ==========================================================
# PC → OPEN SAVED TABS IN CHROME
# ==========================================================
@app.route("/open_saved", methods=["POST"])
def open_saved():
    data = request.get_json(force=True)
    task = data.get("task")

    if not task:
        return jsonify({"ok": False, "error": "missing task"}), 400

    try:
        if not os.path.isfile(URLS_PATH):
            return jsonify({"ok": False, "error": "no saved tabs"}), 404

        with open(URLS_PATH, "r") as f:
            db = json.load(f)

        urls = db.get(task, [])

        cmd = set_pending("open_saved_from_pc", {
            "name": task,
            "urls": urls
        })

        return jsonify({"ok": True, "pending": cmd})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ==========================================================
# AUTOMATIC TASK-BASED BEHAVIOUR
# Called by scheduler every loop or by a cron thread
# ==========================================================
def get_current_slot():
    """Return active task name if the current time is in a slot."""
    try:
        df = pd.read_csv(TIMETABLE, dtype=str).fillna("")
    except:
        return None

    today = datetime.now().date().isoformat()
    rows = df[df["Date"] == today]

    now = datetime.now().time()

    for _, r in rows.iterrows():
        if not r["StartTime"] or not r["EndTime"]:
            continue

        start = datetime.strptime(r["StartTime"], "%H:%M").time()
        end = datetime.strptime(r["EndTime"], "%H:%M").time()

        if start <= now < end:
            return r["SlotName"]

    return None


last_active_task = None


def slot_watcher():
    """
    Background thread:
    - detects slot start → open saved tabs
    - detects slot end → auto-save + close tabs
    """
    global last_active_task

    logging.info("Started slot watcher thread.")

    while True:
        try:
            current = get_current_slot()

            # SLOT STARTED
            if current and current != last_active_task:
                logging.info(f"SLOT STARTED: {current}")

                # open saved tabs
                set_pending("open_saved_from_pc", {
                    "name": current,
                    "urls": load_saved_urls(current)
                })

                last_active_task = current

            # SLOT ENDED
            if last_active_task and current != last_active_task:
                logging.info(f"SLOT ENDED: {last_active_task}")

                # auto-save open tabs from Chrome
                set_pending("auto_save", {"name": last_active_task})

                # auto-close handled by extension window logic
                last_active_task = None

        except Exception as e:
            logging.error(f"slot_watcher error: {e}")

        time.sleep(5)


def load_saved_urls(task):
    if not os.path.isfile(URLS_PATH):
        return []
    try:
        with open(URLS_PATH, "r") as f:
            db = json.load(f)
        return db.get(task, [])
    except:
        return []


# ==========================================================
# START SERVER
# ==========================================================
def main():
    logging.info("Control server started on http://127.0.0.1:5050")

    watcher = threading.Thread(target=slot_watcher, daemon=True)
    watcher.start()

    app.run(
        host="127.0.0.1",
        port=5050,
        debug=False,
        use_reloader=False
    )


# ==========================================================
# GRACEFUL EXIT
# ==========================================================
def _handle_signal(sig, frame):
    logging.info(f"Received shutdown: {sig}")
    exit(0)


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


# ==========================================================
# FOR GUI LAUNCHER
# ==========================================================
def start_tab_server():
    import subprocess, sys
    script = os.path.abspath(__file__)
    return subprocess.Popen([sys.executable, script])


if __name__ == "__main__":
    main()
