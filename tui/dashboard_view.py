"""
Dashboard view component with section navigation
"""

import curses
from .colors import C


class DashboardView:
    """
    Dashboard with LEFT/RIGHT navigation between sections
    """
    
    def __init__(self):
        self.sections = {}
        self.section_names = []
        self.active = 0
        self.rows = []
        self.scroll = 0

    def set_sections(self, sections_dict):
        """
        Set dashboard sections
        sections_dict = {
            "Dashboard Name 1": [...],
            "Dashboard Name 2": [...],
            ...
        }
        """
        self.sections = sections_dict
        self.section_names = list(sections_dict.keys())
        self.active = 0
        self._update_rows()

    def _update_rows(self):
        """Update visible rows based on active section"""
        if not self.section_names:
            self.rows = ["(no dashboards available)"]
            return
        
        active_name = self.section_names[self.active]
        # Don't add duplicate header - dashboard content already has headers
        self.rows = self.sections.get(active_name, [])
        self.scroll = 0

    def handle_key(self, k):
        """Handle keyboard navigation"""
        if not self.section_names:
            return
            
        if k == curses.KEY_LEFT:
            self.active = (self.active - 1) % len(self.section_names)
            self._update_rows()

        elif k == curses.KEY_RIGHT:
            self.active = (self.active + 1) % len(self.section_names)
            self._update_rows()

        elif k == curses.KEY_UP:
            self.scroll = max(0, self.scroll - 1)

        elif k == curses.KEY_DOWN:
            self.scroll = min(len(self.rows)-1, self.scroll + 1)

    def draw(self, std, y, x, h, w):
        """Draw the dashboard view"""
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

