#!/usr/bin/env python3
# Simple training service for the learning system

from flask import Flask, render_template, request, jsonify
from learning_system import LearningSystem

app = Flask(__name__)
learning_system = LearningSystem()

# Simple training service endpoints
@app.route('/')
def index():
    return "Learning System Training Service"

@app.route('/stats')
def get_stats():
    return jsonify(learning_system.get_learning_stats())

@app.route('/feedback', methods=['POST'])
def feedback():
    data = request.json
    original_command = data.get('original_command')
    corrected_data = data.get('corrected_data')
    
    if original_command and corrected_data:
        success = learning_system.learn_from_correction(original_command, corrected_data)
        return jsonify({'success': success})
    
    return jsonify({'success': False, 'message': 'Missing required data'})

@app.route('/suggest', methods=['POST'])
def suggest():
    command = request.json.get('command')
    suggestion = learning_system.suggest_command_interpretation(command)
    return jsonify(suggestion)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
