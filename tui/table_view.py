"""
Table view component for displaying scrollable lists
"""

import curses
from .colors import C


class TableView:
    """Scrollable table view for displaying search results"""
    
    def __init__(self):
        self.rows = []
        self.scroll = 0

    def set_rows(self, rows):
        """Set the rows to display"""
        self.rows = rows
        self.scroll = 0

    def handle_key(self, k):
        """Handle keyboard navigation"""
        if k == curses.KEY_UP:
            self.scroll = max(0, self.scroll - 1)
        elif k == curses.KEY_DOWN:
            self.scroll = min(len(self.rows)-1, self.scroll + 1)

    def draw(self, std, y, x, h, w):
        """Draw the table view"""
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

