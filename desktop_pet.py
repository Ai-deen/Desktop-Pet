# desktop_pet_resized.py - ready-to-run for resized cat gifs
import tkinter as tk
import random
import os
import sys

IMPATH = os.path.dirname(__file__)
FILES = {
    "idle": "idle.gif",
    "idle_to_sleep": "idle_to_sleep.gif",
    "sleep": "sleep.gif",
    "sleep_to_idle": "sleep_to_idle.gif",
    "walk_right": "walk_right.gif",
    "walk_left": "walk_left.gif"
}
window = tk.Tk()
window.overrideredirect(True)
window.attributes('-topmost', True)
PET_WIDTH = 100
PET_HEIGHT = 100
START_X = window.winfo_screenwidth() - PET_WIDTH - 50
GROUND_Y = window.winfo_screenheight() - PET_HEIGHT - 30

if not os.path.isdir(IMPATH):
    print("ERROR: IMPATH does not exist:", IMPATH)
    sys.exit(1)

def load_gif_frames(path):
    frames = []
    i = 0
    while True:
        try:
            frm = tk.PhotoImage(file=path, format=f"gif -index {i}")
            frames.append(frm)
            i += 1
        except tk.TclError:
            break
    return frames

for key, fname in FILES.items():
    full = os.path.join(IMPATH, fname)
    if not os.path.isfile(full):
        print(f"ERROR: Expected file for '{key}' not found: {full}")
        sys.exit(1)



window.config(highlightbackground='black')
window.wm_attributes('-transparentcolor', 'black')
label = tk.Label(window, bd=0, bg='black')
label.pack()

idle = load_gif_frames(os.path.join(IMPATH, FILES["idle"]))
idle_to_sleep = load_gif_frames(os.path.join(IMPATH, FILES["idle_to_sleep"]))
sleep = load_gif_frames(os.path.join(IMPATH, FILES["sleep"]))
sleep_to_idle = load_gif_frames(os.path.join(IMPATH, FILES["sleep_to_idle"]))
walk_right = load_gif_frames(os.path.join(IMPATH, FILES["walk_right"]))
walk_left = load_gif_frames(os.path.join(IMPATH, FILES["walk_left"]))

if not (idle and idle_to_sleep and sleep and sleep_to_idle and walk_right and walk_left):
    print("ERROR: One or more GIFs failed to load (no frames).")
    sys.exit(1)

cycle = 0
check = 1
event_number = random.randrange(1, 19)
x = START_X
global_x = x


# Heavily weighted toward sleeping
idle_num = [1,2,3]                      # almost never idle
idle_to_sleep_num = [ 4, 5, 6 ]    # goes to sleep quickly
sleep_nums =  [7, 8, 9, 10, 11]  # long sleep cycle
sleep_to_idle_num = [ 12, 13, 14 ]            # rare wake-up
walk_left_num = [15, 16]                # very rare walking
walk_right_num = [17,18]               # very rare walking


def gif_work(cycle_local, frames, first_num, last_num):
    if cycle_local < len(frames) - 1:
        cycle_local += 1
    else:
        cycle_local = 0
        event = random.randrange(first_num, last_num + 1)
        return cycle_local, event
    return cycle_local, None

def update(cycle_local, check_local, event_num_local, x_local):
    next_event = None
    if check_local == 0:
        frame = idle[cycle_local % len(idle)]
        cycle_local, next_event = gif_work(cycle_local, idle, 1, 9)
    elif check_local == 1:
        frame = idle_to_sleep[cycle_local % len(idle_to_sleep)]
        cycle_local, next_event = gif_work(cycle_local, idle_to_sleep, 10, 10)
    elif check_local == 2:
        frame = sleep[cycle_local % len(sleep)]
        cycle_local, next_event = gif_work(cycle_local, sleep, 10, 15)
    elif check_local == 3:
        frame = sleep_to_idle[cycle_local % len(sleep_to_idle)]
        cycle_local, next_event = gif_work(cycle_local, sleep_to_idle, 1, 1)
    elif check_local == 4:
        frame = walk_right[cycle_local % len(walk_right)]
        cycle_local, next_event = gif_work(cycle_local, walk_right, 1, 9)
        x_local += 3
    elif check_local == 5:
        frame = walk_left[cycle_local% len(walk_left)]
        cycle_local, next_event = gif_work(cycle_local, walk_left, 1, 9)
        x_local -= 3
    else:
        frame = idle[0]
        cycle_local, next_event = gif_work(cycle_local, idle, 1, 9)

    screen_w = window.winfo_screenwidth()
    if x_local < -PET_WIDTH:
        x_local = screen_w
    if x_local > screen_w:
        x_local = -PET_WIDTH

    window.geometry(f"{PET_WIDTH}x{PET_HEIGHT}+{int(x_local)}+{int(GROUND_Y)}")
    label.configure(image=frame)

    if next_event is not None:
        event_num_local = next_event

    window.after(1, event, cycle_local, check_local, event_num_local, x_local)

def event(cycle_local, check_local, event_num_local, x_local):
    if event_num_local in idle_num:
        check_local = 0
        window.after(400, update, cycle_local, check_local, event_num_local, x_local)
    elif event_num_local in idle_to_sleep_num:
        check_local = 1
        window.after(100, update, cycle_local, check_local, event_num_local, x_local)
    elif event_num_local in walk_left_num:
        check_local = 5
        window.after(100, update, cycle_local, check_local, event_num_local, x_local)
    elif event_num_local in walk_right_num:
        check_local = 4
        window.after(100, update, cycle_local, check_local, event_num_local, x_local)
    elif event_num_local in sleep_nums:
        check_local = 2
        window.after(10000, update, cycle_local, check_local, event_num_local, x_local)
    elif event_num_local in sleep_to_idle_num:
        check_local = 3
        window.after(100, update, cycle_local, check_local, event_num_local, x_local)
    else:
        new_ev = random.randrange(1, 16)
        window.after(200, update, cycle_local, check_local, new_ev, x_local)

def on_right_click(event):
    window.destroy()

drag_data = {"x": 0, "y": 0, "start_win_x": None, "start_win_y": None}
def on_press(event):
    drag_data["x"] = event.x_root
    drag_data["y"] = event.y_root
    geom = window.geometry().split('+')
    if len(geom) >= 3:
        drag_data["start_win_x"] = int(geom[1])
        drag_data["start_win_y"] = int(geom[2])

def on_motion(event):
    if drag_data["start_win_x"] is None:
        return
    dx = event.x_root - drag_data["x"]
    dy = event.y_root - drag_data["y"]
    new_x = drag_data["start_win_x"] + dx
    new_y = drag_data["start_win_y"] + dy
    window.geometry(f"{PET_WIDTH}x{PET_HEIGHT}+{new_x}+{new_y}")

def on_release(event):
    drag_data["start_win_x"] = None
    drag_data["start_win_y"] = None

label.bind("<Button-3>", on_right_click)
label.bind("<Button-1>", on_press)
label.bind("<B1-Motion>", on_motion)
label.bind("<ButtonRelease-1>", on_release)

window.geometry(f"{PET_WIDTH}x{PET_HEIGHT}+{START_X}+{GROUND_Y}")
window.after(1, update, cycle, check, event_number, x)
window.mainloop()
