from pathlib import Path
import json
import os
import queue
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).parents[1]))
from single_instance import SingleInstance
import resource_mapper as mapper


class SingleInstanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.first = SingleInstance(self.temp.name); self.addCleanup(self.first.close)

    def test_second_launch_cannot_lock_and_activates_first(self):
        self.assertTrue(self.first.acquire())
        second = SingleInstance(self.temp.name); self.addCleanup(second.close)
        self.assertFalse(second.acquire())
        self.assertTrue(second.activate_existing())
        self.assertEqual(self.first.events.get(timeout=1), 'activate')

    def test_stale_file_does_not_block_restart(self):
        self.first.path.write_text('stale invalid metadata')
        self.assertTrue(self.first.acquire()); self.first.close()
        replacement = SingleInstance(self.temp.name); self.addCleanup(replacement.close)
        self.assertTrue(replacement.acquire())

    def test_unauthenticated_activation_is_ignored(self):
        self.first.acquire()
        info = json.loads(self.first.path.read_text())
        with socket.create_connection(('127.0.0.1', info['port']), timeout=1) as client:
            client.sendall(b'{"token":"wrong","command":"activate"}\n')
            self.assertEqual(client.recv(16), b'')
        with self.assertRaises(queue.Empty): self.first.events.get_nowait()

    def test_existing_launch_returns_before_creating_tk_or_app(self):
        with patch('single_instance.SingleInstance') as guard, patch.object(mapper.tk, 'Tk') as tk, patch.object(mapper, 'App') as app:
            guard.return_value.acquire.return_value = False
            mapper.main()
            guard.return_value.activate_existing.assert_called_once()
            tk.assert_not_called(); app.assert_not_called()

    def test_activation_restores_and_focuses_window_on_ui_thread(self):
        root = Mock(); self.first.attach(root)
        callback = root.after.call_args.args[1]
        self.first.events.put('activate'); callback()
        root.deiconify.assert_called_once(); root.lift.assert_called_once(); root.focus_force.assert_called_once()

    def test_crashed_process_releases_lock(self):
        source = str(Path(__file__).parents[1])
        code = 'import sys; sys.path.insert(0,sys.argv[1]); from single_instance import SingleInstance; g=SingleInstance(sys.argv[2]); assert g.acquire(); print("ready",flush=True); sys.stdin.read()'
        child = subprocess.Popen([sys.executable, '-c', code, source, self.temp.name], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            self.assertFalse(self.first.acquire())
            child.kill(); child.wait(timeout=5)
            self.assertTrue(self.first.acquire())
        finally:
            if child.poll() is None: child.kill(); child.wait(timeout=5)
            child.stdin.close(); child.stdout.close(); child.stderr.close()


if __name__ == '__main__': unittest.main()
