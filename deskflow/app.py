"""Tkinter GUI for DeskFlow."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk

from .core import TaskConfig, TaskConfigError, TaskRunner
from .core import MouseController

if os.name == "nt":
    from .windows_mouse import WindowsMouseController
    from .hotkeys import GlobalHotkeyManager
else:
    WindowsMouseController = None
    GlobalHotkeyManager = None


MODE_OPTIONS = {
    "Random Walk": "random_walk",
    "Lissajous Figure Eight": "lissajous",
    "Inertial Drift": "inertial_drift",
    "Levy Walk": "levy_walk",
    "Breathing": "breathing",
    "Lorenz Butterfly": "lorenz",
    "Rose Curve": "rose_curve",
    "Spirograph": "spirograph",
    "Golden Spiral": "golden_spiral",
    "Damped Pendulum": "damped_pendulum",
    "Mean Reversion": "mean_reversion",
}


class _DummyMouse(MouseController):
    def __init__(self) -> None:
        self.position = (0, 0)

    def move_and_click(self, x: int, y: int, button: str = "left", count: int = 1) -> None:
        self.position = (x, y)

    def get_cursor_position(self) -> tuple[int, int]:
        return self.position


class DeskFlowApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("DeskFlow")
        self.resizable(False, False)

        self._mouse = WindowsMouseController() if WindowsMouseController else _DummyMouse()
        self._runner = TaskRunner(
            TaskConfig(),
            self._mouse,
            on_state_change=self._on_state_change,
        )
        self._runner.stop(wait=False)
        self._hotkeys = None
        self._build_ui()
        self._wire_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        content = ttk.Frame(self, padding=10)
        content.grid(row=0, column=0, sticky="nsew")

        row = 0
        ttk.Label(content, text="클릭 간격(초):").grid(row=row, column=0, sticky="w")
        self.interval_var = tk.StringVar(value="1.0")
        ttk.Entry(content, textvariable=self.interval_var, width=10).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(content, text="클릭 버튼:").grid(row=row, column=0, sticky="w")
        self.button_var = tk.StringVar(value="left")
        ttk.Combobox(content, textvariable=self.button_var, values=["left", "right", "middle"], width=8, state="readonly").grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(content, text="포인트당 클릭 수:").grid(row=row, column=0, sticky="w")
        self.click_count_var = tk.StringVar(value="0")
        ttk.Entry(content, textvariable=self.click_count_var, width=10).grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(content, text="동작 모드:").grid(row=row, column=0, sticky="w")
        self.mode_var = tk.StringVar(value=next(iter(MODE_OPTIONS)))
        self.mode_combo = ttk.Combobox(
            content,
            textvariable=self.mode_var,
            values=list(MODE_OPTIONS),
            width=20,
            state="readonly",
        )
        self.mode_combo.grid(row=row, column=1, sticky="w")

        row += 1
        ttk.Label(content, text="이동 반경(px):").grid(row=row, column=0, sticky="w")
        self.move_radius_var = tk.StringVar(value="50")
        self.move_radius_entry = ttk.Entry(content, textvariable=self.move_radius_var, width=10)
        self.move_radius_entry.grid(row=row, column=1, sticky="w")

        row += 1
        control = ttk.Frame(content)
        control.grid(row=row, column=0, columnspan=2, pady=(8, 0), sticky="ew")
        self.start_btn = ttk.Button(control, text="시작(F7)", command=self._start)
        self.stop_btn = ttk.Button(control, text="정지(F8)", command=self._stop, state="disabled")
        self.start_btn.grid(row=0, column=0, padx=(0, 4))
        self.stop_btn.grid(row=0, column=1)

        row += 1
        self.status_var = tk.StringVar(value="대기")
        ttk.Label(content, textvariable=self.status_var).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))

        if os.name != "nt":
            ttk.Label(content, text="현재 OS는 글로벌 단축키를 지원하지 않습니다.").grid(
                row=row + 1,
                column=0,
                columnspan=2,
                sticky="w",
                pady=(4, 0),
            )
    def _wire_hotkeys(self) -> None:
        if GlobalHotkeyManager is None:
            return
        self._hotkeys = GlobalHotkeyManager(self._start, self._stop)
        self._hotkeys.start()

    def _start(self) -> None:
        if self._runner.is_running:
            return

        if self.state() == "iconic":
            self.deiconify()

        try:
            mode = MODE_OPTIONS[self.mode_var.get()]
            start_position = self._mouse.get_cursor_position()
            interval_seconds = float(self.interval_var.get())
            button = self.button_var.get()
            clicks_per_point = int(self.click_count_var.get())
            move_radius = int(self.move_radius_var.get())
            screen_bounds = None
            if hasattr(self._mouse, "get_screen_bounds"):
                screen_bounds = self._mouse.get_screen_bounds()

            config = TaskConfig(
                start_position=start_position,
                interval_seconds=interval_seconds,
                button=button,
                clicks_per_point=clicks_per_point,
                mode=mode,
                move_radius=move_radius,
                screen_bounds=screen_bounds,
            ).validate()
        except (TaskConfigError, ValueError, OSError) as exc:
            messagebox.showerror("설정 오류", str(exc))
            return

        self._runner = TaskRunner(
            config,
            self._mouse,
            on_state_change=self._on_state_change,
        )
        if not self._runner.start():
            messagebox.showinfo("정보", "이미 실행 중입니다.")

    def _stop(self) -> None:
        self._runner.stop(wait=False)
        self._on_state_change(False)

    def _on_state_change(self, running: bool) -> None:
        self.after(0, lambda: self._sync_state(running))

    def _sync_state(self, running: bool) -> None:
        if running:
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self._update_status("동작 중 (F8로 정지)")
        else:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self._update_status("중지됨")

    def _update_status(self, text: str) -> None:
        self.status_var.set(text)

    def _on_close(self) -> None:
        self._runner.stop(wait=False)
        if self._hotkeys is not None:
            self._hotkeys.stop()
        self.destroy()


def launch() -> None:
    app = DeskFlowApp()
    app.mainloop()
