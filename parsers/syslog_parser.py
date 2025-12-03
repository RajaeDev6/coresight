"""
Syslog parser
Fields: timestamp, host, service, message
"""

import re
from datetime import datetime
from typing import Optional, Dict


class SyslogParser:
    """Parser for syslog format logs"""
    
    # Pattern for classic syslog: Jan 12 11:33:22 hostname service[pid]: message
    CLASSIC_PATTERN = re.compile(
        r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+)(?:\[(\d+)\])?:\s*(.*)$"
    )
    
    # Pattern for ISO/RFC3339 syslog: 2025-02-13T11:22:33 hostname service: message
    ISO_PATTERN = re.compile(
        r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?)\s+(\S+)\s+(\S+)(?:\[(\d+)\])?:\s*(.*)$"
    )

    @staticmethod
    def parse(line: str) -> Optional[Dict]:
        """
        Parse a syslog line into structured data
        
        Returns:
            Dict with keys: timestamp, host, service, message
            or None if parsing fails
        """
        line = line.strip()
        if not line:
            return None

        # Try ISO format first
        match = SyslogParser.ISO_PATTERN.match(line)
        if match:
            ts_str, host, service, pid, message = match.groups()
            timestamp = SyslogParser._parse_iso_timestamp(ts_str)
            service_full = f"{service}[{pid}]" if pid else service
            return {
                "timestamp": timestamp,
                "host": host,
                "service": service_full,
                "message": message or ""
            }

        # Try classic format
        match = SyslogParser.CLASSIC_PATTERN.match(line)
        if match:
            ts_str, host, service, pid, message = match.groups()
            timestamp = SyslogParser._parse_classic_timestamp(ts_str)
            service_full = f"{service}[{pid}]" if pid else service
            return {
                "timestamp": timestamp,
                "host": host,
                "service": service_full,
                "message": message or ""
            }

        # Fallback: try to extract at least timestamp and message
        # Look for ISO timestamp at start
        iso_match = re.match(r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})", line)
        if iso_match:
            timestamp = SyslogParser._parse_iso_timestamp(iso_match.group(1))
            parts = line.split(None, 2)
            host = parts[1] if len(parts) > 1 else "unknown"
            service = parts[2].split(":")[0] if len(parts) > 2 else "unknown"
            message = parts[2].split(":", 1)[1] if len(parts) > 2 and ":" in parts[2] else line
            return {
                "timestamp": timestamp,
                "host": host,
                "service": service,
                "message": message
            }

        # Look for classic timestamp
        classic_match = re.match(r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", line)
        if classic_match:
            timestamp = SyslogParser._parse_classic_timestamp(classic_match.group(1))
            parts = line.split(None, 2)
            host = parts[1] if len(parts) > 1 else "unknown"
            service = parts[2].split(":")[0] if len(parts) > 2 else "unknown"
            message = parts[2].split(":", 1)[1] if len(parts) > 2 and ":" in parts[2] else line
            return {
                "timestamp": timestamp,
                "host": host,
                "service": service,
                "message": message
            }

        return None

    @staticmethod
    def _parse_iso_timestamp(ts_str: str) -> str:
        """Parse ISO/RFC3339 timestamp to ISO format"""
        try:
            # Try various ISO formats
            for fmt in [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S%z",
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
        """Parse classic syslog timestamp (Jan 12 11:33:22) to ISO format"""
        try:
            current_year = datetime.now().year
            dt = datetime.strptime(f"{ts_str} {current_year}", "%b %d %H:%M:%S %Y")
            return dt.isoformat()
        except Exception:
            return ts_str

