#!/usr/bin/env python3
"""ShareScout: native SMB connections and rclone cloud mounts."""
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
from app_info import window_title
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
        self.folder_dialog = None
        self.cloud_dialog = None
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
        root.title(window_title())
        style = ttk.Style()
        style.theme_use('clam')
        ui.apply_theme(root)
        style.configure('Treeview', rowheight=34)
        style.configure('TButton', padding=(10, 7))
        style.configure('Accent.TButton', background='#2563eb', foreground='white', padding=(14, 9))
        style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('disabled', '#cbd5e1')], foreground=[('disabled', '#64748b')])
        layout = ui.Layout(root, 920, 570)
        main = layout.body
        ui.label(main, text='A home for all your folders', font=ui.heading_font(root), style='Hero.TLabel').pack(fill='x')
        ui.label(main, text='Find it. Connect it. Make yourself at home.', style='Subtitle.TLabel').pack(fill='x', pady=(8, 12))
        bar = ttk.Frame(main); bar.pack(fill='x', pady=(0, 10))
        ui.buttons(bar, [('Find network folders', self.find), ('Connect cloud storage', self.sign_in),
                         ('Share a folder from this PC', self.share_folder)],
                   accent=('Find network folders', 'Connect cloud storage'), maximum=3)
        ui.label(main, text='Your folders', font=('', 14, 'bold')).pack(fill='x', pady=(8, 4))
        self.summary = tk.StringVar()
        ui.label(main, textvariable=self.summary).pack(fill='x', pady=(0, 6))
        self.tree = ui.tree(main, columns=('kind', 'location', 'status', 'auto'), show='tree headings', selectmode='browse', height=8)
        self.tree.heading('#0', text='Name'); self.tree.column('#0', width=160)
        for key, label, width in [('kind', 'Type', 110), ('location', 'Location', 260), ('status', 'Status', 130), ('auto', 'On launch', 80)]:
            self.tree.heading(key, text=label); self.tree.column(key, width=width)
        self.tree.bind('<Double-1>', lambda _: self.open())
        ui.buttons(layout.footer, [('Connect', lambda: self.operation(True)), ('Disconnect', lambda: self.operation(False)), ('Open folder', self.open), ('Forget folder', self.remove)], accent=('Open folder',))
        tools = ttk.LabelFrame(main, text='More ways to connect & help', padding=6); tools.pack(fill='x', pady=10)
        ui.buttons(tools, [('Add network address', self.add), ('Refresh connected folders', self.sync_connections),
                          ('Check required tools', self.check), ('Check for updates', self.check_updates),
                          ('Help sharing from this PC', lambda: self.sharing(force=True))] +
                   ([] if WINDOWS else [('File-manager shortcuts', self.install_shortcuts)]), maximum=3)
        self.note = tk.StringVar(value='Choose a folder below and click Open folder. Add your first folder using the buttons above.')
        ui.label(main, textvariable=self.note, wraplength=850).pack(fill='x')
        self.refresh()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(200, self.poll)
        root.after(400, self.startup)
        root.after(700, lambda: [self.operation(True, i) for i, item in enumerate(self.items) if item.get('auto')])

    def check_updates(self):
        if getattr(self, 'update_dialog', None) and self.update_dialog.window.winfo_exists():
            self.update_dialog.window.lift(); return
        from updates_ui import UpdateDialog
        self.update_dialog = UpdateDialog(self.root)

    def share_folder(self):
        if WINDOWS:
            messagebox.showinfo('Share from this PC',
                'This lets other devices open a folder on this computer. Windows will ask for administrator approval, '
                'then guide you through choosing a folder and who can access it.\n\n'
                'To open a folder on another computer, use Find network folders instead.', parent=self.root)
            try: network.win_share_folder()
            except Exception as exc: messagebox.showerror('Share a folder', str(exc), parent=self.root)
            return
        if self.folder_dialog:
            self.folder_dialog.window.lift(); return
        from folder_share_ui import FolderShare
        def closed(): self.folder_dialog = None
        self.folder_dialog = FolderShare(self.root, STATE, done=closed)

    def install_shortcuts(self, notify=True):
        if WINDOWS: return
        import file_manager
        try:
            result = file_manager.install()
            text = 'Detected file managers: ' + (', '.join(result['detected']) or 'No supported native file manager found')
            text += '\nInstalled shortcuts: ' + ', '.join(result['installed'])
            if result['detected']: text += '\n\nReopen your file manager. In Nautilus/Files and Caja, look under Scripts.'
            else: text += '\n\nUse Share a folder in ShareScout or ShareScout — Share a folder in your application menu.'
            if result['errors']: text += '\n\nCould not install:\n' + '\n'.join(result['errors'])
            if notify: messagebox.showinfo('Folder-sharing shortcuts', text, parent=self.root)
            elif result['errors']: self.note.set('Some file-manager shortcuts need attention. Click File-manager shortcuts to check.')
        except Exception as exc:
            if notify: messagebox.showerror('Folder-sharing shortcuts', str(exc), parent=self.root)
            else: self.note.set('File-manager shortcuts could not be installed: ' + str(exc))

    def startup(self):
        self.sync_connections()
        self.install_shortcuts(notify=False)
        self.sharing(force='--check-sharing' in sys.argv, done=self.find if not self.items else None)

    def sharing(self, force=False, done=None):
        if WINDOWS:
            if force: messagebox.showinfo('Sharing', 'To let other devices open your files: use Share a folder from this PC and approve the Windows administrator prompt. Use Windows Settings to enable Network discovery and File and printer sharing on your trusted private network. To open someone else’s folder, use Find network folders; administrator rights are normally unnecessary.')
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
        count = sum(item.get('status') == 'Connected' for item in self.items)
        if hasattr(self, 'summary'):
            self.summary.set(f'{count} connected · {len(self.items)} saved — select a folder, then Open folder.' if self.items else 'No folders yet. Find a network folder or connect your cloud to get started.')
        self.tree.tag_configure('connected', foreground='#047857')
        for i, item in enumerate(self.items):
            self.tree.item(str(i), tags=('connected',) if item.get('status') == 'Connected' else ())

    def selected(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def sync_connections(self):
        if getattr(self, 'syncing', False): return
        self.syncing = True
        def worker():
            try: self.events.put(('desktop', network.connected_folders(), None))
            except Exception: self.events.put(('desktop', [], 'Could not read connected folders. Your saved folders are still available.'))
        threading.Thread(target=worker, daemon=True).start()

    def add(self):
        win = tk.Toplevel(self.root); win.title(window_title('Add a network address'))
        layout = ui.Layout(win, 570, 480); frame = layout.body
        ui.label(frame, text='Know the folder address?', font=ui.heading_font(win, 18)).pack(fill='x')
        ui.label(frame, text='Use this for a folder on another PC or network storage. If you only know the device’s IP address, use Find network folders.').pack(fill='x', pady=10)
        fields = {}
        for label, key, default in [('A friendly name, such as Family photos', 'name', ''),
                (r'Folder address, such as \\server\photos or smb://server/photos', 'source', '')]:
            ui.label(frame, text=label).pack(fill='x', pady=(8, 3))
            fields[key] = tk.StringVar(value=default)
            ttk.Entry(frame, textvariable=fields[key]).pack(fill='x')
        ui.label(frame, text='We choose an available drive letter on Windows. On Linux, your folder opens in the file manager.').pack(fill='x', pady=10)
        auto = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text='Reconnect when ShareScout opens', variable=auto).pack(anchor='w', pady=10)
        def submit():
            try:
                name = fields['name'].get().strip()
                if not name: raise ValueError('Give your folder a friendly name.')
                source = smb_address(fields['source'].get())
                if any(x['source'].casefold() == source.casefold() for x in self.items): raise ValueError('This folder is already in your list.')
                target = network.free_drive([x['target'] for x in self.items]) if WINDOWS else ''
                item = dict(name=name, kind='Network share', source=source, target=target, auto=auto.get(), status='Disconnected')
                self.items.append(item); self.save(); self.refresh(); win.destroy()
                index = len(self.items) - 1; self.tree.selection_set(str(index)); self.open_when_connected.add(index); self.operation(True, index)
            except Exception as exc: messagebox.showerror('Add folder', str(exc), parent=win)
        ui.buttons(layout.footer, [('Cancel', win.destroy), ('Connect & open folder', submit)], accent=('Connect & open folder',))

    def sign_in(self):
        if not shutil.which('rclone'):
            messagebox.showinfo('Cloud storage needs setup', 'Run the setup launcher to install rclone, then return here to sign in with your browser.', parent=self.root); return
        if self.cloud_dialog:
            self.cloud_dialog.window.lift(); return
        from cloud_ui import CloudSignIn
        self.cloud_dialog = CloudSignIn(self)

    def add_cloud_account(self, provider, remote):
        for index, item in enumerate(self.items):
            if item['kind'] != 'Network share' and item['source'] == remote:
                self.tree.selection_set(str(index)); self.open_when_connected.add(index)
                self.operation(True, index); return
        target = network.free_drive([x['target'] for x in self.items]) if WINDOWS else str(Path.home() / 'ShareScout' / remote)
        name = provider
        number = 2
        while any(x['name'] == name for x in self.items):
            name = f'{provider} {number}'; number += 1
        self.items.append(dict(name=name, kind=provider, source=remote, target=target, auto=True, status='Disconnected'))
        try: self.save()
        except Exception:
            self.items.pop(); raise
        self.refresh()
        index = len(self.items) - 1; self.tree.selection_set(str(index))
        self.open_when_connected.add(index); self.operation(True, index)

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
                    if item['source'] + ':' not in remotes: raise RuntimeError('Cloud account is not configured. Click Connect cloud storage to sign in again.')
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
                        raise RuntimeError('Mount did not become ready in 25 seconds. Click Check required tools, then try connecting again.')
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
            if i == 'desktop':
                self.syncing = False
                for incoming in status:
                    existing = next((x for x in self.items if x['source'].casefold() == incoming['source'].casefold() and x.get('target', '').casefold() == incoming['target'].casefold()), None)
                    if existing is not None:
                        if self.items.index(existing) not in self.busy: existing['status'] = 'Connected'
                    else: self.items.append(incoming)
                self.save(); self.refresh()
                self.note.set(error or 'Connected folders refreshed. Select one and click Open folder.')
                continue
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
            self.open_when_connected.add(i); self.operation(True, i); return
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
        if self.folder_dialog and self.folder_dialog.result_file:
            messagebox.showinfo('Setup is running', 'Finish or cancel folder sharing in its terminal before closing ShareScout.'); return
        if self.cloud_dialog: self.cloud_dialog.close()
        if self.folder_dialog: self.folder_dialog.close()
        if self.finder: self.finder.close()
        if self.sharing_dialog:
            self.sharing_dialog.done = None; self.sharing_dialog.close()
        self.credentials.clear()
        self.save(); self.root.destroy()


def main():
    from single_instance import SingleInstance
    instance = SingleInstance(STATE)
    if not instance.acquire():
        if not instance.activate_existing():
            print('ShareScout is already running. Its window could not be activated; switch to it using your desktop taskbar.')
        return
    try:
        ui.enable_dpi_awareness()
        app_root = tk.Tk()
        App(app_root)
        instance.attach(app_root)
        app_root.mainloop()
    finally: instance.close()


if __name__ == '__main__': main()
