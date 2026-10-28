import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import permanent_mounts as mounts

AUTH = {'username': 'sharing-user', 'password': 'a private password', 'domain': ''}
SOURCE = 'smb://192.168.1.50/Family%20Photos'


class MountInputTests(unittest.TestCase):
    def test_source_rejects_credentials_subfolders_and_unit_injection(self):
        for value in ('smb://user:secret@server/photos', 'smb://server/photos/other',
                      'smb://server/photos%0AOptions=rw', 'smb://server/%25n', 'smb://server/../', 'file:///etc/passwd'):
            with self.subTest(value=value), self.assertRaises(ValueError): mounts.source_parts(value)
        self.assertEqual(mounts.source_parts(SOURCE), ('192.168.1.50', 'Family Photos'))

    def test_target_is_limited_to_direct_managed_children(self):
        for target in ('/etc', '/mnt/sharescout/../etc', '/mnt/sharescout/photos/sub', '/mnt/sharescout/foo\nbar'):
            with self.subTest(target=target), self.assertRaises(ValueError): mounts.validate_target(target)

    def test_symlink_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); (root/'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(RuntimeError): mounts.secure_directory(root/'link')

    def test_credential_and_metadata_modes_do_not_depend_on_umask(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.umask(0o077)
            try:
                secret = Path(directory)/'secret'
                record = Path(directory)/'record'
                mounts.create_file(secret, 'private', 0o600)
                mounts.create_file(record, 'public metadata', 0o644)
            finally:
                os.umask(previous)
            self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
            self.assertEqual(record.stat().st_mode & 0o777, 0o644)

    def test_admin_request_carries_password_only_on_stdin(self):
        with patch.object(mounts, 'supported', return_value=True), patch.object(mounts.shutil, 'which', return_value='/usr/bin/pkexec'), patch.object(mounts.subprocess, 'run') as run:
            run.return_value = SimpleNamespace(returncode=0, stdout='{"ok": true}')
            mounts.invoke({'credentials': AUTH})
            args, kwargs = run.call_args
            self.assertNotIn(AUTH['password'], str(args))
            self.assertIn(AUTH['password'], kwargs['input'])
            self.assertIn('-I', args[0])

    def test_cancelled_admin_approval_is_not_success(self):
        with patch.object(mounts, 'supported', return_value=True), patch.object(mounts.shutil, 'which', return_value='pkexec'), patch.object(mounts.subprocess, 'run', return_value=SimpleNamespace(returncode=126, stdout='')):
            with self.assertRaisesRegex(RuntimeError, 'cancelled'): mounts.invoke({})


class ManagedMountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root/'mnt'/'Photos'
        self.state = self.root/'state'; self.units = self.root/'units'; self.units.mkdir()
        self.commands = []
        self.request = {'operation': 'create', 'source': SOURCE, 'target': str(self.target),
                        'account': 'plex', 'readOnly': True, 'credentials': AUTH}
        def directory(path): path.mkdir(parents=True, exist_ok=True)
        def run(args, **kwargs):
            self.commands.append(args)
            return SimpleNamespace(returncode=0, stdout='mnt-sharescout-Photos\n' if 'systemd-escape' in args[0] else '')
        patches = [patch.object(mounts, 'MOUNT_ROOT', self.root/'mnt'), patch.object(mounts, 'STATE_ROOT', self.state),
                   patch.object(mounts, 'UNIT_ROOT', self.units), patch.object(mounts, 'secure_directory', side_effect=directory),
                   patch.object(mounts, 'ensure_cifs'), patch.object(mounts, 'command', side_effect=run),
                   patch.object(mounts, 'tool', side_effect=lambda name: '/usr/bin/'+name),
                   patch.object(mounts, 'mounted', return_value=True),
                   patch('pwd.getpwnam', return_value=SimpleNamespace(pw_name='plex', pw_uid=997)),
                   patch('pwd.getpwuid', return_value=SimpleNamespace(pw_name='owner', pw_gid=1000)),
                   patch.object(mounts.subprocess, 'run', return_value=SimpleNamespace(returncode=0))]
        for p in patches: p.start(); self.addCleanup(p.stop)

    def test_success_protects_credentials_and_grants_only_selected_access(self):
        result = mounts.apply(self.request, 1000)
        password_file = self.state/(result['id']+'.credentials')
        self.assertEqual(password_file.stat().st_mode & 0o777, 0o600)
        self.assertIn('password='+AUTH['password'], password_file.read_text())
        metadata = (self.state/(result['id']+'.json')).read_text()
        self.assertNotIn('password', metadata)
        self.assertNotIn('sharing-user', metadata)
        unit = next(self.units.glob('*.mount')).read_text()
        self.assertIn('uid=997,gid=1000,forceuid,forcegid,nounix,file_mode=0440,dir_mode=0550', unit)
        self.assertIn('Options=ro,nosuid,nodev,noexec,', unit)
        self.assertIn('TimeoutSec=25', unit)
        self.assertIn('What=//192.168.1.50/Family Photos\n', unit)
        self.assertNotIn(AUTH['password'], unit)
        self.assertTrue(result['ok'])

    def test_existing_target_and_files_are_preserved(self):
        self.target.mkdir(parents=True); (self.target/'keep').write_text('original')
        with self.assertRaisesRegex(RuntimeError, 'already exists'): mounts.apply(self.request, 1000)
        self.assertEqual((self.target/'keep').read_text(), 'original')
        self.assertEqual(list(self.units.iterdir()), [])

    def test_failed_readback_rolls_back_units_and_credentials(self):
        mounts.mounted.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'not mounted'): mounts.apply(self.request, 1000)
        self.assertEqual(list(self.state.iterdir()), [])
        self.assertEqual(list(self.units.iterdir()), [])
        self.assertFalse(self.target.exists())

    def test_failed_service_access_rolls_back(self):
        mounts.mounted.side_effect = [True, False]
        mounts.subprocess.run.return_value.returncode = 1
        with self.assertRaisesRegex(RuntimeError, 'cannot read'): mounts.apply(self.request, 1000)
        self.assertEqual(list(self.units.iterdir()), [])
        self.assertEqual(list(self.state.iterdir()), [])

    def test_busy_rollback_preserves_configuration_for_recovery(self):
        mounts.subprocess.run.return_value.returncode = 1
        with self.assertRaisesRegex(RuntimeError, 'configuration was kept'): mounts.apply(self.request, 1000)
        self.assertEqual(len(list(self.units.glob('*.mount'))), 1)
        self.assertEqual(len(list(self.state.glob('*.json'))), 1)

    def test_remove_checks_owner_and_keeps_original_share(self):
        result = mounts.apply(self.request, 1000)
        mounts.mounted.return_value = False
        with patch.object(mounts, 'trusted_file', return_value=True):
            removed = mounts.apply({'operation':'remove', 'source':SOURCE}, 1000)
        self.assertTrue(removed['removed'])
        self.assertFalse(self.target.exists())
        self.assertEqual(list(self.units.iterdir()), [])
        self.assertEqual(list(self.state.iterdir()), [])

    def test_missing_credentials_do_not_create_mount(self):
        request = {**self.request, 'credentials': None}
        with self.assertRaisesRegex(ValueError, 'username and password'): mounts.apply(request, 1000)
        self.assertFalse(self.target.exists())

    def test_credential_line_injection_is_rejected(self):
        request = {**self.request, 'credentials': {**AUTH, 'password':'secret\nusername=someone'}}
        with self.assertRaises(ValueError): mounts.apply(request, 1000)
        self.assertFalse(self.target.exists())

class ServiceIntegrationTests(unittest.TestCase):
    def test_system_mounts_are_not_disconnected_as_desktop_mounts(self):
        import desktop_service as desktop
        with patch.object(desktop.network, 'command') as command:
            with self.assertRaisesRegex(RuntimeError, 'Permanent Mount'):
                desktop.DesktopService().unmount({'kind':'Network share','mountMode':'system'})
            command.assert_not_called()

    def test_missing_mount_record_never_falls_back_to_desktop_mount(self):
        import desktop_service as desktop
        item={'name':'Movies','source':'smb://server/Movies','kind':'Network share','mountMode':'system','auto':False}
        with patch.object(mounts,'records',return_value=[]), patch.object(desktop.network,'mount_share') as normal:
            with self.assertRaisesRegex(RuntimeError, 'no longer configured'): desktop.DesktopService().mount(item)
            normal.assert_not_called()

    def test_refresh_merges_managed_mount_and_preserves_system_mode(self):
        import desktop_service as desktop
        item={'name':'Movies','source':'smb://server/Movies','kind':'Network share','auto':True,'target':''}
        record={'source':item['source'],'target':'/mnt/sharescout/Movies','connected':True}
        service=desktop.DesktopService()
        with patch.object(service,'read_items',return_value=[item]), patch.object(desktop.network,'connected_folders',return_value=[]), patch.object(mounts,'records',return_value=[record]):
            result=service.refresh()
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['mountMode'],'system')
        self.assertFalse(result[0]['auto'])
        self.assertEqual(result[0]['status'],'Connected')
        self.assertEqual(desktop.validate_items(result)[0]['mountMode'],'system')

    def test_stale_system_mount_does_not_use_a_desktop_mount_with_same_source(self):
        import desktop_service as desktop
        item={'name':'Movies','source':'smb://server/Movies','kind':'Network share','mountMode':'system','status':'Disconnected'}
        service=desktop.DesktopService()
        with patch.object(service,'read_items',return_value=[item]), patch.object(desktop.network,'connected_folders',return_value=[{**item,'target':'/run/user/1000/gvfs','status':'Connected'}]), patch.object(mounts,'records',return_value=[]):
            self.assertEqual(service.refresh()[0]['status'],'Disconnected')

    def test_creation_uses_cached_credentials_without_persisting_them_in_settings(self):
        import desktop_service as desktop
        service=desktop.DesktopService()
        with patch.object(service,'get_auth',return_value=AUTH), patch.object(mounts,'invoke',return_value={'ok':True,'target':'/mnt/sharescout/Movies'}) as invoke, patch.object(service,'refresh',return_value=[]):
            result=service.call('permanent_apply',{'source':'smb://server/Movies','target':'/mnt/sharescout/Movies','account':'plex'})
            self.assertTrue(result['ok'])
            self.assertEqual(invoke.call_args.args[0]['credentials'],AUTH)
