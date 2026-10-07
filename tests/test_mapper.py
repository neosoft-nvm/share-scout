import importlib.util
from pathlib import Path
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('mapper', Path(__file__).parents[1] / 'resource_mapper.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ValidationTests(unittest.TestCase):
    def test_smb_platform_formats(self):
        with patch.object(m, 'WINDOWS', False):
            self.assertEqual(m.smb_address(r'\\server\share'), 'smb://server/share')
        with patch.object(m, 'WINDOWS', True):
            self.assertEqual(m.smb_address('smb://server/share'), r'\\server\share')

    def test_invalid_smb(self):
        for value in ['server', '', 'smb://user:password@server/share']:
            with self.assertRaises(ValueError): m.smb_address(value)

    def test_nonempty_mount_rejected(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(m, 'WINDOWS', False):
            Path(folder, 'precious.txt').write_text('keep')
            with self.assertRaises(ValueError): m.cloud_command('drive', folder)
            self.assertEqual(Path(folder, 'precious.txt').read_text(), 'keep')

    def test_linux_command_arguments(self):
        with tempfile.TemporaryDirectory(prefix='mapper space ') as folder, patch.object(m, 'WINDOWS', False):
            command = m.cloud_command('my drive', folder)
            self.assertEqual(command[:4], ['rclone', 'mount', 'my drive:', folder])

    def test_windows_drive_validation(self):
        with patch.object(m, 'WINDOWS', True):
            for target in ['C:', 'D:/folder', 'ZZ:', '']:
                with self.assertRaises(ValueError): m.cloud_command('drive', target)

    def test_invalid_remote(self):
        with self.assertRaises(ValueError): m.cloud_command('drive:; command', 'R:')

if __name__ == '__main__': unittest.main()
