"""Installation must never follow a failed native build."""
import subprocess
import unittest
from unittest.mock import patch
from scripts.build_install_desktop import main


class BuildFailureTests(unittest.TestCase):
    def test_failed_build_does_not_run_installer(self):
        with patch('scripts.build_install_desktop.subprocess.run', side_effect=subprocess.CalledProcessError(1, 'npm')) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                main()
        self.assertEqual(run.call_count, 1)
