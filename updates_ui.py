"""Responsive, asynchronous update check with platform-specific upgrade help."""
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser
from app_info import VERSION, window_title
import updates
import ui
from pathlib import Path

UPDATE_PREF = Path(os.getenv('LOCALAPPDATA', str(Path.home() / '.config'))) / 'ResourceMapper' / 'update-check.json'


class UpdatePrompt:
    """Ask before showing the upgrade instructions; remember the opt-out."""
    def __init__(self, root, result):
        self.root = root
        self.result = result
        self.window = tk.Toplevel(root)
        self.window.title(window_title('Update available'))
        self.window.transient(root)
        self.window.resizable(False, False)
        body = ttk.Frame(self.window, padding=22); body.pack(fill='both', expand=True)
        ui.label(body, text='A new ShareScout is ready', font=ui.heading_font(self.window)).pack(anchor='w')
        ui.label(body, text=f"Version {result['latest']} is available. You have {result['installed']}.").pack(anchor='w', pady=(10, 14))
        self.disable = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text='Don’t check for updates automatically', variable=self.disable).pack(anchor='w', pady=(0, 16))
        ui.buttons(body, [('Not now', self.close), ('Show upgrade options', self.upgrade)], maximum=2)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.grab_set()

    def close(self):
        try:
            UPDATE_PREF.parent.mkdir(parents=True, exist_ok=True)
            UPDATE_PREF.write_text('{"automatic": ' + ('false' if self.disable.get() else 'true') + '}\n')
        except OSError:
            pass
        self.window.destroy()

    def upgrade(self):
        self.close()
        UpdateDialog(self.root, self.result)


class UpdateDialog:
    def __init__(self, root, result=None):
        self.window = tk.Toplevel(root); self.window.title(window_title('Check for updates')); self.window.transient(root)
        self.events = queue.Queue(); self.busy = False
        layout = ui.Layout(self.window, 670, 540); body = layout.body
        ui.label(body, text='Check for updates', font=ui.heading_font(self.window)).pack(fill='x')
        ui.label(body, text='Installed version: ' + VERSION).pack(fill='x', pady=(10, 4))
        initial = (f"Update available: ShareScout {result['latest']}\nYou have {result['installed']}. Follow the upgrade instructions below."
                   if result and result.get('newer') else 'Checking the latest ShareScout version on GitHub…')
        self.status = tk.StringVar(value=initial)
        ui.label(body, textvariable=self.status).pack(fill='x', pady=12)
        ui.label(body, text='This checks the version in the project’s main branch. Updates are installed when you choose to upgrade.').pack(fill='x', pady=8)
        launcher = 'Launch-Windows.cmd' if os.name == 'nt' else 'bash Launch-Linux.sh'
        ui.label(body, text='To upgrade a cloned repository, close ShareScout and run these commands in its folder:').pack(fill='x', pady=(12, 4))
        commands = tk.Text(body, height=2, wrap='none', font='TkFixedFont')
        commands.insert('1.0', 'git pull --ff-only\n' + launcher); commands.configure(state='disabled'); commands.pack(fill='x', pady=5)
        ui.label(body, text='For a ZIP installation, download the latest source ZIP, extract it, and run the launcher. For a Debian package installation, install an updated package when available or build it from the updated repository.').pack(fill='x', pady=8)
        buttons = ui.buttons(layout.footer, [('Close', self.window.destroy), ('Check again', self.check), ('Open GitHub', lambda: webbrowser.open(updates.REPOSITORY)), ('Download source ZIP', lambda: webbrowser.open(updates.SOURCE_ZIP))], maximum=2)
        self.check_button = buttons[1]
        self.window.after(100, self.poll)
        if not result: self.check()

    def check(self):
        if self.busy: return
        self.busy = True; self.check_button.configure(state='disabled')
        self.status.set('Checking the latest ShareScout version on GitHub…')
        def worker():
            try: self.events.put(('result', updates.check()))
            except Exception as exc: self.events.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        if not self.window.winfo_exists(): return
        while not self.events.empty():
            kind, result = self.events.get(); self.busy = False; self.check_button.configure(state='normal')
            if kind == 'error': self.status.set(result)
            elif result['newer']: self.status.set(f"Update available: ShareScout {result['latest']}\nYou have {result['installed']}. Follow the upgrade instructions below.")
            elif updates.version_tuple(result['latest']) == updates.version_tuple(result['installed']): self.status.set('You’re up to date: ShareScout ' + result['installed'])
            else: self.status.set(f"Your version ({result['installed']}) is newer than GitHub’s main branch ({result['latest']}).")
        self.window.after(150, self.poll)
