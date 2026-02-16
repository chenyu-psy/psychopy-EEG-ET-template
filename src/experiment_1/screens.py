"""Screen-level presentation helpers for Experiment 1."""


def show_instructions(exp) -> None:
    """Display experiment instructions."""
    exp.instruct()


def show_block_start(exp, block_label: str) -> None:
    """Display a block start prompt."""
    exp.display_text_screen(f"{block_label}\n\nPress space to start.", keyList=["space"])


def show_end(exp) -> None:
    """Display end-of-experiment prompt."""
    exp.display_text_screen("Done. Press space to exit.", keyList=["space"])


def show_break(exp, completed_trials: int, total_trials: int, performance: float | None) -> None:
    """Display a break screen with trial progress and current performance."""
    progress = (completed_trials / total_trials) * 100 if total_trials > 0 else 0.0
    if performance is None:
        perf_text = "N/A"
    else:
        perf_text = f"{performance:.1f}%"
    exp.display_text_screen(
        f"Take a short break.\n\nProgress: {progress:.1f}%\n"
        f"Current performance: {perf_text}\n\nPress space to continue.",
        keyList=["space"],
    )
