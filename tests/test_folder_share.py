import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1]))
import folder_share as share


class FolderShareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve(); self.folder = self.home / 'Family Photos'; self.folder.mkdir()
        self.user = SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid(), pw_name='kid', pw_dir=str(self.home))
        self.config = self.home / 'etc/smb.conf'; self.config.parent.mkdir()
        self.config.write_text('[global]\nsecurity = user\n[Existing]\npath = /srv/existing\n')

    def command(self, args, **kwargs):
        if args[0] == 'testparm': return SimpleNamespace(returncode=0, stdout=Path(args[-1]).read_text(), stderr='')
        return SimpleNamespace(returncode=0, stdout='', stderr='')

    def apply(self, name='Photos', writable=False):
        user = SimpleNamespace(**{**vars(self.user), 'pw_uid': 1000})
        with patch('pwd.getpwnam', return_value=user), patch.object(share.os, 'geteuid', return_value=0), patch.dict(os.environ, SUDO_USER='kid'), patch.object(share, 'validate_folder', return_value=self.folder), patch.object(share.setup, 'CONFIG_PATH', self.config), patch.object(share.setup, 'execute', side_effect=self.command), patch.object(share.setup, 'tool', return_value=None):
            return share.apply_custom('kid', str(self.folder), name, writable)

    def test_owned_folder_spaces_and_home_creation_parent(self):
        self.assertEqual(share.validate_folder(str(self.folder), self.user), self.folder)
        self.assertEqual(share.validate_folder(str(self.home), self.user, allow_home=True), self.home)
        with self.assertRaises(ValueError): share.validate_folder(str(self.home), self.user)

    def test_symlink_hidden_settings_unowned_and_macro_paths_rejected(self):
        link = self.home / 'Link'; link.symlink_to(self.folder)
        hidden = self.home / '.ssh'; hidden.mkdir()
        percent = self.home / 'percent%U'; percent.mkdir()
        for folder in [link, hidden, percent, Path('/etc')]:
            with self.subTest(folder=folder), self.assertRaises(ValueError): share.validate_folder(str(folder), self.user)
        user = SimpleNamespace(**{**vars(self.user), 'pw_uid': os.getuid() + 1})
        with self.assertRaises(ValueError): share.validate_folder(str(self.folder), user)

    def test_share_name_injection_and_reserved_names_rejected(self):
        for name in ['global', 'Homes', 'IPC', 'x]\nguest ok = yes', 'a/b', 'x%U', '', 'x'*65]:
            with self.subTest(name=name), self.assertRaises(ValueError): share.validate_name(name)

    def test_readonly_default_and_no_guest_or_symlinks(self):
        section = share.custom_section(self.user, self.folder, 'Photos')
        self.assertIn('read only = yes', section); self.assertIn('guest ok = no', section)
        self.assertIn('valid users = kid', section); self.assertIn('follow symlinks = no', section)
        self.assertIn('read only = no', share.custom_section(self.user, self.folder, 'Photos', True))

    def test_preserves_existing_config_backups_and_folder_permissions(self):
        original = self.config.read_text(); mode = self.folder.stat().st_mode
        self.apply()
        self.assertTrue(self.config.read_text().startswith(original))
        self.assertIn('[Photos]', self.config.read_text())
        self.assertEqual(self.folder.stat().st_mode, mode)
        backups = list(self.config.parent.glob('*.bak')); self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), original)

    def test_duplicate_name_rejected_without_overwrite(self):
        original = self.config.read_text()
        with self.assertRaises(ValueError): self.apply('existing')
        self.assertEqual(self.config.read_text(), original)

    def test_disabled_usershares_do_not_block_custom_share(self):
        self.apply()
        self.assertIn('[Photos]', self.config.read_text())

    def test_enabled_usershare_name_conflict_does_not_change_config(self):
        self.config.write_text('[global]\nusershare max shares = 100\n')
        original = self.config.read_text()
        original_command = self.command
        def commands(args, **kwargs):
            if args[0] == 'net': return SimpleNamespace(returncode=0, stdout='photos\n', stderr='')
            return original_command(args, **kwargs)
        with patch.object(self, 'command', side_effect=commands), self.assertRaises(ValueError): self.apply()
        self.assertEqual(self.config.read_text(), original)

    def test_invalid_staged_configuration_does_not_replace_original(self):
        original = self.config.read_text()
        def invalid(args, **kwargs):
            if args[0] == 'testparm' and Path(args[-1]) != self.config: raise RuntimeError('Invalid staged config')
            return self.command(args, **kwargs)
        with patch.object(self, 'command', side_effect=invalid), self.assertRaises(RuntimeError): self.apply()
        self.assertEqual(self.config.read_text(), original)
        self.assertFalse(list(self.config.parent.glob('.sharescout-*')))

    def test_privileged_helper_requires_requesting_account(self):
        user = SimpleNamespace(**{**vars(self.user), 'pw_uid': 1000})
        with patch('pwd.getpwnam', return_value=user), patch.object(share.os, 'geteuid', return_value=0), patch.dict(os.environ, SUDO_USER='someoneelse'), self.assertRaises(ValueError):
            share.apply_custom('kid', str(self.folder), 'Photos')

    def test_script_selection_is_literal_single_local_folder(self):
        path = '/home/kid/Photos $(touch nope)'
        self.assertEqual(share.selected_folder([path], {}), path)
        self.assertEqual(share.selected_folder(['--from-file-manager'], {'NAUTILUS_SCRIPT_SELECTED_FILE_PATHS':path+'\n'}), path)
        for paths in [['/one', '/two'], ['smb://server/share'], ['relative']]:
            with self.assertRaises(ValueError): share.selected_folder(paths, {})

    def test_cli_dispatches_all_arguments_and_access_mode(self):
        with patch.object(sys, 'argv', ['folder_share.py', '--apply-custom', 'kid', str(self.folder), 'Photos', 'write']), patch.object(share, 'apply_custom') as apply:
            share.main(); apply.assert_called_once_with('kid', str(self.folder), 'Photos', writable=True)

    def test_selinux_home_policy_decline_makes_no_change(self):
        def execute(args, **kwargs): return SimpleNamespace(stdout='Enforcing' if args[0]=='getenforce' else 'samba_enable_home_dirs --> off')
        with patch.object(share.setup, 'tool', return_value='/mock/tool'), patch.object(share.setup, 'execute', side_effect=execute) as run, patch('builtins.input', return_value='no'), self.assertRaises(RuntimeError):
            share.prepare_selinux(self.folder, self.user)
        self.assertFalse(any(call.args[0][0] == 'sudo' for call in run.call_args_list))

    def test_existing_password_preserved_and_end_to_end_configuration(self):
        states = [dict(installed=True, shares=['Existing'], error=None, ready=True), dict(installed=True, shares=['Existing','Photos'], error=None, ready=True)]
        def execute(args, **kwargs):
            if 'pdbedit' in args: return SimpleNamespace(returncode=0, stdout='kid:1000:Kid\n')
            if args[0] == 'ip': return SimpleNamespace(stdout=json.dumps([{'addr_info':[{'family':'inet','scope':'global','local':'192.168.1.7'}]}]))
            return SimpleNamespace(returncode=0, stdout='')
        status = self.home / 'result.json'
        with patch.object(share.setup, 'identity', return_value=self.user), patch.object(share.setup, 'primary_network', return_value=('wlan0','192.168.1.0/24')), patch.object(share.setup, 'inspect', side_effect=states), patch.object(share.setup, 'tool', return_value='/mock/tool'), patch.object(share, 'prepare_selinux'), patch.object(share.setup, 'configure_firewall') as firewall, patch.object(share.setup, 'execute', side_effect=execute) as run:
            share.configure_folder(status, str(self.folder), 'Photos')
        self.assertFalse(any('smbpasswd' in call.args[0] for call in run.call_args_list))
        self.assertTrue(any('--apply-custom' in call.args[0] for call in run.call_args_list))
        firewall.assert_called_once_with('wlan0', '192.168.1.0/24')
        self.assertEqual(json.loads(status.read_text())['address'], '192.168.1.7')


if __name__ == '__main__': unittest.main()
