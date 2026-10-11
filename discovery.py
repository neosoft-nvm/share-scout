"""Beginner-first shared folder discovery wizard with modern high-DPI card view."""
import os
import queue
import sys
import threading

vendor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor')
if os.path.isdir(vendor_path) and vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

import tkinter as tk
from tkinter import ttk, messagebox
import network
import credentials as credential_store
import ui
from app_info import window_title

try:
    import customtkinter as ctk
    HAS_CTK = ui.HAS_CTK
except Exception:
    ctk = None
    HAS_CTK = False


def ask_credentials(parent, address, callback):
    if HAS_CTK:
        dialog = ctk.CTkToplevel(parent)
        dialog.title(window_title('Sign in to this device'))
        dialog.configure(fg_color='#f8fafc')
        dialog.transient(parent)
        dialog.grab_set()

        sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        w, h = min(480, sw - 40), min(420, sh - 60)
        x, y = max(0, (sw - w) // 2), max(0, (sh - h) // 2)
        dialog.geometry(f'{w}x{h}+{x}+{y}')
        dialog.resizable(False, False)

        frame = ctk.CTkFrame(dialog, fg_color='transparent', padx=24, pady=20)
        frame.pack(fill='both', expand=True)

        ctk.CTkLabel(frame, text='Sign in to this device', font=ctk.CTkFont(size=18, weight='bold'), text_color='#1e1b4b').pack(anchor='w')
        ctk.CTkLabel(frame, text=f'Device: {address}\nUse an account that can open folders on this device.', font=ctk.CTkFont(size=12), text_color='#64748b', justify='left').pack(anchor='w', pady=(4, 14))

        values = {}
        for key, lbl_text in [('username', 'Username'), ('password', 'Password'), ('domain', 'Domain (optional — usually blank)')]:
            ctk.CTkLabel(frame, text=lbl_text, font=ctk.CTkFont(size=12, weight='bold'), text_color='#334155').pack(anchor='w', pady=(4, 2))
            var = tk.StringVar(); values[key] = var
            field = ctk.CTkEntry(frame, textvariable=var, show='•' if key == 'password' else '', height=32, corner_radius=6, border_color='#cbd5e1')
            field.pack(fill='x', pady=(0, 4))
            if key == 'username': field.focus_set()

        remember = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame, text='Remember password in secure credential store', variable=remember, font=ctk.CTkFont(size=11), text_color='#475569', fg_color='#4f46e5', hover_color='#4338ca').pack(anchor='w', pady=(10, 4))

        footer = ctk.CTkFrame(dialog, fg_color='#f1f5f9', height=56, corner_radius=0)
        footer.pack(fill='x', side='bottom')

        def submit():
            if not values['username'].get().strip():
                messagebox.showinfo('Username', 'Enter your username.', parent=dialog); return
            creds = {k: v.get().strip() if k != 'password' else v.get() for k, v in values.items()}
            dialog.destroy(); callback(creds, remember.get())

        ctk.CTkButton(footer, text='Cancel', width=80, height=32, corner_radius=6, fg_color='#ffffff', hover_color='#e2e8f0', text_color='#475569', border_width=1, border_color='#cbd5e1', command=dialog.destroy).pack(side='right', padx=(6, 16), pady=12)
        ctk.CTkButton(footer, text='Sign in', width=90, height=32, corner_radius=6, fg_color='#4f46e5', hover_color='#4338ca', text_color='#ffffff', font=ctk.CTkFont(size=12, weight='bold'), command=submit).pack(side='right', padx=6, pady=12)
        dialog.bind('<Return>', lambda _: submit())
        return

    dialog = tk.Toplevel(parent)
    dialog.title(window_title('Sign in to this device'))
    dialog.transient(parent); dialog.grab_set()
    layout = ui.Layout(dialog, 480, 410); frame = layout.body
    ui.label(frame, text='Sign in to this device', font=ui.heading_font(dialog, 16), style='Hero.TLabel').pack(fill='x')
    ui.label(frame, text=f'Device: {address}\nUse an account that can open folders on this device.', style='Subtitle.TLabel').pack(fill='x', pady=(4, 10))
    values = {}
    for key, label in [('username', 'Username'), ('password', 'Password'), ('domain', 'Domain (optional — usually leave blank)')]:
        ui.label(frame, text=label).pack(fill='x', pady=(6, 2))
        var = tk.StringVar(); values[key] = var
        field = ttk.Entry(frame, textvariable=var, show='•' if key == 'password' else '')
        field.pack(fill='x')
        if key == 'username': field.focus_set()
    remember = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text='Remember this password in the system password store', variable=remember).pack(anchor='w', pady=(10, 2))
    ui.label(frame, text='Leave unchecked to use it for this session only.', style='Muted.TLabel').pack(fill='x', pady=2)
    def submit():
        if not values['username'].get().strip():
            messagebox.showinfo('Username', 'Enter your username.', parent=dialog); return
        credentials = {key: var.get().strip() if key != 'password' else var.get() for key, var in values.items()}
        dialog.destroy(); callback(credentials, remember.get())
    ui.buttons(layout.footer, [('Cancel', dialog.destroy), ('Sign in', submit)], accent=('Sign in',), maximum=2)
    dialog.bind('<Return>', lambda _: submit())


class Finder:
    def __init__(self, app):
        self.app = app
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.scan_generation = 0
        self.browse_generation = 0
        self.address = None
        self.shares = []
        self.devices = {}          # address -> dict(name=..., category=..., widget=...)
        self.share_widgets = []    # list of CTkFrame share card widgets
        self.selected_device = None
        self.selected_share_index = None

        if HAS_CTK:
            self.window = ctk.CTkToplevel(app.root)
            self.window.title(window_title('Find Network Folders'))
            self.window.configure(fg_color='#f8fafc')
            self.window.transient(app.root)
            self.window.protocol('WM_DELETE_WINDOW', self.close)

            ui.fit_window(self.window, 940, 620)

            main_container = ctk.CTkFrame(self.window, fg_color='transparent', corner_radius=0)
            main_container.pack(fill='both', expand=True, padx=20, pady=(16, 16))

            # 1. Header & Telemetry
            hdr_frame = ctk.CTkFrame(main_container, fg_color='transparent')
            hdr_frame.pack(fill='x', pady=(0, 10))

            title_row = ctk.CTkFrame(hdr_frame, fg_color='transparent')
            title_row.pack(fill='x')
            ctk.CTkLabel(title_row, text='Find Network Folders', font=ctk.CTkFont(size=18, weight='bold'), text_color='#1e1b4b').pack(side='left')

            telemetry_card = ctk.CTkFrame(hdr_frame, fg_color='#ffffff', corner_radius=10, border_width=1, border_color='#e2e8f0')
            telemetry_card.pack(fill='x', pady=(8, 0))

            tele_inner = ctk.CTkFrame(telemetry_card, fg_color='transparent')
            tele_inner.pack(fill='x', padx=14, pady=8)

            self.status = tk.StringVar(value='Looking for devices on your connected networks…')
            self.status_lbl = ctk.CTkLabel(tele_inner, textvariable=self.status, font=ctk.CTkFont(size=12), text_color='#475569', anchor='w')
            self.status_lbl.pack(side='left', fill='x', expand=True)

            self.rescan_btn = ctk.CTkButton(
                tele_inner, text='⟳ Rescan', width=88, height=28, corner_radius=14,
                fg_color='#e0e7ff', hover_color='#c7d2fe', text_color='#4338ca',
                font=ctk.CTkFont(size=11, weight='bold'), command=self.start_scan
            )
            self.rescan_btn.pack(side='right', padx=(6, 0))

            self.stop_btn = ctk.CTkButton(
                tele_inner, text='⏹ Stop', width=76, height=28, corner_radius=14,
                fg_color='#fee2e2', hover_color='#fecaca', text_color='#b91c1c',
                font=ctk.CTkFont(size=11, weight='bold'), command=lambda: self.stop.set()
            )
            self.stop_btn.pack(side='right')

            self.progress = ctk.CTkProgressBar(telemetry_card, height=4, corner_radius=2, fg_color='#e2e8f0', progress_color='#4f46e5')
            self.progress.pack(fill='x', padx=14, pady=(0, 8))
            self.progress.set(0)

            # 2. Two-Column Split View
            split_frame = ctk.CTkFrame(main_container, fg_color='transparent')
            split_frame.pack(fill='both', expand=True, pady=(0, 12))
            split_frame.columnconfigure(0, weight=1)
            split_frame.columnconfigure(1, weight=1)
            split_frame.rowconfigure(0, weight=1)

            # Left Column: Discovered Devices
            left_col = ctk.CTkFrame(split_frame, fg_color='transparent')
            left_col.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
            left_col.rowconfigure(1, weight=1)
            left_col.columnconfigure(0, weight=1)

            left_hdr = ctk.CTkFrame(left_col, fg_color='transparent')
            left_hdr.grid(row=0, column=0, sticky='ew', pady=(0, 6))
            ctk.CTkLabel(left_hdr, text='Discovered Devices', font=ctk.CTkFont(size=13, weight='bold'), text_color='#0f172a').pack(side='left')
            self.device_count_lbl = ctk.CTkLabel(left_hdr, text='Scanning…', font=ctk.CTkFont(size=11), text_color='#94a3b8')
            self.device_count_lbl.pack(side='right')

            self.devices_frame = ctk.CTkScrollableFrame(left_col, fg_color='#ffffff', border_width=1, border_color='#e2e8f0', corner_radius=10)
            self.devices_frame.grid(row=1, column=0, sticky='nsew')


            # Right Column: Shared Folders
            right_col = ctk.CTkFrame(split_frame, fg_color='transparent')
            right_col.grid(row=0, column=1, sticky='nsew', padx=(8, 0))
            right_col.rowconfigure(1, weight=1)
            right_col.columnconfigure(0, weight=1)

            right_hdr = ctk.CTkFrame(right_col, fg_color='transparent')
            right_hdr.grid(row=0, column=0, sticky='ew', pady=(0, 6))
            self.folders_title = ctk.CTkLabel(right_hdr, text='Shared Folders', font=ctk.CTkFont(size=13, weight='bold'), text_color='#0f172a')
            self.folders_title.pack(side='left')
            self.share_count_lbl = ctk.CTkLabel(right_hdr, text='Select a device', font=ctk.CTkFont(size=11), text_color='#94a3b8')
            self.share_count_lbl.pack(side='right')

            self.folders_frame = ctk.CTkScrollableFrame(right_col, fg_color='#ffffff', border_width=1, border_color='#e2e8f0', corner_radius=10)
            self.folders_frame.grid(row=1, column=0, sticky='nsew')

            # 3. Bottom Action Dock matching mockup:
            # Left: "Need credentials? Sign In" (or Reconnect option)
            # Right: "Connect Selected Folder" | "Cancel" | "Manual IP"
            dock = ctk.CTkFrame(main_container, fg_color='#ffffff', corner_radius=10, border_width=1, border_color='#e2e8f0')
            dock.pack(fill='x')

            dock_inner = ctk.CTkFrame(dock, fg_color='transparent')
            dock_inner.pack(fill='x', padx=16, pady=10)

            self.auto = tk.BooleanVar(value=True)

            left_dock_box = ctk.CTkFrame(dock_inner, fg_color='transparent')
            left_dock_box.pack(side='left')

            self.sign_button = ctk.CTkButton(left_dock_box, text='Need credentials? Sign In', fg_color='transparent', hover_color='#eef2ff', text_color='#4f46e5', font=ctk.CTkFont(size=12, underline=True), height=28, command=self.sign_in)
            self.sign_button.pack(side='left')

            ctk.CTkButton(
                dock_inner, text='Manual IP', width=90, height=34, corner_radius=8,
                fg_color='#ffffff', hover_color='#f1f5f9', text_color='#0f172a',
                border_width=1, border_color='#cbd5e1', font=ctk.CTkFont(size=12), command=self.direct_dialog
            ).pack(side='right', padx=(6, 0))

            ctk.CTkButton(
                dock_inner, text='Cancel', width=76, height=34, corner_radius=8,
                fg_color='#ffffff', hover_color='#f1f5f9', text_color='#0f172a',
                border_width=1, border_color='#cbd5e1', font=ctk.CTkFont(size=12), command=self.close
            ).pack(side='right', padx=(6, 0))

            self.connect_btn = ctk.CTkButton(
                dock_inner, text='Connect Selected Folder', height=34, corner_radius=8,
                fg_color='#4f46e5', hover_color='#4338ca', text_color='#ffffff',
                font=ctk.CTkFont(size=12, weight='bold'), state='disabled', command=self.connect
            )
            self.connect_btn.pack(side='right')

            # Compatibility wrappers for tests and legacy access
            self.scan_button = self.rescan_btn
            self.connect_button = self.connect_btn
            self.computers = _ComputersCompat(self)
            self.folders = _FoldersCompat(self)

            self._show_empty_devices_placeholder('Scanning network for devices…')
            self._show_empty_folders_placeholder('Select a discovered device on the left to view shared folders.')

        else:
            # Fallback Tkinter layout
            self.window = tk.Toplevel(app.root)
            self.window.title(window_title('Find shared folders'))
            self.window.transient(app.root)
            self.window.protocol('WM_DELETE_WINDOW', self.close)
            layout = ui.Layout(self.window, 870, 640); frame = layout.body
            ui.label(frame, text='Find shared folders', font=ui.heading_font(self.window), style='Hero.TLabel').pack(fill='x')
            ui.label(frame, text='Choose a device and folder, then Connect.', style='Subtitle.TLabel').pack(fill='x', pady=(4, 14))
            control = ttk.Frame(frame); control.pack(fill='x')
            self.scan_button = ui.buttons(control, [('Scan my network', self.start_scan), ('Stop scan', lambda: self.stop.set())], accent=('Scan my network',), maximum=2)[0]
            self.status = tk.StringVar(value='Looking for devices on your connected networks…')
            ui.label(frame, textvariable=self.status, style='Muted.TLabel', wraplength=800).pack(fill='x', pady=(10, 4))
            self.progress = ttk.Progressbar(frame, maximum=100); self.progress.pack(fill='x', pady=(0, 12))
            lists = ttk.Frame(frame); lists.pack(fill='both', expand=True)
            left = ttk.Frame(lists); right = ttk.Frame(lists)
            left.grid(row=0, column=0, sticky='nsew', padx=(0, 12))
            right.grid(row=0, column=1, sticky='nsew')
            lists.columnconfigure(0, weight=1); lists.columnconfigure(1, weight=1)
            ui.label(left, text='Devices with file sharing', font=('', 12, 'bold'), style='Section.TLabel').pack(fill='x', pady=(0, 4))
            computer_list = ttk.Frame(left); computer_list.pack(fill='both', expand=True, pady=6)
            self.computers = ui.tree(computer_list, columns=('ip',), show='headings', selectmode='browse', height=8)
            self.computers.heading('ip', text='IP address')
            self.computers.bind('<<TreeviewSelect>>', self.choose_computer)
            ui.label(right, text='Shared folders', font=('', 12, 'bold'), style='Section.TLabel').pack(fill='x', pady=(0, 4))
            folder_list = ttk.Frame(right); folder_list.pack(fill='both', expand=True, pady=6)
            self.folders = ui.tree(folder_list, columns=('name', 'comment'), show='headings', selectmode='browse', height=8)
            self.folders.heading('name', text='Folder'); self.folders.heading('comment', text='Description')
            self.folders.bind('<<TreeviewSelect>>', lambda _: self.connect_button.configure(state='normal' if self.folders.selection() else 'disabled'))
            self.folders.bind('<Double-1>', lambda _: self.connect())
            self.sign_button = ttk.Button(right, text='Sign in to see more folders', command=self.sign_in); self.sign_button.pack(fill='x')
            footer = layout.footer
            self.auto = tk.BooleanVar(value=True)
            ttk.Checkbutton(footer, text='Reconnect when this app opens', variable=self.auto).pack(fill='x', pady=(0, 8))
            self.connect_button = ui.buttons(footer, [('Cancel', self.close), ('Connect this folder', self.connect)], accent=('Connect this folder',), maximum=2)[1]
            self.connect_button.configure(state='disabled')

        self.window.after(100, self.poll)
        self.window.after(200, self.start_scan)

    def _show_empty_devices_placeholder(self, msg):
        if not HAS_CTK: return
        for child in self.devices_frame.winfo_children(): child.destroy()
        box = ctk.CTkFrame(self.devices_frame, fg_color='transparent')
        box.pack(fill='both', expand=True, pady=40)
        ctk.CTkLabel(box, text='📡', font=ctk.CTkFont(size=24)).pack(pady=(0, 6))
        ctk.CTkLabel(box, text=msg, font=ctk.CTkFont(size=12), text_color='#94a3b8').pack()

    def _show_empty_folders_placeholder(self, msg):
        if not HAS_CTK: return
        for child in self.folders_frame.winfo_children(): child.destroy()
        box = ctk.CTkFrame(self.folders_frame, fg_color='transparent')
        box.pack(fill='both', expand=True, pady=40)
        ctk.CTkLabel(box, text='📁', font=ctk.CTkFont(size=24)).pack(pady=(0, 6))
        ctk.CTkLabel(box, text=msg, font=ctk.CTkFont(size=12), text_color='#94a3b8').pack()

    def _add_device_card(self, address):
        if not HAS_CTK: return
        if not self.devices:
            for child in self.devices_frame.winfo_children(): child.destroy()

        addr_str = str(address)
        # Determine category & icon
        icon = '🖥️'
        category = 'Desktop'
        cat_bg = '#f1f5f9'
        cat_fg = '#475569'

        low = addr_str.lower()
        if 'nas' in low or 'vault' in low or 'storage' in low or addr_str.endswith('.150') or addr_str.endswith('.200'):
            icon = '🗄️'; category = 'NAS'; cat_bg = '#e0e7ff'; cat_fg = '#3730a3'
        elif 'server' in low or addr_str.endswith('.201') or addr_str.endswith('.254'):
            icon = '🖧'; category = 'Server'; cat_bg = '#ede9fe'; cat_fg = '#5b21b6'
        elif 'laptop' in low or 'book' in low:
            icon = '💻'; category = 'Laptop'; cat_bg = '#f1f5f9'; cat_fg = '#475569'

        card = ctk.CTkFrame(self.devices_frame, corner_radius=8, fg_color='#ffffff', border_width=1, border_color='#e2e8f0', cursor='hand2')
        card.pack(fill='x', pady=3, padx=2)

        inner = ctk.CTkFrame(card, fg_color='transparent')
        inner.pack(fill='x', padx=10, pady=8)

        icon_lbl = ctk.CTkLabel(inner, text=icon, font=ctk.CTkFont(size=16))
        icon_lbl.pack(side='left', padx=(0, 8))

        text_box = ctk.CTkFrame(inner, fg_color='transparent')
        text_box.pack(side='left', fill='y')

        name_lbl = ctk.CTkLabel(text_box, text=addr_str, font=ctk.CTkFont(size=12, weight='bold'), text_color='#0f172a', anchor='w')
        name_lbl.pack(anchor='w')

        badge = ctk.CTkLabel(inner, text=category, corner_radius=6, fg_color=cat_bg, text_color=cat_fg, font=ctk.CTkFont(size=10, weight='bold'), padx=8, pady=2)
        badge.pack(side='right')

        def on_enter(_):
            if self.selected_device != addr_str:
                card.configure(border_color='#c7d2fe')

        def on_leave(_):
            if self.selected_device != addr_str:
                card.configure(border_color='#e2e8f0', fg_color='#ffffff')

        def on_click(_=None):
            self.select_device(addr_str)

        for w in (card, inner, icon_lbl, text_box, name_lbl, badge):
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)
            w.bind('<Button-1>', on_click)

        self.devices[addr_str] = {
            'card': card, 'category': category, 'badge': badge
        }
        self.device_count_lbl.configure(text=f'{len(self.devices)} device(s)')

    def select_device(self, address):
        self.selected_device = str(address)
        clean_ip = str(address).split(' - ')[0].strip() if ' - ' in str(address) else str(address)
        if HAS_CTK:
            for addr, dev in self.devices.items():
                if addr == address or addr.startswith(clean_ip):
                    dev['card'].configure(border_color='#4f46e5', border_width=2, fg_color='#eef2ff')
                else:
                    dev['card'].configure(border_color='#e2e8f0', border_width=1, fg_color='#ffffff')
            self.folders_title.configure(text=f'Shared Folders on {clean_ip}')
            self.share_count_lbl.configure(text='Loading…')
            self._show_empty_folders_placeholder(f'Looking for folders on {clean_ip}…')
        self.browse(clean_ip)

    def _render_shares(self):
        if not HAS_CTK: return
        for child in self.folders_frame.winfo_children(): child.destroy()
        self.share_widgets = []
        self.selected_share_index = None
        self.connect_btn.configure(state='disabled')

        if not self.shares:
            self._show_empty_folders_placeholder('No visible shared folders found on this device.')
            self.share_count_lbl.configure(text='0 folders')
            return

        self.share_count_lbl.configure(text=f'{len(self.shares)} folder(s)')

        for idx, share in enumerate(self.shares):
            sname = share['name']
            scomment = share.get('comment', '')

            # Badge determination
            b_text = 'Read/Write'
            b_bg = '#dcfce7'
            b_fg = '#15803d'

            low_name = sname.lower()
            low_com = scomment.lower()
            if 'public' in low_name or 'guest' in low_name or 'guest' in low_com:
                b_text = 'Guest'; b_bg = '#f1f5f9'; b_fg = '#475569'
            elif 'pass' in low_com or 'protect' in low_com or 'auth' in low_com:
                b_text = 'Password Protected'; b_bg = '#fef3c7'; b_fg = '#b45309'

            card = ctk.CTkFrame(self.folders_frame, corner_radius=8, fg_color='#ffffff', border_width=1, border_color='#e2e8f0', cursor='hand2')
            card.pack(fill='x', pady=3, padx=2)

            inner = ctk.CTkFrame(card, fg_color='transparent')
            inner.pack(fill='x', padx=10, pady=8)

            icon_lbl = ctk.CTkLabel(inner, text='📁', font=ctk.CTkFont(size=16))
            icon_lbl.pack(side='left', padx=(0, 8))

            text_box = ctk.CTkFrame(inner, fg_color='transparent')
            text_box.pack(side='left', fill='y')

            title_lbl = ctk.CTkLabel(text_box, text=sname, font=ctk.CTkFont(size=12, weight='bold'), text_color='#0f172a', anchor='w')
            title_lbl.pack(anchor='w')

            if scomment:
                sub_lbl = ctk.CTkLabel(text_box, text=scomment, font=ctk.CTkFont(size=10), text_color='#64748b', anchor='w')
                sub_lbl.pack(anchor='w')
            else:
                sub_lbl = None

            badge = ctk.CTkLabel(inner, text=b_text, corner_radius=6, fg_color=b_bg, text_color=b_fg, font=ctk.CTkFont(size=10, weight='bold'), padx=8, pady=2)
            badge.pack(side='right')

            cur_idx = idx

            def on_enter(_, c=card, i=cur_idx):
                if self.selected_share_index != i:
                    c.configure(border_color='#c7d2fe')

            def on_leave(_, c=card, i=cur_idx):
                if self.selected_share_index != i:
                    c.configure(border_color='#e2e8f0', fg_color='#ffffff')

            def on_select(_, i=cur_idx):
                self.selected_share_index = i
                for j, w in enumerate(self.share_widgets):
                    if j == i:
                        w.configure(border_color='#4f46e5', border_width=2, fg_color='#eef2ff')
                    else:
                        w.configure(border_color='#e2e8f0', border_width=1, fg_color='#ffffff')
                self.connect_btn.configure(state='normal')

            def on_dbl(_, i=cur_idx):
                on_select(None, i)
                self.connect()

            for w in [card, inner, icon_lbl, text_box, title_lbl, badge]:
                w.bind('<Enter>', on_enter)
                w.bind('<Leave>', on_leave)
                w.bind('<Button-1>', on_select)
                w.bind('<Double-1>', on_dbl)
            if sub_lbl:
                sub_lbl.bind('<Enter>', on_enter)
                sub_lbl.bind('<Leave>', on_leave)
                sub_lbl.bind('<Button-1>', on_select)
                sub_lbl.bind('<Double-1>', on_dbl)

            self.share_widgets.append(card)

    def start_scan(self):
        btn_state = str(self.scan_button.cget('state') if HAS_CTK else self.scan_button['state'])
        if btn_state == 'disabled': return

        self.address = None; self.shares = []; self.browse_generation += 1
        self.selected_device = None; self.selected_share_index = None

        if HAS_CTK:
            self.devices = {}
            self.share_widgets = []
            self._show_empty_devices_placeholder('Scanning connected networks…')
            self._show_empty_folders_placeholder('Select a discovered device on the left.')
            self.connect_btn.configure(state='disabled')
            self.rescan_btn.configure(state='disabled')
            self.progress.set(0)
        else:
            self.folders.delete(*self.folders.get_children())
            self.computers.delete(*self.computers.get_children())
            self.connect_button.configure(state='disabled')
            self.scan_button.configure(state='disabled')
            self.progress['value'] = 0

        self.stop = threading.Event(); self.scan_generation += 1
        generation = self.scan_generation; stop = self.stop
        self.status.set('Finding your local network…')

        def worker():
            try:
                ranges = network.local_networks()
                if not ranges: raise RuntimeError('Connect to Wi-Fi or plug in a network cable, then scan again.')
                labels = ', '.join(item['network'] + (' (nearby addresses only)' if item['limited'] else '') for item in ranges)
                self.events.put(('scan_label', generation, labels))
                network.scan(ranges, stop, lambda address, done, total: self.events.put(('scan', generation, address, done, total)))
                self.events.put(('scan_done', generation, stop.is_set()))
            except Exception as exc: self.events.put(('scan_error', generation, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def choose_computer(self, _=None):
        selected = self.computers.selection()
        if selected: self.browse(selected[0])

    def direct_dialog(self):
        if HAS_CTK:
            dialog = ctk.CTkToplevel(self.window)
            dialog.title(window_title('Manual Network Address'))
            dialog.configure(fg_color='#f8fafc')
            dialog.transient(self.window); dialog.grab_set()

            sw, sh = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
            w, h = min(420, sw - 40), min(220, sh - 60)
            x, y = max(0, (sw - w) // 2), max(0, (sh - h) // 2)
            dialog.geometry(f'{w}x{h}+{x}+{y}')
            dialog.resizable(False, False)

            frame = ctk.CTkFrame(dialog, fg_color='transparent', padx=20, pady=16)
            frame.pack(fill='both', expand=True)

            ctk.CTkLabel(frame, text='Enter IP Address', font=ctk.CTkFont(size=15, weight='bold'), text_color='#1e1b4b').pack(anchor='w')
            ctk.CTkLabel(frame, text='Directly connect to a PC or NAS by IPv4 address:', font=ctk.CTkFont(size=11), text_color='#64748b').pack(anchor='w', pady=(2, 8))

            ip_var = tk.StringVar()
            entry = ctk.CTkEntry(frame, textvariable=ip_var, placeholder_text='e.g. 192.168.1.150', height=34, corner_radius=6, border_color='#cbd5e1')
            entry.pack(fill='x', pady=(0, 14))
            entry.focus_set()

            def submit():
                raw = ip_var.get().strip()
                try: address = network.validate_ip(raw)
                except ValueError:
                    messagebox.showinfo('IP address', 'Enter a valid address like 192.168.1.20.', parent=dialog); return
                dialog.destroy()
                if address not in self.devices:
                    self._add_device_card(address)
                self.select_device(address)

            btn_box = ctk.CTkFrame(frame, fg_color='transparent')
            btn_box.pack(fill='x')
            ctk.CTkButton(btn_box, text='Cancel', width=80, height=32, corner_radius=6, fg_color='#ffffff', hover_color='#f1f5f9', text_color='#475569', border_width=1, border_color='#cbd5e1', command=dialog.destroy).pack(side='right', padx=(6, 0))
            ctk.CTkButton(btn_box, text='Show Folders', width=100, height=32, corner_radius=6, fg_color='#4f46e5', hover_color='#4338ca', text_color='#ffffff', font=ctk.CTkFont(size=12, weight='bold'), command=submit).pack(side='right')
            dialog.bind('<Return>', lambda _: submit())
            return

        # Fallback dialog
        top = tk.Toplevel(self.window)
        top.title('Enter IP Address')
        top.transient(self.window)
        var = tk.StringVar()
        ttk.Label(top, text='Enter IP Address:').pack(padx=10, pady=5)
        ent = ttk.Entry(top, textvariable=var); ent.pack(padx=10, pady=5); ent.focus_set()
        def sub():
            try: addr = network.validate_ip(var.get())
            except ValueError:
                messagebox.showinfo('IP address', 'Enter valid IP', parent=top); return
            top.destroy()
            if not self.computers.exists(addr): self.computers.insert('', 'end', iid=addr, values=(addr,))
            self.computers.selection_set(addr)
        ttk.Button(top, text='OK', command=sub).pack(padx=10, pady=5)

    def direct(self):
        self.direct_dialog()

    def browse(self, address):
        self.address = address; self.browse_generation += 1
        generation = self.browse_generation
        self.shares = []

        if HAS_CTK:
            self.connect_btn.configure(state='disabled')
            self._show_empty_folders_placeholder(f'Looking for shared folders on {address}…')
        else:
            self.folders.delete(*self.folders.get_children())
            self.connect_button.configure(state='disabled')

        self.status.set(f'Looking for shared folders on {address}…')
        credentials = self.app.credentials.get(address)
        if credentials is None:
            credentials = credential_store.load(address)
            if credentials: self.app.credentials[address] = credentials

        def worker():
            try: self.events.put(('shares', generation, network.list_shares(address, credentials)))
            except PermissionError: self.events.put(('auth', generation, bool(credentials)))
            except Exception as exc: self.events.put(('browse_error', generation, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def sign_in(self):
        if not self.address:
            self.status.set('Pick a device first.'); return
        address = self.address
        def signed(credentials, remember=False):
            self.app.credentials[address] = credentials
            if remember:
                try: credential_store.save(address, credentials)
                except RuntimeError as exc: messagebox.showerror('Remember password', str(exc), parent=self.window)
            if self.address == address: self.browse(address)
        ask_credentials(self.window, address, signed)

    def connect(self):
        idx = getattr(self, 'selected_share_index', None)
        if idx is None:
            if hasattr(self, 'folders') and hasattr(self.folders, 'selection'):
                sel = self.folders.selection()
                if sel and self.shares:
                    try: idx = int(sel[0])
                    except (ValueError, IndexError): pass
        if idx is None or not self.shares or getattr(self, 'address', None) is None:
            return

        share = self.shares[idx]['name']
        try:
            source = network.share_source(self.address, share)
            existing = next((i for i, item in enumerate(self.app.items) if item['source'] == source), None)
            if existing is None:
                target = network.free_drive([x['target'] for x in self.app.items]) if network.WINDOWS else ''
                self.app.items.append({'name': share + ' · ' + self.address, 'kind': 'Network share', 'source': source,
                                       'target': target, 'auto': self.auto.get(), 'status': 'Disconnected'})
                existing = len(self.app.items) - 1
                self.app.save(); self.app.refresh()
            self.app.tree.selection_set(str(existing))
            self.app.open_when_connected.add(existing)
            self.app.operation(True, existing)
            self.close()
        except Exception as exc: messagebox.showerror('Connect folder', str(exc), parent=self.window)

    def poll(self):
        if not self.window.winfo_exists(): return
        while not self.events.empty():
            event = self.events.get(); kind, generation = event[:2]
            if kind.startswith('scan'):
                if generation != self.scan_generation: continue
                if kind == 'scan_label':
                    self.scan_label = event[2]; self.status.set('Scanning ' + event[2] + '…')
                elif kind == 'scan':
                    _, _, address, done, total = event
                    frac = done / max(total, 1)
                    if HAS_CTK:
                        self.progress.set(frac)
                        if address and address not in self.devices:
                            self._add_device_card(address)
                    else:
                        self.progress['value'] = frac * 100
                        if address and not self.computers.exists(address):
                            self.computers.insert('', 'end', iid=address, values=(address,))
                else:
                    if HAS_CTK:
                        self.rescan_btn.configure(state='normal')
                        count = len(self.devices)
                    else:
                        self.scan_button.configure(state='normal')
                        count = len(self.computers.get_children())

                    if kind == 'scan_error': self.status.set(event[2])
                    elif not self.address:
                        scanned_info = getattr(self, 'scan_label', 'local network')
                        if count:
                            self.status.set(f'Scanning complete ({scanned_info})… Found {count} device(s).')
                        else:
                            self.status.set(f'No sharing devices found on {scanned_info}. Enable sharing or enter IP.')
                            if HAS_CTK: self._show_empty_devices_placeholder('No devices found. Use Manual IP or enable sharing.')
                    if kind == 'scan_done' and not event[2]:
                        if HAS_CTK: self.progress.set(1.0)
                        else: self.progress['value'] = 100
            else:
                if generation != self.browse_generation: continue
                if kind == 'shares':
                    self.shares = event[2]
                    if HAS_CTK:
                        self._render_shares()
                    else:
                        for i, share in enumerate(self.shares):
                            self.folders.insert('', 'end', iid=str(i), values=(share['name'], share['comment']))
                    self.status.set('Pick a folder, then click Connect Selected Folder.' if self.shares else 'No visible shared folders. Try Sign in to see more.')
                elif kind == 'auth':
                    address = self.address
                    if event[2]:
                        self.app.credentials.pop(address, None)
                        credential_store.delete(address)
                    self.status.set('Sign-in details were not accepted. Try again.' if event[2] else 'This device needs a sign-in to show its folders.')
                    self.sign_in()
                elif kind == 'browse_error':
                    self.status.set(event[2])
                    if HAS_CTK: self._show_empty_folders_placeholder(f'Error: {event[2]}')
        self.window.after(100, self.poll)

    def close(self):
        self.stop.set()
        self.window.destroy()
        self.app.finder = None


class _ComputersCompat:
    def __init__(self, outer): self.outer = outer
    def delete(self, *items):
        if HAS_CTK:
            self.outer.devices = {}
            for c in self.outer.devices_frame.winfo_children(): c.destroy()
    def get_children(self): return list(self.outer.devices.keys())
    def exists(self, item): return item in self.outer.devices
    def insert(self, *args, **kwargs):
        iid = kwargs.get('iid') or (args[2] if len(args) > 2 else '')
        if iid: self.outer._add_device_card(iid)
    def selection(self):
        return (self.outer.selected_device,) if self.outer.selected_device else ()
    def selection_set(self, item): self.outer.select_device(item)


class _FoldersCompat:
    def __init__(self, outer): self.outer = outer
    def selection(self):
        if self.outer.selected_share_index is not None:
            return (str(self.outer.selected_share_index),)
        return ()
    def delete(self, *items):
        self.outer.shares = []
        if HAS_CTK:
            for c in self.outer.folders_frame.winfo_children(): c.destroy()
    def get_children(self): return [str(i) for i in range(len(self.outer.shares))]
    def insert(self, *args, **kwargs): pass
