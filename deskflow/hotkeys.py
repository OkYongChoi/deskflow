"""Global hotkey registration for Windows."""

from __future__ import annotations

import os
import threading
from ctypes import WinDLL, byref, wintypes

if os.name != "nt":
    raise RuntimeError("hotkeys are only supported on Windows.")

user32 = WinDLL("user32", use_last_error=True)
kernel32 = WinDLL("kernel32", use_last_error=True)

WM_HOTKEY = 0x0312
MOD_NONE = 0x0000
VK_F7 = 0x76
VK_F8 = 0x77
HOTKEY_ID_START = 1
HOTKEY_ID_STOP = 2


class GlobalHotkeyManager:
    def __init__(self, on_start, on_stop) -> None:
        self._on_start = on_start
        self._on_stop = on_stop
        self._thread_id: int | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> bool:
        if self._running:
            return False
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._thread_id is not None:
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)

    def _run(self) -> None:
        if not user32.RegisterHotKey(None, HOTKEY_ID_START, MOD_NONE, VK_F7):
            return
        if not user32.RegisterHotKey(None, HOTKEY_ID_STOP, MOD_NONE, VK_F8):
            user32.UnregisterHotKey(None, HOTKEY_ID_START)
            return

        try:
            self._thread_id = kernel32.GetCurrentThreadId()
            msg = wintypes.MSG()
            while self._running:
                ret = user32.GetMessageW(byref(msg), None, 0, 0)
                if ret == 0 or ret == -1:
                    break
                if msg.message == WM_HOTKEY:
                    if msg.wParam == HOTKEY_ID_START:
                        self._on_start()
                    elif msg.wParam == HOTKEY_ID_STOP:
                        self._on_stop()
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID_START)
            user32.UnregisterHotKey(None, HOTKEY_ID_STOP)
