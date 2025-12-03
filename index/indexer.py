"""
Indexer for storing parsed logs in SQLite
"""

import sqlite3
import os
import re
from typing import List, Dict, Optional


class Indexer:
    """SQLite-based indexer for log storage and retrieval"""
    
    def __init__(self, db_path: str = "coresight.db"):
        """
        Initialize the indexer
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        cur = self.conn.cursor()
        
        # Check if table exists and has correct schema
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='logs'")
        table_exists = cur.fetchone()
        
        if table_exists:
            # Check if log_type column exists
            cur.execute("PRAGMA table_info(logs)")
            columns = [row[1] for row in cur.fetchall()]
            if 'log_type' not in columns:
                # Old schema - drop and recreate
                cur.execute("DROP TABLE IF EXISTS logs")
                table_exists = False
        
        if not table_exists:
            # Create table with correct schema
            cur.execute("""
            CREATE TABLE logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT NOT NULL,
                timestamp TEXT,
                host TEXT,
                service TEXT,
                message TEXT,
                ip TEXT,
                method TEXT,
                endpoint TEXT,
                status TEXT,
                size INTEGER,
                user TEXT,
                action TEXT,
                raw TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        # Create indexes for common queries (only if they don't exist)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_log_type ON logs(log_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ip ON logs(ip)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_user ON logs(user)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_status ON logs(status)")
        except sqlite3.OperationalError:
            # Indexes might already exist or table structure issue
            pass
        
        self.conn.commit()

    def add_log(self, log_type: str, parsed_data: Dict, raw_line: str = "") -> bool:
        """
        Add a parsed log entry to the index
        
        Args:
            log_type: Type of log (syslog, access, auth)
            parsed_data: Parsed log data as dictionary
            raw_line: Original raw log line
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cur = self.conn.cursor()
            
            # Map parsed data to database columns
            cur.execute("""
                INSERT INTO logs (
                    log_type, timestamp, host, service, message,
                    ip, method, endpoint, status, size, user, action, raw
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_type,
                parsed_data.get("timestamp"),
                parsed_data.get("host"),
                parsed_data.get("service"),
                parsed_data.get("message"),
                parsed_data.get("ip"),
                parsed_data.get("method"),
                parsed_data.get("endpoint"),
                parsed_data.get("status"),
                parsed_data.get("size", 0),
                parsed_data.get("user"),
                parsed_data.get("action"),
                raw_line
            ))
            
            # Don't commit here - let caller batch commits for performance
            return True
        except Exception as e:
            return False
    
    def commit(self):
        """Commit pending database changes"""
        try:
            self.conn.commit()
            return True
        except Exception as e:
            return False

    def query(self, where_clause: str = "1=1", limit: int = 1000) -> List[Dict]:
        """
        Query logs from the index
        
        Args:
            where_clause: SQL WHERE clause (without WHERE keyword)
            limit: Maximum number of results
            
        Returns:
            List of log dictionaries
        """
        try:
            cur = self.conn.cursor()
            # Note: where_clause is built by QueryParser which sanitizes input
            # For safety, we validate it only contains safe characters
            # In production, consider using parameterized queries for all parts
            if not re.match(r'^[a-zA-Z0-9_<>=()\s\'\",\.:\-+%LIKEISNOTANDOR]+$', where_clause):
                return [{"error": "Invalid WHERE clause"}]
            sql = f"SELECT * FROM logs WHERE {where_clause} ORDER BY id DESC LIMIT ?"
            rows = cur.execute(sql, (limit,))
            return [dict(row) for row in rows]
        except Exception as e:
            return [{"error": str(e)}]

    def get_all(self, limit: int = 1000) -> List[Dict]:
        """Get all logs"""
        return self.query("1=1", limit)

    def count(self, where_clause: str = "1=1") -> int:
        """Count logs matching the where clause"""
        try:
            cur = self.conn.cursor()
            sql = f"SELECT COUNT(*) as count FROM logs WHERE {where_clause}"
            result = cur.execute(sql).fetchone()
            return result["count"] if result else 0
        except Exception:
            return 0

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __del__(self):
        """Cleanup on deletion"""
        self.close()

