"""Asynchronous update checks and one-click application upgrades."""
import os
import queue
import shutil
import threading
import tkinter as tk
from tkinter import ttk
from app_info import VERSION, window_title
import updates
import ui
from pathlib import Path

UPDATE_PREF = Path(os.getenv('LOCALAPPDATA', str(Path.home() / '.config'))) / 'ResourceMapper' / 'update-check.json'


class UpdatePrompt:
    """Ask before showing the upgrade instructions; remember the opt-out."""
    def __init__(self, root, result, on_upgrade=None):
        self.root = root
        self.result = result
        self.on_upgrade = on_upgrade
        self.window = tk.Toplevel(root)
        self.window.title(window_title('Update available'))
        self.window.transient(root)
        self.window.resizable(False, False)
        body = ttk.Frame(self.window, padding=22); body.pack(fill='both', expand=True)
        ui.label(body, text='A new ShareScout is ready', font=ui.heading_font(self.window)).pack(anchor='w')
        ui.label(body, text=f"Version {result['latest']} is available. You have {result['installed']}.").pack(anchor='w', pady=(10, 14))
        self.disable = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text='Don’t check for updates automatically', variable=self.disable).pack(anchor='w', pady=(0, 16))
        ui.buttons(body, [('Not now', self.close), ('Upgrade now', self.upgrade)], accent=('Upgrade now',), maximum=2)
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
        UpdateDialog(self.root, self.result, self.on_upgrade, start_immediately=True)


class UpdateDialog:
    def __init__(self, root, result=None, on_upgrade=None, start_immediately=False):
        self.window = tk.Toplevel(root); self.window.title(window_title('Check for updates')); self.window.transient(root)
        self.events = queue.Queue(); self.busy = False
        self.upgrading = False
        self.on_upgrade = on_upgrade
        self.result = result
        layout = ui.Layout(self.window, 670, 540); body = layout.body
        ui.label(body, text='Check for updates', font=ui.heading_font(self.window)).pack(fill='x')
        ui.label(body, text='Installed version: ' + VERSION).pack(fill='x', pady=(10, 4))
        initial = (f"Update available: ShareScout {result['latest']}\nYou have {result['installed']}."
                   if result and result.get('newer') else 'Checking the latest ShareScout version on GitHub…')
        self.status = tk.StringVar(value=initial)
        ui.label(body, textvariable=self.status).pack(fill='x', pady=12)
        ui.label(body, text='Choose Upgrade and restart to download and install the update automatically. ShareScout will reopen when it’s ready.').pack(fill='x', pady=8)
        buttons = ui.buttons(layout.footer, [('Close', self.close), ('Check again', self.check), ('Upgrade and restart', self.upgrade)], accent=('Upgrade and restart',), maximum=2)
        self.check_button = buttons[1]
        self.upgrade_button = buttons[2]
        self.close_button = buttons[0]
        self.upgrade_button.configure(state='normal' if result and result.get('newer') else 'disabled')
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        self.window.after(100, self.poll)
        if start_immediately:
            self.window.after(100, self.upgrade)
        elif not result:
            self.check()

    def check(self):
        if self.busy: return
        self.busy = True; self.check_button.configure(state='disabled')
        self.status.set('Checking the latest ShareScout version on GitHub…')
        def worker():
            try: self.events.put(('result', updates.check()))
            except Exception as exc: self.events.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def upgrade(self):
        if self.upgrading or not self.result or not self.result.get('newer'):
            return
        self.upgrading = True
        self.check_button.configure(state='disabled')
        self.upgrade_button.configure(state='disabled')
        self.close_button.configure(state='disabled')
        self.status.set(f"Downloading ShareScout {self.result['latest']}…")
        def worker():
            try: self.events.put(('stage', updates.stage_update(self.result['latest'])))
            except Exception as exc: self.events.put(('upgrade-error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        if not self.window.winfo_exists(): return
        while not self.events.empty():
            kind, result = self.events.get(); self.busy = False; self.check_button.configure(state='normal')
            if kind == 'stage':
                self.status.set('Update downloaded. Closing ShareScout and installing…')
                if self.on_upgrade:
                    if not self.on_upgrade(result):
                        shutil.rmtree(result, ignore_errors=True)
                        self.upgrading = False
                        self.status.set('Close active connections before upgrading, then try again.')
                        self.close_button.configure(state='normal')
                        self.check_button.configure(state='normal')
                        self.upgrade_button.configure(state='normal')
                else:
                    shutil.rmtree(result, ignore_errors=True)
                    self.status.set('Automatic installation is unavailable from this window. Please restart ShareScout and try again.')
                    self.close_button.configure(state='normal')
                    self.upgrade_button.configure(state='normal')
            elif kind == 'upgrade-error':
                self.upgrading = False
                self.status.set(result)
                self.close_button.configure(state='normal')
                self.check_button.configure(state='normal')
                self.upgrade_button.configure(state='normal')
            elif kind == 'error': self.status.set(result)
            else:
                self.result = result
                if result['newer']:
                    self.status.set(f"Update available: ShareScout {result['latest']}\nYou have {result['installed']}.")
                    self.upgrade_button.configure(state='normal')
                elif updates.version_tuple(result['latest']) == updates.version_tuple(result['installed']):
                    self.status.set('You’re up to date: ShareScout ' + result['installed'])
                    self.upgrade_button.configure(state='disabled')
                else:
                    self.status.set(f"Your version ({result['installed']}) is newer than GitHub’s main branch ({result['latest']}).")
                    self.upgrade_button.configure(state='disabled')
        if self.window.winfo_exists(): self.window.after(150, self.poll)

    def close(self):
        if self.upgrading:
            self.status.set('Please wait for the update to finish downloading.')
            return
        self.window.destroy()
