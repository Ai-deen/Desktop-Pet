# control_server.py
from flask import Flask, request, jsonify
import threading, uuid, time

app = Flask(__name__)

_command_lock = threading.Lock()
_pending = None  # { id, action, payload, created_at }

def set_pending(action, payload):
    global _pending
    with _command_lock:
        _pending = {
            "id": str(uuid.uuid4()),
            "action": action,
            "payload": payload,
            "created_at": time.time()
        }
        return _pending

def get_pending():
    with _command_lock:
        return _pending

def clear_pending(cmd_id=None):
    global _pending
    with _command_lock:
        if _pending is None:
            return False
        if cmd_id is None or str(_pending.get("id")) == str(cmd_id):
            _pending = None
            return True
        return False

@app.route("/command", methods=["GET"])
def command_get():
    p = get_pending()
    return jsonify({"ok": True, "pending": p})

@app.route("/set_command", methods=["POST"])
def command_set():
    data = request.get_json(force=True)
    action = data.get("action")
    payload = data.get("payload", {})
    if not action:
        return jsonify({"ok": False, "error": "missing action"}), 400
    p = set_pending(action, payload)
    return jsonify({"ok": True, "pending": p})

@app.route("/ack", methods=["POST"])
def ack_cmd():
    data = request.get_json(force=True)
    cmd_id = data.get("id")
    if not cmd_id:
        return jsonify({"ok": False, "error": "missing id"}), 400
    ok = clear_pending(cmd_id)
    return jsonify({"ok": ok})

if __name__ == "__main__":
    print("Control server running at http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050)
