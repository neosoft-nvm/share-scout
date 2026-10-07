"""One desktop session per user, with authenticated localhost window activation."""
import errno
import json
import os
from pathlib import Path
import queue
import secrets
import socket
import threading
import time


class SingleInstance:
    def __init__(self, state_dir):
        self.path = Path(state_dir) / 'sharescout-instance.lock'
        self.file = None; self.server = None
        self.events = queue.Queue(); self.stop = threading.Event()
        self.thread = None; self.token = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(self.path, flags, 0o600)
        self.file = os.fdopen(fd, 'r+b')
        if os.name != 'nt': os.fchmod(fd, 0o600)
        try:
            if os.name == 'nt':
                import msvcrt
                if self.path.stat().st_size == 0:
                    self.file.write(b'\n'); self.file.flush()
                self.file.seek(0)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close(); self.file = None
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK): return False
            raise
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.bind(('127.0.0.1', 0)); self.server.listen(4); self.server.settimeout(.2)
            self.token = secrets.token_hex(32)
            self.file.seek(0)
            self.file.write(json.dumps({'port': self.server.getsockname()[1], 'token': self.token}).encode())
            self.file.truncate(); self.file.flush()
            self.thread = threading.Thread(target=self.listen, daemon=True); self.thread.start()
        except Exception:
            self.close(); raise
        return True

    def listen(self):
        while not self.stop.is_set():
            try: client, _ = self.server.accept()
            except socket.timeout: continue
            except OSError: break
            with client:
                try:
                    client.settimeout(.5)
                    data = b''
                    while b'\n' not in data and len(data) < 2048:
                        chunk = client.recv(2048 - len(data))
                        if not chunk: break
                        data += chunk
                    request = json.loads(data.decode())
                    token = request.get('token')
                    if not isinstance(token, str) or not secrets.compare_digest(token, self.token): continue
                    if request.get('command') != 'activate': continue
                    self.events.put('activate'); client.sendall(b'OK\n')
                except (OSError, ValueError, AttributeError): pass

    def activate_existing(self, timeout=2):
        # The first process may still be writing its activation address.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                info = json.loads(self.path.read_text())
                port = info['port']; token = info['token']
                if not isinstance(port, int) or not 0 < port < 65536 or not isinstance(token, str) or len(token) != 64: return False
                with socket.create_connection(('127.0.0.1', port), timeout=.3) as client:
                    client.settimeout(.3)
                    client.sendall(json.dumps({'token': token, 'command': 'activate'}).encode() + b'\n')
                    if client.recv(16) == b'OK\n': return True
            except (OSError, ValueError, KeyError, TypeError): pass
            time.sleep(.1)
        return False

    def attach(self, root):
        def poll():
            if self.stop.is_set(): return
            while not self.events.empty():
                self.events.get()
                root.deiconify(); root.lift(); root.focus_force()
            root.after(100, poll)
        root.after(100, poll)

    def close(self):
        self.stop.set()
        if self.server:
            self.server.close()
            if self.thread: self.thread.join(timeout=1)
            self.server = None
        if self.file:
            # Closing releases the OS lock even after a crash. Keep the file in
            # place: unlinking it could let another process lock a different inode.
            self.file.close(); self.file = None
