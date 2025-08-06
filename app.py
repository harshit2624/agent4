from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import re
import os
from email_notifications import EmailNotifier
from learning_system import LearningSystem

app = Flask(__name__)
learning_system = LearningSystem()

# Initialize database
def init_db():
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

# Function to parse time and person
def parse_command(command):
    command = command.lower()
    
    # Handle queries about meetings
    if any(phrase in command for phrase in ['how many meetings', 'list meetings', 'show meetings', 'meetings today', 'scheduled today', 'how many meeting are schedule today']):
        return 'query', 'meetings'
    
    # Check learned patterns first
    suggestion = learning_system.suggest_command_interpretation(command)
    if suggestion:
        return suggestion['suggestion'], suggestion
    
    # Handle scheduling commands with time
    match = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s*with\s+([\w\s]+)\s+at\s+([\d: ]+[ap]m|\d{1,2})(?:\s*(tomorrow))?', command)
    if not match:
        match = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s+([\w\s]+)\s+at\s+([\d: ]+[ap]m|\d{1,2})(?:\s*(tomorrow))?', command)
    if not match:
        # Try to match time without space before am/pm (e.g. 4pm)
        match = re.search(r'(?:schedule|meet|meeting)?\s*(?:meeting)?\s*(?:with)?\s*([\w\s]+)\s+at\s+([\d:]+[ap]m|\d{1,2})(?:\s*(tomorrow))?', command)
    if not match:
        # Try to match just hour number (e.g. 6)
        match = re.search(r'(?:schedule|meet|meeting)?\s*(?:meeting)?\s*(?:with)?\s*([\w\s]+)\s+at\s+(\d{1,2})(?:\s*(tomorrow))?', command)
    if match:
        person = match.group(1).strip().title()
        time_str = match.group(2).strip()
        tomorrow = match.group(3)

        now = datetime.now()
        try:
            meeting_time = datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            try:
                meeting_time = datetime.strptime(time_str, "%I %p")
            except ValueError:
                try:
                    meeting_time = datetime.strptime(time_str, "%I:%M %p.")
                except ValueError:
                    try:
                        meeting_time = datetime.strptime(time_str, "%I %p.")
                    except ValueError:
                        try:
                            meeting_time = datetime.strptime(time_str, "%I%p")
                        except ValueError:
                            try:
                                meeting_time = datetime.strptime(time_str, "%I:%M%p")
                            except ValueError:
                                return None, None

        meeting_time = meeting_time.replace(year=now.year, month=now.month, day=now.day)

        if tomorrow:
            meeting_time += timedelta(days=1)

        return person, meeting_time
    
    # Handle scheduling commands without time (missing time)
    match_person_only = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s*with\s*([\w\s]+)', command)
    if not match_person_only:
        match_person_only = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s*([\w\s]+)', command)
    if match_person_only:
        person = match_person_only.group(1).strip().title()
        return 'missing_time', person
    
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/schedule', methods=['POST'])
def schedule_meeting():
    data = request.json
    command = data.get('command', '')
    
    result_type, result_data = parse_command(command)
    
    if result_type == 'query' and result_data == 'meetings':
        # Handle meeting queries
        conn = sqlite3.connect("meetings.db")
        cursor = conn.cursor()
        
        # Get today's meetings
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        cursor.execute("SELECT person, time FROM meetings WHERE date(time) = ? ORDER BY time", (today.isoformat(),))
        today_meetings = cursor.fetchall()
        
        # Get all meetings for context
        cursor.execute("SELECT person, time FROM meetings ORDER BY time")
        all_meetings = cursor.fetchall()
        conn.close()
        
        if not today_meetings and not all_meetings:
            return jsonify({
                'success': True,
                'message': "No meetings scheduled today or in the future."
            })
        
        if today_meetings:
            meeting_list = []
            for person, time_str in today_meetings:
                meeting_time = datetime.fromisoformat(time_str)
                meeting_list.append(f"{person} at {meeting_time.strftime('%I:%M %p')}")
            
            meetings_text = "\n".join(f"• {meeting}" for meeting in meeting_list)
            return jsonify({
                'success': True,
                'message': f"📅 You have {len(today_meetings)} meeting(s) scheduled today:\n{meetings_text}"
            })
        else:
            # Show upcoming meetings if none today
            upcoming_list = []
            for person, time_str in all_meetings[:5]:  # Show next 5 meetings
                meeting_time = datetime.fromisoformat(time_str)
                upcoming_list.append(f"{person} at {meeting_time.strftime('%I:%M %p, %d %b')}")
            
            meetings_text = "\n".join(f"• {meeting}" for meeting in upcoming_list)
            return jsonify({
                'success': True,
                'message': f"No meetings scheduled today. Here are your upcoming meetings:\n{meetings_text}"
            })
    
    elif result_type == 'missing_time':
        # Ask user for missing time
        person = result_data
        return jsonify({
            'success': False,
            'missing_time': True,
            'message': f"Schedule meeting with {person} at what time?"
        })
    
    elif result_type and result_data:
        # Handle scheduling
        person, meeting_time = result_type, result_data
        if not person:
            return jsonify({'success': False, 'message': 'Could not understand the command.'})

        conn = sqlite3.connect("meetings.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO meetings (person, time) VALUES (?, ?)", 
                       (person, meeting_time.isoformat()))
        conn.commit()
        conn.close()

        # Send email notification and schedule reminder
        notifier = EmailNotifier()
        notifier.send_scheduled_notification(person, meeting_time)
        notifier.schedule_reminder(person, meeting_time)
        
        return jsonify({
            'success': True,
            'message': f"✅ Meeting with {person} scheduled at {meeting_time.strftime('%I:%M %p, %d %b %Y')}"
        })
    
    return jsonify({'success': False, 'message': 'Could not understand the command.'})

@app.route('/meetings')
def get_meetings():
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT person, time FROM meetings ORDER BY time")
    meetings = cursor.fetchall()
    conn.close()
    
    formatted_meetings = []
    for person, time_str in meetings:
        meeting_time = datetime.fromisoformat(time_str)
        formatted_meetings.append({
            'person': person,
            'time': meeting_time.strftime('%I:%M %p, %d %b %Y')
        })
    
    return jsonify(formatted_meetings)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
