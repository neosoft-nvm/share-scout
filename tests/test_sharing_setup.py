import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).parents[1]))
import sharing_setup as sharing


def result(output='', code=0): return SimpleNamespace(stdout=output, stderr='', returncode=code)

class SharingTests(unittest.TestCase):
    def test_only_visible_file_shares(self):
        config = '''[global]\nsecurity=user\n[Photos]\npath=/srv/photos\n[hidden]\npath=/srv/hidden\nbrowsable=no\n[disabled]\npath=/srv/off\navailable=no\n[printer]\npath=/var/spool\nprintable=yes\n[Admin$]\npath=/srv/admin\n[homes]\npath=/home/%S\n'''
        self.assertEqual(sharing.visible_shares(config), ['Photos'])

    def test_listener_must_accept_other_computers(self):
        self.assertFalse(sharing.reachable_listener('LISTEN 0 50 127.0.0.1:445 0.0.0.0:*\nLISTEN 0 50 [::1]:445 [::]:*'))
        for address in ['0.0.0.0', '*', '192.168.1.4']:
            self.assertTrue(sharing.reachable_listener(f'LISTEN 0 50 {address}:445 0.0.0.0:*'))

    def test_missing_server_offers_setup(self):
        with patch.object(sharing, 'tool', return_value=None), patch.object(sharing, 'execute', return_value=result()):
            state = sharing.inspect()
            self.assertFalse(state['ready']); self.assertFalse(state['installed'])

    def test_ready_requires_configured_share_and_listener(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'smb.conf'; config.write_text('[global]\n')
            with patch.object(sharing, 'CONFIG_PATH', config), patch.object(sharing, 'tool', return_value='/mock/tool'), patch.object(sharing, 'execute', side_effect=lambda args, **kwargs: result('[Photos]\npath=/srv/photos\n') if args[0]=='testparm' else result('LISTEN 0 50 0.0.0.0:445 0.0.0.0:*') if args[0]=='ss' else result()):
                self.assertTrue(sharing.inspect()['ready'])

    def test_config_errors_are_not_called_no_shares(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / 'smb.conf'; config.touch()
            with patch.object(sharing, 'CONFIG_PATH', config), patch.object(sharing, 'tool', return_value='/mock/tool'), patch.object(sharing, 'execute', side_effect=lambda args, **kwargs: (_ for _ in ()).throw(RuntimeError('invalid config')) if args[0]=='testparm' else result()):
                state = sharing.inspect(); self.assertIn('invalid config', state['error']); self.assertFalse(state['ready'])

    def test_file_manager_usershares_are_detected(self):
        with patch.object(sharing, 'tool', return_value='/mock/tool'), patch.object(sharing, 'CONFIG_PATH', Path('/nonexistent/smb.conf')), patch.object(sharing, 'execute', side_effect=lambda args, **kwargs: result('Public\nPhotos\n') if args[0]=='net' else result('LISTEN 0 50 0.0.0.0:445 0.0.0.0:*')):
            self.assertEqual(sharing.inspect()['shares'], ['Photos', 'Public'])

    def test_firewall_current_subnet_and_zone_only(self):
        commands = sharing.firewall_commands('wlan0', '192.168.1.0/24', 'firewalld', 'FedoraWorkstation')
        self.assertEqual(len(commands), 2)
        self.assertTrue(all('--zone=FedoraWorkstation' in command for command in commands))
        self.assertTrue(all('source address="192.168.1.0/24"' in command[-1] and 'port="445"' in command[-1] for command in commands))
        self.assertIn('--permanent', commands[1]); self.assertNotIn('--reload', str(commands))

    def test_ufw_scope(self):
        command = sharing.firewall_commands('wlan0', '192.168.1.0/24', 'ufw')[0]
        self.assertEqual(command, ['sudo', 'ufw', 'allow', 'from', '192.168.1.0/24', 'to', 'any', 'port', '445', 'proto', 'tcp'])

    def test_package_and_service_names(self):
        for manager, service in [('dnf', 'smb'), ('apt-get', 'smbd'), ('pacman', 'smb')]:
            with patch.object(sharing, 'tool', side_effect=lambda name: '/mock/' + name if name == manager else None):
                self.assertEqual(sharing.package_command()[1], manager)
                self.assertEqual(sharing.service_name(), service)

    def test_default_connection_subnet(self):
        routes = json.dumps([{'dev': 'wlan0', 'metric': 600}])
        addresses = json.dumps([{'addr_info': [{'family':'inet','scope':'global','local':'192.168.5.10','prefixlen':24}]}])
        with patch.object(sharing, 'execute', side_effect=[result(routes), result(addresses)]):
            self.assertEqual(sharing.primary_network(), ('wlan0', '192.168.5.0/24'))

    def test_no_route_does_not_change_sharing(self):
        with patch.object(sharing, 'execute', return_value=result('[]')):
            with self.assertRaises(RuntimeError): sharing.primary_network()

    def test_share_is_password_protected(self):
        section = sharing.share_section('kid', '/srv/share-scout/kid')
        self.assertIn('guest ok = no', section); self.assertIn('valid users = kid', section)
        for username in ['root\n[Injected]', '../kid', 'kid;cmd']:
            with self.assertRaises(ValueError): sharing.share_section(username, '/srv/share-scout/kid')

    def apply(self, directory, text, validate=None):
        config = Path(directory) / 'etc/smb.conf'; config.parent.mkdir(); config.write_text(text)
        root = Path(directory) / 'shared'
        user = SimpleNamespace(pw_uid=1000, pw_gid=1000)
        patches = [patch.object(sharing, 'CONFIG_PATH', config), patch.object(sharing, 'SHARE_ROOT', root),
                   patch.object(sharing.os, 'geteuid', return_value=0), patch.object(sharing.os, 'chown'),
                   patch('pwd.getpwnam', return_value=user), patch.object(sharing, 'execute', side_effect=validate or (lambda args: result(text)))]
        from contextlib import ExitStack
        with ExitStack() as stack:
            for p in patches: stack.enter_context(p)
            sharing.apply_share('kid')
        return config, root

    def test_add_share_preserves_original_and_creates_backup(self):
        original = '[global]\nsecurity=user\n[Photos]\npath=/srv/photos\n'
        with tempfile.TemporaryDirectory() as folder:
            config, root = self.apply(folder, original)
            self.assertIn('[Photos]', config.read_text()); self.assertIn('[ShareScout-kid]', config.read_text())
            backups = list(config.parent.glob('*.bak')); self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)
            self.assertEqual((root / 'kid').stat().st_mode & 0o777, 0o700)

    def test_bad_new_config_does_not_replace_original(self):
        original = '[global]\nsecurity=user\n'
        def validate(args):
            if '.sharescout-' in args[-1]: raise RuntimeError('Validation rejected the new config')
            return result(original)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError): self.apply(folder, original, validate)
            self.assertEqual(Path(folder, 'etc/smb.conf').read_text(), original)
            self.assertFalse(list(Path(folder, 'etc').glob('.sharescout-*')))

    def test_existing_named_share_not_overwritten(self):
        original = '[ShareScout-kid]\npath=/custom/folder\n'
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError): self.apply(folder, original)
            self.assertEqual(Path(folder, 'etc/smb.conf').read_text(), original)

    def test_existing_shares_repaired_without_password_or_new_share(self):
        state = {'installed':True,'shares':['Photos'],'error':None,'ready':True,'listening':True}
        user = SimpleNamespace(pw_name='kid', pw_dir='/tmp')
        with tempfile.TemporaryDirectory() as folder, patch.object(sharing, 'identity', return_value=user), patch.object(sharing, 'primary_network', return_value=('wlan0','192.168.1.0/24')), patch.object(sharing, 'inspect', return_value=state), patch.object(sharing, 'tool', return_value='/mock/tool'), patch.object(sharing, 'execute', return_value=result()) as execute, patch.object(sharing, 'configure_firewall') as firewall:
            sharing.configure(Path(folder) / 'status.json')
            calls = [call.args[0] for call in execute.call_args_list]
            self.assertFalse(any('smbpasswd' in command or '--apply' in command for command in calls))
            firewall.assert_called_once_with('wlan0','192.168.1.0/24')
            self.assertTrue(json.loads(Path(folder, 'status.json').read_text())['ok'])

if __name__ == '__main__': unittest.main()
