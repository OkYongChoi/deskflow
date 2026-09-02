"""Windows mouse control using ctypes + Win32 SendInput."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import time

from .core import MouseController, Point

if os.name != "nt":
    raise RuntimeError("windows_mouse is only supported on Windows.")

user32 = ctypes.WinDLL("user32", use_last_error=True)


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def _send_mouse_input(flag: int, dx: int = 0, dy: int = 0) -> None:
    inp = INPUT(
        type=INPUT_MOUSE,
        u=INPUT._U(
            mi=MOUSEINPUT(
                dx=dx,
                dy=dy,
                dwFlags=flag,
            )
        ),
    )
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) == 0:
        raise OSError("SendInput failed.")


def _send_flag(flag: int) -> None:
    _send_mouse_input(flag)


def _virtual_screen_bounds() -> tuple[int, int, int, int]:
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if width <= 0 or height <= 0:
        raise OSError("Unable to determine virtual screen bounds.")
    return left, top, width, height


def _normalize_absolute_coordinate(value: int, origin: int, size: int) -> int:
    if size <= 1:
        return 0
    clamped = min(max(value, origin), origin + size - 1)
    return round((clamped - origin) * 65535 / (size - 1))


def _send_absolute_move(x: int, y: int) -> None:
    left, top, width, height = _virtual_screen_bounds()
    normalized_x = _normalize_absolute_coordinate(x, left, width)
    normalized_y = _normalize_absolute_coordinate(y, top, height)
    _send_mouse_input(
        MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
        dx=normalized_x,
        dy=normalized_y,
    )


class WindowsMouseController(MouseController):
    """Mouse controller for Windows."""

    def move_and_click(self, x: int, y: int, button: str = "left", count: int = 1) -> None:
        self._move_smoothly(x, y)
        if button == "left":
            down = MOUSEEVENTF_LEFTDOWN
            up = MOUSEEVENTF_LEFTUP
        elif button == "right":
            down = MOUSEEVENTF_RIGHTDOWN
            up = MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            down = MOUSEEVENTF_MIDDLEDOWN
            up = MOUSEEVENTF_MIDDLEUP
        else:
            raise ValueError(f"Unsupported button: {button}")

        for _ in range(count):
            _send_flag(down)
            _send_flag(up)

    def _move_smoothly(self, x: int, y: int) -> None:
        start_x, start_y = self.get_cursor_position()
        distance = max(abs(x - start_x), abs(y - start_y))
        steps = min(24, max(1, distance // 8))
        step_delay = 0.18 / steps
        for step in range(1, steps + 1):
            progress = step / steps
            eased = progress * progress * (3.0 - 2.0 * progress)
            next_x = round(start_x + (x - start_x) * eased)
            next_y = round(start_y + (y - start_y) * eased)
            _send_absolute_move(next_x, next_y)
            if step < steps:
                time.sleep(step_delay)

    def get_cursor_position(self) -> Point:
        point = POINT()
        if not user32.GetCursorPos(ctypes.byref(point)):
            raise OSError("GetCursorPos failed.")
        return point.x, point.y

    def get_screen_bounds(self) -> tuple[int, int, int, int]:
        left, top, width, height = _virtual_screen_bounds()
        return (left, top, left + width, top + height)
