"""Provider sign-in and rclone account choices presented inside Tk."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cloud_setup
import ui
from app_info import window_title


class CloudSignIn:
    def __init__(self, app):
        self.app = app; self.session = None; self.running = False; self.closed = False
        self.events = queue.Queue(); self.state = None; self.option = None
        self.window = tk.Toplevel(app.root); self.window.title(window_title('Connect your cloud'))
        self.window.transient(app.root); self.window.protocol('WM_DELETE_WINDOW', self.close)
        layout = ui.Layout(self.window, 650, 550); body = layout.body
        ui.label(body, text='Your cloud, one click closer', font=ui.heading_font(self.window, 19)).pack(fill='x')
        ui.label(body, text='1  Choose your cloud   →   2  Sign in securely   →   3  Open your files').pack(fill='x', pady=12)
        self.provider = tk.StringVar(value='Google Drive')
        self.picker = ttk.Combobox(body, textvariable=self.provider, values=list(cloud_setup.PROVIDERS), state='readonly')
        self.picker.pack(fill='x', pady=8)
        ui.label(body, text='Your browser opens for Google or Microsoft sign-in. Return here to choose your drive. '
                 'ShareScout never asks for your cloud password.').pack(fill='x', pady=8)
        self.status = tk.StringVar(value='Ready when you are. Choose a cloud above, then Sign in with browser.')
        ui.label(body, textvariable=self.status).pack(fill='x', pady=10)
        self.progress = ttk.Progressbar(body, mode='indeterminate'); self.progress.pack(fill='x', pady=8)
        self.existing = ttk.LabelFrame(body, text='Already signed in? Pick a saved account', padding=8)
        self.existing.pack(fill='x', pady=8)
        self.account = tk.StringVar(); self.accounts = {}
        self.account_picker = ttk.Combobox(self.existing, textvariable=self.account, state='readonly')
        self.account_picker.pack(fill='x')
        self.reuse = ttk.Button(self.existing, text='Connect saved account', command=self.use_existing, state='disabled')
        self.reuse.pack(fill='x', pady=4)
        self.questions = ttk.Frame(body); self.questions.pack(fill='x', pady=8)
        self.buttons = ui.buttons(layout.footer, [('Cancel', self.close), ('Sign in with browser', self.start)], accent=('Sign in with browser',), maximum=2)
        self.window.after(150, self.poll)
        def load():
            try: self.events.put(('accounts', cloud_setup.existing_accounts()))
            except Exception: self.events.put(('accounts', []))
        threading.Thread(target=load, daemon=True).start()

    def use_existing(self):
        if self.running: return
        selected = self.accounts.get(self.account.get())
        if selected:
            try: self.app.add_cloud_account(selected[1], selected[0])
            except Exception as exc:
                messagebox.showerror('Connect cloud', str(exc), parent=self.window); return
            self.finish()

    def start(self):
        if self.running: return
        if self.session:
            if self.session.complete:
                try: self.app.add_cloud_account(self.provider.get(), self.session.remote)
                except Exception as exc:
                    self.status.set('Could not save this folder: ' + str(exc)); return
                self.finish(); return
            self.continue_signin(); return
        self.session = cloud_setup.CloudSession(self.provider.get())
        self.picker.configure(state='disabled')
        self.work()

    def work(self, state=None, answer=None):
        self.reuse.configure(state='disabled')
        self.running = True; self.buttons[1].configure(state='disabled'); self.progress.start(12)
        self.status.set('Opening secure sign-in… Finish in your browser, then return here. You can cancel at any time.')
        def worker():
            try:
                result = self.session.step(state, answer)
                if self.session.cancelled.is_set():
                    self.session.cleanup(force=True); return
                self.events.put(('result', result))
            except Exception as exc:
                try: self.session.cleanup()
                except Exception: pass
                self.events.put(('error', str(exc)))
        self.worker_thread = threading.Thread(target=worker)
        self.worker_thread.start()

    def show_question(self, result):
        self.state = result['State']; self.option = result.get('Option') or {}
        for widget in self.questions.winfo_children(): widget.destroy()
        name = self.option.get('Name', '')
        friendly = {'config_is_local': 'Open your browser for secure sign-in?',
                    'config_type': 'Which kind of OneDrive account do you use?',
                    'config_driveid': 'Choose the drive you want to open.',
                    'config_team_drive': 'Use a shared Google Drive? Choose No for your own files.',
                    'config_driveok': 'Use this drive?'}
        help_text = friendly.get(name, self.option.get('Help', 'Choose an option to continue.'))
        ui.label(self.questions, text=help_text).pack(fill='x', pady=8)
        if result.get('Error'): ui.label(self.questions, text='That choice was not accepted. Please choose again.').pack(fill='x')
        self.answer = tk.StringVar(value=cloud_setup.answer_text(self.option.get('Default')))
        self.examples = self.option.get('Examples') or []
        self.values = {f"{example['Value']} — {example.get('Help', '')}": str(example['Value']) for example in self.examples}
        if self.values:
            default = next((label for label, value in self.values.items() if value == self.answer.get()), '')
            self.answer.set(default)
            ttk.Combobox(self.questions, textvariable=self.answer, values=list(self.values),
                         state='readonly' if self.option.get('Exclusive') else 'normal').pack(fill='x')
        else:
            ttk.Entry(self.questions, textvariable=self.answer, show='•' if self.option.get('IsPassword') else '').pack(fill='x')
        self.status.set('One more choice to make your files available.')
        self.buttons[1].configure(text='Continue', state='normal')

    def continue_signin(self):
        answer = self.values.get(self.answer.get(), self.answer.get())
        if self.option.get('Required') and not answer:
            messagebox.showinfo('Choose an option', 'Choose or enter a value before continuing.', parent=self.window); return
        self.work(self.state, answer)

    def poll(self):
        if self.closed: return
        while not self.events.empty():
            kind, result = self.events.get()
            if kind == 'accounts':
                self.accounts = {f'{provider} — {remote}': (remote, provider) for remote, provider in result}
                self.account_picker.configure(values=list(self.accounts))
                if self.accounts:
                    self.account.set(next(iter(self.accounts)))
                    if not self.session: self.reuse.configure(state='normal')
                else: self.account.set('No saved cloud accounts yet')
                continue
            self.running = False; self.progress.stop()
            if kind == 'error':
                self.status.set(result); self.session = None; self.picker.configure(state='readonly')
                self.buttons[1].configure(text='Try sign-in again', state='normal')
                if self.accounts: self.reuse.configure(state='normal')
            elif not result['State']:
                if result.get('Error'):
                    self.status.set('Sign-in was not accepted. Cancel and try again.'); continue
                try: self.app.add_cloud_account(self.provider.get(), self.session.remote)
                except Exception as exc:
                    self.status.set('Signed in, but the folder could not be saved: ' + str(exc))
                    self.buttons[1].configure(text='Save & connect', state='normal'); continue
                self.finish(); return
            elif (result.get('Option') or {}).get('Name') == 'config_is_local':
                self.work(result['State'], True)
            else: self.show_question(result)
        self.window.after(150, self.poll)

    def finish(self):
        self.closed = True; self.window.destroy(); self.app.cloud_dialog = None

    def close(self):
        if self.closed: return
        if self.session:
            self.session.cancel()
            session = self.session
            worker = getattr(self, 'worker_thread', None)
            def cleanup():
                if worker: worker.join()
                try: session.cleanup(force=True)
                except Exception: pass
            threading.Thread(target=cleanup).start()
        self.finish()
