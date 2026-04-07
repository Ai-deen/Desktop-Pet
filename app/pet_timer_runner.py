import threading
import subprocess
import sys
import os
import time

from app.focus_pet_scheduler import Scheduler, TIMETABLE, PET_SCRIPT, TIMER_SCRIPT

class PetTimerRunner:
    def __init__(self):
        self.pet_proc = None
        self.timer_proc = None
        self.scheduler_thread = None
        self.running = False

    # -------------------------------------------------------
    # START
    # -------------------------------------------------------
    def start(self):
        if self.running:
            return self

        # launch pet.py
        self.pet_proc = subprocess.Popen(
            [sys.executable, PET_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # launch focus_pet_timer.py
        self.timer_proc = subprocess.Popen(
            [sys.executable, TIMER_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # start scheduler loop in background thread
        scheduler = Scheduler(TIMETABLE)

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=scheduler.run_loop,
            daemon=True
        )
        self.scheduler_thread.start()

        # GUI expects a .pid attr
        self.pid = self.timer_proc.pid  
        return self

    # -------------------------------------------------------
    # STOP
    # -------------------------------------------------------
    def stop(self):
        self.running = False

        # kill pet
        if self.pet_proc and self.pet_proc.poll() is None:
            self.pet_proc.terminate()
            time.sleep(0.5)
            try:
                self.pet_proc.kill()
            except:
                pass

        # kill timer
        if self.timer_proc and self.timer_proc.poll() is None:
            self.timer_proc.terminate()
            time.sleep(0.5)
            try:
                self.timer_proc.kill()
            except:
                pass

        return True


# -------------------------------------------------------
# FUNCTION GUI WILL CALL
# -------------------------------------------------------
def start_timer_pet():
    runner = PetTimerRunner()
    return runner.start()
