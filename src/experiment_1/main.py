"""Main entrypoint for Experiment 1.

Subclass `BaseTrackerExp` and implement experiment-specific logic here.
"""

from random import choice

import pandas as pd
from _paths import PROJECT_ROOT # absolute path to project root directory

from templates import BaseTrackerExp, EyeMovementError
from utils import assign_conditions
from data_io import append_trial, init_data_file
from screens import show_block_start, show_break, show_end, show_instructions
from settings import (
    CODE,
    COLORS,
    DESIGN,
    EYE_TRACKING,
    EXPERIMENT_NAME,
    MONITOR,
    REALTIME_EEG,
    REALTIME_TRACKER,
    RESPONSES,
    TIMING,
)
from trial import TrialRunner


def build_trials(n_trials: int, design: dict) -> list[dict]:
    """Return trial definitions with symbol plus condition assignment."""
    symbols = ["A", "B", "C", "D"]
    # Build the full trial table from block/mixed conditions and practice settings.
    trial_df = assign_conditions(
        block=design["condition"]["block"],
        mixed=design["condition"]["mixed"],
        n_trials=n_trials,
        n_practice=design.get("N_practice", 0),
    )
    # Add per-trial stimulus content; keep condition assignment unchanged.
    trial_df = trial_df.copy()
    trial_df["symbol"] = [choice(symbols) for _ in range(len(trial_df))]
    return trial_df.to_dict(orient="records")


def calc_accuracy(rows: list[dict], correct_key: str) -> float | None:
    """Return percent correct from trial rows using pandas."""
    if not rows:
        return None
    trial_df = pd.DataFrame(rows)
    if "resp" not in trial_df.columns:
        return None
    return float(trial_df["resp"].eq(correct_key).mean() * 100)


class Experiment1(BaseTrackerExp):
    """Experiment 1 implementation built on top of BaseTrackerExp."""

    def __init__(self):
        # Base class handles shared PsychoPy/EEG/EyeLink infrastructure.
        super().__init__(
            experiment_name=EXPERIMENT_NAME,
            instructions=[
                "Welcome to Experiment 1.",
                "Press space to continue.",
            ],
            conditions=["default"],
            keys=RESPONSES.values(),
            monitor_details=MONITOR,
            bg_color=COLORS["background"],
            eyetracker_config=EYE_TRACKING,
            do_realtime_eyetracking=REALTIME_TRACKER,
        )
        self.do_eeg = REALTIME_EEG
        self.timing = TIMING
        self.code = CODE
        self.responses = RESPONSES
        self.colors = COLORS
        self.subject_data_dir = None
        self.data_file = None
        self.data_fields = None
        self.trial_runner = None
        self.trials: list[dict] = []
        self._eyetracker_initialized = False

    def _run_trials(self, trials: list[dict]) -> list[dict]:
        """Run trial list, append CSV rows, and return completed rows."""
        trial_runner, data_file, data_fields = self._require_runtime()
        completed_rows: list[dict] = []
        for trial_def in trials:
            row = trial_runner.run_trial(trial_def)
            append_trial(data_file, row, data_fields)
            completed_rows.append(row)
        return completed_rows

    def _condition_key(self, trial_def: dict) -> str:
        """Return condition key used for rejection counting."""
        return str(trial_def.get("label", "default"))

    def _run_trials_with_replacement(self, trials: list[dict], on_trial_update=None) -> list[dict]:
        """Run trials and append replacement trials when eye movement is detected."""
        # `pending` is a mutable queue; rejected trials are cloned and appended.
        trial_runner, data_file, data_fields = self._require_runtime()
        pending = [dict(t) for t in trials]
        completed_rows: list[dict] = []
        trial_i = 0

        while trial_i < len(pending):
            trial_def = pending[trial_i]
            condition_key = self._condition_key(trial_def)
            if condition_key not in self.rejection_counter:
                self.rejection_counter[condition_key] = 0

            try:
                row = trial_runner.run_trial(trial_def)
            except EyeMovementError as err:
                # Show immediate gaze-break feedback and schedule same-condition retry.
                self.display_eyemovement_feedback((err.x, err.y))
                self.do_rejection(True, condition=condition_key)
                pending.append(dict(trial_def))
                # Callback lets caller update progress/denominators for replacements.
                if on_trial_update is not None:
                    on_trial_update(None, True)
                trial_i += 1
                continue

            append_trial(data_file, row, data_fields)
            completed_rows.append(row)
            self.do_rejection(False, condition=condition_key)
            if on_trial_update is not None:
                on_trial_update(row, False)
            trial_i += 1

        return completed_rows

    def _require_runtime(self):
        """Return initialized runtime objects needed for trial execution."""
        if self.trial_runner is None or self.data_file is None or self.data_fields is None:
            raise RuntimeError("Experiment runtime is not initialized. Call initialize() first.")
        return self.trial_runner, self.data_file, self.data_fields

    def _ensure_eyetracker(self) -> None:
        """Initialize eye tracker once when enabled."""
        if not REALTIME_TRACKER or self._eyetracker_initialized:
            return
        self.et_initialize(f"sub{self.sub_num:02d}.edf")
        # Realtime fixation checks are only active after tracker startup.
        self.do_realtime = self.realtime_eyetrack_enabled
        self._eyetracker_initialized = True

    def initialize(self) -> bool:
        """Prepare experiment resources before any task phase."""
        # Collect subject info before opening the PsychoPy stimulus window.
        self.subject_data_dir = self.resolve_subject_dir(PROJECT_ROOT / "data", screen=0)
        if self.subject_data_dir is None:
            return False

        self.open_window(screen=0)
        self.fixation.hide()

        if self.do_eeg:
            self.setup_eeg()

        # Pre-build all planned trials and initialize per-condition rejection counters.
        self.trials = build_trials(DESIGN["N_trials"], DESIGN)
        self.rejection_counter = {str(t.get("label", "default")): 0 for t in self.trials}
        condition_cols = list(DESIGN["condition"]["block"].keys()) + list(DESIGN["condition"]["mixed"].keys())
        self.data_file = self.subject_data_dir / f"sub{self.sub_num:02d}_beh.csv"
        self.data_fields = init_data_file(self.data_file, condition_cols)
        self.trial_runner = TrialRunner(self)
        return True

    def run_pre_test(self) -> tuple[list[dict], list[dict]]:
        """Run instruction + warmup + eye-tracking acclimation trials.

        Returns remaining practice trials and experiment trials.
        """
        show_instructions(self)

        practice_trials = [t for t in self.trials if t.get("trial_type") == "pra"]
        experiment_trials = [t for t in self.trials if t.get("trial_type") == "exp"]
        if not practice_trials:
            return [], experiment_trials

        warmup_n = int(DESIGN.get("N_familiarization", 4) or 0)
        eyetrack_warmup_n = int(DESIGN.get("N_eyetracking_familiarization", 4) or 0)

        warmup_trials = practice_trials[:warmup_n] if warmup_n > 0 else []
        eyetrack_warmup_trials = practice_trials[warmup_n : warmup_n + eyetrack_warmup_n] if eyetrack_warmup_n > 0 else []
        remaining_practice_trials = practice_trials[warmup_n + eyetrack_warmup_n :]

        if warmup_trials:
            self.display_text_screen(
                "Task familiarization\n\nRead the instructions and try a few trials.\n\nPress space to start.",
                keyList=["space"],
            )
            self._run_trials(warmup_trials)

        if eyetrack_warmup_trials and REALTIME_TRACKER:
            self._ensure_eyetracker()
            self.display_text_screen(
                "Eye-tracking familiarization\n\nNow keep your eyes on fixation while responding.\n\nPress space to start.",
                keyList=["space"],
            )
            # Warmup with replacements trains fixation behavior before formal blocks.
            self._run_trials_with_replacement(eyetrack_warmup_trials)

        return remaining_practice_trials, experiment_trials

    def run_experiment(self, practice_trials: list[dict], experiment_trials: list[dict]) -> None:
        """Run block-level practice and experiment sessions."""
        if not experiment_trials:
            return

        self._require_runtime()
        self._ensure_eyetracker()
        self.display_text_screen("Main experiment\n\nPress space to start the main task.", keyList=["space"])

        break_every = int(DESIGN.get("break", 0) or 0)
        exp_done = 0
        # `exp_total` grows when rejected trials trigger replacement trials.
        exp_total = len(experiment_trials)
        completed_exp_rows: list[dict] = []

        for block_id in sorted({t["block_id"] for t in experiment_trials}):
            block_practice = [t for t in practice_trials if t["block_id"] == block_id]
            if block_practice:
                show_block_start(self, f"Practice Block {block_id}")
                self._run_trials_with_replacement(block_practice)

            show_block_start(self, f"Block {block_id}")
            block_trials = [t for t in experiment_trials if t["block_id"] == block_id]

            def on_exp_trial(row, rejected):
                nonlocal exp_done, exp_total, completed_exp_rows
                if rejected:
                    exp_total += 1
                    return
                completed_exp_rows.append(row)
                exp_done += 1
                if break_every > 0 and exp_done % break_every == 0 and exp_done < exp_total:
                    perf = calc_accuracy(completed_exp_rows, self.responses["CORRECT"])
                    show_break(self, exp_done, exp_total, perf)

            completed_block_rows = self._run_trials_with_replacement(block_trials, on_trial_update=on_exp_trial)

            acc = calc_accuracy(completed_block_rows, self.responses["CORRECT"])
            print(f"Block {block_id} accuracy: {acc:.1f}%" if acc is not None else f"Block {block_id} accuracy: N/A")

    def finalize(self) -> None:
        """Close and transfer eyetracker files."""
        if REALTIME_TRACKER and self.subject_data_dir is not None and self._eyetracker_initialized:
            edf_out = self.subject_data_dir / f"sub{self.sub_num:02d}.edf"
            self.et_conclude(new_filename=str(edf_out))

if __name__ == "__main__":
    
    # Initialize the experiment
    exp = Experiment1()
    if not exp.initialize():
        exp.quit_experiment()
    else:
        try:
            # Run pre-test phase and get remaining practice and experiment trials.
            practice_trials, experiment_trials = exp.run_pre_test()
            # Run main experiment with remaining trials.
            exp.run_experiment(practice_trials, experiment_trials)
        finally:
            # Finalize experiment (e.g., transfer eye-tracking data) and show end screen.
            exp.finalize()
        show_end(exp)
        # Quit PsychoPy and exit.
        exp.quit_experiment()
