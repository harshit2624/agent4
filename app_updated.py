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
    
    # Create meetings table with status column
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT,
            time TEXT,
            agenda TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    # Add status column to existing table if it doesn't exist
    try:
        cursor.execute("ALTER TABLE meetings ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        # Column already exists, ignore
        pass
    
<<<<<<< HEAD
    # Create solana_alerts table for persistent storage
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solana_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            email TEXT NOT NULL,
            price REAL,
            min_price REAL,
            max_price REAL,
            triggered BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
=======
>>>>>>> 0c70400fa145562ce84df59fbbd1fe784c9b5a51
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

@app.route('/meeting/<int:meeting_id>')
def meeting_detail(meeting_id):
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda FROM meetings WHERE id = ?", (meeting_id,))
    meeting = cursor.fetchone()
    conn.close()
    
    if not meeting:
        return "Meeting not found", 404
    
    id, person, time_str, agenda = meeting
    meeting_time = datetime.fromisoformat(time_str)
    
    return render_template('meeting_edit.html', 
                         meeting={
                             'id': id,
                             'person': person,
                             'time': meeting_time.strftime('%Y-%m-%dT%H:%M'),
                             'agenda': agenda or ''
                         })

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
    cursor.execute("SELECT id, person, time, agenda, status FROM meetings ORDER BY time")
    meetings = cursor.fetchall()
    conn.close()
    
    formatted_meetings = []
    for id, person, time_str, agenda, status in meetings:
        meeting_time = datetime.fromisoformat(time_str)
        meeting_data = {
            'id': id,
            'person': person,
            'time': meeting_time.strftime('%I:%M %p, %d %b %Y'),
            'time_iso': time_str,
            'agenda': agenda or '',
            'status': status or 'pending'
        }
        formatted_meetings.append(meeting_data)
    
    return jsonify(formatted_meetings)

@app.route('/meetings/pending')
def get_pending_meetings():
    """Get all pending meetings"""
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, person, time, agenda, status 
        FROM meetings 
        WHERE status = 'pending' 
        ORDER BY time
    """)
    meetings = cursor.fetchall()
    conn.close()
    
    formatted_meetings = []
    for id, person, time_str, agenda, status in meetings:
        meeting_time = datetime.fromisoformat(time_str)
        meeting_data = {
            'id': id,
            'person': person,
            'time': meeting_time.strftime('%I:%M %p, %d %b %Y'),
            'time_iso': time_str,
            'agenda': agenda or '',
            'status': status
        }
        formatted_meetings.append(meeting_data)
    
    return jsonify(formatted_meetings)

@app.route('/meetings/completed')
def get_completed_meetings():
    """Get all completed meetings"""
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, person, time, agenda, status 
        FROM meetings 
        WHERE status = 'completed' 
        ORDER BY time
    """)
    meetings = cursor.fetchall()
    conn.close()
    
    formatted_meetings = []
    for id, person, time_str, agenda, status in meetings:
        meeting_time = datetime.fromisoformat(time_str)
        meeting_data = {
            'id': id,
            'person': person,
            'time': meeting_time.strftime('%I:%M %p, %d %b %Y'),
            'time_iso': time_str,
            'agenda': agenda or '',
            'status': status
        }
        formatted_meetings.append(meeting_data)
    
    return jsonify(formatted_meetings)

@app.route('/meetings/<int:meeting_id>/complete', methods=['POST'])
def mark_meeting_complete(meeting_id):
    """Mark a meeting as completed"""
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE meetings 
        SET status = 'completed' 
        WHERE id = ?
    """, (meeting_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Meeting not found'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Meeting marked as completed'})

@app.route('/meetings/<int:meeting_id>')
def get_meeting(meeting_id):
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda FROM meetings WHERE id = ?", (meeting_id,))
    meeting = cursor.fetchone()
    conn.close()
    
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404
    
    id, person, time_str, agenda = meeting
    meeting_time = datetime.fromisoformat(time_str)
    
    return jsonify({
        'id': id,
        'person': person,
        'time': meeting_time.strftime('%Y-%m-%dT%H:%M'),
        'agenda': agenda or ''
    })

@app.route('/meetings/<int:meeting_id>', methods=['PUT'])
def update_meeting(meeting_id):
    data = request.json
    person = data.get('person')
    time_str = data.get('time')
    agenda = data.get('agenda', '')
    
    if not person or not time_str:
        return jsonify({'error': 'Person and time are required'}), 400
    
    try:
        meeting_time = datetime.fromisoformat(time_str)
    except ValueError:
        return jsonify({'error': 'Invalid time format'}), 400
    
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE meetings 
        SET person = ?, time = ?, agenda = ? 
        WHERE id = ?
    """, (person, meeting_time.isoformat(), agenda, meeting_id))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Meeting not found'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Meeting updated successfully'})

@app.route('/meetings/<int:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Meeting not found'}), 404
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Meeting deleted successfully'})

# API routes for meeting update/delete to match frontend
@app.route('/api/meeting/<int:meeting_id>', methods=['PUT'])
def api_update_meeting(meeting_id):
    return update_meeting(meeting_id)

@app.route('/api/meeting/<int:meeting_id>', methods=['DELETE'])
def api_delete_meeting(meeting_id):
    return delete_meeting(meeting_id)

@app.route('/api/meeting/<int:meeting_id>/notify-other', methods=['POST'])
def notify_other_person(meeting_id):
    data = request.json
    email = data.get('email')
    person = data.get('person')
    agenda = data.get('agenda')
    time_str = data.get('time')
    host = data.get('host')
    if not email:
        return jsonify({'success': False, 'error': 'Email is required'})
    # If any of person, agenda, or time is missing, fetch from DB
    if not (person and agenda is not None and time_str):
        conn = sqlite3.connect("meetings.db")
        cursor = conn.cursor()
        cursor.execute("SELECT person, time, agenda FROM meetings WHERE id = ?", (meeting_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return jsonify({'success': False, 'error': 'Meeting not found'})
        person, time_str, agenda = row
    host_name = host if host else person
    try:
        meeting_time = datetime.fromisoformat(time_str)
    except Exception:
        return jsonify({'success': False, 'error': 'Invalid meeting time'})
    # Send email now
    subject = f"Meeting Scheduled with {host_name}"
    body = f"""
Hello,

You have a meeting scheduled with {host_name}.

Agenda: {agenda or 'No agenda provided'}
Time: {meeting_time.strftime('%I:%M %p, %d %b %Y')}
Host: {host_name}

You will also receive a reminder 10 minutes before the meeting.

Best regards,
Meeting Scheduler Bot
"""
    EmailNotifier().send_custom_notification(email, subject, body)
    # Schedule reminder
    def send_reminder():
        now = datetime.now()
        reminder_time = meeting_time - timedelta(minutes=10)
        delay = (reminder_time - now).total_seconds()
        if delay > 0:
            time.sleep(delay)
        reminder_subject = f"Meeting Reminder: Meeting with {host_name} in 10 minutes"
        reminder_body = f"""
Hello,

This is a reminder for your meeting with {host_name}.

Agenda: {agenda or 'No agenda provided'}
Time: {meeting_time.strftime('%I:%M %p, %d %b %Y')}
Host: {host_name}

The meeting starts in 10 minutes.

Best regards,
Meeting Scheduler Bot
"""
        EmailNotifier().send_custom_notification(email, reminder_subject, reminder_body)
    t = threading.Thread(target=send_reminder)
    t.daemon = True
    t.start()
    return jsonify({'success': True})

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

@app.route('/meeting/<int:meeting_id>/edit')
def edit_meeting(meeting_id):
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda FROM meetings WHERE id = ?", (meeting_id,))
    meeting = cursor.fetchone()
    conn.close()
    if not meeting:
        return "Meeting not found", 404
    id, person, time_str, agenda = meeting
    meeting_time = datetime.fromisoformat(time_str)
    return render_template('meeting_edit.html', 
        meeting={
            'id': id,
            'person': person,
            'time': meeting_time.strftime('%Y-%m-%dT%H:%M'),
            'agenda': agenda or ''
        }
    )

import threading
import time
import requests

<<<<<<< HEAD
=======
# In-memory Solana alert storage (for demo; use DB for production)
solana_alerts = []
>>>>>>> 0c70400fa145562ce84df59fbbd1fe784c9b5a51
solana_last_price = None

def get_solana_price():
    try:
        resp = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT', timeout=5)
        data = resp.json()
        return float(data['price'])
    except Exception:
        return None

@app.route('/solana/price')
def solana_price():
    price = get_solana_price()
    if price is not None:
        global solana_last_price
        solana_last_price = price
    return jsonify({'price': price})

@app.route('/solana/alert', methods=['POST'])
def solana_alert():
    data = request.json
    alert_type = data.get('type')
    email = data.get('email')
    if not email or not alert_type:
        return jsonify({'success': False, 'error': 'Email and alert type required'})
<<<<<<< HEAD
    
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    
=======
>>>>>>> 0c70400fa145562ce84df59fbbd1fe784c9b5a51
    if alert_type == 'range':
        min_price = data.get('min')
        max_price = data.get('max')
        if min_price is None or max_price is None:
<<<<<<< HEAD
            conn.close()
            return jsonify({'success': False, 'error': 'Min and max price required'})
        
        cursor.execute("""
            INSERT INTO solana_alerts (alert_type, email, min_price, max_price)
            VALUES (?, ?, ?, ?)
        """, ('range', email, min_price, max_price))
    else:
        price = data.get('price')
        if price is None:
            conn.close()
            return jsonify({'success': False, 'error': 'Price required'})
        
        cursor.execute("""
            INSERT INTO solana_alerts (alert_type, email, price)
            VALUES (?, ?, ?)
        """, (alert_type, email, price))
    
    conn.commit()
    conn.close()
=======
            return jsonify({'success': False, 'error': 'Min and max price required'})
        solana_alerts.append({'type': 'range', 'min': min_price, 'max': max_price, 'email': email, 'triggered': False})
    else:
        price = data.get('price')
        if price is None:
            return jsonify({'success': False, 'error': 'Price required'})
        solana_alerts.append({'type': alert_type, 'price': price, 'email': email, 'triggered': False})
>>>>>>> 0c70400fa145562ce84df59fbbd1fe784c9b5a51
    return jsonify({'success': True})

@app.route('/solana/alerts')
def solana_alerts_list():
<<<<<<< HEAD
    conn = sqlite3.connect("meetings.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, alert_type, email, price, min_price, max_price, triggered
        FROM solana_alerts
        WHERE triggered = 0
        ORDER BY created_at DESC
    """)
    
    alerts = []
    for row in cursor.fetchall():
        id, alert_type, email, price, min_price, max_price, triggered = row
        alert_data = {
            'id': id,
            'type': alert_type,
            'email': email,
            'triggered': bool(triggered)
        }
        
        if alert_type == 'range':
            alert_data['min'] = min_price
            alert_data['max'] = max_price
        else:
            alert_data['price'] = price
            
        alerts.append(alert_data)
    
    conn.close()
    return jsonify(alerts)
=======
    # Do not expose emails in production! For demo only.
    return jsonify([
        {k: v for k, v in alert.items() if k != 'triggered'} for alert in solana_alerts
    ])
>>>>>>> 0c70400fa145562ce84df59fbbd1fe784c9b5a51

def solana_alert_checker():
    while True:
        price = get_solana_price()
        if price is not None:
<<<<<<< HEAD
            conn = sqlite3.connect("meetings.db")
            cursor = conn.cursor()
            
            # Get all non-triggered alerts
            cursor.execute("""
                SELECT id, alert_type, email, price, min_price, max_price
                FROM solana_alerts
                WHERE triggered = 0
            """)
            
            alerts = cursor.fetchall()
            
            for alert_row in alerts:
                alert_id, alert_type, email, price_val, min_price, max_price = alert_row
                
                should_trigger = False
                alert_message = ""
                
                if alert_type == 'above' and price > price_val:
                    should_trigger = True
                    alert_message = f'Solana price is above ${price_val}: Current price ${price}'
                elif alert_type == 'below' and price < price_val:
                    should_trigger = True
                    alert_message = f'Solana price is below ${price_val}: Current price ${price}'
                elif alert_type == 'range' and min_price <= price <= max_price:
                    should_trigger = True
                    alert_message = f'Solana price is in your range ${min_price} - ${max_price}: Current price ${price}'
                
                if should_trigger:
                    EmailNotifier().send_custom_notification(
                        email, 
                        f'Solana Price Alert', 
                        alert_message
                    )
                    
                    # Update triggered status in database
                    cursor.execute("""
                        UPDATE solana_alerts
                        SET triggered = 1
                        WHERE id = ?
                    """, (alert_id,))
                    conn.commit()
            
            conn.close()
        time.sleep(10)
=======
            for alert in solana_alerts:
                if alert.get('triggered'):
                    continue
                if alert['type'] == 'above' and price > alert['price']:
                    EmailNotifier().send_custom_notification(alert['email'], f'Solana Price Alert', f'Solana price is above ${alert["price"]}: Current price ${price}')
                    alert['triggered'] = True
                elif alert['type'] == 'below' and price < alert['price']:
                    EmailNotifier().send_custom_notification(alert['email'], f'Solana Price Alert', f'Solana price is below ${alert["price"]}: Current price ${price}')
                    alert['triggered'] = True
                elif alert['type'] == 'range' and alert['min'] <= price <= alert['max']:
                    EmailNotifier().send_custom_notification(alert['email'], f'Solana Price Alert', f'Solana price is in your range ${alert["min"]} - ${alert["max"]}: Current price ${price}')
                    alert['triggered'] = True
        time.sleep(60)
>>>>>>> 0c70400fa145562ce84df59fbbd1fe784c9b5a51

# Start background checker thread
threading.Thread(target=solana_alert_checker, daemon=True).start()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
