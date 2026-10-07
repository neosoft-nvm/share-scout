#!/usr/bin/env python3
"""Resource Mapper: native SMB connections and rclone cloud mounts."""
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import network
import ui
from discovery import Finder, ask_credentials
from urllib.parse import urlsplit

WINDOWS = os.name == 'nt'
STATE = Path(os.getenv('LOCALAPPDATA', str(Path.home() / '.config'))) / 'ResourceMapper'
CONFIG = STATE / 'connections.json'


def run(args, timeout=30):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or 'Command failed').strip())
    return result.stdout


def cloud_command(remote, target):
    if not re.fullmatch(r'[\w .-]+', remote):
        raise ValueError('Select a configured remote name (without a colon).')
    if WINDOWS:
        if not re.fullmatch(r'[D-Zd-z]:', target):
            raise ValueError('Choose a drive letter from D: to Z:.')
        if Path(target + '\\').exists():
            raise ValueError('That drive letter is already in use.')
    else:
        path = Path(target).expanduser().absolute()
        if path == Path('/') or path == Path.home():
            raise ValueError('Choose a dedicated empty folder for this drive.')
        path.mkdir(parents=True, exist_ok=True)
        if os.path.ismount(path) or any(path.iterdir()):
            raise ValueError('The mount folder must be empty and not already mounted.')
        target = str(path)
    return ['rclone', 'mount', remote + ':', target, '--vfs-cache-mode', 'full',
            '--vfs-cache-max-size', '2G', '--log-level', 'INFO']


def smb_address(value):
    value = value.strip().replace('\\', '/')
    if value.startswith('smb://'):
        value = value[6:]
    value = value.lstrip('/')
    if not re.fullmatch(r'[^/@:\s]+/[^/\s]+(?:/[^\r\n]*)?', value):
        raise ValueError('Enter a server and share, for example \\server\\shared or smb://server/shared.')
    return ('\\\\' + value.replace('/', '\\')) if WINDOWS else 'smb://' + value


class App:
    def __init__(self, root):
        STATE.mkdir(parents=True, exist_ok=True)
        self.root = root
        self.events = queue.Queue()
        self.processes = {}
        self.busy = set()
        self.credentials = {}
        self.open_when_connected = set()
        self.finder = None
        self.sharing_dialog = None
        try:
            self.items = json.loads(CONFIG.read_text())
            if not isinstance(self.items, list):
                raise ValueError('Expected a list')
        except FileNotFoundError:
            self.items = []
        except (ValueError, OSError):
            messagebox.showwarning('Settings', 'Saved settings could not be read. A backup will be kept.')
            if CONFIG.exists():
                shutil.copy2(CONFIG, CONFIG.with_suffix('.backup.json'))
            self.items = []
        for item in self.items:
            item['status'] = 'Disconnected'
        root.title('ShareScout')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=34)
        style.configure('TButton', padding=(10, 7))
        style.configure('Accent.TButton', background='#2563eb', foreground='white', padding=(14, 9))
        style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('disabled', '#cbd5e1')], foreground=[('disabled', '#64748b')])
        layout = ui.Layout(root, 920, 570)
        main = layout.body
        ui.label(main, text='Your shared folders', font=ui.heading_font(root)).pack(fill='x')
        ui.label(main, text='We find sharing devices and folders for you. You just choose what to open.').pack(fill='x', pady=(8, 18))
        bar = ttk.Frame(main)
        bar.pack(fill='x', pady=(0, 12))
        ui.buttons(bar, [('Find shared folders', self.find), ('Cloud / manual connection', self.add), ('Cloud sign-in', self.sign_in), ('Check setup', self.check), ('Check sharing', lambda: self.sharing(force=True))], accent=('Find shared folders',), maximum=3)
        self.tree = ui.tree(main, columns=('kind', 'location', 'status', 'auto'), show='tree headings', selectmode='browse', height=8)
        self.tree.heading('#0', text='Name'); self.tree.column('#0', width=160)
        for key, label, width in [('kind', 'Type', 110), ('location', 'Location', 260), ('status', 'Status', 130), ('auto', 'On launch', 80)]:
            self.tree.heading(key, text=label); self.tree.column(key, width=width)
        self.tree.bind('<Double-1>', lambda _: self.open())
        ui.buttons(layout.footer, [('Connect', lambda: self.operation(True)), ('Disconnect', lambda: self.operation(False)), ('Open folder', self.open), ('Remove', self.remove)])
        self.note = tk.StringVar(value='Click Find shared folders to browse your network. No hostnames needed.')
        ui.label(main, textvariable=self.note, wraplength=850).pack(fill='x')
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(200, self.poll)
        root.after(400, self.startup)
        root.after(700, lambda: [self.operation(True, i) for i, item in enumerate(self.items) if item.get('auto')])

    def startup(self):
        self.sharing(force='--check-sharing' in sys.argv, done=self.find if not self.items else None)

    def sharing(self, force=False, done=None):
        if WINDOWS:
            if force: messagebox.showinfo('Sharing', 'Use Windows Settings to turn on file sharing and share a folder. Linux Samba setup is available on Linux.')
            if done: done()
            return
        if self.sharing_dialog:
            self.sharing_dialog.window.lift(); return
        if not force and (STATE / 'sharing-choice.json').exists():
            if done: done()
            return
        from sharing_ui import SharingSetup
        self.sharing_dialog = SharingSetup(self, STATE, force=force, done=done)

    def find(self):
        if self.finder is not None:
            self.finder.window.lift(); return
        self.finder = Finder(self)

    def save(self):
        temp = CONFIG.with_suffix('.tmp')
        temp.write_text(json.dumps(self.items, indent=2))
        if not WINDOWS: temp.chmod(0o600)
        temp.replace(CONFIG)

    def refresh(self):
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(self.items):
            self.tree.insert('', 'end', iid=str(i), text=item['name'], values=(item['kind'], item['target'] or item['source'], item.get('status', 'Disconnected'), 'Yes' if item.get('auto') else 'No'))
        if selected and self.tree.exists(selected[0]): self.tree.selection_set(selected)

    def selected(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def add(self):
        win = tk.Toplevel(self.root); win.title('Add connection')
        layout = ui.Layout(win, 570, 520); frame = layout.body
        fields = {}
        for label, key, default in [('Name', 'name', ''), ('Type', 'kind', 'Network share'), ('Server/share or cloud remote name', 'source', ''), ('Drive letter (Windows) or mount folder (Linux)', 'target', 'R:' if WINDOWS else str(Path.home() / 'CloudDrive'))]:
            ui.label(frame, text=label).pack(anchor='w', pady=(8, 3))
            var = tk.StringVar(value=default); fields[key] = var
            widget = ttk.Combobox(frame, textvariable=var, state='readonly', values=['Network share', 'OneDrive', 'Google Drive']) if key == 'kind' else ttk.Entry(frame, textvariable=var)
            widget.pack(fill='x')
        auto = tk.BooleanVar()
        ttk.Checkbutton(frame, text='Reconnect when this app opens', variable=auto).pack(anchor='w', pady=10)
        ui.label(frame, text='For cloud drives, sign in first and use the remote name you created.\nLinux network shares open under your file manager’s Network section.', wraplength=460).pack(fill='x')
        def submit():
            item = {key: var.get().strip() for key, var in fields.items()}
            try:
                if not item['name']: raise ValueError('Give this connection a name.')
                if item['kind'] == 'Network share':
                    item['source'] = smb_address(item['source'])
                    if not WINDOWS: item['target'] = ''
                    elif not re.fullmatch(r'[D-Zd-z]:', item['target']): raise ValueError('Use a drive letter from D: to Z:.')
                elif not re.fullmatch(r'[\w .-]+', item['source']): raise ValueError('Enter your rclone remote name without a colon.')
                elif not item['target']: raise ValueError('Enter a mount folder or drive letter.')
                if any(x['name'] == item['name'] for x in self.items): raise ValueError('Choose a unique name.')
                if item['target'] and any(x['target'] == item['target'] for x in self.items): raise ValueError('That mount location is already assigned.')
                item['auto'] = auto.get(); self.items.append(item); self.save(); self.refresh(); win.destroy()
            except Exception as exc: messagebox.showerror('Connection', str(exc), parent=win)
        ui.buttons(layout.footer, [('Cancel', win.destroy), ('Save connection', submit)], accent=('Save connection',))

    def sign_in(self):
        if not shutil.which('rclone'): return self.check()
        messagebox.showinfo('Cloud sign-in', 'A setup terminal will open. Choose New remote, give it a name, select Google Drive or OneDrive, and follow browser sign-in. Then add a connection using that name.')
        if WINDOWS:
            subprocess.Popen(['cmd', '/c', 'start', '', 'cmd', '/k', 'rclone', 'config'])
        else:
            for terminal, args in [('ptyxis', ['--new-window', '--']), ('x-terminal-emulator', ['-e']), ('gnome-terminal', ['--']), ('kgx', ['--']), ('konsole', ['-e']), ('xterm', ['-e'])]:
                if shutil.which(terminal):
                    subprocess.Popen([terminal] + args + ['rclone', 'config']); return
            messagebox.showinfo('Cloud sign-in', 'Open a terminal and run: rclone config')

    def check(self):
        checks = ['rclone: ' + ('Ready' if shutil.which('rclone') else 'Missing — rerun the setup launcher')]
        if WINDOWS:
            checks.append('Cloud mounting requires WinFsp. Install it using the setup launcher.')
        else:
            checks += ['Folder discovery: ' + ('Ready' if shutil.which('smbclient') else 'Missing — reopen the launcher'), 'FUSE: ' + ('Ready' if shutil.which('fusermount3') or shutil.which('fusermount') else 'Missing — install fuse3'), 'Network shares: ' + ('Ready' if shutil.which('gio') else 'Missing — install GLib/GVfs SMB support')]
        messagebox.showinfo('Setup', '\n'.join(checks))

    def operation(self, connect, index=None):
        i = self.selected() if index is None else index
        if i is None or i in self.busy: return
        item = self.items[i]
        if connect and item.get('status') == 'Connected':
            if i in self.open_when_connected:
                self.open_when_connected.discard(i); self.tree.selection_set(str(i)); self.open()
            return
        self.busy.add(i); item['status'] = 'Connecting…' if connect else 'Disconnecting…'; self.refresh()
        def worker():
            try:
                if item['kind'] == 'Network share':
                    address = urlsplit(item['source']).hostname if not WINDOWS else item['source'].lstrip('\\').split('\\')[0]
                    if connect:
                        network.mount_share(item['source'], item['target'], self.credentials.get(address))
                    elif WINDOWS:
                        network.win_disconnect(item['target'])
                    else:
                        run(['gio', 'mount', '-u', item['source']])
                elif connect:
                    if not shutil.which('rclone'): raise RuntimeError('rclone is missing. Run the setup launcher.')
                    remotes = run(['rclone', 'listremotes']).splitlines()
                    if item['source'] + ':' not in remotes: raise RuntimeError('Cloud account is not configured. Use Cloud sign-in first.')
                    args = cloud_command(item['source'], item['target'])
                    log = STATE / ('mount-' + str(i) + '.log')
                    with log.open('a') as stream:
                        proc = subprocess.Popen(args, stdout=stream, stderr=stream, creationflags=subprocess.CREATE_NO_WINDOW if WINDOWS else 0)
                    self.processes[i] = proc
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        if proc.poll() is not None: raise RuntimeError('Cloud mount failed. ' + log.read_text(errors='replace')[-1200:])
                        ready = Path(item['target'] + '\\').exists() if WINDOWS else os.path.ismount(Path(item['target']).expanduser())
                        if ready: break
                        time.sleep(.3)
                    else:
                        proc.terminate()
                        raise RuntimeError('Mount did not become ready in 25 seconds. Check setup and the mount log.')
                else:
                    proc = self.processes.get(i)
                    if proc and proc.poll() is None:
                        if not WINDOWS: run([shutil.which('fusermount3') or 'fusermount', '-u', str(Path(item['target']).expanduser())])
                        proc.terminate(); proc.wait(timeout=15)
                    self.processes.pop(i, None)
                self.events.put((i, 'Connected' if connect else 'Disconnected', None))
            except PermissionError as exc: self.events.put((i, 'Sign in', str(exc)))
            except Exception as exc: self.events.put((i, 'Error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        while not self.events.empty():
            i, status, error = self.events.get()
            self.busy.discard(i); self.items[i]['status'] = status; self.refresh()
            self.note.set(error or self.items[i]['name'] + ': ' + status)
            if status == 'Sign in':
                source = self.items[i]['source']
                address = urlsplit(source).hostname if not WINDOWS else source.lstrip('\\').split('\\')[0]
                def signed(credentials, index=i, host=address):
                    self.credentials[host] = credentials; self.operation(True, index)
                ask_credentials(self.root, address, signed)
            elif error:
                self.open_when_connected.discard(i)
                messagebox.showerror('Connection issue', error)
            elif status == 'Connected' and i in self.open_when_connected:
                self.open_when_connected.discard(i)
                self.tree.selection_set(str(i)); self.open()
        for i, proc in list(self.processes.items()):
            if proc.poll() is not None and i not in self.busy:
                self.processes.pop(i); self.items[i]['status'] = 'Disconnected'; self.refresh()
        self.root.after(300, self.poll)

    def open(self):
        i = self.selected()
        if i is None: return
        item = self.items[i]
        if item.get('status') != 'Connected':
            messagebox.showinfo('Open folder', 'Connect this resource first.'); return
        location = item['target'] if WINDOWS or item['kind'] != 'Network share' else item['source']
        try:
            if WINDOWS: os.startfile(location + '\\')
            else: subprocess.Popen(['gio', 'open', str(Path(location).expanduser()) if item['target'] else location])
        except OSError as exc: messagebox.showerror('Open folder', str(exc))

    def remove(self):
        i = self.selected()
        if i is None: return
        if self.busy or self.processes or any(x.get('status') == 'Connected' for x in self.items):
            messagebox.showinfo('Remove', 'Disconnect all resources before removing a saved connection.'); return
        if messagebox.askyesno('Remove', 'Remove this saved connection?'):
            self.items.pop(i); self.save(); self.refresh()

    def close(self):
        if self.busy:
            messagebox.showinfo('Please wait', 'Wait for the current connection operation to finish.'); return
        if any(p.poll() is None for p in self.processes.values()):
            messagebox.showinfo('Cloud drives still connected', 'Disconnect cloud drives before closing so pending writes can finish.'); return
        if self.finder: self.finder.close()
        if self.sharing_dialog:
            self.sharing_dialog.done = None; self.sharing_dialog.close()
        self.credentials.clear()
        self.save(); self.root.destroy()


if __name__ == '__main__':
    ui.enable_dpi_awareness()
    app_root = tk.Tk()
    App(app_root)
    app_root.mainloop()
