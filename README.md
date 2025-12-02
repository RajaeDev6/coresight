# CoreSight — Modern CLI SIEM (TUI + Indexing + Splunk-like Search)

CoreSight is a **terminal-based SIEM** designed for students, SOC beginners,
and analysts who want a **lightweight Splunk-like experience** from the CLI.

It provides:

- Modern **TUI**
- Real-time search
- Log ingestion
- Auto field extraction
- SQLite indexing
- Splunk-style mini query language
- Stats engine (`stats count`, `stats count by`, `stats top`)
- Syslog, auth.log, nginx, Suricata/JSON support

---

## Features

### ✔ Splunk-like Query Language
Examples:

```
source=auth event=failed_ssh
"failed password" last 1h
ip=192.168.1.50 | stats count
source=nginx | stats top 10 status
```

### ✔ Ingest Any Log

Press **F2** inside CoreSight, then enter a file path:

```
/var/log/auth.log
/var/log/syslog
nginx-access.log
eve.json
```

### ✔ Modern TUI (Bubble Tea–style)

- Search bar  
- Scrollable results  
- Status bar  
- Modal ingest window  
- Arrow key navigation  

### ✔ Log Types Supported

- System logs (`auth.log`, `syslog`)
- Nginx access logs
- JSON Lines (Suricata `eve.json`, custom apps)
- Plaintext semi-structured logs

---

## Project Structure

```
coresight/
 ├─ coresight_engine.py   # Indexing, parsing, search engine
 ├─ coresight_tui.py      # TUI widgets + layout
 └─ coresight_app.py      # Main program: UI + engine integration
```

---

## Install Dependencies

CoreSight uses only the **Python standard library**  
(no external dependencies).

```
python3 coresight_app.py
```

---

## Keyboard Controls

```
F2   → Ingest logs
Enter → Run search
Up/Down → Scroll results
ESC  → Cancel ingest mode
q    → Quit
```

---

## Example Queries

```
source=auth event=failed_ssh last 1h
"sudo" | stats count by user
source=nginx status=500 | stats count
source=nginx | stats top 5 ip
```

---

## Why CoreSight?

- Helps SOC beginners learn log analysis without Splunk/Sentinel
- Works offline
- Super lightweight
- Easy to extend
- Excellent portfolio project

---

## License

MIT

