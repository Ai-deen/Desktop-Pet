#!/usr/bin/env python3
"""
FOCUS AUTOLOGGER + SUMMARISER (COMBINED)
---------------------------------------
This file merges:
1. The improved summariser
2. The autologger loop that runs summariser every N minutes

Nothing is removed. Everything is intact.
"""

import os
import csv
import json
import re
import time
import threading
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------
# PATH RESOLUTION
# ---------------------------------------------------------

try:
    from app.utils.log_file import log_file
    def lf(name):
        return log_file(name)
except Exception:
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_DIR = os.path.join(THIS_DIR, "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    def lf(name):
        return os.path.join(LOG_DIR, name)

PRESENCE_LOG = lf("presence_log.csv")
FOCUS_LOG = lf("focus_server.log")
UNIFIED_LOG = lf("unified_focus_log.csv")
SESSION_LOG = lf("task_session_log.jsonl")

print("DEBUG: presence log path:", PRESENCE_LOG)
print("DEBUG: focus log path:", FOCUS_LOG)
print("DEBUG: unified log path:", UNIFIED_LOG)

FALLBACK_PRESENCE_ROWS = 200
FALLBACK_FOCUS_LINES = 200

AI_RAW_RE = re.compile(r"AI Raw:\s*```json(.*?)```", re.DOTALL)


# ---------------------------------------------------------
# TIMESTAMP HELPERS
# ---------------------------------------------------------

def parse_presence_timestamp(ts_str):
    if not isinstance(ts_str, str):
        return None
    try:
        if ts_str.endswith("Z"):
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except:
        try:
            return datetime.fromisoformat(ts_str)
        except:
            return None


# ---------------------------------------------------------
# FILE HELPERS
# ---------------------------------------------------------

def tail_lines(path, n=200):
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        avg_line = 200
        to_read = n * avg_line
        try:
            f.seek(-to_read, os.SEEK_END)
        except OSError:
            f.seek(0)
        data = f.read().decode(errors="ignore")
    lines = data.splitlines()
    return lines[-n:]


def read_presence_rows():
    rows = []
    if not os.path.exists(PRESENCE_LOG):
        return rows
    with open(PRESENCE_LOG, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def select_by_time_window_presence(rows, cutoff):
    out = []
    for r in rows:
        ts = parse_presence_timestamp(r.get("timestamp", ""))
        if ts and ts >= cutoff:
            out.append(r)
    return out


def select_last_n_presence(rows, n):
    return rows[-n:] if rows else []


def select_by_time_window_focus(lines, cutoff):
    out = []
    for line in lines:
        try:
            prefix = line.split(" [FOCUS_SERVER]")[0].strip()
            ts = datetime.strptime(prefix, "%Y-%m-%d %H:%M:%S,%f")
            ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                out.append(line)
        except:
            pass
    return out


def select_last_n_lines(lines, n):
    return lines[-n:]


# ---------------------------------------------------------
# FOCUS LOG PARSING
# ---------------------------------------------------------

def extract_ai_actions(lines):
    actions = []
    for line in lines:
        m = AI_RAW_RE.search(line)
        if m:
            try:
                js = json.loads(m.group(1))
                a = js.get("action")
                if a:
                    actions.append(a)
            except:
                try:
                    jmatch = re.search(r"(\{.*\})", line)
                    if jmatch:
                        js = json.loads(jmatch.group(1))
                        a = js.get("action")
                        if a:
                            actions.append(a)
                except:
                    pass
    return actions


def extract_domains_from_focus(lines):
    domains = []
    for line in lines:
        if "Incoming check:" in line:
            try:
                data_str = line.split("Incoming check:",1)[1].strip()
                dm = re.search(r"'domain':\s*'([^']+)'", data_str)
                if dm:
                    domains.append(dm.group(1))
                    continue
                jdm = re.search(r'"domain":\s*"([^"]+)"', data_str)
                if jdm:
                    domains.append(jdm.group(1))
            except:
                continue
    return domains


# ---------------------------------------------------------
# SUMMARISERS
# ---------------------------------------------------------

def summarise_presence_rows(rows):
    if not rows:
        return {
            "work_ratio": 0.0,
            "distracted_ratio": 0.0,
            "sleep_ratio": 0.0,
            "away_ratio": 0.0,
            "final_status": "unknown",
            "avg_ear": 0.0,
            "gaze_focus_ratio": 0.0,
            "total_rows": 0
        }

    total = len(rows)
    counts = {"working": 0, "distracted": 0, "sleeping": 0, "away": 0}
    gaze_center = 0
    ear_sum = 0.0
    valid_ear = 0

    for r in rows:
        status = r.get("status", "").lower().strip()
        if status in counts:
            counts[status] += 1

        g = r.get("gaze_direction", "").lower().strip()
        if g == "center":
            gaze_center += 1

        try:
            ear = float(r.get("avg_ear") or 0)
            ear_sum += ear
            valid_ear += 1
        except:
            pass

    final_status = rows[-1].get("status", "unknown")

    return {
        "work_ratio": round(counts["working"]/total, 3),
        "distracted_ratio": round(counts["distracted"]/total, 3),
        "sleep_ratio": round(counts["sleeping"]/total, 3),
        "away_ratio": round(counts["away"]/total, 3),
        "final_status": final_status,
        "avg_ear": round((ear_sum/valid_ear) if valid_ear else 0, 3),
        "gaze_focus_ratio": round(gaze_center/total, 3),
        "total_rows": total
    }


def summarise_focus_lines(lines):
    actions = extract_ai_actions(lines)
    domains = extract_domains_from_focus(lines)
    domain_counts = {}
    for d in domains:
        domain_counts[d] = domain_counts.get(d, 0) + 1

    top_sites = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
    top_sites = [d for d, c in top_sites[:3]]

    if "block" in actions:
        verdict = "off-task"
    elif "warn" in actions:
        verdict = "uncertain"
    elif "allow" in actions:
        verdict = "on-task"
    else:
        verdict = "unknown"

    return {
        "top_sites": top_sites,
        "ai_verdict": verdict,
        "actions": actions,
        "total_lines": len(lines)
    }


# ---------------------------------------------------------
# UNIFIED SUMMARY BUILDER
# ---------------------------------------------------------

def build_unified_summary(window_minutes=5,
                          fallback_n_presence=FALLBACK_PRESENCE_ROWS,
                          fallback_n_focus=FALLBACK_FOCUS_LINES):

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=window_minutes)

    # Presence
    presence_rows = read_presence_rows()
    print("DEBUG: total rows loaded from presence_log.csv:", len(presence_rows))
    rows_window = select_by_time_window_presence(presence_rows, cutoff)
    used_fallback_presence = False

    if not rows_window:
        rows_window = select_last_n_presence(presence_rows, fallback_n_presence)
        used_fallback_presence = True

    # Focus
    focus_all = tail_lines(FOCUS_LOG, n=20000)
    lines_window = select_by_time_window_focus(focus_all, cutoff)
    used_fallback_focus = False

    if not lines_window:
        lines_window = select_last_n_lines(focus_all, fallback_n_focus)
        used_fallback_focus = True

    presence_summary = summarise_presence_rows(rows_window)
    focus_summary = summarise_focus_lines(lines_window)

    unified = {
        "start": cutoff.isoformat(),
        "end": now.isoformat(),
        "work_ratio": presence_summary["work_ratio"],
        "distracted_ratio": presence_summary["distracted_ratio"],
        "sleep_ratio": presence_summary["sleep_ratio"],
        "away_ratio": presence_summary["away_ratio"],
        "final_status": presence_summary["final_status"],
        "avg_ear": presence_summary["avg_ear"],
        "gaze_focus_ratio": presence_summary["gaze_focus_ratio"],
        "top_sites": "|".join(focus_summary["top_sites"]),
        "ai_verdict": focus_summary["ai_verdict"],
        "presence_rows_used": presence_summary["total_rows"],
        "focus_lines_used": focus_summary["total_lines"],
        "used_fallback_presence": used_fallback_presence,
        "used_fallback_focus": used_fallback_focus,
    }

    write_header = not os.path.exists(UNIFIED_LOG)
    with open(UNIFIED_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(unified.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(unified)

    print("Unified summary written:", unified)
    return unified


# ---------------------------------------------------------
# AUTOLOGGER LOOP
# ---------------------------------------------------------

class AutoLogger:
    def __init__(self, interval_minutes=5):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.thread = None

    def _loop(self):
        print("[AUTOLOGGER] Started.")
        while self.running:
            try:
                summary = build_unified_summary(self.interval_minutes)
                summary["timestamp"] = datetime.now(timezone.utc).isoformat()

                with open(SESSION_LOG, "a", encoding="utf-8") as f:
                    f.write(json.dumps(summary) + "\n")

                print("[AUTOLOGGER] Summary appended.")

            except Exception as e:
                print("[AUTOLOGGER ERROR]", e)

            for _ in range(self.interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        print("[AUTOLOGGER] Stopped.")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("[AUTOLOGGER] Start requested.")

    def stop(self):
        self.running = False
        print("[AUTOLOGGER] Stop requested.")


# ---------------------------------------------------------
# SCRIPT MODE
# ---------------------------------------------------------

if __name__ == "__main__":
    build_unified_summary()
