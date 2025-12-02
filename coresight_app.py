#!/usr/bin/env python3
import curses, traceback
from coresight_engine import CoreSightEngine
from coresight_tui import C, InputBox, TableView, DashboardView


# ============================================================
# MAIN CORESIGHT APPLICATION
# ============================================================
class CoreSightApp:
    def __init__(self, stdscr):
        curses.curs_set(0)
        self.std = stdscr

        self.engine = CoreSightEngine()

        # UI Elements
        self.input = InputBox("search")
        self.table = TableView()
        self.dashboard = DashboardView()

        self.mode = "search"   # "search", "ingest", "dashboard"
        self.ingest_buffer = ""
        self.status_msg = "Ready."

        self.table.set_rows(["Press F2 to ingest logs."])

    # ============================================================
    # MAIN LOOP
    # ============================================================
    def run(self):
        while True:
            self.draw()
            k = self.std.getch()

            if k == ord("q"):
                break

            if k == curses.KEY_F2:
                self.mode = "ingest"
                self.ingest_buffer = ""
                self.status_msg = "Enter file path to ingest..."
                continue

            if self.mode == "dashboard":
                self.dashboard.handle_key(k)
                continue

            if self.mode == "ingest":
                self.handle_ingest_mode(k)
                continue

            self.handle_search_mode(k)

    # ============================================================
    # INGEST MODE
    # ============================================================
    def handle_ingest_mode(self, k):
        if k == 27:  # ESC
            self.mode = "search"
            self.status_msg = "Ingest cancelled."
            return

        if k in (curses.KEY_BACKSPACE, 127):
            self.ingest_buffer = self.ingest_buffer[:-1]
            return

        if k == 10:  # Enter → ingest
            path = self.ingest_buffer.strip()
            if not path:
                self.status_msg = "Empty path."
                self.mode = "search"
                return

            result = self.engine.ingest_file(path)
            self.status_msg = result

            # Load dashboard data
            rows = self.engine.search("*")
            sections = self.build_dashboard_sections(rows)
            self.dashboard.set_sections(sections)
            self.mode = "dashboard"

            return

        if 32 <= k <= 126:
            self.ingest_buffer += chr(k)

    # ============================================================
    # BUILD DASHBOARD DATA
    # ============================================================
    def ascii_bar(self, count, max_count, width=30):
        if max_count == 0:
            return ""
        filled = int((count / max_count) * width)
        return "█" * filled + " " * (width - filled)

    def build_section(self, title, data):
        if not data:
            return [f"{title}: (none)"]

        max_count = max(count for _, count in data)

        lines = []
        for key, count in data:
            bar = self.ascii_bar(count, max_count)
            lines.append(f"{key:<20} {bar}  {count}")

        return lines

    def build_dashboard_sections(self, rows):
        events, ips, sources = {}, {}, {}

        for r in rows:
            evt = r.get("event")
            ip = r.get("ip")
            src = r.get("source")

            if evt:
                events[evt] = events.get(evt, 0) + 1
            if ip:
                ips[ip] = ips.get(ip, 0) + 1
            if src:
                sources[src] = sources.get(src, 0) + 1

        top_events = sorted(events.items(),  key=lambda x: x[1], reverse=True)[:5]
        top_ips = sorted(ips.items(),       key=lambda x: x[1], reverse=True)[:5]
        top_sources = sorted(sources.items(), key=lambda x: x[1], reverse=True)[:5]

        preview = [r.get("raw","")[:80] for r in rows[:10]]

        return {
            "Top Events":  self.build_section("Top Events", top_events),
            "Top IPs":     self.build_section("Top IPs", top_ips),
            "Top Sources": self.build_section("Top Sources", top_sources),
            "Preview":     preview,
        }

    # ============================================================
    # SEARCH MODE
    # ============================================================
    def handle_search_mode(self, k):
        if k in (curses.KEY_UP, curses.KEY_DOWN):
            self.table.handle_key(k)
            return

        if k == 10:  # Enter
            self.execute_search()
            return

        self.input.handle_key(k)

    # Execute search
    def execute_search(self):
        q = self.input.value.strip()
        if not q:
            self.status_msg = "Empty search."
            return

        rows = self.engine.search(q)
        formatted = []

        for r in rows:
            if "error" in r:
                formatted.append("ERROR: " + r["error"])
            else:
                ts = r.get("timestamp","?")
                src = r.get("source","?")
                evt = r.get("event","?")
                ip = r.get("ip","")
                formatted.append(f"{ts} | {src} | {evt} | {ip}")

        self.table.set_rows(formatted if formatted else ["No results."])
        self.status_msg = f"{len(formatted)} results."

    # ============================================================
    # DRAW UI
    # ============================================================
    def draw_input_or_ingest(self, y, x, w):
        if self.mode == "ingest":
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

        else:
            self.input.draw(self.std, y, x, w)

    def draw(self):
        self.std.erase()
        h, w = self.std.getmaxyx()

        self.std.addstr(0, 0, " CoreSight — CLI SIEM ".center(w), curses.color_pair(C.TITLE))

        self.draw_input_or_ingest(2, 2, w - 4)

        table_y = 6
        table_h = h - table_y - 3

        if self.mode == "dashboard":
            self.dashboard.draw(self.std, table_y, 2, table_h, w - 4)
        else:
            self.table.draw(self.std, table_y, 2, table_h, w - 4)

        bottom = f" q:quit | enter:search | F2:ingest | ←/→:switch dashboard | ↑↓scroll | {self.status_msg}"
        self.std.addstr(h-1, 0, bottom[:w], curses.color_pair(C.DIM))

        self.std.refresh()


# ============================================================
# ENTRY
# ============================================================
def run_app(stdscr):
    curses.start_color()
    for i in range(1, 16):
        curses.init_pair(i, i, 0)
    CoreSightApp(stdscr).run()

def main():
    try:
        curses.wrapper(run_app)
    except Exception:
        curses.endwin()
        print(traceback.format_exc())


if __name__ == "__main__":
    main()

