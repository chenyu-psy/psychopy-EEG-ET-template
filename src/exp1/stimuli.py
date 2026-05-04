"""Stimulus constructors for exp1."""

from psychopy import visual


def build_sample_stimulus(exp, symbol: str):
    """Return the main sample stimulus for a trial."""
    return visual.TextStim(
        exp.experiment_window,
        text=symbol,
        pos=(0, 0),
        height=1.2,
        color="#FFFFFF",
        colorSpace="hex",
        units="deg",
    )
