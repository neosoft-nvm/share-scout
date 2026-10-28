import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
import desktop_service as desktop

ITEM = {'name': 'Photos', 'kind': 'Network share', 'source': 'smb://192.168.1.50/Family%20Photos', 'target': '', 'auto': False, 'status': 'Disconnected'}


class DesktopServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)
        self.patches = [patch.object(desktop, 'STATE', self.state), patch.object(desktop, 'CONFIG', self.state / 'connections.json')]
        for item in self.patches:
            item.start(); self.addCleanup(item.stop)
        self.service = desktop.DesktopService()

    def test_settings_do_not_persist_credentials_or_status(self):
        self.service.save_items([{**ITEM, 'password': 'private', 'status': 'Connected'}])
        saved = json.loads(desktop.CONFIG.read_text())[0]
        self.assertNotIn('password', saved)
        self.assertEqual(saved['status'], 'Disconnected')

    def test_malformed_settings_are_preserved(self):
        desktop.CONFIG.write_text('{broken')
        with self.assertRaises(ValueError): self.service.save_items([ITEM])
        self.assertEqual(desktop.CONFIG.read_text(), '{broken')

    def test_existing_connections_get_backup(self):
        self.service.save_items([ITEM]); previous = desktop.CONFIG.read_text()
        self.service.save_items([])
        self.assertEqual(desktop.CONFIG.with_suffix('.backup.json').read_text(), previous)

    def test_atomic_save_failure_preserves_settings(self):
        self.service.save_items([ITEM]); previous = desktop.CONFIG.read_text()
        with patch.object(desktop.os, 'replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.service.save_items([])
        self.assertEqual(desktop.CONFIG.read_text(), previous)
        self.assertEqual(list(self.state.glob('*.tmp')), [])

    def test_mount_failure_propagates_and_password_is_not_saved(self):
        with patch.object(desktop.network, 'mount_share', side_effect=PermissionError('Sign in')), patch.object(desktop.credential_store, 'save') as save:
            with self.assertRaises(PermissionError): self.service.mount(ITEM, {'username':'test', 'password':'private'}, True)
            save.assert_not_called()

    def test_failed_network_connection_names_the_share_including_route_errors(self):
        with patch.object(desktop.network,'mount_share',side_effect=RuntimeError('No route to host')), patch.object(self.service,'get_auth',return_value=None):
            with self.assertRaises(RuntimeError) as result:self.service.mount(ITEM)
            self.assertIn(ITEM['name'],str(result.exception))
            self.assertIn(ITEM['source'],str(result.exception))
            self.assertIn('No route to host',str(result.exception))

    def test_windows_assigns_unused_letter_and_normalizes_source(self):
        with patch.object(desktop, 'WINDOWS', True), patch.object(desktop.network, 'free_drive', return_value='T:'), patch.object(desktop.network, 'mount_share') as mount, patch.object(self.service, 'get_auth', return_value=None):
            result = self.service.mount(ITEM)
            mount.assert_called_once_with('\\\\192.168.1.50\\Family Photos', 'T:', None)
            self.assertEqual(result['target'], 'T:')
            self.assertEqual(result['status'], 'Connected')

    def test_credential_reuse_and_optional_keyring(self):
        auth = {'username': 'test', 'password': 'private', 'domain': ''}
        with patch.object(desktop.credential_store, 'save') as save:
            self.service.signed_in('192.168.1.50', auth, False); save.assert_not_called()
            self.service.signed_in('192.168.1.50', auth, True); save.assert_called_once()
        self.assertEqual(self.service.get_auth('192.168.1.50'), auth)

    def test_refresh_uses_actual_mounts(self):
        self.service.save_items([ITEM])
        with patch.object(desktop.network, 'connected_folders', return_value=[]):
            self.assertEqual(self.service.refresh()[0]['status'], 'Disconnected')
        with patch.object(desktop.network, 'connected_folders', return_value=[{**ITEM, 'status':'Connected'}]):
            self.assertEqual(self.service.refresh()[0]['status'], 'Connected')

    def test_empty_scan_stays_empty(self):
        with patch.object(desktop.network, 'local_networks', return_value=[]), patch.object(desktop.network, 'scan'):
            result = self.service.scan('scan-test')
            self.assertEqual(result['devices'], [])
            self.assertEqual(self.service.scans, {})

    def test_scan_can_be_cancelled(self):
        stop = threading.Event(); self.service.scans['test'] = stop
        self.service.call('stop_scan', {'scanId':'test'})
        self.assertTrue(stop.is_set())

    def test_browse_passes_credentials(self):
        auth = {'username':'test', 'password':'private', 'domain':''}
        with patch.object(desktop.network, 'list_shares', return_value=[]) as browse, patch.object(self.service, 'signed_in') as signed:
            self.assertEqual(self.service.call('shares', {'address':'192.168.1.50','credentials':auth,'remember':True}), [])
            browse.assert_called_once_with('192.168.1.50', auth); signed.assert_called_once_with('192.168.1.50', auth, True)

    def test_unmount_failure_propagates(self):
        with patch.object(desktop, 'WINDOWS', False), patch.object(desktop.network, 'command', side_effect=RuntimeError('busy')):
            with self.assertRaises(RuntimeError): self.service.unmount(ITEM)

    def test_cloud_requires_actual_configured_account(self):
        item = {**ITEM, 'kind':'Google Drive', 'source':'unknown'}
        with patch.object(desktop.cloud_setup, 'existing_accounts', return_value=[]), patch.object(desktop.subprocess, 'Popen') as process:
            with self.assertRaises(ValueError): self.service.mount(item)
            process.assert_not_called()

    def test_cloud_folder_must_be_empty(self):
        target = self.state / 'mount'; target.mkdir(); (target / 'existing.txt').write_text('preserve')
        item = {**ITEM, 'kind':'Google Drive', 'source':'account', 'target':str(target)}
        with patch.object(desktop, 'WINDOWS', False), patch.object(desktop.cloud_setup, 'existing_accounts', return_value=[('account','Google Drive')]), patch.object(desktop.subprocess, 'Popen') as process:
            with self.assertRaises(ValueError): self.service.mount(item)
            process.assert_not_called()
        self.assertEqual((target / 'existing.txt').read_text(), 'preserve')

    def test_cloud_process_failure_does_not_report_connected(self):
        item = {**ITEM, 'kind':'Google Drive', 'source':'account', 'target':str(self.state / 'mount')}
        process = Mock(); process.poll.return_value = 1
        with patch.object(desktop, 'WINDOWS', False), patch.object(desktop.cloud_setup, 'existing_accounts', return_value=[('account','Google Drive')]), patch.object(desktop.subprocess, 'Popen', return_value=process):
            with self.assertRaises(RuntimeError): self.service.mount(item)
        self.assertEqual(self.service.mounts, {})

    def test_cloud_status_requires_mountpoint_not_directory(self):
        item = {**ITEM, 'kind':'Google Drive', 'source':'account', 'target':str(self.state / 'mount')}
        self.service.save_items([item]); process = Mock(); process.poll.return_value = None
        self.service.mounts[desktop.resource_key(item)] = {'process':process,'target':item['target']}
        with patch.object(desktop.network, 'connected_folders', return_value=[]), patch.object(self.service, 'is_mounted', return_value=False):
            self.assertEqual(self.service.refresh()[0]['status'], 'Disconnected')

    def test_shutdown_refuses_active_cloud_mounts(self):
        self.service.mounts[('Google Drive','account')] = {}
        with self.assertRaises(RuntimeError): self.service.call('shutdown', {})

    def test_cancellation_removes_only_this_cloud_session(self):
        session = Mock(); session.process = None; self.service.sessions['unique'] = session
        self.service.call('cloud_cancel', {'session':'unique'})
        session.cancel.assert_called_once(); session.cleanup.assert_called_once_with(force=True)
        self.assertNotIn('unique', self.service.sessions)

    def test_terminal_arguments_are_quoted_for_mate(self):
        with patch.object(desktop.shutil, 'which', side_effect=lambda name: name if name == 'mate-terminal' else None):
            result = desktop.terminal_command(['python3', 'folder_share.py', "/home/test/John's Photos"])
        import shlex
        self.assertEqual(shlex.split(result[-1]), ['python3','folder_share.py',"/home/test/John's Photos"])

    def test_normalization_handles_spaces_and_unc(self):
        with patch.object(desktop, 'WINDOWS', False):
            self.assertEqual(desktop.normalize_source('\\\\server\\Family Photos'), 'smb://server/Family%20Photos')
        for invalid in ['server', 'smb://server/', 'smb://user:password@server/photos']:
            with self.assertRaises(ValueError): desktop.normalize_source(invalid)


if __name__ == '__main__': unittest.main()

class CloudUploadProtectionTests(unittest.TestCase):
    def test_disconnect_keeps_process_alive_while_uploads_pending(self):
        service = desktop.DesktopService()
        item = {**ITEM, 'kind':'Google Drive', 'source':'account'}
        process = Mock(); process.poll.return_value = None
        service.mounts[desktop.resource_key(item)] = {'process':process,'target':'/tmp/cloud'}
        with patch.object(service, 'uploads_pending', return_value=True):
            with self.assertRaisesRegex(RuntimeError, 'uploads are pending'): service.unmount(item)
        process.terminate.assert_not_called()
        self.assertIn(desktop.resource_key(item), service.mounts)

class CloudStatsTests(unittest.TestCase):
    def test_queued_uploads_block_disconnect(self):
        service = desktop.DesktopService(); process = Mock(); process.poll.return_value = None
        response = Mock(); response.read.return_value = json.dumps({'inUse':0,'diskCache':{'uploadsQueued':1,'uploadsInProgress':0,'erroredFiles':0}}).encode()
        context = Mock(); context.__enter__ = Mock(return_value=response); context.__exit__ = Mock(return_value=False)
        with patch.object(desktop,'urlopen',return_value=context):
            self.assertTrue(service.uploads_pending({'process':process,'rc_port':12345,'rc_password':'test-secret'}))

    def test_unavailable_stats_do_not_allow_disconnect(self):
        service = desktop.DesktopService(); process = Mock(); process.poll.return_value = None
        with patch.object(desktop,'urlopen',side_effect=OSError('unreachable')):
            with self.assertRaisesRegex(RuntimeError,'pending cloud uploads'):
                service.uploads_pending({'process':process,'rc_port':12345,'rc_password':'test-secret'})

class EarlyScanCancellationTests(unittest.TestCase):
    def test_cancel_before_scan_starts_is_retained(self):
        service = desktop.DesktopService(); service.call('stop_scan',{'scanId':'early'})
        with patch.object(desktop.network,'local_networks',return_value=[]), patch.object(desktop.network,'scan') as scan:
            result=service.scan('early')
        self.assertTrue(scan.call_args.args[1].is_set())
        self.assertTrue(result['cancelled'])

class UpdatePreferenceTests(unittest.TestCase):
    def test_startup_check_respects_existing_opt_out(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desktop,'STATE',Path(directory)):
            (Path(directory)/'update-check.json').write_text('{"automatic":false}')
            service=desktop.DesktopService()
            import native_updates
            with patch.object(native_updates,'check') as check:
                self.assertIsNone(service.call('startup_update',{}));check.assert_not_called()

    def test_offline_startup_check_is_quiet(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(desktop,'STATE',Path(directory)):
            import native_updates
            with patch.object(native_updates,'check',side_effect=RuntimeError('offline')):
                self.assertIsNone(desktop.DesktopService().call('startup_update',{}))

class LocalSharesTests(unittest.TestCase):
    def test_linux_inventory_includes_hidden_disabled_and_file_manager_shares(self):
        config = '[global]\nusershare max shares = 100\n[Hidden$]\npath = /mnt/data\nbrowseable = no\n[Disabled]\npath = /srv/off\navailable = no\n[printers]\npath = /spool\nprintable = yes\n'
        users = '[Photos]\npath=/home/test/Photos\nusershare_acl=Everyone:R,\n'
        with patch.object(desktop, 'WINDOWS', False), patch('sharing_setup.tool', return_value='/usr/bin/tool'), patch('sharing_setup.execute', side_effect=[Mock(returncode=0, stdout=config), Mock(returncode=0, stdout=users)]) as run:
            result = desktop.DesktopService().call('local_shares', {})
        self.assertEqual([x['name'] for x in result['shares']], ['Disabled', 'Hidden$', 'Photos'])
        self.assertFalse(result['shares'][0]['available'])
        self.assertTrue(result['shares'][1]['hidden'])
        self.assertEqual(result['shares'][2]['path'], '/home/test/Photos')
        self.assertEqual(run.call_args_list[1].args[0], ['net', 'usershare', 'info', '--long'])

    def test_failed_inventory_is_not_empty_success(self):
        with patch.object(desktop, 'WINDOWS', False), patch('sharing_setup.tool', return_value='/usr/bin/tool'), patch('sharing_setup.execute', return_value=Mock(returncode=1, stdout='')):
            with self.assertRaisesRegex(RuntimeError, 'could not be read'):
                desktop.DesktopService().local_shares()

    def test_windows_inventory_reads_local_folders_not_mapped_drives(self):
        with patch.object(desktop, 'WINDOWS', True), patch.object(desktop.subprocess, 'run', return_value=Mock(returncode=0, stdout='[{"Name":"Media","Path":"D:\\\\Media"}]')) as run:
            result = desktop.DesktopService().local_shares()
        self.assertEqual(result['shares'][0]['name'], 'Media')
        self.assertIn('Get-SmbShare', run.call_args.args[0][-1])
