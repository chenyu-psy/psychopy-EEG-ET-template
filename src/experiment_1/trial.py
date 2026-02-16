"""Trial-level runtime for Experiment 1."""

from __future__ import annotations

from typing import Any, cast

from psychopy import core, event

from settings import CODE, COLORS, RESPONSES, TIMING
from stimuli import build_sample_stimulus


class TrialRunner:
    """Run one trial using timing/code/response/color settings from `exp`."""

    def __init__(self, exp):
        self.exp = exp
        self.timing = getattr(exp, "timing", TIMING)
        self.code = getattr(exp, "code", CODE)
        self.responses = getattr(exp, "responses", RESPONSES)
        self.colors = getattr(exp, "colors", COLORS)

    def _send_marker(self, code_key: str) -> None:
        """Send synced marker when EEG is enabled and code exists."""
        if not getattr(self.exp, "do_eeg", False):
            return
        if code_key not in self.code:
            return
        self.exp.send_synced_event(self.code[code_key], code_key)

    def start_trial(self, trial_id: int, block_id: int, label: str) -> None:
        """Start status + recording for a trial."""
        if self.exp.is_eyetracking_active("send_status"):
            self.exp.tracker.send_status(f"block {block_id} trial {trial_id} {label}")
        if self.exp.is_eyetracking_active("start_recording"):
            self.exp.tracker.start_recording()
        self._send_marker("TRIAL_START")

    def show_fixation(self) -> None:
        """Display fixation screen."""
        self.exp.display_fixation(wait_time=self.timing["fixation"][0], color=self.colors["item"])

    def show_sample(self, symbol: str) -> None:
        """Display sample screen."""
        stim = build_sample_stimulus(self.exp, symbol)
        stim.draw()
        self.exp.experiment_window.flip()
        core.wait(self.timing["sample"])

    def show_delay(self) -> None:
        """Display delay screen."""
        self._send_marker("DELAY")
        self.exp.display_fixation(wait_time=self.timing["delay"], color=self.colors["item"])

    def get_response(self) -> tuple[str, float]:
        """Collect response and return `(resp, rt_ms)`."""
        self._send_marker("RESPONSE_START")
        rt_clock = core.MonotonicClock()
        wait_keys = cast(Any, event.waitKeys)
        keys = wait_keys(
            keyList=list(self.exp.keys) + ["escape"],
            maxWait=self.timing["test"],
            timeStamped=rt_clock,
        )
        if not keys:
            return "", float("nan")

        key, timestamp = keys[0]
        if key == "escape":
            self.exp.quit_experiment()
        return key, timestamp * 1000

    def end_trial(self) -> None:
        """Stop recording and send trial-end marker."""
        self._send_marker("TRIAL_END")
        if self.exp.is_eyetracking_active("stop_recording"):
            self.exp.tracker.stop_recording()

    def run_trial(self, trial_def: dict) -> dict:
        """Run one trial and return a row for CSV writing."""
        required = ("trial_id", "block_id", "label", "symbol")
        missing = [k for k in required if k not in trial_def]
        if missing:
            raise KeyError(f"Missing trial fields: {missing}")

        trial_id = trial_def["trial_id"]
        block_id = trial_def["block_id"]
        label = trial_def["label"]
        symbol = trial_def["symbol"]

        self.start_trial(trial_id, block_id, label)
        self.show_fixation()
        self.show_sample(symbol)
        self.show_delay()
        resp, rt_ms = self.get_response()
        self.end_trial()

        row = {"subject": self.exp.sub_num, **trial_def, "resp": resp, "rt_ms": rt_ms}
        return row
