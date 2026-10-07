from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).parents[1]))
import ui

class ScalingTests(unittest.TestCase):
    def test_windows_fit_4k_720p_and_480p_at_multiple_scales(self):
        for screen in [(3840,2160),(1280,720),(640,480)]:
            for dpi in (96,144,192):
                for preferred in [(920,570),(870,640),(640,520),(480,410),(570,520)]:
                    with self.subTest(screen=screen,dpi=dpi,preferred=preferred):
                        width,height = ui.window_size(*screen,*preferred,dpi)
                        self.assertLessEqual(width,screen[0]-48)
                        self.assertLessEqual(height,screen[1]-100)

    def test_headings_compact_on_small_high_dpi_screens(self):
        self.assertEqual(ui.heading_size(480,192),12)
        self.assertEqual(ui.heading_size(720,96),22)
        self.assertEqual(ui.heading_size(2160,192),22)

    def test_buttons_wrap_when_scaled_or_window_shrinks(self):
        self.assertEqual(ui.button_columns(900,[130,130,130,130]),4)
        self.assertEqual(ui.button_columns(590,[260,260,260,260]),2)
        self.assertEqual(ui.button_columns(350,[260,260,260,260]),1)

    def test_empty_toolbar_does_not_divide_by_zero(self):
        self.assertEqual(ui.button_columns(0,[]),1)

if __name__ == '__main__': unittest.main()
