#!/usr/bin/env python3
"""
CoreSight - Terminal-based Log Analytics Engine
Main application entry point
"""

import curses
import traceback
from index.indexer import Indexer
from search.query_engine import QueryEngine
from utils.log_ingester import LogIngester
from dashboard.dashboard import Dashboard
from tui import C, InputBox, TableView, DashboardView


class CoreSightApp:
    """Main CoreSight application"""
    
    def __init__(self, stdscr):
        curses.curs_set(0)
        self.std = stdscr

        # Initialize core components
        self.indexer = Indexer("coresight.db")
        self.query_engine = QueryEngine(self.indexer)
        self.ingester = LogIngester(self.indexer)
        self.dashboard_builder = Dashboard(self.query_engine)

        # UI Elements
        self.input = InputBox("search")
        self.table = TableView()
        self.dashboard_view = DashboardView()

        # Application state
        self.mode = "menu"  # menu, ingest, search, dashboard
        self.ingest_buffer = ""
        self.status_msg = "Ready. Select an option from the menu."
        self.menu_selection = 0
        self.menu_options = [
            "1. Ingest Logs",
            "2. Run Search Query",
            "3. View Dashboards",
            "4. Exit"
        ]
        self.current_dashboard_name = None
        self.dashboards = {}

    def run(self):
        """Main application loop"""
        while True:
            self.draw()
            k = self.std.getch()

            if k == ord("q"):
                break

            # Handle mode-specific input
            if self.mode == "menu":
                self.handle_menu_mode(k)
            elif self.mode == "ingest":
                self.handle_ingest_mode(k)
            elif self.mode == "search":
                self.handle_search_mode(k)
            elif self.mode == "dashboard":
                self.handle_dashboard_mode(k)

    def handle_menu_mode(self, k):
        """Handle menu navigation"""
        if k == curses.KEY_UP:
            self.menu_selection = (self.menu_selection - 1) % len(self.menu_options)
        elif k == curses.KEY_DOWN:
            self.menu_selection = (self.menu_selection + 1) % len(self.menu_options)
        elif k == 10:  # Enter
            if self.menu_selection == 0:  # Ingest Logs
                self.mode = "ingest"
                self.ingest_buffer = ""
                self.status_msg = "Enter file path to ingest..."
            elif self.menu_selection == 1:  # Run Search Query
                self.mode = "search"
                self.input.value = ""
                self.status_msg = "Enter search query..."
                # Load default data to show in search view
                self.load_default_search_data()
            elif self.menu_selection == 2:  # View Dashboards
                self.load_dashboards()
                self.mode = "dashboard"
                self.status_msg = "Use ←/→ to navigate dashboards, ESC to return to menu"
            elif self.menu_selection == 3:  # Exit
                return

    def handle_ingest_mode(self, k):
        """Handle ingest mode input"""
        if k == 27:  # ESC
            self.mode = "menu"
            self.status_msg = "Ingest cancelled."
            return

        if k in (curses.KEY_BACKSPACE, 127):
            self.ingest_buffer = self.ingest_buffer[:-1]
            return

        if k == 10:  # Enter → ingest
            path = self.ingest_buffer.strip()
            if not path:
                self.status_msg = "Empty path."
                self.mode = "menu"
                return

            # Show processing message
            self.status_msg = f"Processing {path}... (this may take a moment for large files)"
            self.draw()
            self.std.refresh()
            
            # Ingest file with error handling
            try:
                result = self.ingester.ingest_file(path)
                self.status_msg = result
            except Exception as e:
                self.status_msg = f"Error ingesting file: {str(e)[:60]}"
            self.mode = "menu"
            return

        if 32 <= k <= 126:
            self.ingest_buffer += chr(k)
    
    def get_ingest_help_text(self):
        """Get help text for ingest mode"""
        return [
            "═══════════════════════════════════════════════════════",
            "  Log Ingestion",
            "═══════════════════════════════════════════════════════",
            "",
            "Enter the path to a log file to ingest.",
            "",
            "Supported log types:",
            "  • SYSLOG      - System logs (timestamp, host, service, message)",
            "  • ACCESS LOG  - Web access logs (timestamp, ip, method, endpoint, status, size)",
            "  • AUTH LOG    - Authentication logs (timestamp, user, action, ip)",
            "",
            "Example file paths:",
            "  sample_logs/syslog_sample.log",
            "  sample_logs/access_sample.log",
            "  sample_logs/auth_sample.log",
            "  /var/log/auth.log",
            "  /var/log/syslog",
            "  /var/log/nginx/access.log",
            "",
            "The system will automatically detect the log type",
            "based on the filename or file content.",
            "",
            "Press ESC to cancel.",
        ]
    
    def handle_search_mode(self, k):
        """Handle search mode input"""
        if k == 27:  # ESC
            self.mode = "menu"
            self.status_msg = "Returned to menu."
            return

        if k in (curses.KEY_UP, curses.KEY_DOWN):
            self.table.handle_key(k)
            return

        if k == 10:  # Enter
            self.execute_search()
            # Force UI refresh after search
            self.draw()
            self.std.refresh()
            return

        self.input.handle_key(k)

    def handle_dashboard_mode(self, k):
        """Handle dashboard mode input"""
        if k == 27:  # ESC
            self.mode = "menu"
            self.status_msg = "Returned to menu."
            return

        self.dashboard_view.handle_key(k)

    def execute_search(self):
        """Execute search query with error handling"""
        q = self.input.value.strip()
        if not q:
            # Empty search - show default data with examples
            self.load_default_search_data()
            return

        try:
            results = self.query_engine.search(q)
            
            # Check if we got an error response
            if results and len(results) == 1 and isinstance(results[0], dict) and "error" in results[0]:
                self.table.set_rows([f"Search Error: {results[0]['error']}", "", "Try a different query."])
                self.status_msg = "Search failed - check your query syntax"
                return
            
            if not results or len(results) == 0:
                # No results - show examples
                self._show_no_results_with_examples(q)
                return
            
            formatted = []
            
            # Process all results
            for r in results:
                if not isinstance(r, dict):
                    # Skip non-dict results
                    continue
                    
                if "error" in r:
                    formatted.append(f"ERROR: {r['error']}")
                elif "count" in r and "value" not in r and "time" not in r:
                    # Simple count result
                    formatted.append(f"Count: {r['count']}")
                elif "value" in r and "count" in r:
                    # Stats result - filter out null values for better display
                    value = r.get("value", "")
                    value_str = str(value) if value is not None else ""
                    if value_str and value_str.lower() not in ["null", "none", ""]:
                        formatted.append(f"{value_str:<30} {r['count']}")
                elif "time" in r and "count" in r:
                    # Time bucket result
                    formatted.append(f"{r['time']:<30} {r['count']}")
                else:
                    # Regular log result - ALWAYS format and add these
                    ts = r.get("timestamp", "?")[:19] if r.get("timestamp") else "?"
                    log_type = r.get("log_type", "?")
                    # Try multiple fields for message, with fallback to raw
                    msg = (r.get("endpoint") or r.get("action") or r.get("message") or 
                           (r.get("raw", "")[:50] if r.get("raw") else "?"))
                    if not msg or msg == "?" or msg is None:
                        msg = r.get("raw", "?")[:50] if r.get("raw") else "?"
                    formatted.append(f"{ts} | {log_type:<8} | {str(msg)[:50]}")

            # Always set rows if we have formatted results
            if formatted and len(formatted) > 0:
                self.table.set_rows(formatted)
                self.status_msg = f"{len(formatted)} results found. Use ↑↓ to scroll."
            else:
                # No formatted results - this shouldn't happen if we have results
                # But if it does, show what we got
                if len(results) > 0:
                    # We have results but couldn't format them - show raw info
                    self.table.set_rows([
                        f"Query '{q}' returned {len(results)} results but couldn't format them.",
                        "",
                        "Sample raw result:",
                        str(results[0])[:80],
                        "",
                        "Try ingesting logs first, then search again."
                    ])
                    self.status_msg = f"Query returned {len(results)} results but formatting failed"
                else:
                    # No results at all
                    self._show_no_results_with_examples(q)
        except Exception as e:
            # Catch any errors and display them instead of crashing
            error_msg = str(e)[:100]  # Limit error message length
            self.table.set_rows([f"Search Error: {error_msg}", "", "Try a different query."])
            self.status_msg = "Search failed - check your query syntax"
    
    def _show_no_results_with_examples(self, query: str):
        """Show no results message with example queries"""
        examples = [
            f"No results found for: '{query}'",
            "",
            "Try these example queries:",
            "",
            "KEYWORD SEARCHES:",
            "  service              - Find logs containing 'service'",
            "  start                - Find logs with 'start'",
            "  stop                 - Find logs with 'stop'",
            "  nginx                - Find nginx-related logs",
            "  systemd              - Find systemd service logs",
            "  Failed               - Find failed login attempts",
            "",
            "FIELD SEARCHES:",
            "  service=systemd      - Exact service match",
            "  status=404           - HTTP 404 errors",
            "  user=admin           - Logs for specific user",
            "  log_type=access      - Filter by log type",
            "  action=login_failure - Failed login attempts",
            "",
            "TIME FILTERS (Splunk-like):",
            "  last=15m             - Last 15 minutes",
            "  last=1h              - Last hour",
            "  last=24h             - Last 24 hours",
            "  earliest=-1h         - From 1 hour ago",
            "  latest=now           - Up to now",
            "",
            "COMBINED QUERIES:",
            "  service=systemd last=1h",
            "  status=404 last=24h",
            "  Failed earliest=-7d",
            "",
            "STATS & ANALYTICS:",
            "  * | count_by(status) - Count by status",
            "  * | top(10, ip)      - Top 10 IPs",
            "  * | time_bucket(1h)  - Events per hour",
        ]
        self.table.set_rows(examples)
        self.status_msg = "No results - try example queries above"

    def load_default_search_data(self):
        """Load default data to display in search view"""
        try:
            # Get recent logs (last 20)
            results = self.query_engine.search("*")
            
            if results and len(results) > 0:
                formatted = []
                formatted.append("═══════════════════════════════════════════════════════")
                formatted.append("  Recent Log Events (showing last 20)")
                formatted.append("═══════════════════════════════════════════════════════")
                formatted.append("")
                formatted.append("Example queries that work with your data:")
                formatted.append("")
                
                # Show example queries that will actually return data
                formatted.append("KEYWORD SEARCHES:")
                formatted.append("  service              - Find logs containing 'service'")
                formatted.append("  start                - Find logs with 'start'")
                formatted.append("  stop                 - Find logs with 'stop'")
                formatted.append("  nginx                - Find nginx-related logs")
                formatted.append("  systemd              - Find systemd service logs")
                formatted.append("  Failed               - Find failed login attempts")
                formatted.append("")
                formatted.append("FIELD SEARCHES:")
                formatted.append("  *                    - Show all logs")
                formatted.append("  log_type=access      - Show access logs only")
                formatted.append("  log_type=syslog      - Show syslog events")
                formatted.append("  log_type=auth        - Show authentication logs")
                
                # Check what data we have to show relevant examples
                access_count = len(self.query_engine.search("log_type=access"))
                auth_count = len(self.query_engine.search("log_type=auth"))
                syslog_count = len(self.query_engine.search("log_type=syslog"))
                status_404 = len(self.query_engine.search("status=404"))
                login_fail = len(self.query_engine.search("action=login_failure"))
                
                if access_count > 0:
                    formatted.append("  status=404            - Find 404 errors")
                    formatted.append("  status=200            - Find successful requests")
                    if status_404 > 0:
                        formatted.append(f"  status=404            - ({status_404} found)")
                
                if auth_count > 0:
                    formatted.append("  action=login_failure   - Find failed logins")
                    formatted.append("  action=login_success   - Find successful logins")
                    if login_fail > 0:
                        formatted.append(f"  action=login_failure   - ({login_fail} found)")
                
                formatted.append("")
                formatted.append("TIME FILTERS (Splunk-like):")
                formatted.append("  last=15m             - Last 15 minutes")
                formatted.append("  last=1h              - Last hour")
                formatted.append("  last=24h             - Last 24 hours")
                formatted.append("  earliest=-1h         - From 1 hour ago")
                formatted.append("  latest=now           - Up to now")
                formatted.append("")
                formatted.append("COMBINED QUERIES:")
                if syslog_count > 0:
                    formatted.append("  service=systemd last=1h")
                if access_count > 0:
                    formatted.append("  status=404 last=24h")
                if auth_count > 0:
                    formatted.append("  Failed earliest=-7d")
                formatted.append("")
                formatted.append("STATS & ANALYTICS:")
                formatted.append("  * | count_by(log_type)     - Count by log type")
                if access_count > 0:
                    formatted.append("  log_type=access | count_by(status) - Status distribution")
                if auth_count > 0:
                    formatted.append("  log_type=auth | count_by(user) - Users with most events")
                formatted.append("  * | top(10, ip)             - Top 10 IP addresses")
                formatted.append("  * | time_bucket(1h)          - Events per hour")
                formatted.append("")
                formatted.append("───────────────────────────────────────────────────────")
                formatted.append("")
                
                # Show recent logs
                for r in results[:20]:
                    if "error" not in r:
                        ts = r.get("timestamp", "?")[:19] if r.get("timestamp") else "?"
                        log_type = r.get("log_type", "?")
                        msg = r.get("message", r.get("endpoint", r.get("action", "?")))
                        formatted.append(f"{ts} | {log_type:<8} | {msg[:50]}")
                
                if len(results) > 20:
                    formatted.append("")
                    formatted.append(f"... and {len(results) - 20} more events")
                
                self.table.set_rows(formatted)
                self.status_msg = f"Showing {min(20, len(results))} recent events. Enter a query to search."
            else:
                # No data yet - show instructions
                instructions = [
                    "═══════════════════════════════════════════════════════",
                    "  CoreSight Search",
                    "═══════════════════════════════════════════════════════",
                    "",
                    "No logs have been ingested yet.",
                    "",
                    "To get started:",
                    "  1. Press ESC to return to menu",
                    "  2. Select 'Ingest Logs'",
                    "  3. Enter path to a log file",
                    "",
                    "Example log file paths:",
                    "  sample_logs/syslog_sample.log",
                    "  sample_logs/access_sample.log",
                    "  sample_logs/auth_sample.log",
                    "  /var/log/auth.log",
                    "  /var/log/syslog",
                    "",
                    "After ingesting logs, you can use these queries:",
                    "",
                    "KEYWORD SEARCHES:",
                    "  service              - Find logs containing 'service'",
                    "  start, stop          - Find start/stop events",
                    "  nginx, systemd       - Find service-specific logs",
                    "",
                    "FIELD SEARCHES:",
                    "  *                    - Show all logs",
                    "  log_type=access       - Show access logs",
                    "  status=404            - Find 404 errors",
                    "  action=login_failure  - Find failed logins",
                    "",
                    "TIME FILTERS:",
                    "  last=1h               - Last hour",
                    "  earliest=-24h         - From 24h ago",
                    "",
                    "STATS:",
                    "  * | count_by(log_type) - Count by type",
                    "  * | top(10, ip)        - Top 10 IPs",
                ]
                self.table.set_rows(instructions)
                self.status_msg = "No data yet - ingest logs first"
        except Exception:
            # If there's an error loading default data, show instructions
            instructions = [
                "═══════════════════════════════════════════════════════",
                "  CoreSight Search",
                "═══════════════════════════════════════════════════════",
                "",
                "Enter a search query above and press Enter.",
                "",
                "Example queries:",
                "",
                "KEYWORD: service, start, stop, nginx, systemd",
                "FIELD: log_type=access, status=404, user=admin",
                "TIME: last=1h, earliest=-24h, latest=now",
                "STATS: * | count_by(status), * | top(10, ip)",
                "",
                "  *                         - Show all logs",
                "  service                  - Find 'service' in logs",
                "  status=404                - Find 404 errors",
                "  last=1h                   - Last hour",
                "  * | count_by(log_type)     - Count by type",
            ]
            self.table.set_rows(instructions)
            self.status_msg = "Enter a search query..."

    def load_dashboards(self):
        """Load all dashboard data"""
        self.dashboards = self.dashboard_builder.build_all_dashboards()
        
        # Convert to format expected by DashboardView
        sections = {}
        for name, dashboard_data in self.dashboards.items():
            # Dashboard data already includes title in content, so just use content
            sections[name] = dashboard_data["content"]
        
        self.dashboard_view.set_sections(sections)

    def draw(self):
        """Draw the UI"""
        self.std.erase()
        h, w = self.std.getmaxyx()

        # Title bar
        title = " CoreSight — Terminal Log Analytics Engine "
        self.std.addstr(0, 0, title.center(w), curses.color_pair(C.TITLE))

        if self.mode == "menu":
            self.draw_menu(2, 2, w - 4)
        elif self.mode == "ingest":
            self.draw_ingest(2, 2, h - 3, w - 4)
        elif self.mode == "search":
            self.draw_search(2, 2, h - 3, w - 4)
        elif self.mode == "dashboard":
            self.draw_dashboard(2, 2, h - 3, w - 4)

        # Status bar
        bottom = f" q:quit | ESC:back | {self.status_msg}"
        self.std.addstr(h-1, 0, bottom[:w], curses.color_pair(C.DIM))

        self.std.refresh()

    def draw_menu(self, y, x, w):
        """Draw main menu"""
        self.std.addstr(y, x, "┌" + "─"*(w-2) + "┐", curses.color_pair(C.BORDER))
        
        for i, option in enumerate(self.menu_options):
            row_y = y + 1 + i
            self.std.addstr(row_y, x, "│", curses.color_pair(C.BORDER))
            
            if i == self.menu_selection:
                self.std.addstr(row_y, x+1, option.center(w-2), curses.color_pair(C.HIGHLIGHT))
            else:
                self.std.addstr(row_y, x+1, option.center(w-2), curses.color_pair(C.TEXT))
            
            self.std.addstr(row_y, x+w-1, "│", curses.color_pair(C.BORDER))
        
        self.std.addstr(y + len(self.menu_options) + 1, x, "└" + "─"*(w-2) + "┘", curses.color_pair(C.BORDER))

    def draw_ingest(self, y, x, h, w):
        """Draw ingest input with help text"""
        # Input box
        self.std.addstr(y, x, "┌" + "─"*(w-2) + "┐", curses.color_pair(C.BORDER))
        self.std.addstr(y+1, x, "│", curses.color_pair(C.BORDER))
        
        label = "ingest: "
        self.std.addstr(y+1, x+1, label, curses.color_pair(C.TITLE))
        
        txt = self.ingest_buffer[: w - 2 - len(label)]
        self.std.addstr(y+1, x+1+len(label), txt, curses.color_pair(C.INPUT))
        
        cx = x + 1 + len(label) + len(txt)
        if cx < x + w - 1:
            self.std.addstr(y+1, cx, "█", curses.color_pair(C.CURSOR))
        
        self.std.addstr(y+1, x+w-1, "│", curses.color_pair(C.BORDER))
        self.std.addstr(y+2, x, "└" + "─"*(w-2) + "┘", curses.color_pair(C.BORDER))
        
        # Help text below input
        help_text = self.get_ingest_help_text()
        help_y = y + 4
        help_h = min(len(help_text), h - (help_y - y))
        
        for i, line in enumerate(help_text[:help_h]):
            if help_y + i < y + h - 1:
                self.std.addstr(help_y + i, x, line[:w-2], curses.color_pair(C.DIM))

    def draw_search(self, y, x, h, w):
        """Draw search interface"""
        self.input.draw(self.std, y, x, w)
        
        table_y = y + 4
        table_h = h - table_y + y
        self.table.draw(self.std, table_y, x, table_h, w)

    def draw_dashboard(self, y, x, h, w):
        """Draw dashboard view"""
        self.dashboard_view.draw(self.std, y, x, h, w)


def run_app(stdscr):
    """Initialize curses and run application"""
    curses.start_color()
    for i in range(1, 16):
        curses.init_pair(i, i, 0)
    CoreSightApp(stdscr).run()


def main():
    """Main entry point"""
    try:
        curses.wrapper(run_app)
    except Exception:
        curses.endwin()
        print(traceback.format_exc())


if __name__ == "__main__":
    main()

