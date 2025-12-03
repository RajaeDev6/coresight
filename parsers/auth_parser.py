"""
Auth log parser
Fields: timestamp, user, action (login success/failure), ip
"""

import re
from datetime import datetime
from typing import Optional, Dict


class AuthParser:
    """Parser for authentication logs (auth.log, secure, etc.)"""
    
    # Pattern for auth logs: timestamp hostname service: message
    # Example: Jan 12 11:33:22 hostname sshd[1234]: Failed password for user from 192.168.1.1
    TIMESTAMP_PATTERN = re.compile(
        r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"
    )
    
    ISO_TIMESTAMP_PATTERN = re.compile(
        r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"
    )

    @staticmethod
    def parse(line: str) -> Optional[Dict]:
        """
        Parse an auth log line into structured data
        
        Returns:
            Dict with keys: timestamp, user, action, ip
            or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None

        # Extract timestamp
        timestamp = None
        rest = line
        
        # Try ISO format first
        iso_match = AuthParser.ISO_TIMESTAMP_PATTERN.match(line)
        if iso_match:
            timestamp = AuthParser._parse_iso_timestamp(iso_match.group(1))
            rest = line[iso_match.end():].strip()
        else:
            # Try classic format
            classic_match = AuthParser.TIMESTAMP_PATTERN.match(line)
            if classic_match:
                timestamp = AuthParser._parse_classic_timestamp(classic_match.group(1))
                rest = line[classic_match.end():].strip()

        if not timestamp:
            return None

        # Extract user, action, and IP
        user = None
        action = None
        ip = None

        # Look for login success
        if "Accepted password" in rest or "Accepted publickey" in rest:
            action = "login_success"
            # Extract user
            user_match = re.search(r"for\s+(\S+)", rest)
            if user_match:
                user = user_match.group(1)
            # Extract IP
            ip_match = re.search(r"from\s+(\d{1,3}(?:\.\d{1,3}){3})", rest)
            if ip_match:
                ip = ip_match.group(1)

        # Look for login failure
        elif "Failed password" in rest or "authentication failure" in rest.lower():
            action = "login_failure"
            # Extract user
            user_match = re.search(r"for\s+(\S+)", rest) or re.search(r"user\s+(\S+)", rest)
            if user_match:
                user = user_match.group(1)
            # Extract IP
            ip_match = re.search(r"from\s+(\d{1,3}(?:\.\d{1,3}){3})", rest)
            if ip_match:
                ip = ip_match.group(1)

        # Look for sudo events
        elif "sudo:" in rest:
            action = "sudo"
            sudo_match = re.search(r"sudo:\s+(\S+)", rest)
            if sudo_match:
                user = sudo_match.group(1)

        # Look for other authentication events
        elif "authentication" in rest.lower():
            action = "auth_event"
            user_match = re.search(r"user\s+(\S+)", rest)
            if user_match:
                user = user_match.group(1)

        # Default action if none matched
        if not action:
            action = "auth_event"

        # Extract IP if not found yet
        if not ip:
            ip_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", rest)
            if ip_match:
                ip = ip_match.group(1)

        return {
            "timestamp": timestamp,
            "user": user or "unknown",
            "action": action,
            "ip": ip
        }

    @staticmethod
    def _parse_iso_timestamp(ts_str: str) -> str:
        """Parse ISO timestamp to ISO format"""
        try:
            for fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(ts_str[:19], fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            return ts_str
        except Exception:
            return ts_str

    @staticmethod
    def _parse_classic_timestamp(ts_str: str) -> str:
        """Parse classic timestamp to ISO format"""
        try:
            current_year = datetime.now().year
            dt = datetime.strptime(f"{ts_str} {current_year}", "%b %d %H:%M:%S %Y")
            return dt.isoformat()
        except Exception:
            return ts_str

