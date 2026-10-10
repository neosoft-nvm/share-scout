import base64
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import shutil
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).parents[1]))
import updates


class UpdateTests(unittest.TestCase):
    def response(self, version):
        return io.BytesIO(json.dumps({'encoding':'base64','content':base64.b64encode(f"VERSION = '{version}'\n".encode()).decode()}).encode())

    def test_semantic_numeric_comparison(self):
        self.assertGreater(updates.version_tuple('0.10.0'), updates.version_tuple('0.9.9'))

    def test_newer_same_and_older_versions(self):
        for remote, newer in [('0.4.4',True),('0.4.3',False),('0.4.2',False)]:
            with patch.object(updates, 'urlopen', return_value=self.response(remote)) as request:
                result = updates.check('0.4.3')
            self.assertEqual(result['newer'],newer)
            self.assertEqual(result['latest'],remote)
            self.assertEqual(request.call_args.kwargs['timeout'],8)

    def test_downloaded_python_is_not_executed(self):
        source = "raise RuntimeError('must not run')\nVERSION='1.2.3'"
        self.assertEqual(updates.source_version(source),'1.2.3')
        with self.assertRaises(ValueError): updates.source_version("VERSION=__import__('os').getcwd()")

    def test_invalid_version_and_missing_version_rejected(self):
        for source in ["VERSION='latest'", "NAME='ShareScout'", "VERSION=4"]:
            with self.assertRaises(ValueError): updates.source_version(source)

    def test_offline_failure_is_not_reported_as_up_to_date(self):
        with patch.object(updates,'urlopen',side_effect=TimeoutError('offline')), self.assertRaisesRegex(RuntimeError,'Could not check GitHub'):
            updates.check()

    def test_large_or_malformed_response_is_reported(self):
        for payload in [b'x'*65537,b'not json',b'{"encoding":"unknown"}']:
            with patch.object(updates,'urlopen',return_value=io.BytesIO(payload)), self.assertRaises(RuntimeError): updates.check()

    def test_update_archive_is_version_checked_and_staged_without_extracting_other_paths(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('share-scout-main/app_info.py', "VERSION = '0.5.2'\n")
            for name in ('resource_mapper.py', 'updates.py', 'apply_update.py'):
                archive.writestr('share-scout-main/' + name, '# test source\n')
            archive.writestr('share-scout-main/sharescout.png', b'icon')
            archive.writestr('share-scout-main/../../outside.py', 'must not escape')
            archive.writestr('share-scout-main/tests/ignored.py', 'not installed')
        with tempfile.TemporaryDirectory() as parent, \
                patch.object(updates, 'install_root', return_value=Path(parent) / 'ResourceMapper'), \
                patch.object(updates, 'urlopen', return_value=io.BytesIO(payload.getvalue())):
            stage = updates.stage_update('0.5.2')
            self.addCleanup(shutil.rmtree, stage, ignore_errors=True)
            self.assertTrue((stage / 'resource_mapper.py').is_file())
            self.assertTrue((stage / 'sharescout.png').is_file())
            self.assertFalse((Path(parent) / 'outside.py').exists())
            self.assertFalse((stage / 'ignored.py').exists())

    def test_update_archive_version_must_match_checked_version(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            for name, data in {
                'app_info.py': "VERSION = '0.5.3'\n",
                'resource_mapper.py': '', 'updates.py': '', 'apply_update.py': '',
            }.items():
                archive.writestr('share-scout-main/' + name, data)
        with tempfile.TemporaryDirectory() as parent, \
                patch.object(updates, 'install_root', return_value=Path(parent) / 'ResourceMapper'), \
                patch.object(updates, 'urlopen', return_value=io.BytesIO(payload.getvalue())):
            with self.assertRaisesRegex(RuntimeError, 'changed during download'):
                updates.stage_update('0.5.2')

    def test_update_archive_is_version_checked_and_staged_without_extracting_other_paths(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            archive.writestr('share-scout-main/app_info.py', "VERSION = '0.5.2'\n")
            for name in ('resource_mapper.py', 'updates.py', 'apply_update.py'):
                archive.writestr('share-scout-main/' + name, '# safe test source\n')
            archive.writestr('share-scout-main/sharescout.png', b'icon')
            archive.writestr('share-scout-main/../../outside.py', 'must not escape')
            archive.writestr('share-scout-main/tests/ignored.py', 'not installed')
        with tempfile.TemporaryDirectory() as parent, patch.object(updates, 'install_root', return_value=Path(parent) / 'ResourceMapper'), patch.object(updates, 'urlopen', return_value=io.BytesIO(payload.getvalue())):
            stage = updates.stage_update('0.5.2')
            self.addCleanup(__import__('shutil').rmtree, stage, ignore_errors=True)
            self.assertTrue((stage / 'resource_mapper.py').is_file())
            self.assertTrue((stage / 'sharescout.png').is_file())
            self.assertFalse((Path(parent) / 'outside.py').exists())
            self.assertFalse((stage / 'ignored.py').exists())

    def test_update_archive_version_must_match_checked_version(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as archive:
            for name, data in {
                'app_info.py': "VERSION = '0.5.3'\n",
                'resource_mapper.py': '', 'updates.py': '', 'apply_update.py': '',
            }.items():
                archive.writestr('share-scout-main/' + name, data)
        with tempfile.TemporaryDirectory() as parent, patch.object(updates, 'install_root', return_value=Path(parent) / 'ResourceMapper'), patch.object(updates, 'urlopen', return_value=io.BytesIO(payload.getvalue())):
            with self.assertRaisesRegex(RuntimeError, 'changed during download'):
                updates.stage_update('0.5.2')


if __name__ == '__main__': unittest.main()
