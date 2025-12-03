"""
Access log parser (Common Web Access Format)
Fields: timestamp, ip, method, endpoint, status, size
"""

import re
from datetime import datetime
from typing import Optional, Dict


class AccessParser:
    """Parser for web access logs (nginx/apache format)"""
    
    # Common format: IP - - [timestamp] "METHOD /endpoint HTTP/1.1" STATUS SIZE
    # Example: 192.168.1.1 - - [13/Feb/2025:11:22:33 +0000] "GET /api/users HTTP/1.1" 200 1234
    # Also handles: IP - user [timestamp] "METHOD /endpoint HTTP/1.1" STATUS SIZE
    PATTERN = re.compile(
        r'^(\S+)\s+(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+"(\w+)\s+([^\s"]+)(?:\s+[^"]+)?"\s+(\d{3})\s+(\d+|-)$'
    )
    
    # Simpler pattern for logs without user field
    SIMPLE_PATTERN = re.compile(
        r'^(\S+)\s+-\s+-\s+\[([^\]]+)\]\s+"(\w+)\s+([^\s"]+)(?:\s+[^"]+)?"\s+(\d{3})\s+(\d+|-)$'
    )

    @staticmethod
    def parse(line: str) -> Optional[Dict]:
        """
        Parse an access log line into structured data
        
        Returns:
            Dict with keys: timestamp, ip, method, endpoint, status, size
            or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None

        # Try full pattern first (with user field)
        match = AccessParser.PATTERN.match(line)
        if match:
            ip, user1, user2, raw_timestamp, method, endpoint, status, size = match.groups()
            
            # Parse timestamp (common formats: 13/Feb/2025:11:22:33 +0000)
            timestamp = AccessParser._parse_timestamp(raw_timestamp)
            
            # Parse size (can be "-" for no size)
            try:
                size_int = int(size) if size != "-" else 0
            except ValueError:
                size_int = 0

            return {
                "timestamp": timestamp,
                "ip": ip,
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "size": size_int
            }

        # Try simpler pattern (without user field)
        match = AccessParser.SIMPLE_PATTERN.match(line)
        if match:
            ip, raw_timestamp, method, endpoint, status, size = match.groups()
            
            # Parse timestamp
            timestamp = AccessParser._parse_timestamp(raw_timestamp)
            
            # Parse size
            try:
                size_int = int(size) if size != "-" else 0
            except ValueError:
                size_int = 0

            return {
                "timestamp": timestamp,
                "ip": ip,
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "size": size_int
            }

        # Fallback: try even simpler pattern (more lenient)
        simple_match = re.match(r'^(\S+).*?\[([^\]]+)\].*?"(\w+)\s+([^\s"]+).*?"\s+(\d{3})', line)
        if simple_match:
            ip, raw_timestamp, method, endpoint, status = simple_match.groups()
            timestamp = AccessParser._parse_timestamp(raw_timestamp)
            return {
                "timestamp": timestamp,
                "ip": ip,
                "method": method,
                "endpoint": endpoint,
                "status": status,
                "size": 0
            }

        return None

    @staticmethod
    def _parse_timestamp(raw_ts: str) -> str:
        """Parse access log timestamp to ISO format"""
        try:
            # Try common formats
            for fmt in [
                "%d/%b/%Y:%H:%M:%S %z",
                "%d/%b/%Y:%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(raw_ts, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # If all fail, return as-is
            return raw_ts
        except Exception:
            return raw_ts

