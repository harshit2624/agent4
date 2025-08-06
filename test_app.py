import pytest
import json
from app_updated import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Meeting Scheduler' in response.data

def test_get_meetings(client):
    response = client.get('/meetings')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_schedule_meeting_success(client):
    command = "Schedule meeting with Alice at 3pm"
    response = client.post('/schedule', json={'command': command})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert 'Alice' in data['message']

def test_schedule_meeting_missing_time(client):
    command = "Schedule meeting with Bob"
    response = client.post('/schedule', json={'command': command})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is False
    assert data.get('missing_time') is True

def test_learning_feedback(client):
    original_command = "Schedule meeting with Charlie"
    corrected_data = {
        'type': 'schedule',
        'person': 'Charlie',
        'time': '4pm'
    }
    response = client.post('/learning/feedback', json={
        'original_command': original_command,
        'corrected_data': corrected_data
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True

def test_get_learning_stats(client):
    response = client.get('/learning/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_failed_commands' in data

def test_get_failed_commands(client):
    response = client.get('/learning/failed-commands')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
