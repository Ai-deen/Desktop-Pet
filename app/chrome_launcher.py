import subprocess
import os
import sys
import webbrowser

def start_chrome_debug():
    # Common Chrome locations
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            break

    if chrome_exe is None:
        print("Chrome not found. Opening system default browser instead.")
        webbrowser.open("https://google.com")
        return
    
    subprocess.Popen([
        chrome_exe,
        "--remote-debugging-port=9222",
        "--restore-last-session"
    ])

    print("Chrome opened with debugging enabled.")
