import base64
import io
import json
from pathlib import Path
import sys
import unittest
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


if __name__ == '__main__': unittest.main()
