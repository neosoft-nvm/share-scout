"""Screen-aware folder sharing dialog, also used by file-manager actions."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid
import folder_share
from sharing_ui import terminal_command
import ui
from app_info import window_title


class FolderShare:
    def __init__(self, root, state_dir, folder=None, done=None):
        self.state_dir = state_dir; self.done = done; self.finished = False; self.result_file = None
        self.window = tk.Toplevel(root); self.window.title(window_title('Share a folder')); self.window.transient(root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        layout = ui.Layout(self.window, 680, 590); body = layout.body
        ui.label(body, text='Share a folder', font=ui.heading_font(self.window)).pack(fill='x')
        ui.label(body, text='Let your other devices open a folder on this computer. You choose whether other devices can change its files.').pack(fill='x', pady=(8, 14))
        ui.label(body, text='Folder to share').pack(fill='x')
        self.folder = tk.StringVar(value=folder or '')
        ttk.Entry(body, textvariable=self.folder).pack(fill='x', pady=5)
        choices = ttk.Frame(body); choices.pack(fill='x')
        ui.buttons(choices, [('Choose folder…', self.choose), ('Create a new folder…', self.create)], maximum=2)
        ui.label(body, text='Share name shown on your network').pack(fill='x', pady=(12, 0))
        self.name = tk.StringVar(value=folder_share.suggested_name(folder) if folder else '')
        ttk.Entry(body, textvariable=self.name).pack(fill='x', pady=5)
        self.writable = tk.BooleanVar(value=False)
        ttk.Radiobutton(body, text='Read only — other devices can open and copy files', variable=self.writable, value=False).pack(anchor='w', pady=4)
        ttk.Radiobutton(body, text='Read and write — other devices can change and delete files', variable=self.writable, value=True).pack(anchor='w', pady=4)
        ui.label(body, text='Sign in from another device with your account on this computer and its sharing password. Guest access stays off. The selected folder and its subfolders are included.').pack(fill='x', pady=12)
        ui.label(body, text='Setup installs Samba if needed and asks for administrator approval. On SELinux systems, sharing from home may ask to enable Samba’s home-folder policy; other chosen folders are labeled for Samba. Use your home Wi-Fi or Ethernet network.').pack(fill='x', pady=8)
        self.status = tk.StringVar(value='Choose a folder, then click Share this folder.')
        ui.label(body, textvariable=self.status).pack(fill='x', pady=8)
        self.buttons = ui.buttons(layout.footer, [('Close', self.close), ('Share this folder', self.share)], accent=('Share this folder',), maximum=2)
        self.window.after(250, self.poll)

    def choose(self):
        selected = filedialog.askdirectory(parent=self.window, title='Choose a folder to share', mustexist=True)
        if selected:
            self.folder.set(selected); self.name.set(folder_share.suggested_name(selected))

    def create(self):
        selected = filedialog.askdirectory(parent=self.window, title='Choose a parent folder, or use New Folder', mustexist=True)
        if not selected: return
        from tkinter import simpledialog
        name = simpledialog.askstring('New folder', 'Name for the new folder:', parent=self.window)
        if name is None: return
        if not name.strip() or name in ('.', '..') or any(char in name for char in '/\\\n\r%'):
            messagebox.showerror('New folder', 'Use a simple folder name without slashes, % or line breaks.', parent=self.window); return
        try:
            parent = Path(selected)
            # Validate ownership/location before creating anything.
            folder_share.validate_folder(str(parent), folder_share.setup.identity(), allow_home=True)
            folder = parent / name; folder.mkdir(mode=0o700)
            self.folder.set(str(folder)); self.name.set(folder_share.suggested_name(folder))
        except Exception as exc: messagebox.showerror('New folder', str(exc), parent=self.window)

    def share(self):
        if self.result_file: return
        try:
            if not self.folder.get().strip(): raise ValueError('Choose a folder first.')
            folder = folder_share.validate_folder(self.folder.get(), folder_share.setup.identity())
            name = folder_share.validate_name(self.name.get().strip())
        except Exception as exc:
            messagebox.showerror('Share a folder', str(exc), parent=self.window); return
        result = self.state_dir / ('folder-share-' + uuid.uuid4().hex + '.json')
        args = [sys.executable, str(Path(__file__).with_name('folder_share.py')), '--configure-folder', str(result), str(folder), name, 'write' if self.writable.get() else 'read']
        try:
            subprocess.Popen(terminal_command(args))
            self.result_file = result
            self.buttons[1].configure(state='disabled')
            self.status.set('Complete the administrator and sharing-password prompts in the setup terminal.')
        except Exception as exc:
            messagebox.showerror('Sharing setup', str(exc) + '\n\nRun manually:\n' + shlex.join(args), parent=self.window)

    def poll(self):
        if self.finished: return
        if self.result_file and self.result_file.exists():
            try: result = json.loads(self.result_file.read_text())
            except (ValueError, OSError): result = None
            if result:
                self.result_file.unlink(missing_ok=True); self.result_file = None
                self.buttons[1].configure(state='normal')
                if result.get('ok'):
                    location = f"//{result['address']}/{result['name']}" if result.get('address') else result['name']
                    self.status.set('Shared: ' + location)
                    messagebox.showinfo('Your folder is shared', f"Shared folder: {result['name']}\nLocation: {location}\nSign-in account: {result['account']}\nAccess: {'Read and write' if result['writable'] else 'Read only'}\n\nOpen ShareScout on another device and scan to find it. Local setup is verified; a connection from another device still needs checking.", parent=self.window)
                else: self.status.set('Setup could not finish: ' + result.get('error', 'Unknown error'))
        self.window.after(250, self.poll)

    def close(self):
        if self.finished: return
        if self.result_file:
            messagebox.showinfo('Setup is running', 'Finish or cancel setup in its terminal before closing this dialog.', parent=self.window); return
        self.finished = True; self.window.destroy()
        if self.done: self.done()
