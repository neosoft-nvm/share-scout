from pathlib import Path
from types import SimpleNamespace
import os,tempfile,unittest
from unittest.mock import patch
import sharing_permissions as permissions
import folder_share


class FusePermissionTests(unittest.TestCase):
    def test_fresh_install_detects_fuse_without_changing_policy(self):
        def run(args,**kwargs):
            output={'getenforce':'Enforcing\n','findmnt':'fuseblk\n','getsebool':'samba_share_fusefs --> off\n'}[args[0]]
            return SimpleNamespace(returncode=0,stdout=output)
        with patch.object(permissions,'tool',return_value='/usr/bin/tool'), patch.object(permissions,'configured_paths',return_value=['/mnt/games']), patch.object(permissions,'run',side_effect=run) as execute:
            result=permissions.status()
            self.assertTrue(result['applicable']);self.assertFalse(result['enabled'])
            self.assertEqual(result['paths'],['/mnt/games'])
            self.assertFalse(any(x.args[0][0]=='setsebool' for x in execute.call_args_list))

    def test_non_fuse_folders_do_not_trigger_fuse_permission(self):
        with patch.object(permissions,'run',return_value=SimpleNamespace(returncode=0,stdout='ext4\n')):
            self.assertFalse(permissions.is_fuse('/home/user/Videos'))

    def test_root_approval_required(self):
        with patch.object(permissions.os,'geteuid',return_value=1000), patch.object(permissions,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'approval'):permissions.enable(None,1000)
            run.assert_not_called()

    def test_enable_changes_only_named_permission_and_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);owner=folder.stat().st_uid
            info={'applicable':True,'enabled':False,'paths':[str(folder)]}
            with patch.object(permissions.os,'geteuid',return_value=0), patch('pwd.getpwuid',return_value=SimpleNamespace(pw_dir=directory)), patch.object(permissions,'status',side_effect=[info,{**info,'enabled':True}]), patch.object(permissions,'run') as run:
                result=permissions.enable(None,owner)
                self.assertTrue(result['ok'])
                run.assert_called_once_with(['setsebool','-P','samba_share_fusefs','on'])

    def test_failed_readback_restores_original_disabled_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);info={'applicable':True,'enabled':False,'paths':[str(folder)]}
            with patch.object(permissions.os,'geteuid',return_value=0), patch('pwd.getpwuid',return_value=SimpleNamespace(pw_dir=directory)), patch.object(permissions,'status',return_value=info), patch.object(permissions,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'verified'):permissions.enable(None,folder.stat().st_uid)
                self.assertEqual([x.args[0][-1] for x in run.call_args_list],['on','off'])

    def test_repair_of_another_users_share_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);info={'applicable':True,'enabled':False,'paths':[str(folder)]}
            with patch.object(permissions.os,'geteuid',return_value=0), patch('pwd.getpwuid',return_value=SimpleNamespace(pw_dir=directory)), patch.object(permissions,'status',return_value=info), patch.object(permissions,'run') as run:
                with self.assertRaisesRegex(RuntimeError,'owned'):permissions.enable(None,folder.stat().st_uid+1)
                run.assert_not_called()

    def test_admin_entrypoint_requires_explicit_confirmation(self):
        with patch.object(permissions.sys,'argv',['sharing_permissions.py','--admin']), patch.object(permissions.sys,'stdin',__import__('io').StringIO('{"confirmed":false}')), patch.object(permissions,'enable') as enable, patch('builtins.print'):
            self.assertEqual(permissions.main(),1);enable.assert_not_called()

    def test_sharing_fuse_folder_requires_consent_and_does_not_relabel(self):
        user=SimpleNamespace(pw_dir='/home/test')
        info={'applicable':True,'enabled':False,'paths':['/mnt/games']}
        with patch.object(folder_share.setup,'tool',return_value='tool'), patch.object(folder_share.setup,'execute',return_value=SimpleNamespace(stdout='Enforcing')), patch.object(folder_share.sharing_permissions,'status',return_value=info), patch('builtins.input',return_value='no'), patch.object(folder_share.setup,'label_folder') as label:
            with self.assertRaisesRegex(RuntimeError,'No share was created'):folder_share.prepare_selinux(Path('/mnt/games'),user)
            label.assert_not_called()

    def test_sharing_fuse_folder_applies_confirmed_policy_instead_of_relabel(self):
        user=SimpleNamespace(pw_dir='/home/test');info={'applicable':True,'enabled':False,'paths':['/mnt/games']}
        with patch.object(folder_share.setup,'tool',return_value='tool'), patch.object(folder_share.setup,'execute',return_value=SimpleNamespace(stdout='Enforcing')) as execute, patch.object(folder_share.sharing_permissions,'status',side_effect=[info,{**info,'enabled':True}]), patch('builtins.input',return_value='yes'), patch.object(folder_share.setup,'label_folder') as label:
            folder_share.prepare_selinux(Path('/mnt/games'),user)
            self.assertIn(['sudo','setsebool','-P','samba_share_fusefs','on'],[x.args[0] for x in execute.call_args_list])
            label.assert_not_called()
