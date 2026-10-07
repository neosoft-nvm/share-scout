"""Headless checks for the discovery-to-mapping flow, with controlled hosts."""
import queue
import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from discovery import Finder
from resource_mapper import App

class FlowTests(unittest.TestCase):
    def finder(self):
        finder = Finder.__new__(Finder)
        finder.app = Mock(items=[], open_when_connected=set())
        finder.shares = [{'name': 'Family Photos', 'comment': ''}]
        finder.address = '192.168.1.12'
        finder.folders = Mock(); finder.folders.selection.return_value = ('0',)
        finder.auto = Mock(); finder.auto.get.return_value = True
        finder.close = Mock()
        return finder

    def test_discovered_folder_saved_connected_opened_without_typing(self):
        finder = self.finder()
        with patch('discovery.network.WINDOWS', False): finder.connect()
        self.assertEqual(finder.app.items[0]['source'], 'smb://192.168.1.12/Family%20Photos')
        self.assertTrue(finder.app.items[0]['auto'])
        finder.app.operation.assert_called_once_with(True, 0)
        self.assertEqual(finder.app.open_when_connected, {0})
        finder.close.assert_called_once()

    def test_connect_same_folder_does_not_duplicate(self):
        finder = self.finder()
        finder.app.items = [{'source': 'smb://192.168.1.12/Family%20Photos'}]
        with patch('discovery.network.WINDOWS', False): finder.connect()
        self.assertEqual(len(finder.app.items), 1)

    def test_windows_letter_is_chosen_automatically(self):
        finder = self.finder()
        with patch('discovery.network.WINDOWS', True), patch('discovery.network.free_drive', return_value='S:'):
            finder.connect()
        self.assertEqual(finder.app.items[0]['target'], 'S:')
        self.assertEqual(finder.app.items[0]['source'], r'\\192.168.1.12\Family Photos')

    def test_connection_success_opens_chosen_folder(self):
        app = App.__new__(App)
        app.items = [{'name': 'Photos', 'status': 'Connecting…'}]
        app.events = queue.Queue(); app.events.put((0, 'Connected', None))
        app.busy = {0}; app.open_when_connected = {0}; app.processes = {}
        app.refresh = Mock(); app.note = Mock(); app.tree = Mock(); app.open = Mock(); app.root = Mock()
        app.poll()
        app.open.assert_called_once()
        self.assertEqual(app.items[0]['status'], 'Connected')
        self.assertFalse(app.open_when_connected)

    def test_late_share_results_cannot_connect_wrong_host(self):
        finder = self.finder()
        finder.events = queue.Queue(); finder.events.put(('shares', 1, [{'name': 'Wrong host'}]))
        finder.browse_generation = 2; finder.window = Mock(); finder.window.winfo_exists.return_value = True
        finder.poll()
        self.assertEqual(finder.shares[0]['name'], 'Family Photos')

if __name__ == '__main__': unittest.main()
