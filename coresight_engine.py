#!/usr/bin/env python3
import os
import re
import json
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


# =============================================================
#  CoreSight Engine — UNIVERSAL LOG PARSER EDITION
# =============================================================
class CoreSightEngine:
    """
    Splunk-like engine:
      • Universal log ingestion
      • Automatic log format detection
      • Field extraction for syslog, nginx, json, windows, generic
      • SQLite index
      • SPL-like search + stats
    """

    def __init__(self, db_path="coresight.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    # ---------------------------------------------------------
    # DB Setup
    # ---------------------------------------------------------
    def _init_schema(self):
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            source TEXT,
            ip TEXT,
            user TEXT,
            status TEXT,
            event TEXT,
            raw TEXT
        )
        """)
        self.conn.commit()

    # ---------------------------------------------------------
    # Ingestion
    # ---------------------------------------------------------
    def ingest_file(self, filepath, source_name=None):
        if not os.path.isfile(filepath):
            return f"Error: file '{filepath}' not found."

        source = source_name or os.path.basename(filepath)
        count = 0

        with open(filepath, "r", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parsed = self.parse_universal(line)
                if parsed:
                    ts, ip, user, status, event = parsed
                    self._insert_event(ts, source, ip, user, status, event, line)
                    count += 1

        self.conn.commit()
        return f"Ingested {count} events from {filepath}"

    def _insert_event(self, ts, src, ip, user, status, event, raw):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO logs (timestamp, source, ip, user, status, event, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ts, src, ip, user, status, event, raw))

    # =========================================================
    # UNIVERSAL PARSER
    # =========================================================
    def parse_universal(self, line):
        """
        Attempts all major formats:
          1. JSON
          2. RFC3339/ISO timestamps (modern Linux/macOS)
          3. Classic syslog
          4. nginx/apache
          5. Windows EVTX XML
          6. Generic fallback
        """

        # -------- JSON (Suricata, Docker, Kubernetes, custom) --------
        if self.is_json(line):
            return self.parse_json(line)

        # -------- Windows EVTX XML (exported logs) --------
        if self.is_windows_xml(line):
            return self.parse_windows_xml(line)

        # -------- nginx/apache logs --------
        if self.is_nginx(line):
            return self.parse_nginx(line)

        # -------- RFC3339/ISO timestamps (Linux/macOS) --------
        if self.is_iso(line):
            return self.parse_iso_syslog(line)

        # -------- Classic syslog --------
        if self.is_classic_syslog(line):
            return self.parse_classic_syslog(line)

        # -------- Fallback generic parser --------
        return self.parse_generic(line)

    # =========================================================
    # LOG TYPE DETECTION
    # =========================================================

    def is_json(self, line):
        return line.startswith("{") and line.endswith("}")

    def is_windows_xml(self, line):
        return line.startswith("<Event")

    def is_nginx(self, line):
        return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}.*?\[.*?\].*?\"\w+ .*?\" \d+", line))

    def is_iso(self, line):
        # 2025-02-13T11:22:33 or 2025-02-13 11:22:33
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:", line))

    def is_classic_syslog(self, line):
        # Jan 12 11:33:22 hostname app[1234]:
        return bool(re.match(r"^[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}", line))

    # =========================================================
    # PARSERS
    # =========================================================

    # -------------- JSON (EVE, Docker, K8S, custom) ----------
    def parse_json(self, line):
        try:
            obj = json.loads(line)
        except:
            return None

        ts = (
            obj.get("timestamp")
            or obj.get("time")
            or obj.get("@timestamp")
            or "unknown"
        )

        ip = obj.get("ip") or obj.get("src_ip") or obj.get("source_ip")
        user = obj.get("user")
        status = obj.get("status")
        event = (
            obj.get("event")
            or obj.get("alert", {}).get("signature")
            or obj.get("msg")
            or "json_event"
        )

        return ts, ip, user, status, event

    # ---------------- Windows EVTX XML -----------------------
    def parse_windows_xml(self, line):
        try:
            root = ET.fromstring(line)
        except:
            return None

        system = root.find("System")
        data = root.find("EventData")

        ts = system.find("TimeCreated").attrib.get("SystemTime", "unknown") \
            if system is not None else "unknown"

        event_id = system.find("EventID").text if system is not None else None
        user = None
        ip = None
        status = None

        if data is not None:
            for child in data:
                if child.attrib.get("Name") == "IpAddress":
                    ip = child.text
                if child.attrib.get("Name") == "SubjectUserName":
                    user = child.text

        event = f"windows_event_{event_id}" if event_id else "windows_event"

        return ts, ip, user, status, event

    # ---------------- nginx/apache ---------------------------
    def parse_nginx(self, line):
        # IP - - [timestamp] "VERB PATH" STATUS SIZE
        m = re.match(r"([\d\.]+).*?\[(.*?)\].*?\".*?\" (\d{3})", line)
        if not m:
            return None

        ip, raw_ts, status = m.groups()
        try:
            ts = datetime.strptime(raw_ts, "%d/%b/%Y:%H:%M:%S %z").isoformat()
        except:
            ts = "unknown"

        return ts, ip, None, status, "nginx_access"

    # ---------------- ISO syslog ----------------------------
    def parse_iso_syslog(self, line):
        # 2025-02-13T11:22:33 hostname process: message
        m = re.match(r"^(\S+)\s+(\S+)\s+(.*)", line)
        if not m:
            return None

        ts, host, rest = m.groups()
        event = "syslog_iso"
        ip = self.extract_ip(line)
        user = self.extract_user(line)

        return ts, ip, user, None, event

    # ---------------- Classic syslog -------------------------
    def parse_classic_syslog(self, line):
        # Jan 12 11:33:22 hostname process[pid]: msg
        raw_ts = line[:15]  # "Jan 12 11:33:22"
        try:
            ts = datetime.strptime(
                raw_ts + f" {datetime.now().year}",
                "%b %d %H:%M:%S %Y"
            ).isoformat()
        except:
            ts = "unknown"

        if "Failed password" in line:
            return ts, self.extract_ip(line), None, None, "failed_ssh"

        if "Accepted password" in line:
            return ts, self.extract_ip(line), self.extract_user(line), None, "login_success"

        if "sudo:" in line:
            return ts, None, self.extract_sudo_user(line), None, "sudo_event"

        return ts, None, None, None, "syslog_event"

    # ---------------- Fallback generic -----------------------
    def parse_generic(self, line):
        return (
            "unknown",
            self.extract_ip(line),
            None,
            None,
            "generic_event"
        )

    # =========================================================
    # EXTRACTORS
    # =========================================================

    def extract_ip(self, line):
        m = re.search(r"(\d{1,3}(\.\d{1,3}){3})", line)
        return m.group(1) if m else None

    def extract_user(self, line):
        m = re.search(r"user\s+(\S+)", line)
        m2 = re.search(r"for\s+(\S+)", line)
        return (m.group(1) if m else (m2.group(1) if m2 else None))

    def extract_sudo_user(self, line):
        m = re.search(r"sudo:\s+(\S+)", line)
        return m.group(1) if m else None

    # =========================================================
    # SEARCH ENGINE (unchanged)
    # =========================================================
    def search(self, query):
        try:
            where, stats_cmd = self._parse_query(query)
            rows = self._run_where(where)
            if stats_cmd:
                return self._run_stats(rows, stats_cmd)
            return rows
        except Exception as e:
            return [{"error": str(e)}]

    def _parse_query(self, q):
        if "|" in q:
            left, right = q.split("|", 1)
            return self._build_where(left.strip()), right.strip()
        return self._build_where(q.strip()), None

    def _build_where(self, text):
        if not text:
            return "1=1"

        tokens = text.split()
        clauses = []

        for t in tokens:
            if t.startswith('"') and t.endswith('"'):
                clauses.append(f"raw LIKE '%{t.strip('\"')}%'")
                continue

            if "=" in t:
                k, v = t.split("=", 1)
                v = v.strip('"')
                if k in ("source", "event", "ip", "user", "status"):
                    clauses.append(f"{k}='{v}'")
                continue

            if t.startswith("last"):
                num = int(re.findall(r"\d+", t)[0])
                period = num * 3600 if "h" in t else num * 86400
                dt = datetime.utcnow() - timedelta(seconds=period)
                clauses.append(f"timestamp > '{dt.isoformat()}'")

        return " AND ".join(clauses) if clauses else "1=1"

    def _run_where(self, where):
        cur = self.conn.cursor()
        sql = f"SELECT * FROM logs WHERE {where} ORDER BY id DESC LIMIT 1000;"
        return [dict(r) for r in cur.execute(sql)]

    # ---------------- STATS ----------------------
    def _run_stats(self, rows, cmd):
        cmd = cmd.strip()

        if cmd == "stats count":
            return [{"count": len(rows)}]

        m = re.match(r"stats count by ([A-Za-z_]+)", cmd)
        if m:
            f = m.group(1)
            d = {}
            for r in rows:
                key = r.get(f)
                d[key] = d.get(key, 0) + 1
            return [{"value": k, "count": v} for k,v in d.items()]

        m = re.match(r"stats top (\d+) ([A-Za-z_]+)", cmd)
        if m:
            n = int(m.group(1))
            f = m.group(2)
            d = {}
            for r in rows:
                key = r.get(f)
                d[key] = d.get(key, 0) + 1
            top = sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]
            return [{"value": k, "count": v} for k,v in top]

        return [{"error": "Invalid stats command"}]

