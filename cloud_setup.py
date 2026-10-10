"""Cancellable rclone configuration protocol; no terminal or token logging."""
import json
import os
import subprocess
import threading
import time
import uuid

PROVIDERS = {'Google Drive': 'drive', 'OneDrive': 'onedrive'}


def answer_text(value):
    if isinstance(value, bool): return str(value).lower()
    return '' if value is None else str(value)


class CloudSession:
    def __init__(self, provider):
        self.backend = PROVIDERS[provider]
        self.remote = 'sharescout-' + uuid.uuid4().hex
        self.cancelled = threading.Event()
        self.process = None
        self.created = False
        self.complete = False

    def execute(self, args):
        if self.cancelled.is_set(): raise InterruptedError('Sign-in cancelled.')
        self.process = subprocess.Popen(['rclone'] + args, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        deadline = time.monotonic() + 300
        try:
            while True:
                try:
                    output, error = self.process.communicate(timeout=.25)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancelled.is_set() or time.monotonic() > deadline:
                        self.process.terminate()
                        try: self.process.communicate(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.process.kill(); self.process.communicate()
                        raise InterruptedError('Sign-in cancelled or timed out. Try again when you are ready.')
            if self.cancelled.is_set(): raise InterruptedError('Sign-in cancelled.')
            if self.process.returncode:
                # Provider output can contain OAuth data. Keep errors out of UI/logs.
                raise RuntimeError('Cloud sign-in could not finish. Check your internet connection, '
                                   'allow access in the browser, and try again. Update rclone if this continues.')
            return output
        finally: self.process = None

    def step(self, state=None, answer=None):
        args = ['config', 'create', self.remote, self.backend] if state is None else [
            'config', 'update', self.remote, '--continue', '--state', state,
            '--result', answer_text(answer)]
        self.created = True
        result = json.loads(self.execute(args + ['--non-interactive']))
        if not isinstance(result, dict) or 'State' not in result:
            raise RuntimeError('This rclone version cannot use the sign-in dialog. Update it with the setup launcher.')
        self.complete = not result['State'] and not result.get('Error')
        return result

    def cancel(self):
        self.cancelled.set()

    def cleanup(self, force=False):
        # Only the unique account created by this session is ever removed.
        if self.created and (force or not self.complete):
            subprocess.run(['rclone', 'config', 'delete', self.remote],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=15, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.created = False


def existing_accounts():
    result = subprocess.run(['rclone', 'listremotes', '--long'], stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode: raise RuntimeError('Saved cloud accounts could not be loaded.')
    providers = {value: key for key, value in PROVIDERS.items()}
    accounts = []
    for line in result.stdout.splitlines():
        # Names can contain spaces; --long separates the name and type with a colon.
        remote, separator, detail = line.partition(':')
        backend = detail.split()[0] if detail.split() else ''
        if separator and backend in providers:
            accounts.append((remote.strip(), providers[backend]))
    return accounts
