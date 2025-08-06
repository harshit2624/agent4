import sqlite3
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import hashlib

class LearningSystem:
    def __init__(self, db_path="meetings.db"):
        self.db_path = db_path
        self.init_learning_tables()
    
    def init_learning_tables(self):
        """Initialize database tables for learning system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Failed commands table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                command_hash TEXT UNIQUE NOT NULL,
                failure_reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                resolution_data TEXT
            )
        """)
        
        # Learned patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_regex TEXT NOT NULL,
                template TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME
            )
        """)
        
        # Command feedback table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_command TEXT NOT NULL,
                suggested_interpretation TEXT,
                user_feedback BOOLEAN,
                feedback_text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_failed_command(self, command: str, failure_reason: str) -> int:
        """Log a failed command for learning"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        cursor = conn.cursor()
        
        command_hash = hashlib.md5(command.lower().encode()).hexdigest()
        
        cursor.execute("""
            INSERT OR IGNORE INTO failed_commands (command, command_hash, failure_reason)
            VALUES (?, ?, ?)
        """, (command, command_hash, failure_reason))
        
        conn.commit()
        failed_id = cursor.lastrowid
        conn.close()
        
        return failed_id
    
    def learn_from_correction(self, original_command: str, corrected_data: Dict) -> bool:
        """Learn from user correction of a failed command"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        cursor = conn.cursor()
        
        # Update failed command as resolved
        command_hash = hashlib.md5(original_command.lower().encode()).hexdigest()
        cursor.execute("""
            UPDATE failed_commands 
            SET resolved = TRUE, resolution_data = ?
            WHERE command_hash = ?
        """, (json.dumps(corrected_data), command_hash))
        
        # Extract pattern from correction
        pattern_type = corrected_data.get('type')
        if pattern_type == 'schedule':
            pattern = self._extract_schedule_pattern(original_command, corrected_data)
            self._store_learned_pattern(pattern)
        
        conn.commit()
        conn.close()
        return True
    
    def _extract_schedule_pattern(self, command: str, data: Dict) -> Dict:
        """Extract scheduling pattern from successful correction"""
        person = data.get('person', '')
        time = data.get('time', '')
        
        # Create flexible regex pattern
        # Replace specific names and times with regex groups
        name_pattern = r'([\w\s]+?)'
        time_pattern = r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?)'
        
        # Common scheduling phrases
        patterns = [
            rf'schedule meeting with {name_pattern} at {time_pattern}',
            rf'meet with {name_pattern} at {time_pattern}',
            rf'set up meeting with {name_pattern} at {time_pattern}',
            rf'book meeting with {name_pattern} at {time_pattern}',
        ]
        
        return {
            'type': 'schedule',
            'patterns': patterns,
            'template': {
                'person': person,
                'time_format': 'flexible'
            }
        }
    
    def _store_learned_pattern(self, pattern: Dict):
        """Store extracted pattern in database"""
        conn = sqlite3.connect(self.db_path, timeout=10)
        cursor = conn.cursor()
        
        for regex_pattern in pattern['patterns']:
            cursor.execute("""
                INSERT OR IGNORE INTO learned_patterns 
                (pattern_type, pattern_regex, template, confidence)
                VALUES (?, ?, ?, ?)
            """, (
                pattern['type'],
                regex_pattern,
                json.dumps(pattern['template']),
                0.5  # Initial confidence
            ))
        
        conn.commit()
        conn.close()
    
    def find_similar_commands(self, command: str) -> List[Dict]:
        """Find similar previously failed commands that were resolved"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Simple similarity search based on keywords
        keywords = set(command.lower().split())
        
        cursor.execute("""
            SELECT command, resolution_data, COUNT(*) as frequency
            FROM failed_commands
            WHERE resolved = TRUE
            GROUP BY command
            ORDER BY frequency DESC
            LIMIT 5
        """)
        
        similar = []
        for cmd, resolution_data, freq in cursor.fetchall():
            resolution = json.loads(resolution_data) if resolution_data else {}
            cmd_keywords = set(cmd.lower().split())
            similarity = len(keywords.intersection(cmd_keywords)) / max(len(keywords), len(cmd_keywords))
            
            if similarity > 0.3:  # Threshold for similarity
                similar.append({
                    'command': cmd,
                    'resolution': resolution,
                    'similarity': similarity
                })
        
        conn.close()
        return similar
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about the learning system"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM failed_commands WHERE resolved = FALSE")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM failed_commands WHERE resolved = TRUE")
        resolved = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learned_patterns")
        patterns = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'pending_failures': pending,
            'resolved_failures': resolved,
            'learned_patterns': patterns
        }
    
    def suggest_command_interpretation(self, command: str) -> Optional[Dict]:
        """Suggest interpretation for failed command based on learning"""
        similar = self.find_similar_commands(command)
        
        if similar:
            # Return the most similar resolved command
            best_match = max(similar, key=lambda x: x['similarity'])
            return {
                'suggestion': best_match['resolution'],
                'confidence': best_match['similarity'],
                'based_on': best_match['command']
            }
        
        return None
    
    def update_pattern_confidence(self, pattern_id: int, success: bool):
        """Update confidence score for a learned pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if success:
            cursor.execute("""
                UPDATE learned_patterns 
                SET success_count = success_count + 1, 
                    usage_count = usage_count + 1,
                    last_used = CURRENT_TIMESTAMP,
                    confidence = (success_count + 1.0) / (usage_count + 1.0)
                WHERE id = ?
            """, (pattern_id,))
        else:
            cursor.execute("""
                UPDATE learned_patterns 
                SET usage_count = usage_count + 1,
                    last_used = CURRENT_TIMESTAMP,
                    confidence = success_count / (usage_count + 1.0)
                WHERE id = ?
            """, (pattern_id,))
        
        conn.commit()
        conn.close()
