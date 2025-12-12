# CoreSight

***note: rewrite the TUI as an independent library***

Terminal-based log analytics engine for ingesting, parsing, indexing, and searching logs with SPL-like query syntax.

## Overview

CoreSight processes log files, extracts structured data, stores it in SQLite, and provides search and analytics capabilities through a terminal interface. If you have log files, then CoreSight can parse them. If you need to search logs, then CoreSight provides a query interface. If you want analytics, then CoreSight generates visualizations.

## Features

### Log Ingestion
- Supports three log types: syslog, web access logs, and authentication logs
- Automatic log type detection based on filename or content
- Batch processing for large files
- Handles multiple timestamp formats

### Search Engine
- SPL-like query syntax for flexible searching
- Keyword search across all log fields
- Field-based filtering with exact or partial matches
- Time-based filtering with relative and absolute date ranges
- Statistical analysis with aggregation functions

### Analytics
- Pre-built dashboards for common metrics
- Terminal-based visualizations (bar charts, line charts, tables)
- Real-time statistics and aggregations
- Time-based bucketing for trend analysis

### Terminal Interface
- Custom TUI library for interactive navigation
- Menu-driven interface for all operations
- Scrollable results and dashboard views
- Keyboard-based navigation

## Installation

If you have Python 3.7 or later, then CoreSight requires no external dependencies. All functionality uses the Python standard library.

```bash
python main.py
```

## Usage

### Main Menu

The application starts with a main menu offering four options:

1. **Ingest Logs** - Import log files into the index
2. **Run Search Query** - Execute SPL-like queries
3. **View Dashboards** - View analytics dashboards
4. **Exit** - Quit the application

### Keyboard Controls

- **↑/↓** - Navigate menu options and scroll results
- **Enter** - Select option or execute search
- **ESC** - Return to menu or cancel operation
- **q** - Quit application
- **←/→** - Navigate between dashboard sections

### Ingesting Logs

If you select "Ingest Logs" from the menu, then you can enter a file path. The system automatically detects the log type based on the filename or content.

Example paths:
```
sample_logs/syslog_sample.log
sample_logs/access_sample.log
sample_logs/auth_sample.log
/var/log/auth.log
/var/log/syslog
/var/log/nginx/access.log
```

### Search Queries

If you want to search logs, then use the SPL-like query syntax. If you want keyword search, then enter a word or phrase. If you want field filtering, then use `field=value` syntax. If you want time filtering, then use `last=X` or `earliest=X` syntax.

#### Keyword Search

Search for text across all log fields:

```
service
start
stop
nginx
systemd
Failed
```

#### Field Search

Filter by specific fields with exact or partial matches:

```
status=404
user=admin
log_type=access
service=systemd
ip=192.168.1.1
method=GET
action=login_failure
```

#### Time Filtering

Filter logs by time using relative or absolute dates:

```
last=15m
last=1h
last=24h
last=7d
earliest=-1h
earliest=-24h
earliest=2025-01-01
latest=2025-01-13
latest=now
```

#### Combined Queries

Combine multiple filters:

```
service=systemd last=1h
status=404 earliest=2025-01-01 latest=2025-01-13
Failed earliest=-7d
```

#### Stats Commands

Perform statistical analysis on search results:

```
* | count_by(log_type)
* | count_by(status)
* | top(10, ip)
* | time_bucket(1h)
* | stats count
```

### Dashboards

If you select "View Dashboards", then you can navigate through pre-built analytics:

- **HTTP Status Codes** - Status code distribution from access logs
- **Events Over Time** - Line chart showing event frequency over time
- **Top IP Addresses** - Most active IP addresses
- **Failed Login Attempts** - Failed logins grouped by user
- **Logs per Service** - Service distribution from syslog

Use **←/→** arrow keys to navigate between dashboards.

## Supported Log Types

### SYSLOG
Fields: timestamp, host, service, message

Supports both classic syslog format (Jan 12 11:33:22) and ISO timestamp format (2025-01-12T11:33:22).

### ACCESS LOG (Common Web Access Format)
Fields: timestamp, ip, method, endpoint, status, size

Compatible with nginx and Apache access log formats.

### AUTH LOG
Fields: timestamp, user, action (login success/failure), ip

Parses SSH authentication events and other authentication-related logs.

## Project Structure

```
coresight/
├── tui/                    # Custom TUI library
│   ├── __init__.py
│   ├── colors.py          # Color constants
│   ├── input_box.py       # Text input component
│   ├── table_view.py      # Scrollable table component
│   └── dashboard_view.py  # Dashboard navigation component
├── parsers/               # Log parsers
│   ├── __init__.py
│   ├── syslog_parser.py   # Syslog format parser
│   ├── access_parser.py   # Web access log parser
│   └── auth_parser.py     # Authentication log parser
├── index/                 # Indexing system
│   ├── __init__.py
│   └── indexer.py         # SQLite-based indexer
├── search/                 # Search engine
│   ├── __init__.py
│   ├── query_parser.py    # SPL-like query parser
│   └── query_engine.py    # Query execution engine
├── dashboard/             # Dashboard and visualizations
│   ├── __init__.py
│   ├── charts.py          # Chart rendering utilities
│   └── dashboard.py       # Dashboard builder
├── utils/                 # Utility functions
│   ├── __init__.py
│   └── log_ingester.py    # Log file ingestion utility
├── sample_logs/           # Sample log files for testing
│   ├── syslog_sample.log
│   ├── access_sample.log
│   └── auth_sample.log
├── main.py                # Main application entry point
├── requirements.txt       # Dependencies (none - uses stdlib)
└── README.md              # This file
```

## Architecture

### Modular Design

The project is organized into focused modules:

- **TUI**: Reusable terminal UI components for interactive interfaces
- **Parsers**: Format-specific log parsers with consistent interfaces
- **Index**: Database abstraction layer for persistent storage
- **Search**: Query parsing and execution engine with stats support
- **Dashboard**: Analytics and visualization builder

### Data Flow

1. **Ingestion**: Log files are read, parsed by format-specific parsers, and stored in SQLite
2. **Query**: Query strings are parsed into SQL WHERE clauses, executed against the database, and optionally processed by stats functions
3. **Dashboard**: Query results are aggregated, visualized using chart utilities, and displayed through the TUI

## Technical Details

- **Database**: SQLite for persistent storage with automatic schema management
- **Indexing**: Automatic indexing on timestamp, log_type, ip, user, and status fields
- **Parsing**: Regex-based parsers with fallback handling for format variations
- **TUI**: Custom curses-based library with color support and keyboard navigation
- **Charts**: ASCII art rendering for terminal compatibility

## Example Workflow

1. Start the application:
   ```bash
   python main.py
   ```

2. Ingest sample logs:
   - Select "1. Ingest Logs"
   - Enter: `sample_logs/syslog_sample.log`
   - Enter: `sample_logs/access_sample.log`
   - Enter: `sample_logs/auth_sample.log`

3. Run searches:
   - Select "2. Run Search Query"
   - Try: `status=404`
   - Try: `action=login_failure | count_by(user)`
   - Try: `log_type=access | top(5, status)`

4. View dashboards:
   - Select "3. View Dashboards"
   - Navigate with arrow keys

## Extending the Project

### Adding a New Log Parser

If you want to add support for a new log format, then:

1. Create a new parser in `parsers/` directory
2. Implement a `parse(line: str) -> Optional[Dict]` method
3. Return a dictionary with standardized field names
4. Add the parser to `parsers/__init__.py`
5. Update the log type detection in `utils/log_ingester.py`

### Adding a New Dashboard

If you want to add a new dashboard, then:

1. Add a method to `dashboard/dashboard.py`
2. Use `query_engine.search()` to get data
3. Use `charts` utilities to render visualizations
4. Add the dashboard to `build_all_dashboards()` method

### Adding a New Stats Function

If you want to add a new stats command, then:

1. Add parsing logic to `search/query_parser.py` in the `_run_stats()` method
2. Add execution logic to `search/query_engine.py`
3. Implement the aggregation function

## License

MIT

## Author

Professional terminal-based log analytics engine designed for portfolio and educational purposes.
