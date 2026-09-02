"""Core task execution engine."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from threading import Event, Lock, Thread, current_thread
from typing import Callable, Optional, Tuple


Point = Tuple[int, int]
StateCallback = Callable[[bool], None]
SUPPORTED_MODES = frozenset(
    {
        "random_walk",
        "lissajous",
        "inertial_drift",
        "levy_walk",
        "breathing",
        "lorenz",
        "rose_curve",
        "spirograph",
        "golden_spiral",
        "damped_pendulum",
        "mean_reversion",
    }
)


class TaskConfigError(ValueError):
    """Raised when the click configuration is invalid."""


@dataclass(frozen=True)
class TaskConfig:
    start_position: Point = (0, 0)
    interval_seconds: float = 1.0
    button: str = "left"
    clicks_per_point: int = 0
    delay_between_clicks: float = 0.05
    mode: str = "random_walk"
    move_radius: int = 50
    screen_bounds: Optional[Tuple[int, int, int, int]] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_position", tuple(self.start_position))
        if self.screen_bounds is not None:
            object.__setattr__(self, "screen_bounds", tuple(self.screen_bounds))

    def validate(self) -> "TaskConfig":
        if self.mode not in SUPPORTED_MODES:
            raise TaskConfigError(f"Unsupported mode: {self.mode}")
        if len(self.start_position) != 2:
            raise TaskConfigError("start_position must contain x and y.")
        if not all(isinstance(value, int) for value in self.start_position):
            raise TaskConfigError("start_position values must be integers.")
        if self.move_radius <= 0:
            raise TaskConfigError("move_radius must be greater than 0.")
        if self.interval_seconds < 0.05:
            raise TaskConfigError("interval_seconds must be at least 0.05.")
        if self.clicks_per_point < 0 or self.clicks_per_point > 20:
            raise TaskConfigError("clicks_per_point must be between 0 and 20.")
        if self.delay_between_clicks < 0:
            raise TaskConfigError("delay_between_clicks must be >= 0.")
        if self.button not in {"left", "right", "middle"}:
            raise TaskConfigError("button must be 'left', 'right', or 'middle'.")
        if self.screen_bounds is not None:
            if len(self.screen_bounds) != 4:
                raise TaskConfigError("screen_bounds must be (x_min, y_min, x_max, y_max).")
            x_min, y_min, x_max, y_max = self.screen_bounds
            if not all(isinstance(v, int) for v in self.screen_bounds):
                raise TaskConfigError("screen_bounds values must be integers.")
            if x_max <= x_min or y_max <= y_min:
                raise TaskConfigError("screen_bounds must have positive width and height.")
        return self


class MouseController:
    def move_and_click(self, x: int, y: int, button: str = "left", count: int = 1) -> None:
        raise NotImplementedError

    def get_cursor_position(self) -> Point:
        raise NotImplementedError


class TaskRunner:
    def __init__(
        self,
        config: TaskConfig,
        mouse_controller: MouseController,
        on_state_change: StateCallback | None = None,
    ) -> None:
        self._config = config.validate()
        self._mouse = mouse_controller
        self._on_state_change = on_state_change
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._running = False
        self._lock = Lock()
        center_x, center_y = self._config.start_position
        self._center = (float(center_x), float(center_y))
        self._position = [float(center_x), float(center_y)]
        self._velocity = [0.0, 0.0]
        self._phase = 0.0
        self._step_index = 0
        self._lorenz_state = [0.1, 0.0, 0.0]

    @property
    def config(self) -> TaskConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def _notify(self, running: bool) -> None:
        self._running = running
        callback = self._on_state_change
        if callback is not None:
            callback(running)

    def _get_bounds(self) -> tuple[int, int, int, int] | None:
        if self._config.screen_bounds is not None:
            return self._config.screen_bounds
        provider = getattr(self._mouse, "get_screen_bounds", None)
        if callable(provider):
            return provider()
        return None

    def _bounded_point(self, x: float, y: float) -> Point:
        target_x = int(round(x))
        target_y = int(round(y))
        bounds = self._get_bounds()
        if bounds is not None:
            min_x, min_y, max_x, max_y = bounds
            target_x = min(max(target_x, min_x), max_x - 1)
            target_y = min(max(target_y, min_y), max_y - 1)
        self._position[0] = float(target_x)
        self._position[1] = float(target_y)
        return target_x, target_y

    def _next_random_point(self) -> Point:
        x, y = self._mouse.get_cursor_position()
        delta_x = random.randint(-self._config.move_radius, self._config.move_radius)
        delta_y = random.randint(-self._config.move_radius, self._config.move_radius)
        return self._bounded_point(x + delta_x, y + delta_y)

    def _next_lissajous_point(self) -> Point:
        self._phase += 0.32
        radius = self._config.move_radius
        center_x, center_y = self._center
        return self._bounded_point(
            center_x + radius * math.sin(self._phase),
            center_y + radius * math.sin(2 * self._phase),
        )

    def _next_inertial_point(self) -> Point:
        radius = self._config.move_radius
        center_x, center_y = self._center
        acceleration = radius * 0.08
        spring = 0.025
        damping = 0.86
        self._velocity[0] = (
            damping * self._velocity[0]
            + random.uniform(-acceleration, acceleration)
            + spring * (center_x - self._position[0])
        )
        self._velocity[1] = (
            damping * self._velocity[1]
            + random.uniform(-acceleration, acceleration)
            + spring * (center_y - self._position[1])
        )
        max_speed = max(1.0, radius * 0.28)
        speed = math.hypot(*self._velocity)
        if speed > max_speed:
            scale = max_speed / speed
            self._velocity[0] *= scale
            self._velocity[1] *= scale
        return self._bounded_point(
            self._position[0] + self._velocity[0],
            self._position[1] + self._velocity[1],
        )

    def _next_levy_point(self) -> Point:
        angle = random.uniform(0.0, math.tau)
        radius = self._config.move_radius
        step = min(radius * 4.0, max(1.0, radius * 0.12 * random.paretovariate(1.5)))
        return self._bounded_point(
            self._position[0] + step * math.cos(angle),
            self._position[1] + step * math.sin(angle),
        )

    def _next_breathing_point(self) -> Point:
        self._phase += 0.28
        radius = self._config.move_radius * (0.1 + 0.9 * (math.sin(self._phase) + 1.0) / 2.0)
        angle = self._phase * 0.72
        center_x, center_y = self._center
        return self._bounded_point(
            center_x + radius * math.cos(angle),
            center_y + radius * math.sin(angle),
        )

    def _next_lorenz_point(self) -> Point:
        x, y, z = self._lorenz_state
        sigma, rho, beta, dt = 10.0, 28.0, 8.0 / 3.0, 0.01
        for _ in range(24):
            delta_x = sigma * (y - x)
            delta_y = x * (rho - z) - y
            delta_z = x * y - beta * z
            x += delta_x * dt
            y += delta_y * dt
            z += delta_z * dt
        self._lorenz_state = [x, y, z]
        radius = self._config.move_radius
        center_x, center_y = self._center
        return self._bounded_point(
            center_x + radius * x / 22.0,
            center_y + radius * (z - 25.0) / 25.0,
        )

    def _next_rose_point(self) -> Point:
        self._phase += 0.22
        radius = self._config.move_radius * math.cos(5.0 * self._phase)
        center_x, center_y = self._center
        return self._bounded_point(
            center_x + radius * math.cos(self._phase),
            center_y + radius * math.sin(self._phase),
        )

    def _next_spirograph_point(self) -> Point:
        # Sample farther along the same curve so R=50 produces visible motion.
        self._phase += 0.4
        outer_radius, inner_radius, pen_offset = 5.0, 3.0, 4.0
        scale = self._config.move_radius / (outer_radius - inner_radius + pen_offset)
        center_x, center_y = self._center
        ratio = (outer_radius - inner_radius) / inner_radius
        return self._bounded_point(
            center_x
            + scale
            * ((outer_radius - inner_radius) * math.cos(self._phase) + pen_offset * math.cos(ratio * self._phase)),
            center_y
            + scale
            * ((outer_radius - inner_radius) * math.sin(self._phase) - pen_offset * math.sin(ratio * self._phase)),
        )

    def _next_golden_spiral_point(self) -> Point:
        outward_sample_count = 24
        round_trip_length = 2 * (outward_sample_count - 1)
        cycle_step = (self._step_index - 1) % round_trip_length
        if cycle_step >= outward_sample_count:
            cycle_step = round_trip_length - cycle_step
        theta = math.tau * 2.0 * cycle_step / (outward_sample_count - 1)
        growth = math.log(10.0) / (math.tau * 2.0)
        radius = self._config.move_radius * 0.1 * math.exp(growth * theta)
        center_x, center_y = self._center
        return self._bounded_point(
            center_x + radius * math.cos(theta),
            center_y + radius * math.sin(theta),
        )

    def _next_pendulum_point(self) -> Point:
        sample_scale = 2.0
        cycle_step = self._step_index % 60
        sample_time = cycle_step * sample_scale
        damping = math.exp(-0.018 * sample_time)
        angle = 0.95 * damping * math.cos(sample_time * 0.3)
        radius = self._config.move_radius
        center_x, center_y = self._center
        return self._bounded_point(
            center_x + radius * math.sin(angle),
            center_y + radius * 0.55 * (1.0 - math.cos(angle)),
        )

    def _next_mean_reversion_point(self) -> Point:
        center_x, center_y = self._center
        pull = 0.16
        noise = self._config.move_radius * 0.16
        return self._bounded_point(
            self._position[0] + pull * (center_x - self._position[0]) + random.gauss(0.0, noise),
            self._position[1] + pull * (center_y - self._position[1]) + random.gauss(0.0, noise),
        )

    def _next_point(self) -> Point:
        self._step_index += 1
        generators = {
            "random_walk": self._next_random_point,
            "lissajous": self._next_lissajous_point,
            "inertial_drift": self._next_inertial_point,
            "levy_walk": self._next_levy_point,
            "breathing": self._next_breathing_point,
            "lorenz": self._next_lorenz_point,
            "rose_curve": self._next_rose_point,
            "spirograph": self._next_spirograph_point,
            "golden_spiral": self._next_golden_spiral_point,
            "damped_pendulum": self._next_pendulum_point,
            "mean_reversion": self._next_mean_reversion_point,
        }
        return generators[self._config.mode]()

    def _perform_click(self, x: int, y: int) -> None:
        if self._config.clicks_per_point == 0:
            self._mouse.move_and_click(x, y, button=self._config.button, count=0)
            return
        if self._config.clicks_per_point == 1 or self._config.delay_between_clicks == 0:
            self._mouse.move_and_click(
                x,
                y,
                button=self._config.button,
                count=self._config.clicks_per_point,
            )
            return

        for _ in range(self._config.clicks_per_point):
            self._mouse.move_and_click(
                x,
                y,
                button=self._config.button,
                count=1,
            )
            if self._stop_event.wait(self._config.delay_between_clicks):
                break

    def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                x, y = self._next_point()
                self._perform_click(x, y)
                if self._stop_event.wait(self._config.interval_seconds):
                    break
        finally:
            with self._lock:
                if self._running:
                    self._notify(False)

    def start(self) -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._stop_event.clear()
            self._thread = Thread(target=self._run, daemon=True)
            self._thread.start()
            self._notify(True)
            return True

    def stop(self, wait: bool = True, timeout: float | None = 1.0) -> bool:
        with self._lock:
            if not self._running:
                return False
            self._stop_event.set()
            thread = self._thread

        if wait and thread is not None and thread is not current_thread():
            thread.join(timeout=timeout)
        return True
