# DeskFlow

DeskFlow is a Windows desktop utility that performs configured cursor actions at a repeating interval.

## Download

Download the latest standalone Windows executable from
[GitHub Releases](https://github.com/OkYongChoi/deskflow/releases/latest).

1. Download `DeskFlow.exe`.
2. Run it directly; no installer is required.
3. Use `F7` to start and `F8` to stop.

Because the executable is not code-signed, Windows SmartScreen may ask you to confirm
before running it. Release checksums are published with each release.

## Features

- Eleven movement modes: random walk, Lissajous figure-eight, inertial drift, Levy walk,
  breathing, Lorenz attractor, rose curve, spirograph, golden spiral, damped pendulum,
  and mean reversion
- Smooth interpolated cursor movement with a configurable radius
- Click with left / right / middle button
- Number of clicks per target
- Global hotkeys (Windows): `F7` start, `F8` stop
- Safe stop at any time

## Movement mode reference

- See [Movement Modes](docs/MOVEMENT_MODES.md) for the equations, constants, and behavior of every mode.

## Run

- `python -m deskflow`
- or run `run_deskflow.bat`

## Build

- Run `powershell -ExecutionPolicy Bypass -File .\build_exe.ps1`
- The build script creates an isolated `.build-env` and installs PyInstaller there when needed.
- The console-free executable is created at `dist\DeskFlow.exe`

## Test

- `python -m unittest`

## Notes

- This project targets Windows for real mouse control.
- For non-Windows environments, only the core logic and unit tests are safe to run.
- Use DeskFlow only on systems and applications you control, and follow applicable
  workplace, service, and automation policies.

## License

DeskFlow is available under the [MIT License](LICENSE).
