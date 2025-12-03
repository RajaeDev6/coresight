"""
Query parser for SPL-like syntax
"""

import re
from datetime import datetime, timedelta
from typing import Tuple, Optional, List


class QueryParser:
    """Parser for SPL-like query syntax"""
    
    def __init__(self):
        self.field_mappings = {
            "host": "host",
            "service": "service",
            "ip": "ip",
            "user": "user",
            "status": "status",
            "method": "method",
            "endpoint": "endpoint",
            "action": "action",
            "log_type": "log_type",
            "type": "log_type"
        }

    def parse(self, query: str) -> Tuple[str, Optional[str]]:
        """
        Parse a query into WHERE clause and stats command
        
        Args:
            query: Query string (e.g., "error", "status=404", "last=15m")
            
        Returns:
            Tuple of (where_clause, stats_command)
        """
        query = query.strip()
        if not query:
            return "1=1", None

        # Split on pipe for stats
        if "|" in query:
            parts = query.split("|", 1)
            search_part = parts[0].strip()
            stats_part = parts[1].strip()
            where_clause = self._parse_search(search_part)
            return where_clause, stats_part
        
        where_clause = self._parse_search(query)
        return where_clause, None

    def _parse_search(self, search: str) -> str:
        """Parse search part into WHERE clause"""
        if not search:
            return "1=1"

        clauses = []
        tokens = self._tokenize(search)

        for token in tokens:
            # Field=value syntax
            if "=" in token and not token.startswith('"') and not token.startswith("last=") and not token.startswith("earliest=") and not token.startswith("latest="):
                key, value = token.split("=", 1)
                value = value.strip('"\'')
                key = key.strip()
                
                if key in self.field_mappings:
                    db_field = self.field_mappings[key]
                    # Handle partial matches for text fields
                    if db_field in ["service", "message", "user", "host", "endpoint", "action"]:
                        clauses.append(f"LOWER({db_field}) LIKE LOWER('%{value}%')")
                    else:
                        clauses.append(f"{db_field}='{value}'")
                continue

            # Time filtering: last=15m, last=24h, earliest=..., latest=...
            if token.startswith("last="):
                time_clause = self._parse_time_filter(token)
                if time_clause:
                    clauses.append(time_clause)
                continue
            
            # earliest= and latest= for date/time ranges (Splunk-like)
            if token.startswith("earliest="):
                time_clause = self._parse_earliest_latest(token, "earliest")
                if time_clause:
                    clauses.append(time_clause)
                continue
            
            if token.startswith("latest="):
                time_clause = self._parse_earliest_latest(token, "latest")
                if time_clause:
                    clauses.append(time_clause)
                continue

            # Keyword search (quoted or unquoted)
            if token == "*":
                # Wildcard means match all - don't add clause
                continue
            elif token.startswith('"') and token.endswith('"'):
                keyword = token.strip('"')
                # Search in multiple fields: raw log, message, service, user, etc. (case-insensitive)
                # Handle NULL values properly
                keyword_lower = keyword.lower()
                clauses.append(f"((raw IS NOT NULL AND LOWER(raw) LIKE '%{keyword_lower}%') OR "
                             f"(message IS NOT NULL AND LOWER(message) LIKE '%{keyword_lower}%') OR "
                             f"(service IS NOT NULL AND LOWER(service) LIKE '%{keyword_lower}%') OR "
                             f"(user IS NOT NULL AND LOWER(user) LIKE '%{keyword_lower}%') OR "
                             f"(action IS NOT NULL AND LOWER(action) LIKE '%{keyword_lower}%') OR "
                             f"(endpoint IS NOT NULL AND LOWER(endpoint) LIKE '%{keyword_lower}%') OR "
                             f"(host IS NOT NULL AND LOWER(host) LIKE '%{keyword_lower}%'))")
            elif not token.startswith("last=") and not token.startswith("earliest=") and not token.startswith("latest=") and "=" not in token:
                # Unquoted keyword - search across all text fields (case-insensitive)
                # Handle NULL values properly
                token_lower = token.lower()
                clauses.append(f"((raw IS NOT NULL AND LOWER(raw) LIKE '%{token_lower}%') OR "
                             f"(message IS NOT NULL AND LOWER(message) LIKE '%{token_lower}%') OR "
                             f"(service IS NOT NULL AND LOWER(service) LIKE '%{token_lower}%') OR "
                             f"(user IS NOT NULL AND LOWER(user) LIKE '%{token_lower}%') OR "
                             f"(action IS NOT NULL AND LOWER(action) LIKE '%{token_lower}%') OR "
                             f"(endpoint IS NOT NULL AND LOWER(endpoint) LIKE '%{token_lower}%') OR "
                             f"(host IS NOT NULL AND LOWER(host) LIKE '%{token_lower}%'))")

        return " AND ".join(clauses) if clauses else "1=1"

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize query string, handling quoted strings"""
        tokens = []
        current = ""
        in_quotes = False
        quote_char = None

        for char in text:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
                current += char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
                current += char
                tokens.append(current)
                current = ""
            elif char == " " and not in_quotes:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

        if current:
            tokens.append(current)

        return tokens

    def _parse_time_filter(self, token: str) -> Optional[str]:
        """
        Parse time filter like last=15m, last=24h, last=7d
        Supports: last=15m, last=1h, last=2d, last=1w, last=1M
        """
        # Match: last=NUMBER(UNIT) where UNIT is m, h, d, w, M
        match = re.match(r"last=(\d+)([mhdwM])", token.lower())
        if not match:
            return None

        num = int(match.group(1))
        unit = match.group(2).lower()

        # Convert to seconds
        if unit == "m":
            seconds = num * 60
        elif unit == "h":
            seconds = num * 3600
        elif unit == "d":
            seconds = num * 86400
        elif unit == "w":
            seconds = num * 604800  # 7 days
        elif unit == "M":
            seconds = num * 2592000  # ~30 days
        else:
            return None

        # Calculate cutoff time
        cutoff = datetime.utcnow() - timedelta(seconds=seconds)
        cutoff_iso = cutoff.isoformat()

        # Use proper SQL comparison - SQLite can compare ISO timestamp strings
        return f"timestamp > '{cutoff_iso}'"
    
    def _parse_earliest_latest(self, token: str, mode: str) -> Optional[str]:
        """
        Parse earliest= and latest= time filters (Splunk-like)
        Supports: 
        - Relative: earliest=-15m, earliest=-1h, earliest=-7d, earliest=-1w
        - Absolute: earliest=2024-01-01, earliest=2024-01-01T10:00:00
        - Special: latest=now, earliest=@0 (epoch)
        """
        # Extract the time value using regex
        if mode == "earliest":
            match = re.match(r"earliest=(.+)", token, re.IGNORECASE)
        else:
            match = re.match(r"latest=(.+)", token, re.IGNORECASE)
        
        if not match:
            return None
        
        time_value = match.group(1).strip()
        
        # Handle relative time: -15m, -1h, -7d, -1w, -1M
        rel_match = re.match(r"-(\d+)([mhdwM])", time_value.lower())
        if rel_match:
            num = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            
            if unit == "m":
                seconds = num * 60
            elif unit == "h":
                seconds = num * 3600
            elif unit == "d":
                seconds = num * 86400
            elif unit == "w":
                seconds = num * 604800  # 7 days
            elif unit == "M":
                seconds = num * 2592000  # ~30 days
            else:
                return None
            
            cutoff = datetime.utcnow() - timedelta(seconds=seconds)
            cutoff_iso = cutoff.isoformat()
            
            if mode == "earliest":
                return f"timestamp >= '{cutoff_iso}'"
            else:
                return f"timestamp <= '{cutoff_iso}'"
        
        # Handle "now"
        if time_value.lower() == "now":
            now_iso = datetime.utcnow().isoformat()
            if mode == "earliest":
                return f"timestamp >= '{now_iso}'"
            else:
                return f"timestamp <= '{now_iso}'"
        
        # Handle epoch time: @1234567890 or @1234567890.123
        epoch_match = re.match(r"@(\d+(?:\.\d+)?)", time_value)
        if epoch_match:
            try:
                epoch_float = float(epoch_match.group(1))
                # Handle both seconds and milliseconds
                if epoch_float > 1e10:  # Likely milliseconds
                    epoch_float = epoch_float / 1000.0
                dt = datetime.fromtimestamp(epoch_float, tz=None)
                dt_iso = dt.isoformat()
                if mode == "earliest":
                    return f"timestamp >= '{dt_iso}'"
                else:
                    return f"timestamp <= '{dt_iso}'"
            except (ValueError, OSError):
                pass
        
        # Handle absolute dates: 2024-01-01, 2024-01-01T10:00:00, 2024-01-01 10:00:00
        try:
            # Try various date formats
            dt = None
            
            # ISO format with T: 2024-01-01T10:00:00
            if "T" in time_value:
                try:
                    dt = datetime.fromisoformat(time_value.replace("Z", "+00:00"))
                except ValueError:
                    pass
            
            # ISO format with space: 2024-01-01 10:00:00
            if not dt:
                try:
                    dt = datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            
            # Date only: 2024-01-01
            if not dt:
                try:
                    dt = datetime.strptime(time_value, "%Y-%m-%d")
                except ValueError:
                    pass
            
            # Classic format: Jan 01 2024 10:00:00
            if not dt:
                try:
                    dt = datetime.strptime(time_value, "%b %d %Y %H:%M:%S")
                except ValueError:
                    pass
            
            if dt:
                dt_iso = dt.isoformat()
                if mode == "earliest":
                    return f"timestamp >= '{dt_iso}'"
                else:
                    return f"timestamp <= '{dt_iso}'"
        except Exception:
            pass
        
        # If all parsing fails, return None
        return None

