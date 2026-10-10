import json
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).parents[1]))
from cloud_setup import CloudSession, existing_accounts
from resource_mapper import App
import network


class CloudTests(unittest.TestCase):
    def test_browser_questions_continue_without_a_terminal(self):
        session = CloudSession('Google Drive')
        outputs = [json.dumps({'State': 'oauth', 'Option': {'Name': 'config_is_local', 'Default': True}}),
                   json.dumps({'State': ''})]
        with patch.object(session, 'execute', side_effect=outputs) as execute:
            self.assertEqual(session.step()['State'], 'oauth')
            self.assertFalse(session.complete)
            self.assertEqual(session.step('oauth', True)['State'], '')
            self.assertTrue(session.complete)
            self.assertEqual(execute.call_args_list[1].args[0][-5:], ['--state', 'oauth', '--result', 'true', '--non-interactive'])
            self.assertIn('--non-interactive', execute.call_args_list[0].args[0])

    def test_cancelled_session_never_launches_browser(self):
        session = CloudSession('OneDrive'); session.cancel()
        with patch('cloud_setup.subprocess.Popen') as process:
            with self.assertRaises(InterruptedError): session.step()
            process.assert_not_called()

    def test_cancellation_terminates_inflight_oauth_process(self):
        session = CloudSession('Google Drive')
        process = Mock()
        calls = 0
        def communicate(timeout=None):
            nonlocal calls
            calls += 1
            if calls == 1:
                session.cancel()
                raise subprocess.TimeoutExpired('rclone', timeout)
            return '', ''
        process.communicate.side_effect = communicate
        with patch('cloud_setup.subprocess.Popen', return_value=process):
            with self.assertRaises(InterruptedError): session.execute(['config', 'create'])
        process.terminate.assert_called_once()
        self.assertIsNone(session.process)

    def test_partial_account_cleanup_only_deletes_its_unique_remote(self):
        session = CloudSession('OneDrive'); session.created = True
        with patch('cloud_setup.subprocess.run') as run:
            session.cleanup()
            self.assertEqual(run.call_args.args[0], ['rclone', 'config', 'delete', session.remote])
            self.assertTrue(session.remote.startswith('sharescout-'))

    def test_successful_account_is_retained(self):
        session = CloudSession('Google Drive'); session.created = session.complete = True
        with patch('cloud_setup.subprocess.run') as run:
            session.cleanup(); run.assert_not_called()
            session.cleanup(force=True); run.assert_called_once()

    def test_existing_accounts_accept_spaces_and_filter_other_backends(self):
        with patch('cloud_setup.subprocess.run', return_value=Mock(returncode=0, stdout='my photos: drive\nwork: onedrive\nbackup: s3\n')):
            self.assertEqual(existing_accounts(), [('my photos', 'Google Drive'), ('work', 'OneDrive')])

    def test_reuse_saved_account_opens_instead_of_duplicating(self):
        app = App.__new__(App)
        app.items = [dict(kind='Google Drive', source='photos')]
        app.tree = Mock(); app.open_when_connected = set(); app.operation = Mock()
        app.add_cloud_account('Google Drive', 'photos')
        self.assertEqual(len(app.items), 1)
        self.assertEqual(app.open_when_connected, {0})
        app.operation.assert_called_once_with(True, 0)

    def test_open_disconnected_folder_connects_then_opens(self):
        app = App.__new__(App); app.selected = Mock(return_value=0)
        app.items = [dict(status='Disconnected')]; app.operation = Mock(); app.open_when_connected = set()
        app.open()
        app.operation.assert_called_once_with(True, 0)
        self.assertEqual(app.open_when_connected, {0})


class WindowsTests(unittest.TestCase):
    def test_share_wizard_requests_elevation_only_for_wizard(self):
        api = Mock(); api.ShellExecuteW.return_value = 42
        with patch('network.ctypes.WinDLL', return_value=api, create=True): network.win_share_folder()
        args = api.ShellExecuteW.call_args.args
        self.assertEqual(args[1], 'runas')
        self.assertTrue(args[2].endswith('shrpubw.exe'))
        self.assertNotIn('python', args[2])

    def test_cancelled_elevation_explains_how_to_retry(self):
        api = Mock(); api.ShellExecuteW.return_value = 5
        with patch('network.ctypes.WinDLL', return_value=api, create=True):
            with self.assertRaisesRegex(RuntimeError, 'Administrator approval'): network.win_share_folder()

    def test_existing_mapping_is_imported_without_admin_command(self):
        api = Mock()
        def get_connection(target, buffer, size):
            if target == 'R:': buffer.value = r'\\nas\photos'; return 0
            return 2250
        api.WNetGetConnectionW.side_effect = get_connection
        with patch.object(network, 'WINDOWS', True), patch('network.ctypes.WinDLL', return_value=api, create=True):
            folders = network.connected_folders()
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0]['target'], 'R:')
        self.assertEqual(folders[0]['status'], 'Connected')

    def test_linux_reads_existing_mounts(self):
        with patch.object(network, 'WINDOWS', False), patch('network.shutil.which', return_value='/usr/bin/gio'), patch('network.command', return_value='  Mount(0): Photos -> smb://nas/Family%20Photos\n    Type: GProxyMount\n'):
            self.assertEqual(network.connected_folders()[0]['name'], 'Family Photos')

if __name__ == '__main__': unittest.main()
