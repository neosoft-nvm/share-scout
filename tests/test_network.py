from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
import threading
import unittest
from unittest.mock import patch, Mock
import network

class DiscoveryTests(unittest.TestCase):
    def test_only_disk_shares_and_no_admin_shares(self):
        data = 'Disk|Family Photos|Shared photos\nIPC|IPC$|IPC\nDisk|C$|System\nPrinter|Office|Print\nDisk|Public|\n'
        self.assertEqual(network.parse_shares(data), [{'name': 'Family Photos', 'comment': 'Shared photos'}, {'name': 'Public', 'comment': ''}])

    def test_large_subnet_visible_bounded_range(self):
        ranges = network.scan_ranges([('127.0.0.1', 8), ('192.168.4.10', 16), ('192.168.4.11', 16), ('10.0.1.2', 24)])
        self.assertEqual([x['network'] for x in ranges], ['192.168.4.0/24', '10.0.1.0/24'])
        self.assertTrue(ranges[0]['limited']); self.assertFalse(ranges[1]['limited'])

    def test_ip_validation(self):
        self.assertEqual(network.validate_ip(' 192.168.1.21 '), '192.168.1.21')
        for value in ['hostname', '1.2.3.999', '0.0.0.0', '224.0.0.1']:
            with self.assertRaises(ValueError): network.validate_ip(value)

    def test_scan_returns_found_ips_and_progress(self):
        events = []
        with patch.object(network, 'has_smb', side_effect=lambda ip: ip.endswith('.2')):
            network.scan([{'network': '192.168.1.0/30'}], threading.Event(), lambda *event: events.append(event))
        self.assertEqual([e[0] for e in events if e[0]], ['192.168.1.2'])
        self.assertEqual(events[-1][1:], (2, 2))

    def test_scan_can_stop(self):
        stop = threading.Event(); stop.set()
        with patch.object(network, 'has_smb', return_value=False):
            update = Mock(); network.scan([{'network': '10.0.0.0/30'}], stop, update)
            update.assert_not_called()

    def test_linux_share_url_encodes_name(self):
        self.assertEqual(network.share_source('10.0.0.1', 'Family #1%', False), 'smb://10.0.0.1/Family%20%231%25')
        self.assertEqual(network.share_source('10.0.0.1', 'Family Photos', True), r'\\10.0.0.1\Family Photos')
        with self.assertRaises(ValueError): network.share_source('10.0.0.1', '../folder', False)

    def test_password_not_in_arguments(self):
        credentials = {'username': 'kid', 'password': 'secret', 'domain': ''}
        with patch.object(network, 'WINDOWS', False), patch.object(network.shutil, 'which', return_value='/usr/bin/smbclient'), patch.object(network, 'command', return_value='Disk|Public|Files') as cmd:
            self.assertEqual(network.list_shares('10.0.0.1', credentials)[0]['name'], 'Public')
            args, kwargs = cmd.call_args
            self.assertNotIn('secret', args[0]); self.assertEqual(kwargs['env']['PASSWD'], 'secret')

    def test_auth_failure_is_distinct(self):
        result = Mock(returncode=1, stdout='', stderr='NT_STATUS_LOGON_FAILURE')
        with patch.object(network.subprocess, 'run', return_value=result):
            with self.assertRaises(PermissionError): network.command(['smbclient'])

    def test_mount_credentials_on_stdin_only(self):
        with patch.object(network, 'WINDOWS', False), patch.object(network, 'command', return_value='{"ok":true}') as cmd:
            network.mount_share('smb://10.0.0.1/Public', '', {'username': 'kid', 'password': 'secret'})
            args, kwargs = cmd.call_args
            self.assertNotIn('secret', args[0]); self.assertIn('secret', kwargs['input'])

    def test_mount_auth_failure(self):
        with patch.object(network, 'WINDOWS', False), patch.object(network, 'command', return_value='{"ok":false,"auth":true}'):
            with self.assertRaises(PermissionError): network.mount_share('smb://10.0.0.1/Public', '')

    def test_linux_interface_detection(self):
        output = '[{"addr_info":[{"family":"inet","local":"192.168.4.2","prefixlen":24}]}]'
        with patch.object(network, 'WINDOWS', False), patch.object(network, 'command', return_value=output):
            self.assertEqual(network.local_networks()[0]['network'], '192.168.4.0/24')

    def test_windows_interface_detection(self):
        with patch.object(network, 'WINDOWS', True), patch.object(network, 'command', return_value='{"IPAddress":"192.168.4.2","PrefixLength":24}'):
            self.assertEqual(network.local_networks()[0]['network'], '192.168.4.0/24')

if __name__ == '__main__': unittest.main()
