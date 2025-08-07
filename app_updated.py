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
            time TEXT,
            agenda TEXT
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
    
    # Handle scheduling commands with time and optional agenda - improved regex patterns
    command = command.lower()
    
    # Pattern 1: "schedule meeting with [name] at [time] for [agenda]"
    match = re.search(r'(?:schedule|meet|meeting)?\s*meeting?\s*with\s+([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2})(?:\s*(tomorrow))?(?:\s+for\s+(.+?))?(?:\s*$)', command)
    if not match:
        # Pattern 2: "schedule [name] at [time] for [agenda]"
        match = re.search(r'(?:schedule|meet|meeting)?\s*([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2})(?:\s*(tomorrow))?(?:\s+for\s+(.+?))?(?:\s*$)', command)
    if not match:
        # Pattern 3: More flexible matching for various formats
        match = re.search(r'(?:schedule|meet|meeting)?\s*(?:meeting)?\s*(?:with)?\s*([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2})(?:\s*(tomorrow))?(?:\s+for\s+(.+?))?(?:\s*$)', command)
    if not match:
        # Pattern 4: Handle cases like "4" or "4pm" or "4:30pm"
        match = re.search(r'(?:schedule|meet|meeting)?\s*(?:meeting)?\s*(?:with)?\s*([\w\s]+?)\s+at\s+(\d{1,2}(?::\d{2})?(?:\s*(?:am|pm))?)(?:\s*(tomorrow))?(?:\s+for\s+(.+?))?(?:\s*$)', command)
    if match:
        person = match.group(1).strip().title()
        time_str = match.group(2).strip()
        tomorrow = match.group(3)
        agenda = match.group(4).strip() if match.group(4) else None

        now = datetime.now()
        time_str = time_str.strip()
        
        # Handle single digit like "4" - assume PM for business hours
        if time_str.isdigit() and 1 <= int(time_str) <= 12:
            hour = int(time_str)
            # Assume PM for business hours (9-17), AM for 8 and below
            if hour >= 9 and hour <= 17:
                ampm = "PM"
            elif hour <= 8:
                ampm = "AM"
            else:
                ampm = "PM"
            time_str = f"{hour}:00 {ampm}"
        
        # Handle cases like "4pm" or "4:30pm"
        elif len(time_str) <= 4 and time_str[-2:].lower() in ['am', 'pm']:
            time_str = time_str[:-2] + " " + time_str[-2:].upper()
            if ":" not in time_str:
                time_str = time_str.replace(" ", ":00 ")
        
        # Handle cases like "4:30" without AM/PM - assume PM
        elif ":" in time_str and not any(ampm in time_str.lower() for ampm in ['am', 'pm']):
            time_str = time_str + " PM"
        
        # Handle cases like "430pm"
        elif len(time_str) >= 3 and len(time_str) <= 5 and time_str[-2:].lower() in ['am', 'pm']:
            digits = time_str[:-2]
            ampm = time_str[-2:].upper()
            if ":" not in digits:
                if len(digits) <= 2:
                    time_str = f"{digits}:00 {ampm}"
                else:
                    # Handle 430 -> 4:30
                    hour = digits[:-2] if len(digits) > 2 else digits
                    minute = digits[-2:] if len(digits) > 2 else "00"
                    time_str = f"{hour}:{minute} {ampm}"
        
        try:
            meeting_time = datetime.strptime(time_str, "%I:%M %p")
        except ValueError:
            try:
                meeting_time = datetime.strptime(time_str, "%I %p")
            except ValueError:
                try:
                    meeting_time = datetime.strptime(time_str, "%I:%M%p")
                except ValueError:
                    try:
                        meeting_time = datetime.strptime(time_str, "%I%p")
                    except ValueError:
                        try:
                            meeting_time = datetime.strptime(time_str, "%H:%M")
                        except ValueError:
                            try:
                                meeting_time = datetime.strptime(time_str, "%H")
                            except ValueError:
                                return None, None

        meeting_time = meeting_time.replace(year=now.year, month=now.month, day=now.day)

        if tomorrow:
            meeting_time += timedelta(days=1)

        return 'schedule', (person, meeting_time, agenda)
    
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
        cursor.execute("SELECT person, time, agenda FROM meetings WHERE date(time) = ? ORDER BY time", (today.isoformat(),))
        today_meetings = cursor.fetchall()
        
        # Get all meetings for context
        cursor.execute("SELECT person, time, agenda FROM meetings ORDER BY time")
        all_meetings = cursor.fetchall()
        conn.close()
        
        if not today_meetings and not all_meetings:
            return jsonify({
                'success': True,
                'message': "No meetings scheduled today or in the future."
            })
        
        if today_meetings:
            meeting_list = []
            for person, time_str, agenda in today_meetings:
                meeting_time = datetime.fromisoformat(time_str)
                meeting_info = f"{person} at {meeting_time.strftime('%I:%M %p')}"
                if agenda:
                    meeting_info += f" - {agenda}"
                meeting_list.append(meeting_info)
            
            meetings_text = "\n".join(f"• {meeting}" for meeting in meeting_list)
            return jsonify({
                'success': True,
                'message': f"📅 You have {len(today_meetings)} meeting(s) scheduled today:\n{meetings_text}"
            })
        else:
            # Show upcoming meetings if none today
            upcoming_list = []
            for person, time_str, agenda in all_meetings[:5]:  # Show next 5 meetings
                meeting_time = datetime.fromisoformat(time_str)
                meeting_info = f"{person} at {meeting_time.strftime('%I:%M %p, %d %b')}"
                if agenda:
                    meeting_info += f" - {agenda}"
                upcoming_list.append(meeting_info)
            
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
    
    elif result_type == 'schedule':
        # Handle scheduling
        person, meeting_time, agenda = result_data
        if not person:
            return jsonify({'success': False, 'message': 'Could not understand the command.'})

        conn = sqlite3.connect("meetings.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO meetings (person, time, agenda) VALUES (?, ?, ?)", 
                       (person, meeting_time.isoformat(), agenda))
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
    
    # Log failed command for learning
    learning_system.log_failed_command(command, "Could not parse command")
    
    # Check for similar commands that were resolved
    suggestion = learning_system.suggest_command_interpretation(command)
    if suggestion:
        return jsonify({
            'success': False,
            'message': f"I didn't understand that command. Did you mean: {suggestion['based_on']}?",
            'suggestion': suggestion,
            'needs_learning': True
        })
    
    return jsonify({
        'success': False, 
        'message': 'Could not understand the command.',
        'needs_learning': True
    })

@app.route('/meetings')
def get_meetings():
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT person, time, agenda FROM meetings ORDER BY time")
    meetings = cursor.fetchall()
    conn.close()
    
    formatted_meetings = []
    for person, time_str, agenda in meetings:
        meeting_time = datetime.fromisoformat(time_str)
        meeting_data = {
            'person': person,
            'time': meeting_time.strftime('%I:%M %p, %d %b %Y')
        }
        if agenda:
            meeting_data['agenda'] = agenda
        formatted_meetings.append(meeting_data)
    
    return jsonify(formatted_meetings)

@app.route('/learning/stats', methods=['GET'])
def get_learning_stats():
    """Get learning system statistics"""
    stats = learning_system.get_learning_stats()
    return jsonify(stats)

@app.route('/learning/feedback', methods=['POST'])
def provide_learning_feedback():
    """Endpoint for users to provide feedback on failed commands"""
    data = request.json
    original_command = data.get('original_command')
    corrected_data = data.get('corrected_data')
    
    if original_command and corrected_data:
        success = learning_system.learn_from_correction(original_command, corrected_data)
        return jsonify({'success': success})
    
    return jsonify({'success': False, 'message': 'Missing required data'})

@app.route('/learning/failed-commands', methods=['GET'])
def get_failed_commands():
    """Get recent failed commands for review"""
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT command, failure_reason, timestamp 
        FROM failed_commands 
        WHERE resolved = FALSE 
        ORDER BY timestamp DESC 
        LIMIT 10
    """)
    
    failed_commands = []
    for command, reason, timestamp in cursor.fetchall():
        failed_commands.append({
            'command': command,
            'reason': reason,
            'timestamp': timestamp
        })
    
    conn.close()
    return jsonify(failed_commands)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
