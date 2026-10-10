"""Screen-aware windows with a scrollable body and permanently visible actions."""
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk


def set_app_icon(root):
    """Keep the icon alive and use it for the root and child windows."""
    try:
        root._sharescout_icon = tk.PhotoImage(file=str(Path(__file__).with_name('sharescout.png')))
        root.iconphoto(True, root._sharescout_icon)
    except tk.TclError:
        root._sharescout_icon = None


def enable_dpi_awareness():
    if os.name != 'nt': return
    import ctypes
    try: ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError): pass


def window_size(screen_width, screen_height, width, height, dpi=96):
    scale = max(1, min(dpi / 96, 3))
    usable_width = max(240, screen_width - 48)
    usable_height = max(180, screen_height - 100)
    return min(round(width * scale), usable_width), min(round(height * scale), usable_height)


def heading_size(screen_height, dpi=96, preferred=22):
    logical_height = screen_height / max(1, dpi / 96)
    return min(preferred, 12 if logical_height <= 400 else 15 if logical_height <= 640 else preferred)


def heading_font(window, preferred=22):
    return ('', heading_size(window.winfo_screenheight(), window.winfo_fpixels('1i'), preferred), 'bold')


def fit_window(window, width=900, height=600):
    w, h = window_size(window.winfo_screenwidth(), window.winfo_screenheight(), width, height, window.winfo_fpixels('1i'))
    window.geometry(f'{w}x{h}')
    window.minsize(min(400, w), min(280, h))


def label(parent, **kwargs):
    kwargs.setdefault('wraplength', 300)
    kwargs.setdefault('justify', 'left')
    widget = ttk.Label(parent, **kwargs)
    widget.bind('<Configure>', lambda event: widget.configure(wraplength=max(60, event.width - 4)))
    return widget


class Layout:
    def __init__(self, window, width=900, height=600):
        fit_window(window, width, height)
        self.window = window
        window._sharescout_layout = self
        try: window.configure(background='#f8fafc')
        except Exception: pass
        outer = ttk.Frame(window, padding=14); outer.pack(fill='both', expand=True)
        outer.columnconfigure(0, weight=1); outer.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(outer, highlightthickness=0, borderwidth=0, background='#f8fafc')
        scroll = ttk.Scrollbar(outer, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.grid(row=0, column=0, sticky='nsew'); scroll.grid(row=0, column=1, sticky='ns')
        self.body = ttk.Frame(self.canvas, padding=(8, 4, 8, 10))
        self.slot = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.footer = ttk.Frame(outer, padding=(8, 10, 8, 0)); self.footer.grid(row=1, column=0, columnspan=2, sticky='ew')
        self.pending = False
        self.canvas.bind('<Configure>', self.schedule_fit)
        self.body.bind('<Configure>', self.schedule_fit)
        window.bind('<MouseWheel>', self.wheel, add='+')
        window.bind('<Button-4>', self.wheel, add='+')
        window.bind('<Button-5>', self.wheel, add='+')
        window.bind('<FocusIn>', self.focus, add='+')
        window.bind('<Destroy>', self.destroyed, add='+')

    def destroyed(self, event):
        if event.widget != self.window: return
        commands = set(self.window._tclCommands or [])
        for callback in self.window.tk.call('after', 'info'):
            try:
                script = str(self.window.tk.call('after', 'info', callback)[0])
                if script.split()[0] in commands: self.window.after_cancel(callback)
            except (tk.TclError, IndexError): pass

    def schedule_fit(self, _=None):
        if not self.pending:
            self.pending = True; self.window.after_idle(self.fit)

    def fit(self):
        self.pending = False
        if not self.canvas.winfo_exists(): return
        width = max(1, self.canvas.winfo_width())
        height = max(self.body.winfo_reqheight(), self.canvas.winfo_height())
        self.canvas.itemconfigure(self.slot, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def descendant(self, widget):
        while widget is not None:
            if widget == self.body: return True
            widget = getattr(widget, 'master', None)
        return False

    def wheel(self, event):
        if not self.descendant(event.widget) or event.widget.winfo_class() in ('Treeview', 'TCombobox', 'Text'): return
        if self.body.winfo_height() <= self.canvas.winfo_height(): return
        direction = -1 if getattr(event, 'num', 0) == 4 or getattr(event, 'delta', 0) > 0 else 1
        self.canvas.yview_scroll(direction * 3, 'units')
        return 'break'

    def focus(self, event):
        widget = event.widget
        if not self.descendant(widget): return
        self.window.after_idle(lambda: self.reveal(widget))

    def reveal(self, widget):
        if not widget.winfo_exists(): return
        region_height = max(1, self.body.winfo_height())
        top = self.canvas.yview()[0] * region_height
        y = widget.winfo_rooty() - self.body.winfo_rooty()
        bottom = y + widget.winfo_height()
        if y < top: self.canvas.yview_moveto(y / region_height)
        elif bottom > top + self.canvas.winfo_height():
            self.canvas.yview_moveto((bottom - self.canvas.winfo_height() + 12) / region_height)


def button_columns(width, requested_widths, maximum=4):
    return max(1, min(maximum, len(requested_widths), int(width / max(1, max(requested_widths, default=1) + 12))))


def buttons(parent, actions, accent=(), maximum=4, hero=False):
    widgets = []
    for text, callback in actions:
        if hero:
            style = 'HeroActionAccent.TButton' if text in accent else 'HeroAction.TButton'
        else:
            style = 'Accent.TButton' if text in accent else 'TButton'
        widgets.append(ttk.Button(parent, text=text, command=callback, style=style))
    old_columns = 0
    def arrange(event=None):
        nonlocal old_columns
        width = event.width if event else parent.winfo_width()
        columns = button_columns(width, [widget.winfo_reqwidth() for widget in widgets], maximum)
        for i in range(max(old_columns, columns)): parent.columnconfigure(i, weight=1 if i < columns else 0)
        for i, widget in enumerate(widgets): widget.grid(row=i // columns, column=i % columns, sticky='ew', padx=4, pady=4)
        old_columns = columns
    parent.bind('<Configure>', arrange)
    for widget in widgets: widget.bind('<Configure>', lambda _event: arrange())
    arrange()
    return widgets


def tree(parent, **kwargs):
    frame = ttk.Frame(parent)
    frame.pack(fill='both', expand=True)
    frame.columnconfigure(0, weight=1); frame.rowconfigure(0, weight=1)
    widget = ttk.Treeview(frame, **kwargs); widget.grid(row=0, column=0, sticky='nsew')
    vertical = ttk.Scrollbar(frame, orient='vertical', command=widget.yview); vertical.grid(row=0, column=1, sticky='ns')
    horizontal = ttk.Scrollbar(frame, orient='horizontal', command=widget.xview); horizontal.grid(row=1, column=0, sticky='ew')
    widget.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    return widget


def apply_theme(root):
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except tk.TclError:
        pass
    bg_color = '#f8fafc'
    text_dark = '#0f172a'
    text_muted = '#475569'
    text_subtle = '#64748b'
    border_color = '#cbd5e1'
    border_light = '#e2e8f0'
    primary = '#4f46e5'
    primary_hover = '#4338ca'

    style.configure('TFrame', background=bg_color)
    style.configure('Card.TFrame', background='#ffffff')
    style.configure('TLabel', background=bg_color, foreground=text_dark)
    style.configure('Muted.TLabel', background=bg_color, foreground=text_subtle)
    style.configure('TLabelframe', background=bg_color, bordercolor=border_light)
    style.configure('TLabelframe.Label', background=bg_color, foreground=text_muted, font=('', 10, 'bold'))
    style.configure('Hero.TLabel', foreground='#1e1b4b', font=('', 20, 'bold'))
    style.configure('Subtitle.TLabel', foreground=text_subtle, font=('', 11))
    style.configure('Section.TLabel', foreground=text_dark, font=('', 13, 'bold'))

    # Button styles
    style.configure('TButton', background='#ffffff', foreground=text_dark, bordercolor=border_color, padding=(12, 7))
    style.map('TButton', background=[('active', '#f1f5f9'), ('disabled', '#f8fafc')],
              foreground=[('disabled', '#94a3b8')], bordercolor=[('active', '#94a3b8')])
    style.configure('Accent.TButton', background=primary, foreground='white', bordercolor=primary_hover, padding=(14, 8))
    style.map('Accent.TButton', background=[('active', primary_hover), ('disabled', '#cbd5e1')],
              foreground=[('disabled', '#94a3b8')], bordercolor=[('active', primary_hover)])
    style.configure('HeroAction.TButton', background='#ffffff', foreground=text_dark, bordercolor=border_light, padding=(16, 12))
    style.map('HeroAction.TButton', background=[('active', '#f1f5f9'), ('disabled', '#cbd5e1')],
              bordercolor=[('active', primary)])
    style.configure('HeroActionAccent.TButton', background=primary, foreground='white', bordercolor=primary_hover, padding=(16, 12))
    style.map('HeroActionAccent.TButton', background=[('active', primary_hover), ('disabled', '#cbd5e1')])

    # Progress bar & inputs
    style.configure('Horizontal.TProgressbar', background=primary, troughcolor=border_light,
                    bordercolor=border_light, lightcolor='#818cf8', darkcolor=primary_hover)
    style.configure('Treeview', background='white', fieldbackground='white', foreground=text_dark, rowheight=34)
    style.configure('Treeview.Heading', background='#f1f5f9', foreground='#334155', font=('', 10, 'bold'), padding=(6, 4))
    style.map('Treeview', background=[('selected', primary)], foreground=[('selected', 'white')])
    style.map('Treeview.Heading', background=[('active', '#e2e8f0')])
    style.configure('TCheckbutton', background=bg_color, foreground=text_dark)
    style.map('TCheckbutton', background=[('active', bg_color)])
    style.configure('TEntry', fieldbackground='white', foreground=text_dark)
