import curses
import sys
import termios
import curses.textpad
from pathlib import Path
from ..core.config_mgmt import export_file, import_file, list_exports_for
from ..config import MIN_TERM_HEIGHT, MIN_TERM_WIDTH
from ..utils import register_key, handle_key_event
from .keybinds import SaveBind, ExitBind, NavigationBind, KeyBind

class TUI:

    @staticmethod
    def init_colors():
        curses.start_color()
        curses.use_default_colors()
        for i, color in enumerate([curses.COLOR_CYAN, curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_WHITE, curses.COLOR_MAGENTA, curses.COLOR_RED], 1):
            curses.init_pair(i, color, -1)
        if curses.COLORS >= 256:
            for i in range(16, 256):
                curses.init_pair(i, i, -1)
        curses.curs_set(0)

    @staticmethod
    def disable_flow_control():
        try:
            fd = sys.stdin.fileno()
            attrs = termios.tcgetattr(fd)
            attrs[0] &= ~(termios.IXON | termios.IXOFF)
            termios.tcsetattr(fd, termios.TCSANOW, attrs)
        except:
            pass

    @staticmethod
    def safe_addstr(scr, y, x, text, attr=0):
        try:
            h, w = scr.getmaxyx()
            real_y = y + 1
            real_x = x + 1
            if 0 <= real_y < h - 1 and 0 <= real_x < w - 1:
                scr.addstr(real_y, real_x, text[:w - 1 - real_x], attr)
        except curses.error:
            pass

    @staticmethod
    def draw_box(scr, y, x, h, w, title=''):
        try:
            real_y, real_x = (y + 1, x + 1)
            scr.addstr(real_y, real_x, '╔' + '═' * (w - 2) + '╗')
            for i in range(1, h - 1):
                scr.addstr(real_y + i, real_x, '║' + ' ' * (w - 2) + '║')
            scr.addstr(real_y + h - 1, real_x, '╚' + '═' * (w - 2) + '╝')
            if title:
                scr.addstr(real_y, real_x + 2, f' {title} ', curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass

    @staticmethod
    def prompt_save(scr):
        h_raw, w_raw = scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        TUI.safe_addstr(scr, h - 1, 2, 'Save? (y/n/c): ', curses.color_pair(3) | curses.A_BOLD)
        scr.refresh()
        c = scr.getch()
        return chr(c) if c in (ord('y'), ord('n'), ord('c')) else 'c'

    @staticmethod
    def prompt_confirm(scr, message='Are you sure? (y/n): '):
        h_raw, w_raw = scr.getmaxyx()
        box_h = 7
        box_w = max(40, len(message) + 8)
        box_y = (h_raw - box_h) // 2
        box_x = (w_raw - box_w) // 2
        TUI.draw_box(scr, box_y, box_x, box_h, box_w, 'CONFIRM')
        msg_y = box_y + 2
        msg_x = box_x + (box_w - len(message)) // 2
        TUI.safe_addstr(scr, msg_y, msg_x, message, curses.color_pair(3) | curses.A_BOLD)
        hint = '[y] Yes    [n] No'
        hint_y = box_y + 4
        hint_x = box_x + (box_w - len(hint)) // 2
        TUI.safe_addstr(scr, hint_y, hint_x, hint, curses.color_pair(4))
        scr.refresh()
        while True:
            c = scr.getch()
            if c in (ord('y'), ord('Y')):
                return True
            if c in (ord('n'), ord('N'), 27):
                return False

    @staticmethod
    def show_saved(scr):
        h_raw, w_raw = scr.getmaxyx()
        h, w = (h_raw - 2, w_raw - 2)
        TUI.safe_addstr(scr, h - 1, 2, 'Saved!', curses.color_pair(2) | curses.A_BOLD)
        scr.refresh()
        curses.napms(500)

    @staticmethod
    def check_terminal_size(scr):
        was_error = False
        while True:
            h, w = scr.getmaxyx()
            if h >= MIN_TERM_HEIGHT and w >= MIN_TERM_WIDTH:
                if was_error:
                    scr.clear()
                    scr.refresh()
                    scr.timeout(-1)
                return True
            was_error = True
            scr.clear()
            y = h // 2 - 1
            TUI.safe_addstr(scr, y, max(0, (w - 19) // 2), 'Terminal too small!', curses.color_pair(6) | curses.A_BOLD)
            TUI.safe_addstr(scr, y + 1, max(0, (w - 15) // 2), f'Current: {h}×{w}', curses.color_pair(4))
            TUI.safe_addstr(scr, y + 2, max(0, (w - 15) // 2), f'Required: {MIN_TERM_HEIGHT}×{MIN_TERM_WIDTH}', curses.color_pair(4) | curses.A_DIM)
            scr.refresh()
            scr.timeout(100)
            if scr.getch() in (ord('q'), 27):
                return False

class BaseEditor:

    def do_export(self):
        from .components.common import LineEditor, show_error_screen
        if not hasattr(self, 'filepath') or not self.filepath:
            return
        suf = LineEditor(self.scr, title='Export Suffix (Optional)', initial_value='').run()
        if suf is None:
            return
        res = export_file(self.filepath, suf)
        if res:
            TUI.show_saved(self.scr)
        else:
            show_error_screen(self.scr, 'Export failed')

    def do_import(self):
        from .components.common import show_error_screen
        if not hasattr(self, 'filepath') or not self.filepath:
            return
        backups = list_exports_for(self.filepath.name)
        if not backups:
            show_error_screen(self.scr, 'No backups found')
            return
        h, w = self.scr.getmaxyx()
        bh, bw = (min(len(backups) + 6, h - 4), min(65, w - 4))
        by, bx = ((h - bh) // 2, (w - bw) // 2)
        sel = 0
        while True:
            self.scr.clear()
            TUI.draw_box(self.scr, by, bx, bh, bw, 'Select Backup')
            for i, b in enumerate(backups):
                if i >= bh - 4:
                    break
                if i == sel:
                    TUI.safe_addstr(self.scr, by + 1 + i, bx + 2, f'> {b}'[:bw - 4], curses.color_pair(3) | curses.A_BOLD)
                else:
                    TUI.safe_addstr(self.scr, by + 1 + i, bx + 4, b[:bw - 6], curses.color_pair(4))
            
            # Helper text
            TUI.safe_addstr(self.scr, by + bh - 2, bx + 2, "Tip: Add .json/.typ to 'exports/' folder", curses.color_pair(4) | curses.A_DIM)

            self.scr.refresh()
            k = self.scr.getch()
            if k == 27:
                return
            elif k in (curses.KEY_UP, ord('k')):
                sel = max(0, sel - 1)
            elif k in (curses.KEY_DOWN, ord('j')):
                sel = min(len(backups) - 1, sel + 1)
            elif k in (ord('\n'), 10):
                if TUI.prompt_confirm(self.scr, 'Overwrite current file?'):
                    from ..config import BASE_DIR
                    src = BASE_DIR / 'exports' / backups[sel]
                    if import_file(src, self.filepath):
                        TUI.show_saved(self.scr)
                        if hasattr(self, '_load'):
                            self._load()
                        elif hasattr(self, 'config'):
                            from ..utils import load_config_safe
                            self.config = load_config_safe()
                            if hasattr(self, '_build_items'):
                                self._build_items()
                        elif hasattr(self, 'hierarchy'):
                            import json
                            try:
                                self.hierarchy = json.loads(self.filepath.read_text())
                            except:
                                self.hierarchy = []
                        elif hasattr(self, 'themes'):
                            pass
                        return
                    else:
                        show_error_screen(self.scr, 'Import failed')
                return

    def __init__(self, scr, title='Editor'):
        self.scr = scr
        self.title = title
        self.modified = False
        self.keymap = {}
        TUI.init_colors()
        
        # Register default bindings
        register_key(self.keymap, ExitBind(self.do_exit))
        register_key(self.keymap, SaveBind()) # Uses default self.save()
        
    def do_exit(self, ctx=None):
        if self.modified:
            if not self.save_dialog():
                return
        return 'EXIT' # Signal to break loop
        
    def save_dialog(self):
        """Returns True if it's safe to exit (saved, discarded, or not modified)."""
        if not self.modified: return True
        
        # This prompts user, logic was in run loop efficiently inline, but we extract it
        # Actually, let's keep it simple. If we trigger exit from binding, we need to handle the flow.
        # The keybind return value is not fully used yet.
        # Let's adjust implementation to just set a flag or handle logic.
        
        # Re-using the logic from old run() loop:
        # if self.modified: if not self.save(): pass 
        
        # Let's try to prompt save.
        res = TUI.prompt_save(self.scr) # y/n/c
        if res == 'c': return False
        if res == 'y':
            return self.save()
        return True # n -> exit without saving

    def refresh(self):
        raise NotImplementedError

    def save(self):
        raise NotImplementedError

    def run(self):
        self.refresh()
        while True:
            if not TUI.check_terminal_size(self.scr):
                return
            k = self.scr.getch()
            
            # Delegate to KeyHandler
            handled, res = handle_key_event(k, self.keymap, self)
            if handled:
                if res == 'EXIT':
                    return
                # If save return True, show saved
                if res is True and not isinstance(res, str): 
                     # Only if it was a save action? 
                     # We can make SaveBind return 'SAVED' or True.
                     # But self.save() usually returns boolean.
                     pass 
            else:
                 # Fallback for manual handling if needed, though we want to deprecate this
                if k == ord('x'):
                    self.do_export()
                elif k == ord('l'):
                    self.do_import()
                else:
                    self._handle_input(k)
            
            self.refresh()

    def _handle_input(self, k):
        pass

class ListEditor(BaseEditor):

    def __init__(self, scr, title='List Editor'):
        super().__init__(scr, title)
        self.items = []
        self.cursor = 0
        self.scroll = 0
        self.box_title = 'Items'
        self.box_width = 70
        
        # Register Navigation
        # Register Navigation
        register_key(self.keymap, NavigationBind('UP', self.cursor_up))
        register_key(self.keymap, NavigationBind('DOWN', self.cursor_down))
        register_key(self.keymap, NavigationBind('PGUP', self.cursor_pgup))
        register_key(self.keymap, NavigationBind('PGDN', self.cursor_pgdn))
        register_key(self.keymap, NavigationBind('HOME', self.cursor_home))
        register_key(self.keymap, NavigationBind('END', self.cursor_end))

    def _draw_item(self, y, x, item, width, selected):
        raise NotImplementedError

    def refresh(self):
        h, w = self.scr.getmaxyx()
        self.scr.clear()
        list_h = min(len(self.items) + 2, h - 8)
        total_h = 2 + list_h + 2
        start_y = max(1, (h - total_h) // 2)
        title_str = f"{self.title}{(' *' if self.modified else '')}"
        TUI.safe_addstr(self.scr, start_y, (w - len(title_str)) // 2, title_str, curses.color_pair(1) | curses.A_BOLD)
        bw = min(self.box_width, w - 4)
        bx = (w - bw) // 2
        TUI.draw_box(self.scr, start_y + 2, bx, list_h, bw, self.box_title)
        vis = list_h - 2
        if self.cursor < self.scroll:
            self.scroll = self.cursor
        elif self.cursor >= self.scroll + vis:
            self.scroll = self.cursor - vis + 1
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            y = start_y + 3 + i
            self._draw_item(y, bx, self.items[idx], bw, idx == self.cursor)
        self._draw_footer(h, w)
        self.scr.refresh()

    def _draw_footer(self, h, w):
        footer = 'Esc: Save & Exit'
        TUI.safe_addstr(self.scr, h - 3, (w - len(footer)) // 2, footer, curses.color_pair(4) | curses.A_DIM)

    def cursor_up(self, ctx):
        self.cursor = max(0, self.cursor - 1)
        
    def cursor_down(self, ctx):
        self.cursor = min(len(self.items) - 1, self.cursor + 1)
        
    def cursor_pgup(self, ctx):
        h, _ = self.scr.getmaxyx()
        jump = h - 8 # Approximate page size based on list_h calculation
        if jump < 1: jump = 1
        self.cursor = max(0, self.cursor - jump)

    def cursor_pgdn(self, ctx):
        h, _ = self.scr.getmaxyx()
        jump = h - 8
        if jump < 1: jump = 1
        self.cursor = min(len(self.items) - 1, self.cursor + jump)
        
    def cursor_home(self, ctx):
        self.cursor = 0
        
    def cursor_end(self, ctx):
        self.cursor = len(self.items) - 1