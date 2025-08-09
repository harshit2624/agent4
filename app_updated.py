import os
import re
import psycopg2
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from email_notifications import EmailNotifier
from learning_system import LearningSystem
import threading
import time
import requests

app = Flask(__name__)
learning_system = LearningSystem()

def get_db_conn():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise Exception('DATABASE_URL environment variable not set')
    db_url = db_url.replace('postgres://', 'postgresql://')
    return psycopg2.connect(db_url)

def init_db():
    print('[DB] Initializing database...')
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id SERIAL PRIMARY KEY,
            person TEXT,
            time TEXT,
            agenda TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()
    print('[DB] Database initialized.')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/meeting/<int:meeting_id>')
def meeting_detail(meeting_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda FROM meetings WHERE id = %s", (meeting_id,))
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

@app.route('/meetings')
def get_meetings():
    print('[DB] /meetings endpoint called')
    conn = get_db_conn()
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
    print(f'[DB] Returning {len(formatted_meetings)} meetings')
    return jsonify(formatted_meetings)

@app.route('/meetings/pending')
def get_pending_meetings():
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda, status FROM meetings WHERE status = 'pending' ORDER BY time")
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
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda, status FROM meetings WHERE status = 'completed' ORDER BY time")
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
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE meetings 
        SET status = 'completed' 
        WHERE id = %s
    """, (meeting_id,))
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Meeting not found'}), 404
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Meeting marked as completed'})

@app.route('/meetings/<int:meeting_id>')
def get_meeting(meeting_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, person, time, agenda FROM meetings WHERE id = %s", (meeting_id,))
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
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE meetings 
        SET person = %s, time = %s, agenda = %s 
        WHERE id = %s
    """, (person, meeting_time.isoformat(), agenda, meeting_id))
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Meeting not found'}), 404
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Meeting updated successfully'})

@app.route('/meetings/<int:meeting_id>', methods=['DELETE'])
def delete_meeting(meeting_id):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meetings WHERE id = %s", (meeting_id,))
    if cursor.rowcount == 0:
        conn.close()
        return jsonify({'error': 'Meeting not found'}), 404
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Meeting deleted successfully'})

# Solana tracker in-memory storage (for demo)
solana_alerts = []
solana_last_price = None

def get_solana_price():
    try:
        print('[Solana] Fetching price from Binance...')
        resp = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT', timeout=5)
        data = resp.json()
        print(f'[Solana] Binance response: {data}')
        price = float(data['price']) if 'price' in data else None
        print(f'[Solana] Price fetched: {price}')
        return price
    except Exception as e:
        print(f'[Solana] Error fetching price: {e}')
        return None

@app.route('/solana/price')
def solana_price():
    print('[Solana] /solana/price endpoint called')
    price = get_solana_price()
    if price is not None:
        global solana_last_price
        solana_last_price = price
    else:
        print('[Solana] Price fetch failed, returning null')
    return jsonify({'price': price})

@app.route('/solana/alerts')
def solana_alerts_list():
    # Do not expose emails in production! For demo only.
    return jsonify([
        {k: v for k, v in alert.items() if k != 'triggered'} for alert in solana_alerts
    ])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)
