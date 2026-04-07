# app/modules.py

# ===== IMPORT YOUR MODULE FILES =====
# (Make sure each imported file has a clean start_x() function)

from app.pet_timer_runner import start_timer_pet
from server.focus_server import start_focus_server
from server.control_server import start_tab_server
from app.presence_detector import start_presence_detector


# ===== ALL MODULES LISTED HERE =====
MODULES = {
    "schedulerpet": {
        "label": "Timer and Desktop Pet",
        "start": start_timer_pet
    },
    "chrome": {
        "label": "Chrome AI Blocker Extension",
        "start": start_focus_server
    },
    "server": {
        "label": "Tab Group Extension",
        "start": start_tab_server
    },
    "presence": {
        "label": "Presence Detector",
        "start": start_presence_detector
    }
}
