"""Condition assignment helpers for trial generation."""

from __future__ import annotations

import pandas as pd


def _label_token(factor: str, value) -> str:
    """Create short token for one condition value."""
    factor_l = factor.lower()
    value_s = str(value).strip().lower()

    if factor_l == "setsize":
        return f"ss{value_s}"
    if value_s == "irrelevant":
        return "irr"
    if value_s == "relevant":
        return "rel"

    cleaned = "".join(ch for ch in value_s if ch.isalnum())
    return cleaned[:4] or "na"


def _to_levels_frame(condition_map: dict):
    """Convert factor->levels mapping into a cartesian-product DataFrame."""
    if not condition_map:
        return pd.DataFrame([{}])

    factors = list(condition_map.keys())
    levels = [
        list(condition_map[factor]) if isinstance(condition_map[factor], (list, tuple)) else [condition_map[factor]]
        for factor in factors
    ]

    return pd.MultiIndex.from_product(levels, names=factors).to_frame(index=False)


def _repeat_rows(df: pd.DataFrame, repeats: int, trial_type: str) -> pd.DataFrame:
    """Repeat each row `repeats` times and annotate with `trial_type`."""
    if repeats <= 0:
        return pd.DataFrame(columns=[*df.columns, "trial_type", "_stage"])
    expanded = df.loc[df.index.repeat(repeats)].reset_index(drop=True).copy()
    expanded["trial_type"] = trial_type
    expanded["_stage"] = 0 if trial_type == "pra" else 1
    return expanded


def assign_conditions(block: dict, mixed: dict, n_trials: int, n_practice: int = 0) -> pd.DataFrame:
    """Assign block and mixed conditions for each trial.

    Parameters
    ----------
    block : dict
        Block-level condition factors and levels.
    mixed : dict
        Trial-level mixed condition factors and levels.
    n_trials : int
        Number of trials per condition combination.
    n_practice : int, optional
        Number of practice repetitions per condition combination in each block.
        Practice rows are marked with `trial_type = "pra"`.

    Returns
    -------
    pd.DataFrame
        Trial table with columns:
        - `block_id`
        - `trial_id`
        - `trial_type` (`"pra"` for practice, `"exp"` for experiment)
        - one column per condition factor name
        - `label` (unique name per condition combination, e.g. `ss2/irr`)
    """
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1.")
    if n_practice < 0:
        raise ValueError("n_practice must be >= 0.")

    block_key_order = list(block.keys())
    mixed_key_order = list(mixed.keys())

    block_df = _to_levels_frame(block).reset_index(drop=True)
    block_df.insert(0, "block_id", range(1, len(block_df) + 1))
    mixed_df = _to_levels_frame(mixed).reset_index(drop=True)

    combo_df = block_df.merge(mixed_df, how="cross")
    label_cols = mixed_key_order + block_key_order
    if label_cols:
        combo_df["label"] = combo_df.apply(
            lambda row: "/".join(_label_token(col, row[col]) for col in label_cols),
            axis=1,
        )
    else:
        combo_df["label"] = "default"

    practice_df = _repeat_rows(combo_df, n_practice, "pra")
    experiment_df = _repeat_rows(combo_df, n_trials, "exp")
    trial_df = pd.concat([practice_df, experiment_df], ignore_index=True)

    # Keep per-block order: all practice rows first, then experiment rows.
    trial_df = trial_df.assign(_row_order=range(len(trial_df))).sort_values(
        by=["block_id", "_stage", "_row_order"],
        kind="stable",
    )
    # trial_id is independent by trial type.
    trial_df["trial_id"] = trial_df.groupby("trial_type").cumcount() + 1

    condition_cols = []
    for key in block_key_order + mixed_key_order:
        if key not in condition_cols:
            condition_cols.append(key)
    out_cols = ["block_id", "trial_id", "trial_type", *condition_cols, "label"]

    return trial_df[out_cols].reset_index(drop=True)
