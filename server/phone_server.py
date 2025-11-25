# server/phone_control_api.py
"""
Phone control API for desktop scheduler -> phone app sync.

Run:
    export PHONE_API_KEY="your_secret_here"
    python server/phone_control_api.py

Or on Windows PowerShell:
    $env:PHONE_API_KEY="your_secret_here"; python server/phone_control_api.py
"""

from flask import Flask, request, jsonify, abort
from datetime import datetime, timedelta
import threading
import json
import os

APP_PORT = int(os.getenv("PHONE_API_PORT", "6000"))
API_KEY = os.getenv("PHONE_API_KEY", "dev_key_change_me")
DATA_FILE = os.path.join(os.path.dirname(__file__), "phone_state.json")
LOCK = threading.Lock()

# persisted state structure
# {
#   "current_task": None or { "id": "...", "slot_name": "...", "start": "iso", "end": "iso" },
#   "unlock_used_for_task": false,
#   "override_until": null,   # iso timestamp of emergency unlock or break unlock if any
#   "mode": "locked"|"break"   # convenience cached mode
# }
DEFAULT_STATE = {
    "current_task": None,
    "unlock_used_for_task": False,
    "override_until": None,
    "mode": "locked",
    "force_reopen_enabled": True   # if true, reply force_reopen to app_closed
}


def load_state():
    if os.path.isfile(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # convert override_until to ISO or None
                return data
        except Exception:
            pass
    return DEFAULT_STATE.copy()


def save_state(state):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


STATE = load_state()


def api_auth(req):
    key = req.headers.get("X-API-Key") or req.args.get("api_key")
    return key == API_KEY


def now_iso():
    return datetime.now().isoformat()


def iso_to_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s)


def allowed_until_dt():
    return iso_to_dt(STATE.get("override_until"))


def is_currently_unlocked():
    u = allowed_until_dt()
    if u and datetime.now() < u:
        return True
    return False


app = Flask(__name__)


@app.before_request
def check_auth():
    if request.path.startswith("/static/"):
        return
    if not api_auth(request):
        return abort(401, "Missing or invalid API key")


@app.route("/phone/status", methods=["GET"])
def phone_status():
    """
    Returns:
    {
      "mode": "work" | "break",
      "remaining_seconds": int,
      "slot_name": str|null,
      "unlocked": bool,
      "unlock_used_for_task": bool,
      "allow_until": iso|null
    }
    """
    with LOCK:
        cur = STATE.get("current_task")
        mode = STATE.get("mode", "locked")
        slot_name = cur.get("slot_name") if cur else None

        # remaining_seconds: if in "work" then time until end, if break then break remaining
        remaining = None
        if cur:
            end = iso_to_dt(cur.get("end"))
            if end:
                remaining = max(0, int((end - datetime.now()).total_seconds()))
        # unlocked if override until in future OR mode is break
        unlocked = False
        if STATE.get("mode") == "break":
            unlocked = True
        elif is_currently_unlocked():
            unlocked = True

        return jsonify({
            "mode": mode,
            "remaining_seconds": remaining,
            "slot_name": slot_name,
            "unlocked": unlocked,
            "unlock_used_for_task": STATE.get("unlock_used_for_task", False),
            "allow_until": STATE.get("override_until")
        })


@app.route("/phone/emergency_unlock", methods=["POST"])
def emergency_unlock():
    """
    Phone requests a 5 minute emergency unlock.
    Response:
      { "unlock_granted": true/false, "duration_seconds": int, "allow_until": iso|null, "reason": str }
    """
    with LOCK:
        if STATE.get("current_task") is None:
            return jsonify({"unlock_granted": False, "reason": "No task active"}), 400

        if STATE.get("unlock_used_for_task"):
            return jsonify({"unlock_granted": False, "reason": "Unlock already used for this task"}), 400

        # grant 5 minutes
        until = datetime.now() + timedelta(minutes=5)
        STATE["override_until"] = until.isoformat()
        STATE["unlock_used_for_task"] = True
        save_state(STATE)
        return jsonify({
            "unlock_granted": True,
            "duration_seconds": 5 * 60,
            "allow_until": STATE["override_until"],
            "reason": "5-minute emergency unlock granted"
        })


@app.route("/phone/heartbeat", methods=["POST"])
def heartbeat():
    """
    Phone posts heartbeat:
      { "device_id": "...", "state": "locked"|"unlocked" }
    Response: { "ok": true }
    """
    data = request.get_json(silent=True) or {}
    device = data.get("device_id")
    st = data.get("state")
    # basic logging - you can extend to real DB
    with LOCK:
        # just store last seen
        STATE.setdefault("_devices", {})
        STATE["_devices"][device or "unknown"] = {
            "last_seen": now_iso(),
            "state": st
        }
        save_state(STATE)
    return jsonify({"ok": True})


@app.route("/phone/app_closed", methods=["POST"])
def app_closed():
    """
    Phone signals it was closed. Server can decide to reply {"force_reopen": true}
    """
    with LOCK:
        # if strict reopen mode enabled, tell phone to reopen
        force = bool(STATE.get("force_reopen_enabled", True) and STATE.get("mode") == "work")
        return jsonify({"force_reopen": force})


# ---------------------- Scheduler integration helpers -----------------------
def scheduler_start_task(task_id: str, slot_name: str, duration_minutes: int):
    """
    Call this when your scheduler starts a work slot.
    It will set the current_task, reset unlock flag, and mark mode=work.
    """
    with LOCK:
        start = datetime.now()
        end = start + timedelta(minutes=duration_minutes)
        STATE["current_task"] = {
            "id": task_id,
            "slot_name": slot_name,
            "start": start.isoformat(),
            "end": end.isoformat()
        }
        STATE["unlock_used_for_task"] = False
        STATE["override_until"] = None
        STATE["mode"] = "work"
        save_state(STATE)


def scheduler_start_break(break_minutes: int):
    """
    Call on break start. Grants unlock for break duration and resets unlock flag.
    """
    with LOCK:
        until = datetime.now() + timedelta(minutes=break_minutes)
        STATE["override_until"] = until.isoformat()
        STATE["mode"] = "break"
        # reset unlock for next task in case you want to track every task separately
        STATE["unlock_used_for_task"] = False
        save_state(STATE)


def scheduler_end_session():
    """
    Call when the session ends (no current task).
    """
    with LOCK:
        STATE["current_task"] = None
        STATE["override_until"] = None
        STATE["mode"] = "locked"
        STATE["unlock_used_for_task"] = False
        save_state(STATE)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"Phone control API running on http://127.0.0.1:{APP_PORT}")
    print(f"Set PHONE_API_KEY env to secure access. Current key: {API_KEY[:6]}...")
    app.run(host="0.0.0.0", port=APP_PORT)
