import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import credentials


class CredentialStoreTests(unittest.TestCase):
    @patch('credentials.subprocess.run')
    def test_save_keeps_secret_out_of_arguments_and_loads_from_keyring(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='')
        value = {'username': 'family', 'password': 'not-in-arguments', 'domain': ''}
        credentials.save('192.168.1.20', value)
        args, kwargs = run.call_args
        self.assertEqual(args[0][:3], ['secret-tool', 'store', '--label=ShareScout network sign-in'])
        self.assertNotIn(value['password'], args[0])
        self.assertEqual(json.loads(kwargs['input']), value)

        run.return_value = SimpleNamespace(returncode=0, stdout=json.dumps(value))
        self.assertEqual(credentials.load('192.168.1.20'), value)
        self.assertEqual(run.call_args.args[0], ['secret-tool', 'lookup', 'application', 'ShareScout', 'server', '192.168.1.20'])

    @patch('credentials.subprocess.run')
    def test_missing_keyring_entry_is_not_an_error(self, run):
        run.return_value = SimpleNamespace(returncode=1, stdout='')
        self.assertIsNone(credentials.load('192.168.1.20'))

    @patch('credentials.subprocess.run')
    def test_delete_targets_only_the_selected_server_entry(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout='')
        credentials.delete('192.168.1.20')
        self.assertEqual(run.call_args.args[0], ['secret-tool', 'clear', 'application', 'ShareScout', 'server', '192.168.1.20'])

    @patch('credentials.subprocess.run', side_effect=FileNotFoundError)
    def test_missing_keyring_tool_explains_how_to_enable_remember(self, _run):
        with self.assertRaisesRegex(RuntimeError, 'system password store is unavailable'):
            credentials.save('192.168.1.20', {'username': 'family', 'password': 'secret'})


if __name__ == '__main__':
    unittest.main()
