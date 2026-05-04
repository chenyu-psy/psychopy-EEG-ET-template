"""Base tracker experiment template utilities.

Author - Colin Quirk (cquirk@uchicago.edu)
Contributor - Chenyu Li
"""

import numpy as np
import os
import csv
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

# Configure runtime before PsychoPy import.
# Keep PsychoPy user data inside the project to avoid home-directory permission problems.
os.environ.setdefault("PSYCHOPY_USERAPPDIR", str(Path(__file__).resolve().parents[1] / ".psychopy"))

from psychopy import core, event, visual, tools, monitors, parallel

import errno

DEFAULT_MONITOR = {
    "name": "Monitor01",
    "distance": 90,
    "resolution": [1920, 1080],
    "width": 53,
    "fullscr": True,
}
DEFAULT_KEYS = ("z", "slash")
DEFAULT_BG_COLOR = "#7F7F7F"
DEFAULT_EYETRACKER_CONFIG = {"eye_max_dist": 1.25, "tracked_eye": "BOTH"}
DialogValue = Union[str, List[str], Tuple[str, ...]]
DEFAULT_USER_INPUT: Dict[str, DialogValue] = {
    "Subject": "",
    "Unique ID": "",
    "Age": "",
    "Gender": ["Male", "Female", "Others"],
}
def _load_eyelinker():
    """Import and return the eyelinker module lazily at runtime."""
    try:
        return importlib.import_module("src.utils.eyelinker")
    except ImportError:
        return importlib.import_module("utils.eyelinker")


def _load_psychopy_gui():
    """Import and return PsychoPy's GUI module when available.

    Returns
    -------
    module | None
        ``psychopy.gui`` module, or ``None`` if import fails (for example,
        missing Qt support on older Windows systems).
    """
    try:
        return importlib.import_module("psychopy.gui")
    except Exception as exc:
        print(f"[warn] psychopy.gui unavailable; using terminal prompts. Reason: {exc}")
        return None


def _load_tkinter():
    """Import and return tkinter modules when available.

    Returns
    -------
    tuple[module, module] | None
        ``(tkinter, tkinter.ttk)`` when imports succeed, otherwise ``None``.
    """
    try:
        tk_module = importlib.import_module("tkinter")
        ttk_module = importlib.import_module("tkinter.ttk")
        return tk_module, ttk_module
    except Exception as exc:
        print(f"[warn] tkinter unavailable; using terminal prompts. Reason: {exc}")
        return None


def _prompt_experiment_info_tkinter(exp_info: Dict[str, Any], title: str) -> Optional[Dict[str, str]]:
    """Collect participant info with a simple tkinter form.

    Parameters
    ----------
    exp_info : dict[str, Any]
        Current experiment-info defaults and choice lists.
    title : str
        Window title shown to the researcher.

    Returns
    -------
    dict[str, str] | None
        Updated participant info when the user clicks OK, else ``None``.
    """
    tkinter_modules = _load_tkinter()
    if tkinter_modules is None:
        return None

    tk_module, ttk_module = tkinter_modules
    root = tk_module.Tk()
    root.title(title)
    root.resizable(False, False)

    values: Dict[str, Any] = {}
    row_idx = 0
    ttk_module.Label(root, text="Enter participant info").grid(row=row_idx, column=0, columnspan=2, padx=12, pady=(10, 6), sticky="w")
    row_idx += 1

    for field, default_value in exp_info.items():
        ttk_module.Label(root, text=str(field)).grid(row=row_idx, column=0, padx=(12, 8), pady=4, sticky="w")
        if isinstance(default_value, (list, tuple)) and len(default_value) > 0:
            options = [str(v) for v in default_value]
            selected_value = tk_module.StringVar(value=options[0])
            widget = ttk_module.Combobox(root, textvariable=selected_value, values=options, state="readonly", width=24)
            widget.grid(row=row_idx, column=1, padx=(0, 12), pady=4, sticky="we")
            values[str(field)] = selected_value
        else:
            default_text = str(default_value) if default_value is not None else ""
            entry_value = tk_module.StringVar(value=default_text)
            widget = ttk_module.Entry(root, textvariable=entry_value, width=27)
            widget.grid(row=row_idx, column=1, padx=(0, 12), pady=4, sticky="we")
            values[str(field)] = entry_value
        row_idx += 1

    result: Dict[str, str] = {}
    was_confirmed = {"ok": False}

    def on_ok() -> None:
        """Store form values and close the dialog."""
        for field, value_var in values.items():
            result[field] = str(value_var.get()).strip()
        was_confirmed["ok"] = True
        root.destroy()

    def on_cancel() -> None:
        """Close the dialog without saving values."""
        root.destroy()

    button_frame = ttk_module.Frame(root)
    button_frame.grid(row=row_idx, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="e")
    ttk_module.Button(button_frame, text="OK", command=on_ok).grid(row=0, column=0, padx=(0, 6))
    ttk_module.Button(button_frame, text="Cancel", command=on_cancel).grid(row=0, column=1)
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()

    if not was_confirmed["ok"]:
        return None
    return result


def _prompt_subject_conflict_tkinter(subject_tag: str) -> Optional[str]:
    """Ask whether to overwrite, continue, or change the subject ID.

    Parameters
    ----------
    subject_tag : str
        Subject label that already has data on disk.

    Returns
    -------
    str | None
        ``"overwrite"``, ``"continue"``, or ``"change"`` when confirmed,
        else ``None``.
    """
    tkinter_modules = _load_tkinter()
    if tkinter_modules is None:
        return None

    tk_module, ttk_module = tkinter_modules
    root = tk_module.Tk()
    root.title("Existing Subject Data")
    root.resizable(False, False)

    ttk_module.Label(
        root,
        text=(
            f"Data already exists for {subject_tag}.\n"
            "Choose whether to overwrite, continue, or change Subject ID."
        ),
        justify="left",
    ).grid(row=0, column=0, columnspan=2, padx=12, pady=(10, 8), sticky="w")

    action_var = tk_module.StringVar(value="overwrite")
    ttk_module.Radiobutton(root, text="Overwrite existing data", variable=action_var, value="overwrite").grid(
        row=1, column=0, columnspan=2, padx=12, pady=2, sticky="w"
    )
    ttk_module.Radiobutton(root, text="Change Subject ID", variable=action_var, value="change").grid(
        row=2, column=0, columnspan=2, padx=12, pady=2, sticky="w"
    )
    ttk_module.Radiobutton(root, text="Continue existing study", variable=action_var, value="continue").grid(
        row=3, column=0, columnspan=2, padx=12, pady=2, sticky="w"
    )

    result: Dict[str, Optional[str]] = {"action": None}

    def on_ok() -> None:
        """Store the chosen action and close the dialog."""
        result["action"] = str(action_var.get())
        root.destroy()

    def on_cancel() -> None:
        """Close the dialog without choosing an action."""
        root.destroy()

    button_frame = ttk_module.Frame(root)
    button_frame.grid(row=4, column=0, columnspan=2, padx=12, pady=(8, 12), sticky="e")
    ttk_module.Button(button_frame, text="OK", command=on_ok).grid(row=0, column=0, padx=(0, 6))
    ttk_module.Button(button_frame, text="Cancel", command=on_cancel).grid(row=0, column=1)
    root.protocol("WM_DELETE_WINDOW", on_cancel)
    root.mainloop()

    action = result["action"]
    return str(action) if action is not None else None


class FixationCross:
    """Layered fixation stimulus used during task timing and feedback screens."""

    def __init__(self, monitor, window, bg_color, base_color="#000000"):
        """Build a Thaler-style fixation stimulus from layered PsychoPy shapes.

        Parameters
        ----------
        monitor : psychopy.monitors.Monitor
            Active monitor object used for degree-to-pixel conversions.
        window : psychopy.visual.Window
            Experiment window where fixation is drawn.
        bg_color : str
            Background HEX color (for example `#7F7F7F`).
        base_color : str, optional
            Inner/outer fixation HEX color.
        """
        self.experiment_monitor = monitor
        self.experiment_window = window
        self.bg_color = bg_color
        self.base_color = base_color
        # set up fixation shapes, based on Thaler et al., 2013
        self.fix_outer = visual.Circle(
            self.experiment_window,
            lineColor=None,
            fillColor=base_color,
            colorSpace="hex",
            radius=0.25,
            units="deg",
            interpolate=True,
        )
        self.fix_cross = visual.ShapeStim(
            self.experiment_window,
            vertices=((0, -0.26), (0, 0.26), (0, 0), (-0.26, 0), (0.26, 0)),
            lineWidth=tools.monitorunittools.deg2pix(0.16, self.experiment_monitor),
            closeShape=False,
            lineColor=self.bg_color,
            fillColor=None,
            colorSpace="hex",
        )
        self.fix_inner = visual.Circle(
            self.experiment_window,
            lineColor=None,
            fillColor=base_color,
            colorSpace="hex",
            radius=0.075,
            units="deg",
            interpolate=True,
        )

    def draw(self):
        """Draw fixation components for the current frame without flipping."""
        self.fix_outer.draw()
        self.fix_cross.draw()
        self.fix_inner.draw()

    def show(self):
        """Enable fixation `autoDraw` and immediately flip the window."""
        self.fix_outer.autoDraw = True
        self.fix_cross.autoDraw = True
        self.fix_inner.autoDraw = True
        self.experiment_window.flip()

    def hide(self):
        """Disable fixation `autoDraw` and immediately flip the window."""
        self.fix_outer.autoDraw = False
        self.fix_cross.autoDraw = False
        self.fix_inner.autoDraw = False
        self.experiment_window.flip()

    def set_color(self, color="#000000"):
        """Update the outer/inner fixation fill colors.

        Parameters
        ----------
        color : str, optional
            HEX color string.
        """
        self.fix_outer.fillColor = color
        self.fix_inner.fillColor = color


class EyeMovementError(Exception):
    """Signal that realtime gaze monitoring detected a fixation break."""

    def __init__(self, message, x, y):
        """Exception raised when gaze leaves the allowed fixation radius.

        Parameters
        ----------
        message : str
            Human-readable error message.
        x : float
            Horizontal gaze offset (pixels relative to screen center).
        y : float
            Vertical gaze offset (pixels relative to screen center).
        """
        super().__init__(message)
        self.x = x
        self.y = y


class BaseTrackerExp:
    """
    Class that handles basic experiment functionality (can probably be left unchanged)
    """

    def __init__(
        self,
        experiment_name,
        conditions,
        keys=DEFAULT_KEYS,
        monitor_details=DEFAULT_MONITOR,
        bg_color=DEFAULT_BG_COLOR,
        user_input=DEFAULT_USER_INPUT,
        eyetracker_config=None,
        do_realtime_eyetracking=True,
        text_color="#000000",
        min_redos=0,
        enable_global_pause=False,
        pause_action_key="p",
        pause_modifiers=("command", "ctrl"),
        drift_action_key="t",
        drift_modifiers=("command", "ctrl"),
    ):
        """Initialize shared configuration/state for an eyetracking experiment.

        Parameters
        ----------
        experiment_name : str
            Name shown in participant dialogs and logs.
        conditions : list[str]
            Condition labels used to initialize per-condition rejection counters.
        keys : iterable[str], optional
            Allowed response keys for `get_response()`.
        monitor_details : dict, optional
            Monitor configuration with keys like `name`, `width`, `distance`,
            and `resolution`.
        bg_color : str, optional
            Default background HEX color.
        user_input : dict, optional
            Default fields shown in the participant info dialog.
        eyetracker_config : dict | None, optional
            Eyetracker settings with keys:
            - ``"eye_max_dist"``: maximum fixation eccentricity in visual degrees.
            - ``"tracked_eye"``: one of `"LEFT"`, `"RIGHT"`, or `"BOTH"`.
        do_realtime_eyetracking : bool, optional
            Whether realtime gaze monitoring is enabled when requested by task code.
        text_color : str, optional
            Default HEX color for text and prompt screens. Individual screens can
            override this by passing ``text_color`` or ``prompt_args["color"]``.
        min_redos : int, optional
            Initial value added to each condition's rejection counter.
        enable_global_pause : bool, optional
            Whether to register a global pause shortcut when opening the window.
        pause_action_key : str, optional
            Keyboard key used with modifiers for global pause (for example, `p`).
        pause_modifiers : tuple[str, ...], optional
            Modifier names used for global pause (for example, `("command", "ctrl")`).
        drift_action_key : str, optional
            Keyboard key used with modifiers to request drift correction before
            the next trial checkpoint (for example, `t`).
        drift_modifiers : tuple[str, ...], optional
            Modifier names used for the drift-correction shortcut.
        """
        self.monitor_details = monitor_details
        self.bg_color = bg_color
        self.text_color = text_color
        self.exp_info: Dict[str, DialogValue] = dict(user_input)
        self.keys = keys
        self.experiment_name = experiment_name

        merged_eyetracker_config = dict(DEFAULT_EYETRACKER_CONFIG)
        if eyetracker_config is not None:
            merged_eyetracker_config.update(eyetracker_config)
        self.eyetracker_config = merged_eyetracker_config

        self.eye_max_dist = float(self.eyetracker_config["eye_max_dist"])
        self.tracked_eye = str(self.eyetracker_config["tracked_eye"]).upper()
        if self.tracked_eye not in ("LEFT", "RIGHT", "BOTH"):
            raise ValueError("tracked_eye must be LEFT, RIGHT, or BOTH.")
        self.realtime_eyetrack_enabled = do_realtime_eyetracking
        self.realtime_monitor_active = False
        self.rejection_counter = {key: 0 + min_redos for key in conditions}
        self.row_rejected = 0
        self.row_rejected_drift_done = False
        self.experiment_window: Any = None
        self.tracker: Any = None
        self.port: Any = None
        self.pause_exp = False
        self.request_drift_correct = False
        self.enable_global_pause = bool(enable_global_pause)
        self.pause_action_key = str(pause_action_key).strip().lower() or "p"
        self.pause_modifiers = tuple(str(mod).strip().lower() for mod in pause_modifiers if str(mod).strip())
        self.drift_action_key = str(drift_action_key).strip().lower() or "t"
        self.drift_modifiers = tuple(str(mod).strip().lower() for mod in drift_modifiers if str(mod).strip())
        self._pause_shortcuts_registered = False
        self._drift_shortcuts_registered = False
        self.subject_dir_action = "new"
        self._missing_tracker_warning_shown = False

    def is_eyetracking_active(self, functionality=None):
        """Validate that a tracker exists and optionally supports a method.

        Parameters
        ----------
        functionality : str | None
            Method name that must exist on `self.tracker` (for example
            `"calibrate"`). If omitted, only tracker existence is checked.

        Returns
        -------
        bool
            `True` when the requested eyetracking functionality is available.

        Side Effects
        ------------
        Prints one warning the first time realtime eyetracking is requested
        before a tracker session has been initialized.
        """
        if self.tracker is None:
            # In non-eyetracking sessions (e.g., EEG-only runs), missing tracker
            # is expected and should not spam console output.
            if (
                bool(getattr(self, "realtime_eyetrack_enabled", False))
                and not bool(getattr(self, "_missing_tracker_warning_shown", False))
            ):
                print("Eye tracker not initialized.")
                self._missing_tracker_warning_shown = True
            return False
        elif functionality is not None and not hasattr(self.tracker, functionality):
            print(f"Eye tracker does not have '{functionality}' functionality.")
            return False
        else:
            return True

    def set_realtime_monitoring(self, active: bool) -> None:
        """Turn realtime gaze monitoring on or off for the current task phase.

        Parameters
        ----------
        active : bool
            `True` to start online fixation monitoring, `False` to stop it.

        Returns
        -------
        None
            Updates `self.realtime_monitor_active`. Monitoring only runs when
            realtime eyetracking is enabled for the session.

        Notes
        -----
        Realtime monitoring stays off until a tracker object exists. This
        avoids repeated polling and console spam during phases that run before
        EyeLink initialization.
        """
        tracker_ready = self.tracker is not None
        self.realtime_monitor_active = (
            bool(active)
            and bool(self.realtime_eyetrack_enabled)
            and tracker_ready
        )

    def reset_missing_tracker_warning(self) -> None:
        """Allow one new missing-tracker warning for the next trial.

        Returns
        -------
        None
            Resets the one-warning guard used by ``is_eyetracking_active()``.
        """
        self._missing_tracker_warning_shown = False

    def start_realtime_monitoring(self) -> None:
        """Start realtime gaze monitoring for upcoming task phases.

        Returns
        -------
        None
            Convenience wrapper around `set_realtime_monitoring(True)`.
        """
        self.set_realtime_monitoring(True)

    def stop_realtime_monitoring(self) -> None:
        """Stop realtime gaze monitoring for upcoming task phases.

        Returns
        -------
        None
            Convenience wrapper around `set_realtime_monitoring(False)`.
        """
        self.set_realtime_monitoring(False)

    def chdir(self):
        """Create and switch into `./subject_data` for output files."""

        try:
            os.makedirs("./subject_data")
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        os.chdir("./subject_data")

    def open_window(self, **kwargs):
        """Create monitor, PsychoPy window, and default fixation stimulus.

        Parameters
        ----------
        **kwargs
            Forwarded directly to `psychopy.visual.Window`.
        """
        self.experiment_monitor = monitors.Monitor(
            self.monitor_details["name"], width=self.monitor_details["width"], distance=self.monitor_details["distance"]
        )
        self.experiment_monitor.setSizePix(self.monitor_details["resolution"])
        window_kwargs = {
            "monitor": self.experiment_monitor,
            "fullscr": bool(self.monitor_details.get("fullscr", True)),
            "size": list(self.monitor_details["resolution"]),
            "color": self.bg_color,
            "colorSpace": "hex",
            "units": "deg",
            "allowGUI": False,
        }
        window_kwargs.update(kwargs)
        self.experiment_window = visual.Window(**window_kwargs)

        self.fixation = FixationCross(self.experiment_monitor, self.experiment_window, self.bg_color)
        # Register a global emergency quit key available across screens/tasks.
        # Use platform-specific key combos and avoid OS-reserved shortcuts.
        quit_shortcuts = self._get_quit_shortcuts()
        global_keys = cast(Any, event.globalKeys)
        try:
            global_keys.remove("escape")
        except Exception:
            pass
        for quit_key, quit_modifier in quit_shortcuts:
            try:
                global_keys.remove(quit_key, modifiers=[quit_modifier])
            except Exception:
                pass
            try:
                global_keys.add(
                    key=quit_key,
                    modifiers=[quit_modifier],
                    func=self._quit_from_global_key,
                    name=f"quit_{quit_modifier}_{quit_key}",
                )
            except ValueError:
                # Keep running if one modifier alias is unavailable on this backend.
                continue
        self._register_pause_shortcuts()
        self._register_drift_shortcuts()

    def _get_quit_shortcuts(self) -> List[Tuple[str, str]]:
        """Return platform-appropriate global quit shortcuts.

        Returns
        -------
        list[tuple[str, str]]
            `(key, modifier)` pairs for global emergency quit.

        Notes
        -----
        Windows reserves ``Ctrl+Esc`` for the Start menu, which can freeze or
        background full-screen PsychoPy windows on older systems. To avoid
        that OS conflict, all platforms use ``Ctrl+Q`` here.
        """
        return [("q", "ctrl")]

    def _quit_from_global_key(self) -> None:
        """Handle modified-ESC global quit safely inside pyglet callback context.

        Returns
        -------
        None
            Terminates the process after closing the window.

        Notes
        -----
        Calling ``core.quit()`` from a pyglet key callback raises ``SystemExit``.
        Some callback paths can surface that exception without fully stopping the
        app loop. This wrapper guarantees termination for emergency modifier+ESC quits.
        """
        try:
            self.quit_experiment()
        except SystemExit:
            # Fallback hard-exit for callback contexts that intercept SystemExit.
            os._exit(0)

    def _set_pause_flag(self) -> None:
        """Set the experiment pause flag from a global key callback.

        Returns
        -------
        None
            Updates `self.pause_exp` only.
        """
        self.pause_exp = True

    def _register_pause_shortcuts(self) -> None:
        """Register cross-platform global pause shortcuts when enabled.

        Returns
        -------
        None
            Adds global key handlers for configured pause modifiers + key.
        """
        if not self.enable_global_pause or self._pause_shortcuts_registered:
            return
        if not self.pause_modifiers:
            return
        global_keys = cast(Any, event.globalKeys)
        for modifier in self.pause_modifiers:
            shortcut_name = f"pause_{modifier}_{self.pause_action_key}"
            global_keys.add(
                key=self.pause_action_key,
                modifiers=[modifier],
                func=self._set_pause_flag,
                name=shortcut_name,
            )
        self._pause_shortcuts_registered = True

    def _set_drift_correct_flag(self) -> None:
        """Queue one drift correction to run at the next trial checkpoint.

        Returns
        -------
        None
            Updates ``self.request_drift_correct`` only.
        """
        self.request_drift_correct = True

    def _register_drift_shortcuts(self) -> None:
        """Register global drift-correction shortcuts when enabled.

        Returns
        -------
        None
            Adds global key handlers for configured drift modifiers + key.
        """
        if not self.enable_global_pause or self._drift_shortcuts_registered:
            return
        if not self.drift_modifiers:
            return
        global_keys = cast(Any, event.globalKeys)
        for modifier in self.drift_modifiers:
            shortcut_name = f"drift_{modifier}_{self.drift_action_key}"
            global_keys.add(
                key=self.drift_action_key,
                modifiers=[modifier],
                func=self._set_drift_correct_flag,
                name=shortcut_name,
            )
        self._drift_shortcuts_registered = True

    def show_pause_screen(self) -> str:
        """Display default researcher pause screen and return selected action.

        Returns
        -------
        str
            Lowercase action key:
            `e` for calibration and `return` for direct continue.
        """
        pressed = self.display_text_screen(
            "The experiment is paused by the researcher.\n\n"
            "Please wait for the next step.",
            keyList=["e", "return", "num_enter"],
        )
        if pressed:
            return str(pressed[0]).lower()
        return "return"

    def handle_pause_if_requested(self) -> str:
        """Handle researcher pause or drift-correction requests.

        Returns
        -------
        str
            Pause action outcome:
            `no_pause`, `continue`, `calibrate`, or `drift_correct`.
        """
        if not self.pause_exp:
            if self.request_drift_correct:
                self.request_drift_correct = False
                if self.is_eyetracking_active("drift_correct"):
                    self.tracker.drift_correct()
                    return "drift_correct"
            return "no_pause"
        self.pause_exp = False
        event.clearEvents(eventType="keyboard")
        pause_choice = self.show_pause_screen()
        if pause_choice == "e":
            if self.is_eyetracking_active("calibrate"):
                self.tracker.calibrate()
            return "calibrate"
        if self.is_eyetracking_active("drift_correct"):
            self.tracker.drift_correct()
            return "drift_correct"
        return "continue"

    def handle_rejection_pause(self) -> str:
        """Handle the eye-tracker recovery pause after repeated rejections.

        Returns
        -------
        str
            Action taken after the pause:
            `calibrate` when the researcher presses `c`, `drift_correct`
            when the researcher presses `return`, otherwise `continue`.

        Notes
        -----
        This screen is only shown after repeated online eye-movement
        rejections. `Return` keeps the recovery step small by re-running
        drift correction, while `c` opens full calibration when the tracker
        appears to have drifted more substantially.
        """
        pressed = self.display_text_screen(
            text=(
                "There may be a problem with the eye tracker.\n"
                "Please wait for the researcher to check the setup."
            ),
            keyList=["c", "return", "num_enter"],
            # Use a distinct alert background so the researcher can spot this
            # recovery screen immediately during data collection.
            bg_color="#E9954D",
            text_color="#FFFFFF",
        )
        choice = str(pressed[0]).lower() if pressed else "return"
        if choice == "c":
            if self.is_eyetracking_active("calibrate"):
                self.tracker.calibrate()
            return "calibrate"
        if self.is_eyetracking_active("drift_correct"):
            self.tracker.drift_correct()
            return "drift_correct"
        return "continue"

    def append_key_event(
        self,
        key_log: Dict[str, List[Dict[str, Any]]],
        phase: str,
        key: str,
        t: float,
    ) -> None:
        """Append one key event to a phase-specific key log.

        Parameters
        ----------
        key_log : dict[str, list[dict[str, Any]]]
            Mutable key-event dictionary for the current trial.
        phase : str
            Phase name (for example ``"fixation"`` or ``"sample"``).
        key : str
            Pressed key name returned by PsychoPy.
        t : float
            Event time (seconds) relative to the provided trial clock.

        Returns
        -------
        None
            Updates ``key_log`` in place.
        """
        if phase not in key_log:
            key_log[phase] = []
        key_log[phase].append({"time": float(t), "key": str(key)})

    def collect_key_events(
        self,
        key_log: Dict[str, List[Dict[str, Any]]],
        phase: str,
        trial_clock,
        key_list: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Collect queued keys and assign them to one phase.

        Parameters
        ----------
        key_log : dict[str, list[dict[str, Any]]]
            Mutable key-event dictionary for the current trial.
        phase : str
            Phase name used for event grouping in ``key_log``.
        trial_clock
            PsychoPy clock used for event timestamps.
        key_list : list[str] | None, optional
            Optional key filter passed to ``event.getKeys``.

        Returns
        -------
        list[dict[str, Any]]
            Newly collected events for this call.
        """
        get_keys = cast(Any, event.getKeys)
        keys = get_keys(keyList=key_list, timeStamped=trial_clock)
        collected: List[Dict[str, Any]] = []
        for key, timestamp in keys:
            event_row = {"time": float(timestamp), "key": str(key)}
            collected.append(event_row)
            self.append_key_event(key_log, phase, str(key), float(timestamp))
        return collected

    def quit_experiment(self):
        """Close the window (if open) and terminate the process."""
        if self.experiment_window is not None:
            self.experiment_window.close()
        print("The experiment has ended")
        # PsychoPy's quit path is safer than `sys.exit` from key callbacks.
        core.quit()

    def display_text_screen(
        self,
        text="",
        text_color=None,
        text_height=36,
        bg_color=None,
        keyList=["space"],
        min_wait=0.2,
        show_fixation=False,
        prompt=None,
        prompt_args=None,
        end_after_resp=True,
        wait_time=None,
        **kwargs,
    ):
        """Draw a centered text screen and wait for a key response.

        Parameters
        ----------
        text : str, optional
            Message to display.
        text_color : str | None, optional
            HEX text color; defaults to ``self.text_color``.
        text_height : int, optional
            Text height in pixels.
        bg_color : str | None, optional
            HEX screen color; defaults to `self.bg_color`.
        keyList : list[str], optional
            Accepted keys for continuing.
        min_wait : float, optional
            Delay before key collection to reduce accidental key carryover.
        show_fixation : bool, optional
            Whether fixation should be visible during this text screen.
        prompt : str | None, optional
            Optional prompt text drawn near the bottom of the screen
            (for example, "Press space to continue.").
        prompt_args : dict | None, optional
            Extra arguments forwarded to ``psychopy.visual.TextStim`` for the
            prompt. Defaults use ``units="height"``, ``height=0.03``, and
            bottom placement.
        end_after_resp : bool, optional
            If True, the screen ends as soon as an allowed key is pressed.
            If False, the screen stays visible until `wait_time` elapses.
        wait_time : float | None, optional
            Time in seconds before automatic continuation. Required when
            `keyList` is empty or when `end_after_resp` is False.
        **kwargs
            Extra arguments forwarded to `psychopy.visual.TextStim`.

        Returns
        -------
        list[str] | None
            Value returned by `psychopy.event.waitKeys`.
        """

        if bg_color is None:
            bg_color = self.bg_color
        if text_color is None:
            text_color = self.text_color

        if hasattr(self, "fixation") and self.fixation is not None:
            self.fixation.fix_outer.autoDraw = show_fixation
            self.fixation.fix_cross.autoDraw = show_fixation
            self.fixation.fix_inner.autoDraw = show_fixation

        backgroundRect = visual.Rect(
            self.experiment_window, fillColor=bg_color, colorSpace="hex", units="norm", width=2, height=2
        )

        textObject = visual.TextStim(
            self.experiment_window,
            text=text,
            color=text_color,
            colorSpace="hex",
            units="pix",
            height=text_height,
            alignHoriz="center",
            alignVert="center",
            wrapWidth=round(0.8 * self.experiment_window.size[0]),
            **kwargs,
        )

        backgroundRect.draw()
        textObject.draw()
        if prompt:
            prompt_cfg = {
                "text": str(prompt),
                "color": self.text_color,
                "colorSpace": "hex",
                "units": "height",
                "height": 0.03,
                "pos": (0.0, -0.45),
                "alignHoriz": "center",
                "alignVert": "center",
                "wrapWidth": 1.6,
            }
            prompt_cfg.update(dict(prompt_args or {}))
            visual.TextStim(self.experiment_window, **prompt_cfg).draw()
        self.experiment_window.flip()

        core.wait(min_wait)  # Prevents accidental key presses
        allowed_keys = list(keyList) if keyList is not None else []

        if not allowed_keys:
            if wait_time is None:
                raise ValueError("wait_time must be provided when keyList is empty.")
            core.wait(float(wait_time))
            return None

        if end_after_resp:
            if wait_time is None:
                return event.waitKeys(keyList=allowed_keys)
            return event.waitKeys(keyList=allowed_keys, maxWait=float(wait_time))

        if wait_time is None:
            raise ValueError("wait_time must be provided when end_after_resp is False.")

        pressed_key = None
        start_time = core.getTime()
        while core.getTime() < start_time + float(wait_time):
            keys = event.getKeys(keyList=allowed_keys)
            if keys and pressed_key is None:
                pressed_key = [keys[0]]
            core.wait(0.01)
        return pressed_key

    def display_image_screen(
        self,
        image,
        bg_color=None,
        keyList=["space"],
        min_wait=0.2,
        show_fixation=False,
        image_units="pix",
        image_size=None,
        scale: Union[float, str] = 1.0,
        pos=(0, 0),
        prompt=None,
        prompt_args=None,
        end_after_resp=True,
        wait_time=None,
        **kwargs,
    ):
        """Draw a centered image screen and wait for a key response.

        Parameters
        ----------
        image : str | pathlib.Path | array-like
            Image source passed to ``psychopy.visual.ImageStim``.
        bg_color : str | None, optional
            HEX screen color; defaults to ``self.bg_color``.
        keyList : list[str], optional
            Accepted keys for continuing.
        min_wait : float, optional
            Delay before key collection to reduce accidental key carryover.
        show_fixation : bool, optional
            Whether fixation should be visible during this image screen.
        image_units : str, optional
            Units used for image position/size (for example ``"pix"`` or ``"deg"``).
        image_size : tuple[float, float] | None, optional
            Optional image size forwarded to ``ImageStim(size=...)``.
        scale : float | str, optional
            Image scale factor. Use ``"auto"`` to fit image to window while
            preserving aspect ratio, or a positive numeric multiplier.
        pos : tuple[float, float], optional
            Image position in ``image_units``.
        prompt : str | None, optional
            Optional prompt text drawn on top of the image (for example,
            "Press space to continue.").
        prompt_args : dict | None, optional
            Extra arguments forwarded to ``psychopy.visual.TextStim`` for the
            prompt. Defaults place prompt text near the bottom of screen,
            use ``units="height"``, set ``height=0.03``, and use
            ``self.text_color``.
        end_after_resp : bool, optional
            If True, the screen ends as soon as an allowed key is pressed.
            If False, the screen stays visible until `wait_time` elapses.
        wait_time : float | None, optional
            Time in seconds before automatic continuation. Required when
            `keyList` is empty or when `end_after_resp` is False.
        **kwargs
            Extra arguments forwarded to ``psychopy.visual.ImageStim``.

        Returns
        -------
        list[str] | None
            Value returned by ``psychopy.event.waitKeys``.
        """
        if bg_color is None:
            bg_color = self.bg_color

        if hasattr(self, "fixation") and self.fixation is not None:
            self.fixation.fix_outer.autoDraw = show_fixation
            self.fixation.fix_cross.autoDraw = show_fixation
            self.fixation.fix_inner.autoDraw = show_fixation

        background_rect = visual.Rect(
            self.experiment_window, fillColor=bg_color, colorSpace="hex", units="norm", width=2, height=2
        )

        image_kwargs = dict(kwargs)
        if image_size is not None and "size" not in image_kwargs:
            image_kwargs["size"] = image_size
        stim_units = "norm" if scale == "auto" else image_units
        image_stim = visual.ImageStim(
            self.experiment_window,
            image=str(image),
            pos=pos,
            units=stim_units,
            **image_kwargs,
        )
        if scale == "auto":
            frame_size = getattr(self.experiment_window, "frameBufferSize", None)
            if frame_size is not None and len(frame_size) == 2:
                win_w, win_h = (float(v) for v in frame_size)
            else:
                win_w, win_h = (float(v) for v in self.experiment_window.size)
            native_size = getattr(image_stim, "_origSize", None)
            if native_size is not None and len(native_size) == 2:
                img_w, img_h = (abs(float(v)) for v in native_size)
            else:
                img_w, img_h = (abs(float(v)) for v in image_stim.size)
            if win_w > 0 and win_h > 0 and img_w > 0 and img_h > 0:
                win_ratio = win_w / win_h
                img_ratio = img_w / img_h
                if img_ratio >= win_ratio:
                    fit_w = 2.0
                    fit_h = 2.0 * (win_ratio / img_ratio)
                else:
                    fit_h = 2.0
                    fit_w = 2.0 * (img_ratio / win_ratio)
                image_stim.size = (fit_w, fit_h)
            else:
                image_stim.size = (2.0, 2.0)
        elif isinstance(scale, (int, float)) and not isinstance(scale, bool):
            if float(scale) <= 0:
                raise ValueError("scale must be > 0 when numeric.")
            if float(scale) != 1.0:
                stim_w, stim_h = (float(v) for v in image_stim.size)
                image_stim.size = (stim_w * float(scale), stim_h * float(scale))
        else:
            raise ValueError("scale must be either 'auto' or a positive number.")

        background_rect.draw()
        image_stim.draw()
        if prompt:
            prompt_cfg = {
                "text": str(prompt),
                "color": self.text_color,
                "colorSpace": "hex",
                "units": "height",
                "height": 0.03,
                "pos": (0.0, -0.45),
                "alignHoriz": "center",
                "alignVert": "center",
                "wrapWidth": 1.6,
            }
            prompt_cfg.update(dict(prompt_args or {}))
            visual.TextStim(self.experiment_window, **prompt_cfg).draw()
        self.experiment_window.flip()

        core.wait(min_wait)
        allowed_keys = list(keyList) if keyList is not None else []

        if not allowed_keys:
            if wait_time is None:
                raise ValueError("wait_time must be provided when keyList is empty.")
            core.wait(float(wait_time))
            return None

        if end_after_resp:
            if wait_time is None:
                return event.waitKeys(keyList=allowed_keys)
            return event.waitKeys(keyList=allowed_keys, maxWait=float(wait_time))

        if wait_time is None:
            raise ValueError("wait_time must be provided when end_after_resp is False.")

        pressed_key = None
        start_time = core.getTime()
        while core.getTime() < start_time + float(wait_time):
            keys = event.getKeys(keyList=allowed_keys)
            if keys and pressed_key is None:
                pressed_key = [keys[0]]
            core.wait(0.01)
        return pressed_key

    def display_fixation(self, wait_time=np.inf, text=None, keyList=None, show=True, color=None):
        """Show/hide fixation and optionally gate progress by time or key press.

        Parameters
        ----------
        wait_time : float, optional
            Duration to wait in seconds when `keyList` is not provided.
        text : str | None, optional
            Optional text drawn above fixation.
        keyList : list[str] | None, optional
            If provided, waits for one of these keys (or until `wait_time`).
        show : bool, optional
            Whether fixation should be visible during the call.
        color : str | None, optional
            Optional temporary fixation color (for example `#FFFFFF`) used for
            this call only.

        Returns
        -------
        bool | tuple | None
            Returns realtime rejection output when monitoring is active;
            otherwise returns `None`.

        Notes
        -----
        This method restores fixation ``autoDraw`` state before returning so
        fixation only remains visible for the duration of this call.
        """
        # wait_time = wait_time / 1000 # convert ms to s
        old_fix_color = None
        old_fix_autodraw = None
        if color is not None and hasattr(self, "fixation") and self.fixation is not None:
            old_fix_color = self.fixation.fix_outer.fillColor
            self.fixation.set_color(color)
        if hasattr(self, "fixation") and self.fixation is not None:
            old_fix_autodraw = (
                self.fixation.fix_outer.autoDraw,
                self.fixation.fix_cross.autoDraw,
                self.fixation.fix_inner.autoDraw,
            )
        try:
            if text:
                visual.TextStim(
                    win=self.experiment_window,
                    text=text,
                    pos=[0, 1],
                    color="#FF0000",
                    colorSpace="hex",
                ).draw()
            if show:
                self.fixation.show()
            else:
                self.fixation.hide()

            if self.realtime_monitor_active:
                reject = self.wait_with_realtime_monitoring(wait_time=wait_time)
                return reject

            if keyList:
                resp = event.waitKeys(maxWait=wait_time, keyList=keyList)
                if resp == ["p"]:
                    self.display_text_screen(text="Paused", keyList=["space"])
                    self.display_fixation(wait_time=1)
                elif resp == ["o"]:
                    if self.is_eyetracking_active("calibrate"):
                        self.tracker.calibrate()
                    self.display_fixation(wait_time=1)
                elif resp == ["escape"]:
                    resp = self.display_text_screen(text="Are you sure you want to exit?", keyList=["y", "n"])
                    if resp == ["y"]:
                        self.experiment_window.saveFrameIntervals()
                        print("Overall, %i frames were dropped." % self.experiment_window.nDroppedFrames)
                        self.quit_experiment()
                    else:
                        self.display_fixation(wait_time=1)
            else:
                core.wait(wait_time)
        finally:
            if old_fix_autodraw is not None:
                self.fixation.fix_outer.autoDraw = old_fix_autodraw[0]
                self.fixation.fix_cross.autoDraw = old_fix_autodraw[1]
                self.fixation.fix_inner.autoDraw = old_fix_autodraw[2]
            if old_fix_color is not None:
                self.fixation.set_color(old_fix_color)

    def draw_trak(self, x=930, y=510):
        """Draw a white tracker marker circle at pixel coordinates.

        Parameters
        ----------
        x : int, optional
            Horizontal pixel coordinate.
        y : int, optional
            Vertical pixel coordinate.
        """
        trak = visual.Circle(
            self.experiment_window,
            lineColor=None,
            fillColor="#FFFFFF",
            colorSpace="hex",
            radius=20,
            pos=[x, y],
            units="pix",
        )

        trak.draw()

    def et_instruct(self):
        """Display eyetracking instructions and open tracker setup if available."""
        if not self.is_eyetracking_active("display_eyetracking_instructions"):
            return
        self.tracker.display_eyetracking_instructions()
        self.tracker.setup_tracker()

    def get_response(self):
        """Collect a key response and return `(key, rt_ms)`.

        Returns
        -------
        tuple[str, float]
            Pressed key and response time in milliseconds.
        """
        rt_timer = core.MonotonicClock()

        core.wait(0.1)

        # Cast suppresses incomplete type hints where `timeStamped` may be typed as bool-only.
        wait_keys = cast(Any, event.waitKeys)
        resp = wait_keys(keyList=self.keys, timeStamped=rt_timer)
        if not resp:
            return "", float("nan")

        return resp[0][0], resp[0][1] * 1000  # key and rt in milliseconds

    def get_experiment_info_from_dialog(self, screen=0, save_info=True, info_path=None, overwrite_info=False):
        """Show participant info dialog and save metadata CSV.

        Parameters
        ----------
        screen : int, optional
            Display index where the dialog should appear.
        save_info : bool, optional
            Whether to write participant info CSV immediately.
        info_path : str | os.PathLike | None, optional
            Optional output path for participant info CSV when ``save_info`` is True.
        overwrite_info : bool, optional
            Whether participant info CSV should overwrite existing files.

        Returns
        -------
        bool
            Dialog confirmation state (`True` when user clicks OK).
        """
        gui_module = _load_psychopy_gui()
        used_gui_backend = "psychopy"
        if gui_module is not None:
            # Modifies experiment_info dict directly.
            # Cast suppresses incomplete type hints for PsychoPy dialog kwargs like `screen`.
            dlg_from_dict = cast(Any, gui_module.DlgFromDict)
            # PsychoPy 2024 Qt backends differ across machines: some expect an
            # integer screen index, others expect a Qt screen object. To keep
            # behavior stable on Win7/Win11, always use Qt's default screen.
            exp_info = dlg_from_dict(
                self.exp_info,
                title=self.experiment_name,
                tip={"Unique subject Identifier": "From the cronus log"},
            )
            self.exp_info = exp_info.dictionary
            ok = bool(exp_info.OK)
        else:
            tkinter_info = _prompt_experiment_info_tkinter(self.exp_info, self.experiment_name)
            if tkinter_info is not None:
                self.exp_info = tkinter_info
                ok = True
                used_gui_backend = "tkinter"
            else:
                # Final fallback for environments where GUI toolkits cannot load.
                used_gui_backend = "terminal"
                print(f"\n{self.experiment_name}: enter participant info (leave blank for defaults).")
                updated_info = dict(self.exp_info)
                for field, default_value in self.exp_info.items():
                    if isinstance(default_value, (list, tuple)) and len(default_value) > 0:
                        options = [str(v) for v in default_value]
                        options_text = "/".join(options)
                        raw_val = input(f"{field} [{options_text}] (default={options[0]}): ").strip()
                        updated_info[field] = raw_val if raw_val else options[0]
                    else:
                        default_text = str(default_value) if default_value is not None else ""
                        raw_val = input(f"{field} (default={default_text}): ").strip()
                        updated_info[field] = raw_val if raw_val else default_text
                self.exp_info = updated_info
                ok = True

        if not ok:
            return False

        # Normalize dialog outputs from different GUI backends to plain strings.
        if used_gui_backend in {"psychopy", "tkinter", "terminal"}:
            self.exp_info = {key: str(value) for key, value in self.exp_info.items()}
        subject_value = self.exp_info["Subject"]
        if isinstance(subject_value, (list, tuple)):
            raise TypeError("Subject field must be a single value, not a list of choices.")
        self.sub_num = int(subject_value)
        if save_info:
            output_path = info_path or f"sub{self.sub_num:02d}_info.csv"
            self.save_experiment_info_csv(output_path, overwrite=overwrite_info)

        return ok

    def save_experiment_info_csv(self, path, overwrite=False):
        """Write participant info metadata CSV.

        Parameters
        ----------
        path : str | os.PathLike
            Destination CSV file path.
        overwrite : bool, optional
            If True, overwrite existing file. If False, fail on existing file.
        """
        mode = "w" if overwrite else "x"
        with open(path, mode, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.exp_info.keys())
            writer.writeheader()
            writer.writerow(self.exp_info)

    def resolve_subject_dir(self, data_root, screen=0, subject_prefix="sub"):
        """Resolve subject output directory, prompting on ID conflicts.

        Parameters
        ----------
        data_root : str | os.PathLike
            Base directory where experiment data is stored.
        screen : int, optional
            Display index where dialogs should appear.
        subject_prefix : str, optional
            Prefix used for per-subject folder and file names (e.g., ``"sub"``).

        Returns
        -------
        pathlib.Path | None
            Subject directory when confirmed, or ``None`` if cancelled.

        Side effects
        ------------
        Sets ``self.subject_dir_action`` to one of ``"new"``,
        ``"overwrite"``, or ``"continue"`` so experiment code can decide
        whether to create fresh output files or resume an existing study.
        """
        experiment_data_dir = Path(data_root) / self.experiment_name
        gui_module = _load_psychopy_gui()

        while True:
            ok = self.get_experiment_info_from_dialog(screen=screen, save_info=False)
            if not ok:
                return None

            subject_tag = f"{subject_prefix}{self.sub_num:02d}"
            subject_data_dir = experiment_data_dir / subject_tag
            has_existing_data = subject_data_dir.exists() and any(subject_data_dir.iterdir())
            overwrite = False
            continue_existing = False

            if has_existing_data:
                if gui_module is not None:
                    dlg = cast(Any, gui_module.Dlg)
                    conflict_dlg = dlg(title="Existing Subject Data")
                    conflict_dlg.addText(
                        f"Data already exists for {subject_tag}.\n"
                        "Choose whether to overwrite, continue, or change Subject ID."
                    )
                    conflict_dlg.addField(
                        "Action",
                        choices=[
                            "Overwrite existing data",
                            "Continue existing study",
                            "Change Subject ID",
                        ],
                    )
                    # Hide PsychoPy's default "required fields" helper text for this selector dialog.
                    if hasattr(conflict_dlg, "requiredMsg"):
                        conflict_dlg.requiredMsg.hide()
                    conflict_dlg.show()

                    if not conflict_dlg.OK:
                        return None

                    if conflict_dlg.data[0] == "Change Subject ID":
                        continue
                    if conflict_dlg.data[0] == "Continue existing study":
                        continue_existing = True
                    else:
                        overwrite = True
                else:
                    conflict_action = _prompt_subject_conflict_tkinter(subject_tag)
                    if conflict_action is None:
                        print(
                            f"\nData already exists for {subject_tag}.\n"
                            "Type O to overwrite, T to continue this study, "
                            "C to choose another Subject ID, or Q to quit."
                        )
                        response = input("[O/T/C/Q]: ").strip().lower()
                        if response in {"q", "quit"}:
                            return None
                        if response in {"c", "change"}:
                            continue
                        if response in {"t", "continue"}:
                            continue_existing = True
                        else:
                            overwrite = True
                    elif conflict_action == "change":
                        continue
                    elif conflict_action == "continue":
                        continue_existing = True
                    else:
                        overwrite = True

            subject_data_dir.mkdir(parents=True, exist_ok=True)
            info_file = subject_data_dir / f"{subject_tag}_info.csv"
            if continue_existing:
                self.subject_dir_action = "continue"
            elif overwrite:
                self.subject_dir_action = "overwrite"
                self.save_experiment_info_csv(info_file, overwrite=True)
            else:
                self.subject_dir_action = "new"
                self.save_experiment_info_csv(info_file, overwrite=False)
            return subject_data_dir

    def et_initialize(self, edf_fname):
        """Initialize EyeLink hardware/session and run setup screens.

        Parameters
        ----------
        edf_fname : str
            EDF filename to create on the EyeLink host.
        """

        self.pix_radius = tools.monitorunittools.deg2pix(self.eye_max_dist, self.experiment_monitor)

        # initialize eye tracker
        try:
            eyelinker = _load_eyelinker()
        except Exception as exc:
            raise RuntimeError(
                "Failed to import utils.eyelinker. Check pylink/EyeLink installation "
                "(e.g., missing EyeLinkCustomDisplay in pylink)."
            ) from exc
        self.tracker = eyelinker.EyeLinker(self.experiment_window, edf_fname, self.tracked_eye)
        if not self.is_eyetracking_active("initialize_graphics"):
            return
        self.tracker.initialize_graphics()
        self.tracker.open_edf()
        self.tracker.initialize_tracker()
        self.tracker.send_tracking_settings()
        # enter basic setup menu
        self.tracker.display_eyetracking_instructions()
        self.tracker.setup_tracker()

        

    def et_conclude(self, new_filename=None):
        """Finalize eyetracking, transfer EDF to local machine, and close connection.

        Parameters
        ----------
        new_filename : str | None, optional
            Optional destination EDF filename/path used during transfer.
        """
        if not self.is_eyetracking_active("set_offline_mode"):
            return
        tracker = self.tracker
        try:
            # Some EyeLink runtime stacks need recording to be stopped and the
            # host briefly left offline before the EDF can be closed cleanly.
            if hasattr(tracker, "stop_recording"):
                try:
                    tracker.stop_recording()
                except Exception:
                    pass
            tracker.set_offline_mode()
            core.wait(0.5)
            tracker.close_edf()
            core.wait(0.5)
            tracker.transfer_edf(new_filename=new_filename)
        finally:
            tracker.close_connection()

    def check_realtime_gaze(self):
        """Check one realtime gaze sample and reject when fixation is broken.

        Parameters
        ----------
        None

        Returns
        -------
        bool | tuple
            `False` when realtime monitoring is disabled or the current sample
            is acceptable; may return `(False, None)` when no eye sample is
            available.

        Raises
        ------
        EyeMovementError
            When gaze distance from fixation exceeds `self.pix_radius`.
        """
        if not self.realtime_monitor_active:
            return False
        if not self.is_eyetracking_active("gaze_data_both"):
            return False

        tracker = self.tracker
        left, right = tracker.gaze_data_both

        if left is not None and right is not None:
            lx, ly = left
            rx, ry = right
            x = np.nanmean([lx, rx])
            y = np.nanmean([ly, ry])
        elif left is not None:
            x, y = left
        elif right is not None:
            x, y = right
        else:  # if no eye data do not reject
            return False, None

        # Convert gaze to screen-centered pixel coordinates before applying
        # the fixation radius threshold.
        winx, winy = self.experiment_window.size / 2
        x -= winx
        y -= winy

        dist = np.linalg.norm(np.array([x, y]))

        if dist > self.pix_radius:
            tracker.stop_recording()
            raise EyeMovementError(f"Eye movement detected at {x},{y}", x, y)

        return False

    def wait_with_realtime_monitoring(self, wait_time, s_rate=0.01):
        """Wait for a fixed duration while polling realtime gaze when enabled.

        Parameters
        ----------
        wait_time : float
            Duration in seconds to wait.
        s_rate : float, optional
            Sampling loop sleep interval in seconds.

        Returns
        -------
        bool | tuple
            `False` when no rejection occurs; may return `(False, None)` if no
            eye sample is available.

        Raises
        ------
        EyeMovementError
            When gaze distance from fixation exceeds `self.pix_radius`.
        """
        if not self.realtime_monitor_active:
            core.wait(wait_time)
            return False
        if not self.is_eyetracking_active("gaze_data_both"):
            core.wait(wait_time)
            return False

        start_time = core.getTime()
        last_result = False
        while core.getTime() < start_time + wait_time:
            last_result = self.check_realtime_gaze()
            core.wait(s_rate)
        return last_result

    def display_eyemovement_feedback(self, eyes):
        """Display eye-movement rejection feedback and wait for space.

        Parameters
        ----------
        eyes : tuple[float, float]
            Eye position (pixels, centered coordinates) to mark on screen.

        Returns
        -------
        None
            Draws a rejection message, the task fixation marker, and the
            measured gaze position. Waits for ``space`` before returning.

        Assumptions
        -----------
        ``self.experiment_window`` is an initialized PsychoPy window.

        Side Effects
        ------------
        Renders feedback directly to the experiment window and blocks until a
        valid key press is received.
        """

        visual.TextStim(
            win=self.experiment_window,
            text="Eye Movement Detected.\nPress space to continue.",
            pos=[0, 1],
            color="#FF0000",
            colorSpace="hex",
        ).draw()
        fixation = getattr(self, "fixation", None)
        if fixation is None:
            raise RuntimeError("Fixation stimulus is not initialized.")
        fixation.set_color("#000000")
        fixation.draw()

        visual.Circle(
            win=self.experiment_window,
            radius=8,
            pos=eyes,
            fillColor="#FF0000",
            colorSpace="hex",
            units="pix",
        ).draw()

        self.experiment_window.flip()
        event.waitKeys(keyList=["space"])

    def do_rejection(self, reject, condition=None):
        """Update rejection counters and handle repeated realtime rejections.

        Parameters
        ----------
        reject : bool
            Whether the current trial was rejected.
        condition : str | None, optional
            Condition label used to increment `self.rejection_counter`.

        Returns
        -------
        None
            Updates rejection counters in place. After 3 consecutive rejected
            trials, the task runs one automatic drift correction. If the
            rejection streak grows beyond 5 trials, the task pauses for the
            researcher to inspect the eye tracker.
        """
        if reject is False:
            self.row_rejected = 0
            self.row_rejected_drift_done = False
        else:
            self.rejection_counter[condition] += 1
            self.row_rejected += 1
            print(f"# of rejected {condition} trials:{self.rejection_counter[condition]}")

        # One automatic drift correction gives the tracker a chance to recover
        # before interrupting the experiment for the researcher.
        if self.row_rejected >= 3 and not self.row_rejected_drift_done:
            self.row_rejected_drift_done = True
            if self.is_eyetracking_active("drift_correct"):
                self.tracker.drift_correct()
            return

        if self.row_rejected > 5:
            self.row_rejected = 0
            self.row_rejected_drift_done = False
            self.handle_rejection_pause()

    ## EEG Helper functions
    def setup_eeg(self):
        """Connect to the parallel port used for EEG trigger output.

        The port address can be overridden by setting
        ``self.port_address`` in the experiment subclass. When no override is
        set, this method falls back to the historical default ``53328``.
        """
        port_address = int(getattr(self, "port_address", 53328) or 53328)
        try:
            print(f"Connecting to parallel port for EEG port codes (address={port_address})")
            self.port = parallel.ParallelPort(address=port_address)
        #            parallel.setData(0)

        except Exception as e:
            self.port = None
            print("No parallel port connected. Port codes will not send!")
            raise e

    def send_synced_event(self, code, keyword="SYNC"):
        """Send port code to EEG and eyetracking message for later synchronization

        Parameters
        ----------
        code : int
            Trigger code sent to the EEG port.
        keyword : str, optional
            Prefix tag included in the EyeLink message log.
        """

        message = keyword + " " + str(code)

        # Always send EEG trigger when the port is available.
        if self.port is not None:
            self.port.setData(code)
            core.wait(0.005)
            self.port.setData(0)
        # EyeLink message logging is optional and only runs when tracker is ready.
        if self.tracker is not None and self.is_eyetracking_active("send_message"):
            self.tracker.send_message(message)
