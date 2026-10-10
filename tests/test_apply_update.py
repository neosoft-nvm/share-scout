import tempfile
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import apply_update


class ApplyUpdateTests(unittest.TestCase):
    def test_launcher_matches_window_class_and_uses_installed_icon(self):
        with tempfile.TemporaryDirectory() as parent:
            home = Path(parent)
            target = home / 'app with spaces'
            target.mkdir()
            (target / 'sharescout.png').write_bytes(b'icon')
            with patch.object(apply_update.Path, 'home', return_value=home):
                apply_update.write_linux_launcher(target)
            entry = (home / '.local/share/applications/resource-mapper.desktop').read_text()
            self.assertIn('StartupWMClass=ShareScout\n', entry)
            self.assertIn('Icon=' + str(target / 'sharescout.png') + '\n', entry)
            self.assertIn('Exec="' + str(target / 'Start-Resource-Mapper') + '"', entry)

    def test_staged_files_replace_install_and_preserve_user_files(self):
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent)
            target = root / 'ResourceMapper'
            target.mkdir()
            (target / 'connections.json').write_text('[]')
            stage = root / 'sharescout-update-test'
            stage.mkdir()
            (stage / 'app_info.py').write_text("VERSION = '0.5.2'\n")
            (stage / 'resource_mapper.py').write_text('# updated\n')
            (stage / 'Start-Resource-Mapper').write_text('#!/bin/sh\n')
            (stage / 'sharescout.png').write_bytes(b'icon')
            with patch.object(apply_update, 'install_root', return_value=target), \
                    patch.object(apply_update, 'wait_for_process'), \
                    patch.object(apply_update, 'write_linux_launcher'), \
                    patch.object(apply_update.subprocess, 'Popen') as launch:
                apply_update.apply(12345, stage, '/usr/bin/python3')
            self.assertIn('0.5.2', (target / 'app_info.py').read_text())
            self.assertEqual((target / 'connections.json').read_text(), '[]')
            self.assertTrue((target / 'Start-Resource-Mapper').stat().st_mode & 0o111)
            launch.assert_called_once()
            self.assertFalse(stage.exists())


if __name__ == '__main__':
    unittest.main()
