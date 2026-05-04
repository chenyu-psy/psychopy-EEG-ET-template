## psychopy-EEG-ET-template

A PsychoPy-based template for building **EEG experiments** with synchronized behavioral tasks and eye-movement monitoring.

This repository is designed for **script-style usage**: you can run experiment entry files directly with your Python/PsychoPy environment.

## Quick Start (uv)

Use `uv` as the recommended way to initialize and run this project.

1. Install `uv` if needed. Common options:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS with Homebrew
brew install uv

# Any platform with pipx
pipx install uv

# Any platform with pip
pip install uv
```

2. Create/sync the project environment from `pyproject.toml` and `uv.lock`:

```bash
cd /Users/chenyu/Pacakges/psychopy-EEG-ET-template
uv sync
```

3. Run the experiment entry script:

```bash
uv run python /Users/chenyu/Pacakges/psychopy-EEG-ET-template/src/exp1/main.py
```

## Project Structure

### `src/exp1/`

This is the main experiment implementation folder.

- `main.py`: entrypoint and phase orchestration (`initialize`, pre-test, formal experiment, `finalize`).
- `settings.py`: experiment configuration (monitor, timing, design, responses, EEG/eyetracking flags).
- `trial.py`: single-trial runtime logic.
- `trial_queue.py`: queue runner for trial execution, data appending, and rejection replacement.
- `screens.py`: instruction, block, break, and end screen helpers.
- `stimuli.py`: stimulus constructors.
- `data_io.py`: behavioral CSV read/write helpers.

### `templates/`

Shared infrastructure for EEG + eyetracking experiments.

- `tracker_template.py`: `BaseTrackerExp` and core reusable functionality, including window setup, participant dialogs, subject-folder handling, EyeLink setup, realtime gaze checks, EEG trigger helpers, and EDF transfer.

### `src/utils/`

General utility modules used by experiments.

- `condition_assignment.py`: builds condition-balanced trial tables.
- `eyelinker.py` and `eyelink_display.py`: EyeLink integration and display bridge.

### `data/`

Output directory. Subject-level files are saved automatically under:

```text
data/<experiment_name>/subXX/
```

## What This Template Provides

- A reusable experiment base class: `BaseTrackerExp` (`templates/tracker_template.py`)
- Structured experiment phases in `main.py`:
  1. `initialize()`
  2. `run_pre_test()`
  3. `run_experiment()`
  4. `finalize()`
- Subject-level output management:
  - `data/<experiment_name>/subXX/`
- Subject conflict dialog with options to overwrite, continue an existing study, or change subject ID
- PsychoPy participant dialog fallback through tkinter or terminal prompts when PsychoPy GUI support is unavailable
- Project-local PsychoPy user app directory (`.psychopy`) to avoid home-directory permission issues
- EEG trigger support through a parallel port for event synchronization
- EyeLink integration for monitoring/controlling eye movements during EEG recording
- EDF transfer and storage when eye tracking is enabled
- Global `escape` quit key and `Ctrl+Q` emergency quit shortcut

## Requirements

- Python managed through `uv`
- PsychoPy
- Parallel-port support for EEG trigger output
- EyeLink dependencies (`pylink`) if using realtime eye-movement monitoring

If you prefer manual venv usage instead of `uv`:

```bash
/Users/chenyu/Pacakges/psychopy-EEG-ET-template/.venv/bin/python -m pip install -e .
```

## How To Run

Recommended (`uv`):

```bash
uv run python /Users/chenyu/Pacakges/psychopy-EEG-ET-template/src/exp1/main.py
```

Alternative (existing venv):

```bash
/Users/chenyu/Pacakges/psychopy-EEG-ET-template/.venv/bin/python /Users/chenyu/Pacakges/psychopy-EEG-ET-template/src/exp1/main.py
```

## Configure an Experiment

Edit:

- `src/exp1/settings.py`

Key sections:

- `MONITOR`
  - display settings and `fullscr` toggle for testing
- `EYE_TRACKING`
  - used to monitor eye movement during EEG sessions
  - `tracked_eye`: `"LEFT" | "RIGHT" | "BOTH"`
  - `eye_max_dist`: fixation radius in visual degrees
- `DESIGN`
  - trial counts, conditions, and break intervals
- `TIMING`
  - presentation time for task phases
- `REALTIME_TRACKER`
  - `True` to enable EyeLink monitoring during EEG
- `REALTIME_EEG`
  - `True` to enable EEG trigger output

## Use Realtime Tracking

Realtime tracking has two layers:

- EyeLink recording:
  - when EyeLink is enabled, the tracker records eye samples/events to the EDF file
- Online rejection:
  - when `REALTIME_TRACKER = True`, the task can check gaze online and reject trials for fixation breaks

To turn realtime tracking on:

1. Open `src/exp1/settings.py`.
2. Set `REALTIME_TRACKER = True`.
3. Check `EYE_TRACKING["tracked_eye"]` and `EYE_TRACKING["eye_max_dist"]`.
4. Run the experiment with a working EyeLink / `pylink` setup.

To turn realtime tracking off:

1. Open `src/exp1/settings.py`.
2. Set `REALTIME_TRACKER = False`.

Current online rejection rule:

- the task samples the newest gaze position online
- gaze is converted to distance from screen center
- if gaze exceeds the fixation radius, the trial is rejected with `eye_movement`
- the fixation radius is set by `EYE_TRACKING["eye_max_dist"]` in visual degrees
- after 3 consecutive eye-movement rejections, the template automatically runs one drift correction
- if the rejection streak grows beyond 5 trials, the experiment pauses for the researcher:
  - `return` reruns drift correction
  - `c` opens full eye-tracker calibration

Implementation note:

- the runtime on/off switch lives in `BaseTrackerExp` inside `templates/tracker_template.py`
- task code starts monitoring with `start_realtime_monitoring()` and stops it with `stop_realtime_monitoring()`

## Data Output

For subject `01` and experiment name `exp1`, files are saved to:

```text
data/exp1/sub01/
├─ sub01_info.csv
├─ sub01_beh.csv
├─ sub01.edf             # when eye tracking is enabled
└─ sub01_eeg.*           # raw EEG file from your acquisition software
```

Notes:

- `sub01_info.csv` and `sub01_beh.csv` are written by this template.
- `sub01.edf` is written when EyeLink is enabled.
- Raw EEG files are saved by your EEG acquisition system/software, not directly by this Python code.

## Creating a New Experiment From This Template

1. Duplicate `src/exp1/` to a new folder, for example `src/exp2/`.
2. Update `settings.py` (`EXPERIMENT_NAME`, design/timing/keys/colors).
3. Modify trial behavior in `trial.py` and stimuli in `stimuli.py`.
4. Adjust flow in `main.py` (`run_pre_test`, `run_experiment`).
5. Run the new `main.py` entrypoint directly.

## Notes

- This template is EEG-first: eye tracking is used to detect/control eye movement contamination during EEG acquisition.
- If EyeLink is enabled but your local `pylink` installation is incompatible, tracker setup can fail at eyetracking initialization.
- On macOS, PsychoPy may show non-fatal warnings for:
  - parallel-port import
  - fullscreen/monitor mode mismatches
  - font manager loading
