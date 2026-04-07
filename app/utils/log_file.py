import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = os.path.join(BASE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log_file(name):
    """Return full path inside logs folder."""
    return os.path.join(LOG_DIR, name)
# Example usage:
# error_log_path = log_file("error.log")    