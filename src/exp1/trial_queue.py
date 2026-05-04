"""Trial queue helpers for exp1 task loops.

This module keeps the "run trials, save rows, and retry rejected trials" logic
outside `main.py`, matching the structure used by the trackNeuAct experiments.
"""

from __future__ import annotations

from typing import Callable

from data_io import append_trial
from templates import EyeMovementError


def _condition_key(trial_def: dict) -> str:
    """Return condition label used for eye-movement rejection counts.

    Parameters
    ----------
    trial_def : dict
        Planned trial dictionary. The optional `label` field names the
        condition combination.

    Returns
    -------
    str
        Condition label, or `"default"` when the trial does not provide one.
    """
    return str(trial_def.get("label", "default"))


def run_trials_in_queue(
    trials: list[dict],
    exp,
    replace_on_reject: bool = False,
    on_trial_update: Callable[[dict | None, bool], None] | None = None,
) -> list[dict]:
    """Run queued trials and optionally schedule retries after gaze rejection.

    Parameters
    ----------
    trials : list[dict]
        Planned trial rows to run.
    exp : Experiment1
        Active experiment object. It must already have `trial_runner`,
        `data_file`, and `data_fields` initialized.
    replace_on_reject : bool, optional
        If True, trials rejected by realtime eye tracking are appended to the
        queue and rerun later. If False, eye-movement rejection is raised.
    on_trial_update : callable | None, optional
        Optional callback called as `(row, rejected)` after each accepted trial
        or rejected attempt. Rejected attempts pass `row=None`.

    Returns
    -------
    list[dict]
        Accepted trial rows, in the order they were completed.
    """
    trial_runner = getattr(exp, "trial_runner", None)
    data_file = getattr(exp, "data_file", None)
    data_fields = getattr(exp, "data_fields", None)
    if trial_runner is None or data_file is None or data_fields is None:
        raise RuntimeError("Experiment runtime is not initialized. Call initialize() first.")

    pending = [dict(t) for t in trials]
    completed_rows: list[dict] = []

    while pending:
        trial_def = pending.pop(0)
        condition_key = _condition_key(trial_def)
        if replace_on_reject and condition_key not in exp.rejection_counter:
            exp.rejection_counter[condition_key] = 0

        try:
            row = trial_runner.run_trial(trial_def)
        except EyeMovementError as err:
            if not replace_on_reject:
                raise
            # Keep the rejected trial in the same task context by retrying it
            # later rather than discarding that condition combination.
            exp.display_eyemovement_feedback((err.x, err.y))
            exp.do_rejection(True, condition=condition_key)
            pending.append(dict(trial_def))
            if on_trial_update is not None:
                on_trial_update(None, True)
            continue

        append_trial(data_file, row, data_fields)
        completed_rows.append(row)
        if replace_on_reject:
            exp.do_rejection(False, condition=condition_key)
        if on_trial_update is not None:
            on_trial_update(row, False)

    return completed_rows
