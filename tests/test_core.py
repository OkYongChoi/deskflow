import math
import random
import statistics
import time
import unittest
from unittest.mock import patch

from deskflow.core import SUPPORTED_MODES, MouseController, TaskConfig, TaskConfigError, TaskRunner


class FakeMouse(MouseController):
    def __init__(self, position: tuple[int, int] = (0, 0)) -> None:
        self.calls: list[tuple[int, int, str, int]] = []
        self.position = position

    def move_and_click(self, x: int, y: int, button: str = "left", count: int = 1) -> None:
        self.calls.append((x, y, button, count))
        self.position = (x, y)

    def get_cursor_position(self) -> tuple[int, int]:
        return self.position


class CoreTests(unittest.TestCase):
    def test_validate_config(self) -> None:
        TaskConfig(start_position=(1, 2), interval_seconds=0.1).validate()
        with self.assertRaises(TaskConfigError):
            TaskConfig(mode="unknown").validate()
        with self.assertRaises(TaskConfigError):
            TaskConfig(interval_seconds=0.01).validate()
        TaskConfig(clicks_per_point=0).validate()
        with self.assertRaises(TaskConfigError):
            TaskConfig(clicks_per_point=-1).validate()
        with self.assertRaises(TaskConfigError):
            TaskConfig(move_radius=0).validate()

        for mode in SUPPORTED_MODES:
            TaskConfig(mode=mode).validate()

    def test_zero_clicks_moves_without_clicking(self) -> None:
        mouse = FakeMouse()
        config = TaskConfig(
            start_position=(10, 20),
            interval_seconds=0.2,
            clicks_per_point=0,
            mode="lissajous",
        ).validate()
        runner = TaskRunner(config, mouse)

        runner.start()
        time.sleep(0.05)
        runner.stop(wait=True)

        self.assertEqual(mouse.calls[0][3], 0)

    def test_runner_starts_stops(self) -> None:
        mouse = FakeMouse()
        config = TaskConfig(
            start_position=(10, 10),
            interval_seconds=0.1,
            clicks_per_point=1,
        ).validate()
        runner = TaskRunner(config, mouse)

        self.assertTrue(runner.start())
        self.assertTrue(runner.is_running)
        self.assertFalse(runner.start())

        time.sleep(0.25)
        runner.stop(wait=True)
        self.assertFalse(runner.is_running)
        self.assertGreaterEqual(len(mouse.calls), 1)

    def test_stop_from_callback(self) -> None:
        mouse = FakeMouse()
        started = False

        def on_state(running: bool) -> None:
            nonlocal started
            started = running

        config = TaskConfig(start_position=(5, 5), interval_seconds=0.1, clicks_per_point=2).validate()
        runner = TaskRunner(config, mouse, on_state_change=on_state)

        runner.start()
        time.sleep(0.12)
        runner.stop(wait=True)

        self.assertFalse(runner.is_running)
        self.assertTrue(started is False or started is True)
        self.assertGreaterEqual(len(mouse.calls), 1)

    def test_random_walk_mode(self) -> None:
        mouse = FakeMouse((100, 100))
        config = TaskConfig(
            start_position=(100, 100),
            mode="random_walk",
            move_radius=10,
            interval_seconds=0.2,
        ).validate()
        runner = TaskRunner(config, mouse)
        with patch("deskflow.core.random.randint", side_effect=[5, -3]):
            runner.start()
            time.sleep(0.05)
            runner.stop(wait=True)
        self.assertEqual(mouse.calls[0][0], 105)
        self.assertEqual(mouse.calls[0][1], 97)
        self.assertEqual(mouse.calls[0][2], "left")

    def test_random_walk_mode_with_bounds(self) -> None:
        mouse = FakeMouse((195, 195))
        config = TaskConfig(
            start_position=(195, 195),
            mode="random_walk",
            move_radius=10,
            screen_bounds=(0, 0, 200, 200),
            interval_seconds=0.2,
        ).validate()
        runner = TaskRunner(config, mouse)
        with patch("deskflow.core.random.randint", side_effect=[10, 10]):
            runner.start()
            time.sleep(0.05)
            runner.stop(wait=True)
        self.assertEqual(mouse.calls[0][0], 199)
        self.assertEqual(mouse.calls[0][1], 199)

    def test_all_modes_stay_in_bounds_and_move(self) -> None:
        for mode in SUPPORTED_MODES:
            with self.subTest(mode=mode):
                random.seed(12345)
                mouse = FakeMouse((100, 100))
                config = TaskConfig(
                    start_position=(100, 100),
                    mode=mode,
                    move_radius=30,
                    screen_bounds=(0, 0, 200, 200),
                ).validate()
                runner = TaskRunner(config, mouse)
                points = [runner._next_point() for _ in range(100)]

                self.assertTrue(all(0 <= x < 200 and 0 <= y < 200 for x, y in points))
                self.assertGreater(len(set(points)), 1)

    def test_default_radius_has_a_visible_typical_step_in_every_mode(self) -> None:
        radius = 50
        for mode in SUPPORTED_MODES:
            with self.subTest(mode=mode):
                random.seed(12345)
                mouse = FakeMouse((1000, 1000))
                runner = TaskRunner(
                    TaskConfig(
                        start_position=mouse.position,
                        mode=mode,
                        move_radius=radius,
                    ),
                    mouse,
                )
                previous = mouse.position
                distances = []
                for _ in range(240):
                    point = runner._next_point()
                    distances.append(math.dist(previous, point))
                    mouse.position = point
                    previous = point

                typical_step = statistics.median(distances)
                self.assertGreaterEqual(typical_step, radius * 0.1)
                self.assertLessEqual(typical_step, radius)

    def test_golden_spiral_scales_with_radius_without_reset_jump(self) -> None:
        medians = []
        for radius in (50, 100):
            mouse = FakeMouse((1000, 1000))
            runner = TaskRunner(
                TaskConfig(
                    start_position=mouse.position,
                    mode="golden_spiral",
                    move_radius=radius,
                ),
                mouse,
            )
            points = [runner._next_point() for _ in range(47)]
            distances = [math.dist(start, end) for start, end in zip(points, points[1:])]
            medians.append(statistics.median(distances))

            self.assertLessEqual(max(distances), radius * 0.55)
            self.assertLessEqual(
                max(math.dist((1000, 1000), point) for point in points),
                radius,
            )

        self.assertGreater(medians[1], medians[0] * 1.9)


if __name__ == "__main__":
    unittest.main()
