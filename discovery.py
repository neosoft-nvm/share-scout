"""Beginner-first shared folder discovery wizard."""
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


def ask_credentials(parent, address, callback):
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
        def arrange_lists(event):
            stacked = event.width < self.folders.winfo_reqwidth() + self.computers.winfo_reqwidth() + 60
            lists.columnconfigure(0, weight=1); lists.columnconfigure(1, weight=0 if stacked else 1)
            left.grid(row=0, column=0, sticky='nsew', padx=(0, 0 if stacked else 12))
            right.grid(row=1 if stacked else 0, column=0 if stacked else 1, sticky='nsew')
        lists.bind('<Configure>', arrange_lists)
        ui.label(left, text='Devices with file sharing', font=('', 12, 'bold'), style='Section.TLabel').pack(fill='x', pady=(0, 4))
        computer_list = ttk.Frame(left); computer_list.pack(fill='both', expand=True, pady=6)
        self.computers = ui.tree(computer_list, columns=('ip',), show='headings', selectmode='browse', height=8)
        self.computers.heading('ip', text='IP address')
        self.computers.bind('<<TreeviewSelect>>', self.choose_computer)
        ui.label(right, text='Shared folders', font=('', 12, 'bold'), style='Section.TLabel').pack(fill='x', pady=(0, 4))
        folder_list = ttk.Frame(right); folder_list.pack(fill='both', expand=True, pady=6)
        self.folders = ui.tree(folder_list, columns=('name', 'comment'), show='headings', selectmode='browse', height=8)
        self.folders.heading('name', text='Folder'); self.folders.heading('comment', text='Description')
        self.folders.column('name', width=150); self.folders.column('comment', width=170)
        self.folders.bind('<<TreeviewSelect>>', lambda _: self.connect_button.configure(state='normal' if self.folders.selection() else 'disabled'))
        self.folders.bind('<Double-1>', lambda _: self.connect())
        self.sign_button = ttk.Button(right, text='Sign in to see more folders', command=self.sign_in); self.sign_button.pack(fill='x')
        fallback = ttk.Frame(frame); fallback.pack(fill='x', pady=12)
        ui.label(fallback, text='Have an IP address?').pack(fill='x')
        self.ip = tk.StringVar()
        ttk.Entry(fallback, textvariable=self.ip, width=20).pack(fill='x', pady=5)
        ttk.Button(fallback, text='Show its folders', command=self.direct).pack(fill='x')
        footer = layout.footer
        self.auto = tk.BooleanVar(value=True)
        ttk.Checkbutton(footer, text='Reconnect when this app opens', variable=self.auto).pack(fill='x', pady=(0, 8))
        self.connect_button = ui.buttons(
            footer, [('Cancel', self.close), ('Connect this folder', self.connect)],
            accent=('Connect this folder',), maximum=2
        )[1]
        self.connect_button.configure(state='disabled')
        self.window.after(100, self.poll)
        self.window.after(200, self.start_scan)

    def start_scan(self):
        if str(self.scan_button['state']) == 'disabled': return
        self.address = None; self.shares = []; self.browse_generation += 1
        self.folders.delete(*self.folders.get_children()); self.connect_button.configure(state='disabled')
        self.stop = threading.Event(); self.scan_generation += 1
        generation = self.scan_generation; stop = self.stop
        self.computers.delete(*self.computers.get_children())
        self.scan_button.configure(state='disabled'); self.progress['value'] = 0
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

    def direct(self):
        try: address = network.validate_ip(self.ip.get())
        except ValueError:
            messagebox.showinfo('IP address', 'Enter an address like 192.168.1.20.', parent=self.window); return
        if not self.computers.exists(address): self.computers.insert('', 'end', iid=address, values=(address,))
        if self.computers.selection() == (address,): self.browse(address)
        else: self.computers.selection_set(address)
        # Selection event starts browsing.

    def browse(self, address):
        self.address = address; self.browse_generation += 1
        generation = self.browse_generation
        self.folders.delete(*self.folders.get_children()); self.shares = []
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
        selected = self.folders.selection()
        if not selected or self.address is None: return
        share = self.shares[int(selected[0])]['name']
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
                if kind == 'scan_label': self.scan_label = event[2]; self.status.set('Scanning ' + event[2] + '…')
                elif kind == 'scan':
                    _, _, address, done, total = event
                    self.progress['value'] = done * 100 / max(total, 1)
                    if address and not self.computers.exists(address): self.computers.insert('', 'end', iid=address, values=(address,))
                else:
                    self.scan_button.configure(state='normal')
                    count = len(self.computers.get_children())
                    if kind == 'scan_error': self.status.set(event[2])
                    elif not self.address:
                        self.status.set((f'Found {count} device(s). Pick one to see its folders.' if count else 'No sharing devices found. Enable file sharing on the device, then rescan. On Linux PCs, use ShareScout’s Set up sharing. You can also enter an IP address below.') + ' Scanned: ' + getattr(self, 'scan_label', 'local network'))
                    if kind == 'scan_done' and not event[2]: self.progress['value'] = 100
            else:
                if generation != self.browse_generation: continue
                if kind == 'shares':
                    self.shares = event[2]
                    for i, share in enumerate(self.shares): self.folders.insert('', 'end', iid=str(i), values=(share['name'], share['comment']))
                    self.status.set('Pick a folder, then click Connect this folder.' if self.shares else 'No visible shared folders. Try Sign in to see more folders.')
                elif kind == 'auth':
                    address = self.address
                    if event[2]:
                        self.app.credentials.pop(address, None)
                        credential_store.delete(address)
                    self.status.set('Sign-in details were not accepted. Try again.' if event[2] else 'This device needs a sign-in to show its folders.')
                    self.sign_in()
                elif kind == 'browse_error': self.status.set(event[2])
        self.window.after(100, self.poll)

    def close(self):
        self.stop.set()
        self.window.destroy()
        self.app.finder = None
