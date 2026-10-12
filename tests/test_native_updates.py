import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import native_updates as updates


class NativeUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'release.zip'; self.dest = self.root / 'candidate'

    def write_archive(self, extra=None, version='0.6.0'):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name in ['share-scout','sharescout.png'] + ['backend/' + name + '.py' for name in updates.BACKEND_FILES]:
                archive.writestr(name, 'test')
            archive.writestr('release.json', json.dumps({'version':version, 'platform':'linux'}))
            if extra: archive.writestr(*extra)

    def test_valid_release_extracts_and_sets_execute_bit(self):
        self.write_archive()
        with patch.object(updates, 'WINDOWS', False): updates.extract_verified(self.archive, self.dest, '0.6.0')
        self.assertTrue((self.dest / 'share-scout').stat().st_mode & 0o100)

    def test_rejects_traversal_before_extracting(self):
        self.write_archive(('../escape.txt','danger'))
        with patch.object(updates, 'WINDOWS', False):
            with self.assertRaises(ValueError): updates.extract_verified(self.archive,self.dest,'0.6.0')
        self.assertFalse(self.dest.exists())

    def test_rejects_wrong_release(self):
        self.write_archive(version='0.7.0')
        with patch.object(updates, 'WINDOWS', False):
            with self.assertRaises(ValueError): updates.extract_verified(self.archive,self.dest,'0.6.0')

    def test_rejects_symlinks(self):
        self.write_archive()
        entry = zipfile.ZipInfo('link'); entry.external_attr = (0o120777 << 16)
        with zipfile.ZipFile(self.archive,'a') as archive: archive.writestr(entry,'/etc/passwd')
        with patch.object(updates, 'WINDOWS', False):
            with self.assertRaises(ValueError): updates.extract_verified(self.archive,self.dest,'0.6.0')

    def test_rejects_unrecognized_stage(self):
        with patch.object(updates, 'install_root', return_value=self.root/'installed'):
            with self.assertRaises(ValueError): updates.apply(self.root/'untrusted')

    def test_failed_install_restores_previous_runtime(self):
        installed = self.root/'installed'; installed.mkdir(); (installed/'original').write_text('keep')
        stage = self.root/'sharescout-native-update-test'; candidate = stage/'candidate'; candidate.mkdir(parents=True)
        (candidate/'release.json').write_text('{}')
        with patch.object(updates, 'install_root', return_value=installed), patch.object(updates.Path, 'home', return_value=self.root), patch.object(updates,'launcher',side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError): updates.apply(stage)
        self.assertEqual((installed/'original').read_text(),'keep')

class UpdateDigestTests(unittest.TestCase):
    def test_bad_digest_leaves_installation_untouched(self):
        import io
        with tempfile.TemporaryDirectory() as directory:
            installed=Path(directory)/'installed'; installed.mkdir(); (installed/'original').write_text('keep')
            result={'latest':'0.7.0','newer':True,'canInstall':True,'asset':{'browser_download_url':'https://github.com/neosoft-nvm/share-scout/releases/download/v0.7.0/runtime.zip','digest':'sha256:'+'0'*64}}
            with patch.object(updates,'check',return_value=result), patch.object(updates,'install_root',return_value=installed), patch.object(updates,'urlopen',return_value=io.BytesIO(b'corrupt download')):
                with self.assertRaisesRegex(ValueError,'verification failed'):updates.stage('0.7.0')
            self.assertEqual((installed/'original').read_text(),'keep')
            self.assertEqual(list(Path(directory).glob('sharescout-native-update-*')),[])
