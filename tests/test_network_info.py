import json
import unittest
from unittest.mock import patch

import network


class NetworkInfoTests(unittest.TestCase):
    def test_linux_full_subnet_and_gateway_by_interface(self):
        addresses = [
            {'ifname': 'lo', 'addr_info': [{'family': 'inet', 'local': '127.0.0.1', 'prefixlen': 8}]},
            {'ifname': 'eth0', 'addr_info': [{'family': 'inet', 'local': '10.2.3.4', 'prefixlen': 16}]},
            {'ifname': 'wlan0', 'addr_info': [{'family': 'inet', 'local': '192.168.1.4', 'prefixlen': 24}]},
        ]
        routes = [{'dev': 'eth0', 'gateway': '10.2.0.1'}]
        with patch.object(network, 'WINDOWS', False), patch.object(network, 'command', side_effect=[json.dumps(addresses), json.dumps(routes)]):
            result = network.local_network_info()
        self.assertEqual(result[0], {'interface': 'eth0', 'address': '10.2.3.4',
                                    'subnet': '10.2.0.0/16', 'netmask': '255.255.0.0',
                                    'gateways': ['10.2.0.1']})
        self.assertEqual(result[1]['gateways'], [])

    def test_windows_single_object_and_multiple_addresses(self):
        first = {'Interface': 'Ethernet', 'Address': '172.16.1.2', 'Prefix': 20, 'Gateways': ['172.16.0.1']}
        second = {'Interface': 'Wi-Fi', 'Address': '192.168.1.2', 'Prefix': 24, 'Gateways': []}
        with patch.object(network, 'WINDOWS', True), patch.object(network, 'command', return_value=json.dumps(first)):
            result = network.local_network_info()
            self.assertEqual(result[0]['subnet'], '172.16.0.0/20')
            self.assertEqual(result[0]['gateways'], ['172.16.0.1'])
        with patch.object(network, 'WINDOWS', True), patch.object(network, 'command', return_value=json.dumps([first, second])):
            self.assertEqual(len(network.local_network_info()), 2)

    def test_no_connections_and_command_failure(self):
        with patch.object(network, 'WINDOWS', True), patch.object(network, 'command', return_value=''):
            self.assertEqual(network.local_network_info(), [])
        with patch.object(network, 'command', side_effect=RuntimeError('Network query failed')):
            with self.assertRaisesRegex(RuntimeError, 'Network query failed'):
                network.local_network_info()
