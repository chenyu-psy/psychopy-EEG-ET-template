## psychopy-EEG-ET-template

A PsychoPy-based template for building **EEG experiments** with synchronized behavioral tasks and eye-movement monitoring.

This repository is designed for **script-style usage** (not package-only usage): you can run experiment entry files directly with your Python/PsychoPy environment.

## Quick Start (uv)

Use `uv` as the recommended way to initialize and run this project.

1. Install `uv` (if needed). Common options:

```bash
# macOS/Linux (official installer)
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS (Homebrew)
brew install uv

# Any platform with pipx
pipx install uv

# Any platform with pip
pip install uv

# Windows PowerShell (official installer):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Create/sync the project environment from `pyproject.toml` + `uv.lock`:

```bash
cd /Users/chenyu/GitHub/psychopy-EEG-ET-template
uv sync
```

3. Run the experiment entry script:

```bash
uv run python /Users/chenyu/GitHub/psychopy-EEG-ET-template/src/experiment_1/main.py
```

## Project Structure

### `src/experiment_1/`

This is the main experiment implementation folder.

- `main.py`: entrypoint and phase orchestration (`initialize`, pre-test, formal experiment, `finalize`).
- `settings.py`: experiment configuration (monitor, timing, design, responses, EEG/eyetracking flags).
- `trial.py`: single-trial runtime logic.
- `screens.py`: instruction/break/end screen helpers.
- `stimuli.py`: stimulus constructors.
- `data_io.py`: behavioral CSV read/write helpers.

### `templates/`

Shared infrastructure for EEG + eyetracking experiments.

- `tracker_template.py`: `BaseTrackerExp` and core reusable functionality (windowing, dialogs, tracker setup, EEG sync helpers).

### `src/utils/`

General utility modules used by experiments.

- `condition_assignment.py`: builds condition-balanced trial tables.
- `eyelinker.py` and `eyelink_display.py`: EyeLink integration and display bridge.

### `examples/`

Reference task scripts showing how to structure experiments with this framework.

### `data/`

Output directory. Subject-level files are saved automatically under:
`data/<experiment_name>/subXX/`

### Root Config Files

- `pyproject.toml`: project metadata and dependency configuration.
- `uv.lock`: locked dependency versions for reproducible `uv sync`.
- `README.md`: usage and template documentation.

## What This Template Provides

- A reusable experiment base class: `BaseTrackerExp` (`templates/tracker_template.py`)
- Structured experiment phases in `main.py`:
1. `initialize()`
2. `run_pre_test()`
3. `run_experiment()`
4. `finalize()`
- Subject-level output management:
  - `data/<experiment_name>/subXX/`
- Subject conflict dialog (overwrite vs change subject ID)
- EEG trigger support via parallel port for event synchronization
- EyeLink integration for monitoring/controlling eye movements during EEG recording
- EDF transfer and storage when eye tracking is enabled
- Global `escape` quit key

## Requirements

- Python (managed via `uv`)
- PsychoPy
- Parallel-port support for EEG trigger output
- EyeLink dependencies (`pylink`) if using realtime eye-movement monitoring

If you prefer manual venv usage (instead of `uv`):

```bash
/Users/chenyu/GitHub/psychopy-EEG-ET-template/.venv/bin/python -m pip install -e .
```

## How To Run

Recommended (`uv`):

```bash
uv run python /Users/chenyu/GitHub/psychopy-EEG-ET-template/src/experiment_1/main.py
```

Alternative (existing venv):

```bash
/Users/chenyu/GitHub/psychopy-EEG-ET-template/.venv/bin/python /Users/chenyu/GitHub/psychopy-EEG-ET-template/src/experiment_1/main.py
```

## Configure an Experiment

Edit:

- `src/experiment_1/settings.py`

Key sections:

- `MONITOR`
  - includes display settings and `fullscr` toggle for testing
- `EYE_TRACKING`
  - used to monitor eye movement during EEG sessions
  - `tracked_eye`: `"LEFT" | "RIGHT" | "BOTH"`
  - `eye_max_dist`
- `DESIGN`
  - Information regarding the experimental design, including trial counts, conditions, and break intervals
- `TIMING`
  - Presentation time of all screens in the experiment
- `REALTIME_TRACKER`
  - `True` to enable EyeLink monitoring during EEG
- `REALTIME_EEG`
  - `True` to enable EEG trigger output (event markers)

## Data Output

For subject `01` and experiment name `experiment_1`, files are saved to:

```text
data/experiment_1/sub01/
├─ sub01_info.csv
├─ sub01_beh.csv
├─ sub01.edf             # when eye tracking is enabled
└─ sub01_eeg.*           # raw EEG file from your acquisition software
```

Notes:

- `sub01_info.csv` and `sub01_beh.csv` are written by this template.
- `sub01.edf` is written when EyeLink is enabled.
- Raw EEG files are saved by your EEG acquisition system/software (not directly by this Python code).

## Creating a New Experiment From This Template

1. Duplicate `src/experiment_1/` to a new folder (e.g. `src/experiment_2/`).
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

## Acknowledgment

The following files were edited in this project and adapted from code contributed by **Colin Quirk (cquirk@uchicago.edu)**:

- `src/utils/eyelink_display.py`
- `src/utils/eyelinker.py`
- `templates/tracker_template.py`

Special thanks to Colin Quirk for these contributions.
