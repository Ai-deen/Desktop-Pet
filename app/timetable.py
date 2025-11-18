# generate_timetable_xlsx.py
import pandas as pd
from datetime import datetime, timedelta

OUT = "focus_timetable.xlsx"

# Config: month / year and the four daily slots you used in the PDF
YEAR = 2025
MONTH = 11

SLOTS = [
    {"name": "Applications", "start": "08:00", "end": "12:00"},
    {"name": "DSA", "start": "15:00", "end": "17:00"},
    {"name": "Course Module", "start": "21:30", "end": "22:30"},
    {"name": "Personal Project", "start": "22:30", "end": "00:00"},  # note: crosses midnight handling below
]

def make_rows(year, month):
    first = datetime(year, month, 1)
    # find number of days in month
    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    days = (next_month - first).days
    rows = []
    for d in range(days):
        date = first + timedelta(days=d)
        for slot in SLOTS:
            start = datetime.strptime(slot["start"], "%H:%M").time()
            end = datetime.strptime(slot["end"], "%H:%M").time()
            # if end == 00:00 treat as midnight next day
            rows.append({
                "Date": date.date().isoformat(),
                "DayName": date.strftime("%a"),
                "SlotName": slot["name"],
                "StartTime": slot["start"],
                "EndTime": slot["end"],
                "Status": "",  # Done / Not Done
                "PomodorosCompleted": 0,
                "LoggedMinutes": 0,
                "Comments": "",
                "LastUpdated": ""
            })
    return rows

if __name__ == "__main__":
    rows = make_rows(YEAR, MONTH)
    df = pd.DataFrame(rows)
    df.to_excel(OUT, index=False)
    print(f"Created {OUT} with {len(df)} slot rows.")
