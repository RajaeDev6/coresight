"""
Input box component for text input
"""

import curses
from .colors import C


class InputBox:
    """Text input box with cursor support"""
    
    def __init__(self, label="search"):
        self.label = label
        self.value = ""
        self.cursor = 0

    def handle_key(self, k):
        """Handle keyboard input"""
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
        """Draw the input box"""
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

