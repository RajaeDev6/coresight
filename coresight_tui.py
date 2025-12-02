#!/usr/bin/env python3
import curses

# ============================================================
# COLORS
# ============================================================
class C:
    TITLE = 14
    BORDER = 6
    TEXT = 15
    DIM = 8
    INPUT = 11
    CURSOR = 10
    ERROR = 9
    HIGHLIGHT = 12


# ============================================================
# INPUT BAR
# ============================================================
class InputBox:
    def __init__(self, label="search"):
        self.label = label
        self.value = ""
        self.cursor = 0

    def handle_key(self, k):
        if k in (curses.KEY_BACKSPACE, 127):
            if self.cursor > 0:
                self.value = self.value[:self.cursor-1] + self.value[self.cursor:]
                self.cursor -= 1

        elif k == curses.KEY_LEFT:
            self.cursor = max(0, self.cursor - 1)

        elif k == curses.KEY_RIGHT:
            self.cursor = min(len(self.value), self.cursor + 1)

        elif 32 <= k <= 126:
            c = chr(k)
            self.value = self.value[:self.cursor] + c + self.value[self.cursor:]
            self.cursor += 1

    def draw(self, std, y, x, w):
        label = f"{self.label}: "

        std.addstr(y, x, "┌" + "─"*(w-2) + "┐", curses.color_pair(C.BORDER))
        std.addstr(y+1, x, "│", curses.color_pair(C.BORDER))

        std.addstr(y+1, x+1, label, curses.color_pair(C.TITLE))

        max_len = w - 2 - len(label)
        txt = self.value[:max_len]

        std.addstr(y+1, x+1+len(label), txt, curses.color_pair(C.INPUT))
        std.addstr(y+1, x+w-1, "│", curses.color_pair(C.BORDER))

        cx = x + 1 + len(label) + self.cursor
        if cx < x + w - 1:
            std.addstr(y+1, cx, "█", curses.color_pair(C.CURSOR))

        std.addstr(y+2, x, "└" + "─"*(w-2) + "┘", curses.color_pair(C.BORDER))


# ============================================================
# TABLE VIEW
# ============================================================
class TableView:
    def __init__(self):
        self.rows = []
        self.scroll = 0

    def set_rows(self, rows):
        self.rows = rows
        self.scroll = 0

    def handle_key(self, k):
        if k == curses.KEY_UP:
            self.scroll = max(0, self.scroll - 1)
        elif k == curses.KEY_DOWN:
            self.scroll = min(len(self.rows)-1, self.scroll + 1)

    def draw(self, std, y, x, h, w):
        std.addstr(y, x, "┌" + "─"*(w-2) + "┐", curses.color_pair(C.BORDER))

        inner_h = h - 2
        visible = self.rows[self.scroll:self.scroll+inner_h]

        for i in range(inner_h):
            row_y = y + 1 + i
            std.addstr(row_y, x, "│", curses.color_pair(C.BORDER))

            if i < len(visible):
                text = visible[i][: w - 2]
                std.addstr(row_y, x+1, text, curses.color_pair(C.TEXT))

            std.addstr(row_y, x+w-1, "│", curses.color_pair(C.BORDER))

        std.addstr(y+h-1, x, "└" + "─"*(w-2) + "┘", curses.color_pair(C.BORDER))


# ============================================================
# DASHBOARD VIEW (with navigation)
# ============================================================
class DashboardView:
    """
    Dashboard with LEFT/RIGHT navigation between:
      1. Top Events
      2. Top IPs
      3. Top Sources
      4. Raw Preview
    """
    SECTIONS = ["Top Events", "Top IPs", "Top Sources", "Preview"]

    def __init__(self):
        self.sections = []
        self.active = 0
        self.rows = []

    def set_sections(self, sections_dict):
        """
        sections_dict = {
            "Top Events": [...],
            "Top IPs": [...],
            "Top Sources": [...],
            "Preview": [...]
        }
        """
        self.sections = sections_dict
        self.active = 0
        self._update_rows()

    def _update_rows(self):
        active_name = self.SECTIONS[self.active]
        self.rows = [f"== {active_name} =="]
        self.rows += self.sections.get(active_name, [])
        self.scroll = 0

    def handle_key(self, k):
        if k == curses.KEY_LEFT:
            self.active = (self.active - 1) % len(self.SECTIONS)
            self._update_rows()

        elif k == curses.KEY_RIGHT:
            self.active = (self.active + 1) % len(self.SECTIONS)
            self._update_rows()

        elif k == curses.KEY_UP:
            self.scroll = max(0, self.scroll - 1)

        elif k == curses.KEY_DOWN:
            self.scroll = min(len(self.rows)-1, self.scroll + 1)

    def draw(self, std, y, x, h, w):
        std.addstr(y, x, "┌" + "─"*(w-2) + "┐", curses.color_pair(C.BORDER))

        inner_h = h - 2
        visible = self.rows[self.scroll:self.scroll+inner_h]

        for i in range(inner_h):
            row_y = y + 1 + i
            std.addstr(row_y, x,   "│", curses.color_pair(C.BORDER))

            if i < len(visible):
                std.addstr(row_y, x+1, visible[i][:w-2], curses.color_pair(C.TEXT))

            std.addstr(row_y, x+w-1, "│", curses.color_pair(C.BORDER))

        std.addstr(y+h-1, x, "└" + "─"*(w-2) + "┘", curses.color_pair(C.BORDER))

