import curses
from ..base import ListEditor, TUI
from ...config import INDEXIGNORE_FILE
from ..components.common import LineEditor
from ...utils import load_indexignore, save_indexignore, register_key
from ...config import INDEXIGNORE_FILE
from ..keybinds import ConfirmBind, KeyBind

class IndexignoreEditor(ListEditor):

    def __init__(self, scr):
        super().__init__(scr, 'INDEXIGNORE EDITOR')
        self.filepath = INDEXIGNORE_FILE
        self.ignored = sorted(list(load_indexignore()))
        self.ignored = sorted(list(load_indexignore()))
        self._update_items()
        self.box_title = 'Ignored Files'
        self.box_title = 'Ignored Files'
        self.box_title = 'Ignored Files'
        self.box_width = 50
        
        register_key(self.keymap, ConfirmBind(self.action_enter))
        register_key(self.keymap, KeyBind(ord('n'), self.action_add, "Add Pattern"))
        register_key(self.keymap, KeyBind(ord('d'), self.action_delete, "Delete Pattern"))
        
    def action_enter(self, ctx):
        if self.items[self.cursor] == "+ Add new ignore pattern...":
            self.action_add(ctx)

    def action_add(self, ctx):
        val = LineEditor(self.scr, title='Ignore File ID').run()
        if val and val not in self.ignored:
            self.ignored.append(val)
            self.ignored.sort()
            self._update_items()
            self.modified = True
            
    def action_delete(self, ctx):
        if self.items and self.items[self.cursor] != "+ Add new ignore pattern...":
            del self.ignored[self.cursor]
            self._update_items()
            self.modified = True
            if self.cursor >= len(self.items):
                self.cursor = max(0, len(self.items) - 1)

    def _update_items(self):
        self.items = self.ignored + ["+ Add new ignore pattern..."]

    def save(self):
        save_indexignore(set(self.ignored))
        self.modified = False
        return True

    def _load(self):
        self.ignored = sorted(list(load_indexignore()))
        self._update_items()

    def _draw_item(self, y, x, item, width, selected):
        if item == "+ Add new ignore pattern...":
            TUI.safe_addstr(self.scr, y, x + 4, item, curses.color_pair(3 if selected else 4) | (curses.A_BOLD if selected else curses.A_DIM))
            if selected: TUI.safe_addstr(self.scr, y, x + 2, '>', curses.color_pair(3) | curses.A_BOLD)
            return

        if selected:
            TUI.safe_addstr(self.scr, y, x + 2, '>', curses.color_pair(3) | curses.A_BOLD)
        TUI.safe_addstr(self.scr, y, x + 4, item, curses.color_pair(5 if selected else 4))

    def _draw_footer(self, h, w):
        footer = 'n:Add d:Del Esc:Save x:Export l:Import'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def _draw_footer(self, h, w):
        footer = 'n:Add d:Del Esc:Save x:Export l:Import'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    # Removed _handle_input