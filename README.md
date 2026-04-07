# Desktop Pet — Focus System

A desktop "focus pet" that helps you stay on task. It combines:

- An animated desktop pet (`app/desktop_pet.py`).
- A Pomodoro-style scheduler and timer UI (`app/focus_pet_scheduler.py`, `app/focus_pet_timer.py`).
- A presence detector using MediaPipe + OpenCV (`app/presence_detector.py`).
- Local Flask servers for content-checking and browser-extension control (`server/focus_server.py`, `server/control_server.py`).
- A small Tkinter launcher UI to start/stop modules (`app/gui_launcher.py`).

## Quick setup

1. Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Additional steps:
- Download a MediaPipe FaceLandmarker `.task` model and place it at `app/data/face_landmarker.task`, or update `MODEL_PATH` in `app/presence_detector.py` to point to your model file.
- (Optional) Set `OPENROUTER_API_KEY` in your environment if you want the `focus_server` to call the OpenRouter API for page classification.

```powershell
$env:OPENROUTER_API_KEY = "your_api_key_here"
```

## Run

- Start the Launcher GUI (recommended):

```powershell
python -m app.gui_launcher
```

- Run modules directly:

```powershell
python -m server.control_server
python -m server.focus_server
python -m app.presence_detector
python -m app.focus_pet_timer
python -m app.desktop_pet
```

## Notes and gotchas

- `app/desktop_pet.py` expects GIFs under `app/assets/gifs/` and will raise an error if missing.
- `app/presence_detector.py` requires a FaceLandmarker `.task` model and a working camera.
- `server/focus_server.py` uses an external API (OpenRouter) — set `OPENROUTER_API_KEY` or the server will fallback to a permissive default.
- There is no exhaustive `requirements.txt` lockfile — the provided `requirements.txt` lists packages inferred from the code; you may need to adjust package versions for your environment.

## Suggested next steps

- (Optional) I can patch `presence_detector.py` to look for a relative model path automatically.
- Add a small PowerShell dev-run script to start the control server, focus server, and launcher in a predictable order.

---

If you want, I can now try to run a quick smoke-check (compile the Python files to check syntax).