import sqlite3
from datetime import datetime, timedelta
import re

# Connect to SQLite database
conn = sqlite3.connect("meetings.db")
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person TEXT,
        time TEXT
    )
""")
conn.commit()

# Function to parse time and person
def parse_command(command):
    # Example: "schedule a meeting with Akshat at 4:00 PM tomorrow"
    match = re.search(r'with ([\w\s]+) at ([\d: ]+[apAP][mM])(?: (tomorrow))?', command)
    if match:
        person = match.group(1).strip()
        time_str = match.group(2).strip()
        tomorrow = match.group(3)

        # Build datetime
        now = datetime.now()
        meeting_time = datetime.strptime(time_str, "%I:%M %p")
        meeting_time = meeting_time.replace(year=now.year, month=now.month, day=now.day)

        if tomorrow:
            meeting_time += timedelta(days=1)

        return person, meeting_time
    return None, None

# Function to schedule a meeting
def schedule_meeting(command):
    person, meeting_time = parse_command(command)
    if not person:
        print("Could not understand the command.")
        return

    cursor.execute("INSERT INTO meetings (person, time) VALUES (?, ?)", (person, meeting_time.isoformat()))
    conn.commit()
    print(f"✅ Meeting with {person} scheduled at {meeting_time.strftime('%I:%M %p, %d %b %Y')}")

# Example usage
while True:
    user_input = input("\nWhat do you want to do? (type 'exit' to quit)\n> ")
    if user_input.lower() == "exit":
        break
    if "schedule" in user_input.lower():
        schedule_meeting(user_input)
    else:
        print("Sorry, I can only schedule meetings right now.")
