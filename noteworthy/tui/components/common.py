import curses
from ...config import SAD_FACE, HAPPY_FACE, HMM_FACE, OUTPUT_FILE
from ...utils import register_key, handle_key_event
from ..base import TUI
from ..keybinds import KeyBind, ConfirmBind

class LineEditor:

    def __init__(self, scr, title='Edit', initial_value=''):
        self.scr = scr
        self.title = title
        self.value = initial_value
        
        self.keymap = {}
        register_key(self.keymap, KeyBind(27, self.action_cancel, "Cancel"))
        register_key(self.keymap, ConfirmBind(self.action_confirm))
        register_key(self.keymap, KeyBind([curses.KEY_BACKSPACE, 127, 8], self.action_backspace, "Backspace"))
        # Character handling is via handle_char override

    def action_cancel(self, ctx):
        return 'EXIT_CANCEL'

    def action_confirm(self, ctx):
        return 'EXIT_CONFIRM'

    def action_backspace(self, ctx):
        self.value = self.value[:-1]

    def handle_char(self, char):
        self.value += char
        return True

    def run(self):
        h_raw, w_raw = self.scr.getmaxyx()
        box_h = 7
        box_w = max(50, len(self.title) + 10, len(self.value) + 10)
        box_y = (h_raw - box_h) // 2
        box_x = (w_raw - box_w) // 2
        curses.curs_set(1)
        
        while True:
            TUI.draw_box(self.scr, box_y, box_x, box_h, box_w, self.title)
            TUI.safe_addstr(self.scr, box_y + 4, box_x + 2, 'Enter: Confirm  Esc: Cancel', curses.color_pair(4) | curses.A_DIM)
            input_y = box_y + 2
            input_x = box_x + 2
            max_len = box_w - 4
            disp_val = self.value
            if len(disp_val) >= max_len:
                disp_val = disp_val[-(max_len - 1):]
            TUI.safe_addstr(self.scr, input_y, input_x, ' ' * max_len, curses.color_pair(4))
            TUI.safe_addstr(self.scr, input_y, input_x, disp_val, curses.color_pair(1) | curses.A_BOLD)
            real_y = input_y + 1
            real_x = input_x + 1 + len(disp_val)
            self.scr.move(real_y, real_x)
            
            k = self.scr.getch()
            handled, res = handle_key_event(k, self.keymap, self)
            if handled:
                if res == 'EXIT_CANCEL':
                    curses.curs_set(0)
                    return None
                elif res == 'EXIT_CONFIRM':
                    curses.curs_set(0)
                    return self.value
            elif 32 <= k <= 126:
                self.handle_char(chr(k))

def copy_to_clipboard(text):
    try:
        subprocess.run(['pbcopy'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['clip'], input=text.encode('utf-16le'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['wl-copy'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    try:
        subprocess.run(['xsel', '-b', '-i'], input=text.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
        return True
    except:
        pass
    return False

class LogScreen:
    def __init__(self, scr, log, title_func, draw_func):
        self.scr = scr
        self.log = log
        self.title_func = title_func
        self.draw_func = draw_func
        self.view_log = False
        self.copied = False
        
        self.keymap = {}
        register_key(self.keymap, KeyBind(ord('v'), self.action_toggle_log, "View Log"))
        register_key(self.keymap, KeyBind(ord('c'), self.action_copy, "Copy Log"))
        register_key(self.keymap, KeyBind(None, self.action_any, "Exit")) # Fallback

    def handle_key(self, k):
        # Specific logic to handle any key if not v or c
        # We manually check the keymap first? handle_key_event does this.
        # But we need 'any other key' behavior.
        # Let's trust handle_key_event logic which we will modify to handle None key as fallback?
        # Actually, let's keep it simple here.
        if k == ord('v') or k == ord('c'):
             return handle_key_event(k, self.keymap, self)
        
        if not self.view_log:
             return True, 'EXIT'
             
        return handle_key_event(k, self.keymap, self)

    def action_toggle_log(self, ctx):
        self.view_log = not self.view_log
        self.copied = False
        
    def action_copy(self, ctx):
        if self.view_log:
            self.copied = copy_to_clipboard(self.log)
            
    def action_any(self, ctx):
        if not self.view_log: return 'EXIT'
        
    def run(self):
        while True:
            self.scr.clear()
            h_raw, w_raw = self.scr.getmaxyx()
            h, w = (h_raw - 2, w_raw - 2)
            
            if self.view_log:
                 header = "LOG (press 'v' to go back, 'c' to copy)"
                 if self.copied: header = 'LOG (copied to clipboard!)'
                 TUI.safe_addstr(self.scr, 0, 2, header, curses.color_pair(6) | curses.A_BOLD)
                 for i, line in enumerate(self.log.split('\n')[:h-3]):
                     TUI.safe_addstr(self.scr, i + 2, 2, line, curses.color_pair(4))
            else:
                 self.draw_func(self.scr, h, w)
            
            self.scr.refresh()
            k = self.scr.getch()
            if k == -1: continue
            handled, res = self.handle_key(k)
            if handled and res == 'EXIT': break


def show_error_screen(scr, error):
    import traceback
    log = traceback.format_exc()
    if log.strip() == 'NoneType: None': log = str(error)
    
    def draw(s, h, w):
        y = max(0, (h - len(SAD_FACE) - 8) // 2)
        for i, line in enumerate(SAD_FACE):
            TUI.safe_addstr(s, y + i, (w - 9) // 2, line, curses.color_pair(6) | curses.A_BOLD)
        my = y + len(SAD_FACE) + 2
        is_build_error = "Build failed" in str(error) or (isinstance(error, Exception) and getattr(error, 'is_build_error', False))
        title = 'BUILD FAILED' if is_build_error else 'FATAL ERROR'
        TUI.safe_addstr(s, my, (w - len(title)) // 2, title, curses.color_pair(6) | curses.A_BOLD)
        err = str(error)[:w - 10]
        TUI.safe_addstr(s, my + 2, (w - len(err)) // 2, err, curses.color_pair(4))
        TUI.safe_addstr(s, my + 4, (w - 50) // 2, "Press 'v' to view log  |  Press any other key to exit", curses.color_pair(4) | curses.A_DIM)

    LogScreen(scr, log, None, draw).run()

def show_success_screen(scr, page_count, has_warnings=False, typst_logs=None):
    log = '\n'.join(typst_logs) if typst_logs else ""
    
    def draw(s, h, w):
        face = HMM_FACE if has_warnings else HAPPY_FACE
        color = curses.color_pair(3) if has_warnings else curses.color_pair(2)
        y = max(0, (h - len(face) - 8) // 2)
        for i, line in enumerate(face):
            TUI.safe_addstr(s, y + i, (w - len(face[0])) // 2, line, color | curses.A_BOLD)
        my = y + len(face) + 2
        title = 'BUILD SUCCEEDED (with warnings)' if has_warnings else 'BUILD SUCCEEDED!'
        TUI.safe_addstr(s, my, (w - len(title)) // 2, title, color | curses.A_BOLD)
        msg = f'Created: {OUTPUT_FILE} ({page_count} pages)'
        TUI.safe_addstr(s, my + 2, (w - len(msg)) // 2, msg, curses.color_pair(4))
        hint = "Press 'v' to view log  |  Press any other key to exit" if has_warnings else 'Press any key to exit...'
        TUI.safe_addstr(s, my + 4, (w - len(hint)) // 2, hint, curses.color_pair(4) | curses.A_DIM)

    LogScreen(scr, log, None, draw).run()