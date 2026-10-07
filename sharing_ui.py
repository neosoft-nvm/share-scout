"""Offer Linux sharing setup with normal-user consent before any sudo command."""
import json
from pathlib import Path
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import uuid
import sharing_setup
import ui


def terminal_command(args):
    options = [('ptyxis', ['--new-window', '--']), ('gnome-terminal', ['--']), ('kgx', ['--']),
               ('x-terminal-emulator', ['-e']), ('konsole', ['-e']), ('xfce4-terminal', ['-x']),
               ('mate-terminal', ['-e']), ('xterm', ['-e'])]
    for terminal, flags in options:
        if shutil.which(terminal): return [terminal] + flags + args
    raise RuntimeError('A setup terminal was not found. Run the setup command shown in the dialog in a terminal.')


class SharingSetup:
    def __init__(self, app, state_dir, force=False, done=None):
        self.app = app; self.state_dir = state_dir; self.force = force; self.done = done
        self.events = queue.Queue(); self.finished = False; self.result_file = None; self.checking = False
        self.choice_file = state_dir / 'sharing-choice.json'
        self.window = tk.Toplevel(app.root); self.window.title('ShareScout — sharing setup'); self.window.transient(app.root)
        self.window.protocol('WM_DELETE_WINDOW', self.close)
        layout = ui.Layout(self.window, 640, 520); frame = layout.body
        ui.label(frame, text='Share this computer', font=ui.heading_font(self.window, 19)).pack(fill='x', pady=(0, 10))
        ui.label(frame, text='We check whether this computer is offering shared folders to your other devices.').pack(fill='x', pady=(0, 14))
        self.status = tk.StringVar(value='Checking Samba and shared folders…')
        ui.label(frame, textvariable=self.status).pack(fill='x', pady=12)
        ui.label(frame, text='If no shared folders are configured, setup can install Samba and create a password-protected folder called “Shared with ShareScout”. Existing shared folders are kept.').pack(fill='x', pady=8)
        ui.label(frame, text='Setup will ask for administrator approval and, for a new folder, a sharing password. It permits SMB connections from your current local IPv4 network. Run this on your home Wi-Fi or Ethernet connection.').pack(fill='x', pady=8)
        self.widgets = ui.buttons(layout.footer, [('Not now', self.skip), ('Recheck', self.check), ('Set up sharing', self.install)], accent=('Set up sharing',), maximum=3)
        self.install_button = self.widgets[2]; self.install_button.configure(state='disabled')
        self.window.after(100, self.poll); self.check()

    def check(self):
        if self.checking: return
        self.checking = True; self.install_button.configure(state='disabled')
        self.status.set('Checking Samba and shared folders…')
        def worker():
            try: self.events.put(('check', sharing_setup.inspect()))
            except Exception as exc: self.events.put(('error', str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def record(self, choice):
        self.choice_file.write_text(json.dumps({'version': 1, 'choice': choice}))

    def skip(self):
        if self.result_file:
            messagebox.showinfo('Setup is running', 'Complete or close the setup terminal first.', parent=self.window); return
        self.record('declined'); self.close()

    def install(self):
        if self.result_file: return
        result_file = self.state_dir / ('sharing-result-' + uuid.uuid4().hex + '.json')
        args = [sys.executable, str(Path(__file__).with_name('sharing_setup.py')), '--configure', str(result_file)]
        try:
            command = terminal_command(args)
            subprocess.Popen(command)
            self.result_file = result_file
            self.install_button.configure(state='disabled')
            self.widgets[0].configure(state='disabled'); self.widgets[1].configure(state='disabled')
            self.status.set('Finish setup in the terminal window. It asks for your administrator password and a sharing password for a new folder.')
        except Exception as exc:
            messagebox.showerror('Sharing setup', str(exc) + '\n\nRun manually:\n' + shlex.join(args), parent=self.window)

    def poll(self):
        if self.finished: return
        while not self.events.empty():
            kind, result = self.events.get(); self.checking = False
            if kind == 'error': self.status.set(result)
            else:
                lines = ['Samba: ' + ('installed' if result['installed'] else 'not installed'),
                         'Shared folders: ' + (', '.join(result['shares']) or 'none configured'),
                         'Network sharing: ' + ('listening on port 445' if result['listening'] else 'not listening on the network')]
                if result['error']: lines.append('Check failed: ' + result['error'])
                self.status.set('\n'.join(lines))
                if result['ready'] and not self.force:
                    self.record('existing'); self.close(); return
                self.install_button.configure(state='disabled' if result['error'] else 'normal')
                if result['ready']: self.install_button.configure(text='Repair network access')
        if self.result_file and self.result_file.exists():
            try: result = json.loads(self.result_file.read_text())
            except (OSError, ValueError): result = None
            if result:
                self.result_file.unlink(missing_ok=True); self.result_file = None
                self.widgets[0].configure(state='normal'); self.widgets[1].configure(state='normal')
                if result.get('ok'):
                    self.record('configured')
                    messagebox.showinfo('Sharing is set up', result['message'] + ('\n\nFolder: ' + result['folder'] if result.get('folder') else ''), parent=self.window)
                    self.close(); return
                else:
                    self.status.set('Setup could not finish: ' + result.get('error', 'Unknown error'))
                    self.install_button.configure(state='normal')
        self.window.after(250, self.poll)

    def close(self):
        if self.finished: return
        self.finished = True; self.window.destroy(); self.app.sharing_dialog = None
        if self.done: self.done()
