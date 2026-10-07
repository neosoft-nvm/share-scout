from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1]))
import file_manager


class FileManagerTests(unittest.TestCase):
    def test_install_idempotent_preserves_thunar_actions_and_xdg_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder); data = home/'data'; config = home/'config'; app = home/'app with spaces'
            custom = config/'Thunar/uca.xml'; custom.parent.mkdir(parents=True)
            custom.write_text('<actions><action><name>Existing action</name><command>existing %f</command></action></actions>')
            env = {'XDG_DATA_HOME':str(data), 'XDG_CONFIG_HOME':str(config)}
            result = file_manager.install(app, home, env); self.assertFalse(result['errors'])
            first = custom.read_bytes(); file_manager.install(app, home, env)
            self.assertEqual(custom.read_bytes(), first)
            self.assertEqual(len(list(custom.parent.glob('*.bak'))), 1)
            actions = ET.parse(custom).getroot().findall('action')
            self.assertEqual(len(actions), 2); self.assertEqual(actions[0].findtext('name'), 'Existing action')
            for path in ['kio/servicemenus/sharescout.desktop', 'kservices5/ServiceMenus/sharescout.desktop', 'nautilus/scripts/Share with ShareScout', 'caja/scripts/Share with ShareScout', 'nemo/actions/sharescout.nemo_action', 'applications/sharescout-share.desktop']:
                self.assertTrue((data/path).exists(), path)
            self.assertTrue(os.access(data/'kio/servicemenus/sharescout.desktop', os.X_OK))

    def test_malformed_thunar_actions_kept_and_other_actions_still_installed(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder); path=home/'.config/Thunar/uca.xml'; path.parent.mkdir(parents=True); path.write_text('broken xml')
            result=file_manager.install(home/'app',home,{})
            self.assertEqual(path.read_text(),'broken xml'); self.assertTrue(result['errors'])
            self.assertIn('Dolphin', result['installed'])

    def test_launcher_passes_metacharacters_as_literal_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder); app=home/'app $ strange'; app.mkdir()
            (app/'folder_share.py').write_text('import sys,json\nprint(json.dumps(sys.argv[1:]))\n')
            file_manager.install(app,home,{})
            selected = str(home/'Photos $(touch BAD)')
            result=subprocess.check_output([str(home/'.local/share/sharescout/share-folder'), selected],text=True)
            import json
            self.assertEqual(json.loads(result),[selected]); self.assertFalse((home/'BAD').exists())


if __name__ == '__main__': unittest.main()
