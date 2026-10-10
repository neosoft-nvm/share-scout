import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

vendor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor')
if os.path.isdir(vendor_path) and vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

try:
    import customtkinter as ctk
    ctk.set_appearance_mode('light')
    ctk.set_default_color_theme('blue')
    HAS_CTK = True
except Exception:
    ctk = None
    HAS_CTK = False


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
        self.scroll = ttk.Scrollbar(outer, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
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
        req_h = self.body.winfo_reqheight()
        canvas_h = self.canvas.winfo_height()
        height = max(req_h, canvas_h)
        self.canvas.itemconfigure(self.slot, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        if req_h > canvas_h + 4:
            self.scroll.grid(row=0, column=1, sticky='ns')
        else:
            self.scroll.grid_remove()

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
    vertical = ttk.Scrollbar(frame, orient='vertical', command=widget.yview)
    horizontal = ttk.Scrollbar(frame, orient='horizontal', command=widget.xview)
    def on_v(f, l):
        if float(f) <= 0.0 and float(l) >= 1.0: vertical.grid_remove()
        else: vertical.grid(row=0, column=1, sticky='ns')
        vertical.set(f, l)
    def on_h(f, l):
        if float(f) <= 0.0 and float(l) >= 1.0: horizontal.grid_remove()
        else: horizontal.grid(row=1, column=0, sticky='ew')
        horizontal.set(f, l)
    widget.configure(yscrollcommand=on_v, xscrollcommand=on_h)
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

    # Flat modern button styles
    style.configure('TButton', background='#ffffff', foreground=text_dark, bordercolor=border_color, padding=(12, 7), relief='flat', borderwidth=1)
    style.map('TButton', background=[('active', '#f1f5f9'), ('disabled', '#f8fafc')],
              foreground=[('disabled', '#94a3b8')], bordercolor=[('active', primary)])
    style.configure('Accent.TButton', background=primary, foreground='white', bordercolor=primary_hover, padding=(14, 8), relief='flat', borderwidth=0)
    style.map('Accent.TButton', background=[('active', primary_hover), ('disabled', '#cbd5e1')],
              foreground=[('disabled', '#94a3b8')])
    style.configure('HeroAction.TButton', background='#ffffff', foreground=text_dark, bordercolor=border_light, padding=(16, 12), relief='flat', borderwidth=1)
    style.map('HeroAction.TButton', background=[('active', '#f1f5f9'), ('disabled', '#cbd5e1')],
              bordercolor=[('active', primary)])
    style.configure('HeroActionAccent.TButton', background=primary, foreground='white', bordercolor=primary_hover, padding=(16, 12), relief='flat', borderwidth=0)
    style.map('HeroActionAccent.TButton', background=[('active', primary_hover), ('disabled', '#cbd5e1')])

    # Progress bar & flat Treeview inputs
    style.configure('Horizontal.TProgressbar', background=primary, troughcolor=border_light,
                    bordercolor=border_light, lightcolor='#818cf8', darkcolor=primary_hover)
    style.configure('Treeview', background='white', fieldbackground='white', foreground=text_dark, rowheight=36, relief='flat', borderwidth=0)
    style.configure('Treeview.Heading', background='#f8fafc', foreground='#334155', font=('', 10, 'bold'), padding=(8, 6), relief='flat', borderwidth=0)
    style.map('Treeview', background=[('selected', primary)], foreground=[('selected', 'white')])
    style.map('Treeview.Heading', background=[('active', '#f1f5f9')], relief=[('active', 'flat'), ('pressed', 'flat')])
    style.configure('TCheckbutton', background=bg_color, foreground=text_dark)
    style.map('TCheckbutton', background=[('active', bg_color)])
    style.configure('TEntry', fieldbackground='white', foreground=text_dark)


def action_card(parent, icon, title, subtitle, callback, accent=False, icon_image=None):
    if HAS_CTK:
        border_norm = '#c7d2fe' if accent else '#e2e8f0'
        border_hover = '#4f46e5'
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color='#ffffff', border_width=1, border_color=border_norm, cursor='hand2')
        if icon_image is not None:
            icon_lbl = tk.Label(card, image=icon_image, bg='#ffffff')
        else:
            icon_lbl = ctk.CTkLabel(card, text=str(icon), font=ctk.CTkFont(size=24))
        icon_lbl.pack(pady=(12, 4))
        title_lbl = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=13, weight='bold'), text_color='#1e1b4b' if accent else '#0f172a')
        title_lbl.pack()
        sub_lbl = ctk.CTkLabel(card, text=subtitle, font=ctk.CTkFont(size=11), text_color='#64748b', wraplength=190)
        sub_lbl.pack(pady=(2, 10))
        btn_text = 'Scan Network' if 'Find' in title else ('Add Cloud Drive' if 'Cloud' in title else 'Share Folder')
        btn_fg = '#4f46e5' if accent else '#f1f5f9'
        btn_hover = '#4338ca' if accent else '#e2e8f0'
        btn_tc = '#ffffff' if accent else '#0f172a'
        action_btn = ctk.CTkButton(card, text=btn_text, corner_radius=8, fg_color=btn_fg, hover_color=btn_hover, text_color=btn_tc, font=ctk.CTkFont(size=12, weight='bold'), height=32, command=callback)
        action_btn.pack(pady=(0, 10), padx=16, fill='x')

        def on_enter(_):
            card.configure(border_color=border_hover)

        def on_leave(_):
            card.configure(border_color=border_norm)

        def on_click(_):
            callback()

        for w in (card, icon_lbl, title_lbl, sub_lbl):
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)
            w.bind('<Button-1>', on_click)

        return card

    bg_norm = '#ffffff'
    border_norm = '#c7d2fe' if accent else '#e2e8f0'
    bg_hover = '#f8fafc'
    border_hover = '#4f46e5'
    card = tk.Frame(parent, bg=bg_norm, highlightbackground=border_norm, highlightthickness=1, padx=14, pady=12, cursor='hand2')
    if icon_image is not None:
        icon_lbl = tk.Label(card, image=icon_image, bg=bg_norm)
    else:
        icon_bg = '#e0e7ff' if accent else '#f1f5f9'
        icon_fg = '#4338ca' if accent else '#334155'
        icon_lbl = tk.Label(card, text=str(icon), font=('', 18), bg=icon_bg, fg=icon_fg, width=3, height=1, relief='flat')
    icon_lbl.pack(pady=(0, 6))
    title_lbl = tk.Label(card, text=title, font=('', 11, 'bold'), bg=bg_norm, fg='#1e1b4b' if accent else '#0f172a')
    title_lbl.pack()
    sub_lbl = tk.Label(card, text=subtitle, font=('', 9), bg=bg_norm, fg='#64748b')
    sub_lbl.pack(pady=(2, 0))

    def on_enter(_):
        card.configure(bg=bg_hover, highlightbackground=border_hover)
        title_lbl.configure(bg=bg_hover)
        sub_lbl.configure(bg=bg_hover)
        if icon_image is not None:
            icon_lbl.configure(bg=bg_hover)

    def on_leave(_):
        card.configure(bg=bg_norm, highlightbackground=border_norm)
        title_lbl.configure(bg=bg_norm)
        sub_lbl.configure(bg=bg_norm)
        if icon_image is not None:
            icon_lbl.configure(bg=bg_norm)

    def on_click(_):
        callback()

    for w in (card, icon_lbl, title_lbl, sub_lbl):
        w.bind('<Enter>', on_enter)
        w.bind('<Leave>', on_leave)
        w.bind('<Button-1>', on_click)

    return card

