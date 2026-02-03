import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite database manager for email history and analytics"""
    
    def __init__(self, db_path='inbox_zero.db'):
        self.db_path = db_path
        self._lock = None  # Will be set for thread safety
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with better locking"""
        conn = sqlite3.connect(
            self.db_path, 
            timeout=30.0,
            isolation_level='IMMEDIATE',  # Reduces lock conflicts
            check_same_thread=False  # Allow multi-threading
        )
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging for better concurrency
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Email history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_history (
                    email_id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body_snippet TEXT,
                    category TEXT,
                    priority TEXT,
                    ai_response TEXT,
                    clean_reply TEXT,
                    needs_reply BOOLEAN,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent BOOLEAN DEFAULT 0,
                    sent_at TIMESTAMP,
                    archived BOOLEAN DEFAULT 0,
                    deleted BOOLEAN DEFAULT 0,
                    thread_id TEXT,
                    is_fallback BOOLEAN DEFAULT 0
                )
            ''')
            
            # Analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    total_emails INTEGER DEFAULT 0,
                    important_count INTEGER DEFAULT 0,
                    personal_count INTEGER DEFAULT 0,
                    newsletter_count INTEGER DEFAULT 0,
                    spam_count INTEGER DEFAULT 0,
                    replies_sent INTEGER DEFAULT 0,
                    emails_archived INTEGER DEFAULT 0,
                    emails_deleted INTEGER DEFAULT 0,
                    UNIQUE(date)
                )
            ''')
            
            # User preferences table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_processed_at 
                ON email_history(processed_at DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_category 
                ON email_history(category)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sent 
                ON email_history(sent)
            ''')
            
            logger.info("Database initialized successfully")
    
    def save_email_analysis(self, email_id: str, email_data: Dict, 
                           ai_result: Dict) -> bool:
        """Save email analysis to database with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO email_history 
                        (email_id, sender, subject, body_snippet, category, priority, 
                         ai_response, clean_reply, needs_reply, thread_id, is_fallback)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        email_id,
                        email_data.get('sender', ''),
                        email_data.get('subject', ''),
                        email_data.get('snippet', ''),
                        ai_result.get('category', 'Unknown'),
                        ai_result.get('priority', 'Medium'),
                        json.dumps(ai_result),
                        ai_result.get('reply', ''),
                        ai_result.get('needs_reply', False),
                        email_data.get('thread_id', ''),
                        ai_result.get('is_fallback', False)
                    ))
                    
                    logger.info(f"Saved analysis for email {email_id}")
                    return True
                    
            except sqlite3.OperationalError as e:
                if 'locked' in str(e) and attempt < max_retries - 1:
                    import time
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                logger.error(f"Error saving email analysis: {e}")
                return False
            except Exception as e:
                logger.error(f"Error saving email analysis: {e}")
                return False
        
        return False
    
    def get_email_analysis(self, email_id: str) -> Optional[Dict]:
        """Retrieve email analysis from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM email_history WHERE email_id = ?
                ''', (email_id,))
                
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    # Parse JSON fields
                    if result.get('ai_response'):
                        try:
                            result['ai_response_parsed'] = json.loads(result['ai_response'])
                        except:
                            pass
                    return result
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving email analysis: {e}")
            return None
    
    def mark_as_sent(self, email_id: str) -> bool:
        """Mark email as sent"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE email_history 
                    SET sent = 1, sent_at = CURRENT_TIMESTAMP
                    WHERE email_id = ?
                ''', (email_id,))
                
                logger.info(f"Marked email {email_id} as sent")
                return True
                
        except Exception as e:
            logger.error(f"Error marking as sent: {e}")
            return False
    
    def mark_as_archived(self, email_id: str) -> bool:
        """Mark email as archived"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE email_history SET archived = 1 WHERE email_id = ?
                ''', (email_id,))
                
                return True
                
        except Exception as e:
            logger.error(f"Error marking as archived: {e}")
            return False
    
    def mark_as_deleted(self, email_id: str) -> bool:
        """Mark email as deleted"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE email_history SET deleted = 1 WHERE email_id = ?
                ''', (email_id,))
                
                return True
                
        except Exception as e:
            logger.error(f"Error marking as deleted: {e}")
            return False
    
    def get_recent_emails(self, limit=50, include_deleted=False) -> List[Dict]:
        """Get recent emails from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT * FROM email_history 
                    WHERE deleted = 0
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''' if not include_deleted else '''
                    SELECT * FROM email_history 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                '''
                
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    email_dict = dict(row)
                    # Parse AI response
                    if email_dict.get('ai_response'):
                        try:
                            email_dict['ai_response_parsed'] = json.loads(email_dict['ai_response'])
                        except:
                            pass
                    results.append(email_dict)
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting recent emails: {e}")
            return []
    
    def get_analytics(self, days=30) -> Dict:
        """Get analytics for the last N days"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get summary stats
                cursor.execute('''
                    SELECT 
                        SUM(total_emails) as total,
                        SUM(important_count) as important,
                        SUM(personal_count) as personal,
                        SUM(newsletter_count) as newsletter,
                        SUM(spam_count) as spam,
                        SUM(replies_sent) as replies,
                        SUM(emails_archived) as archived,
                        SUM(emails_deleted) as deleted
                    FROM analytics 
                    WHERE date >= date('now', '-' || ? || ' days')
                ''', (days,))
                
                row = cursor.fetchone()
                
                # Get daily breakdown
                cursor.execute('''
                    SELECT * FROM analytics 
                    WHERE date >= date('now', '-' || ? || ' days')
                    ORDER BY date DESC
                ''', (days,))
                
                daily_data = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'summary': dict(row) if row else {},
                    'daily': daily_data
                }
                
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {'summary': {}, 'daily': []}
    
    def _update_analytics(self, category: str):
        """Update analytics for today"""
        today = datetime.now().date().isoformat()
        category_field = f"{category.lower()}_count"
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert or update today's analytics
                cursor.execute(f'''
                    INSERT INTO analytics (date, total_emails, {category_field})
                    VALUES (?, 1, 1)
                    ON CONFLICT(date) DO UPDATE SET
                        total_emails = total_emails + 1,
                        {category_field} = {category_field} + 1
                ''', (today,))
                
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
    
    def _increment_analytics_field(self, field: str):
        """Increment a specific analytics field for today"""
        today = datetime.now().date().isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    INSERT INTO analytics (date, {field})
                    VALUES (?, 1)
                    ON CONFLICT(date) DO UPDATE SET
                        {field} = {field} + 1
                ''', (today,))
                
        except Exception as e:
            logger.error(f"Error incrementing {field}: {e}")
    
    def clear_all_data(self):
        """Clear all data from database (use with caution!)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM email_history')
                cursor.execute('DELETE FROM analytics')
                logger.info("All data cleared from database")
                return True
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            return False
    
    def get_preference(self, key: str, default=None) -> Optional[str]:
        """Get user preference"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM user_preferences WHERE key = ?', (key,))
                row = cursor.fetchone()
                return row['value'] if row else default
        except Exception as e:
            logger.error(f"Error getting preference: {e}")
            return default
    
    def set_preference(self, key: str, value: str) -> bool:
        """Set user preference"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (key, value))
                return True
        except Exception as e:
            logger.error(f"Error setting preference: {e}")
            return False 