import os
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Windows-only mouse controller")
class WindowsMouseTests(unittest.TestCase):
    def setUp(self) -> None:
        from deskflow import windows_mouse

        self.windows_mouse = windows_mouse

    def test_absolute_coordinate_normalization(self) -> None:
        normalize = self.windows_mouse._normalize_absolute_coordinate

        self.assertEqual(normalize(100, 100, 101), 0)
        self.assertEqual(normalize(200, 100, 101), 65535)
        self.assertEqual(normalize(150, 100, 101), 32768)
        self.assertEqual(normalize(-500, 100, 101), 0)
        self.assertEqual(normalize(500, 100, 101), 65535)

    def test_absolute_move_uses_virtual_desktop_input(self) -> None:
        module = self.windows_mouse
        expected_flags = (
            module.MOUSEEVENTF_MOVE
            | module.MOUSEEVENTF_ABSOLUTE
            | module.MOUSEEVENTF_VIRTUALDESK
        )

        with (
            patch.object(module, "_virtual_screen_bounds", return_value=(-100, -50, 201, 101)),
            patch.object(module, "_send_mouse_input") as send_input,
        ):
            module._send_absolute_move(0, 0)

        send_input.assert_called_once_with(
            expected_flags,
            dx=32768,
            dy=32768,
        )


if __name__ == "__main__":
    unittest.main()
