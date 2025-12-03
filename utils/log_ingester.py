"""
Log ingestion utility
"""

import os
from typing import Optional
from parsers import SyslogParser, AccessParser, AuthParser
from index.indexer import Indexer


class LogIngester:
    """Utility for ingesting log files"""
    
    def __init__(self, indexer: Indexer):
        """
        Initialize log ingester
        
        Args:
            indexer: Indexer instance for storing logs
        """
        self.indexer = indexer
        self.syslog_parser = SyslogParser()
        self.access_parser = AccessParser()
        self.auth_parser = AuthParser()

    def ingest_file(self, filepath: str, log_type: Optional[str] = None) -> str:
        """
        Ingest a log file
        
        Args:
            filepath: Path to log file
            log_type: Optional log type (syslog, access, auth). If None, auto-detect.
            
        Returns:
            Status message
        """
        if not os.path.isfile(filepath):
            return f"Error: File '{filepath}' not found."

        # Auto-detect log type from filename if not provided
        if not log_type:
            filename = os.path.basename(filepath).lower()
            if "access" in filename or "nginx" in filename or "apache" in filename:
                log_type = "access"
            elif "auth" in filename or "secure" in filename:
                log_type = "auth"
            elif "syslog" in filename or "messages" in filename:
                log_type = "syslog"
            else:
                # Try to detect from content
                log_type = self._detect_log_type(filepath)

        count = 0
        errors = 0
        batch_size = 100  # Commit in batches for better performance
        batch = []
        lines_processed = 0

        try:
            with open(filepath, "r", encoding='utf-8', errors='replace') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    parsed = None
                    
                    if log_type == "syslog":
                        parsed = self.syslog_parser.parse(line)
                    elif log_type == "access":
                        parsed = self.access_parser.parse(line)
                    elif log_type == "auth":
                        parsed = self.auth_parser.parse(line)
                    else:
                        # Try all parsers (only parse once per parser)
                        parsed = self.syslog_parser.parse(line)
                        if parsed:
                            log_type = "syslog"
                        else:
                            parsed = self.access_parser.parse(line)
                            if parsed:
                                log_type = "access"
                            else:
                                parsed = self.auth_parser.parse(line)
                                if parsed:
                                    log_type = "auth"

                    if parsed:
                        batch.append((log_type, parsed, line))
                        count += 1
                        
                        # Commit in batches for performance
                        if len(batch) >= batch_size:
                            for lt, pd, rl in batch:
                                self.indexer.add_log(lt, pd, rl)
                            self.indexer.commit()
                            batch = []
                    else:
                        errors += 1

            # Commit remaining batch
            if batch:
                for lt, pd, rl in batch:
                    self.indexer.add_log(lt, pd, rl)
                self.indexer.commit()

        except Exception as e:
            return f"Error reading file: {e}"

        return f"Ingested {count} events from {filepath} ({log_type} format)" + (f" ({errors} errors)" if errors > 0 else "")

    def _detect_log_type(self, filepath: str) -> str:
        """Detect log type by reading first few lines"""
        try:
            with open(filepath, "r", encoding='utf-8', errors='replace') as f:
                for i, line in enumerate(f):
                    if i >= 5:  # Check first 5 lines
                        break
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Try each parser
                    if self.access_parser.parse(line):
                        return "access"
                    if self.auth_parser.parse(line):
                        return "auth"
                    if self.syslog_parser.parse(line):
                        return "syslog"
        except Exception:
            pass
        
        return "syslog"  # Default fallback

