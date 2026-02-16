"""Base tracker experiment template utilities.

Author - Colin Quirk (cquirk@uchicago.edu)
Contributor - Chenyu Li
"""

import numpy as np
import os
import sys
import csv
import importlib
from pathlib import Path
from typing import Any, cast

from psychopy import core, event, visual, tools, gui, monitors, parallel

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
DEFAULT_USER_INPUT = {"Subject": "0", "Unique ID": "000000", "Age": "0", "Gender": ["Male", "Female", "Others"]}


def _load_eyelinker():
    """Import and return the eyelinker module lazily at runtime."""
    try:
        return importlib.import_module("src.utils.eyelinker")
    except ImportError:
        return importlib.import_module("utils.eyelinker")


class FixationCross:
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
        instructions,
        conditions,
        keys=DEFAULT_KEYS,
        monitor_details=DEFAULT_MONITOR,
        bg_color=DEFAULT_BG_COLOR,
        user_input=DEFAULT_USER_INPUT,
        eyetracker_config=None,
        do_realtime_eyetracking=True,
        min_redos=0,
    ):
        """Initialize shared configuration/state for an eyetracking experiment.

        Parameters
        ----------
        experiment_name : str
            Name shown in participant dialogs and logs.
        instructions : list[str]
            Instruction screens shown by `instruct()`.
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
        min_redos : int, optional
            Initial value added to each condition's rejection counter.
        """
        self.monitor_details = monitor_details
        self.bg_color = bg_color
        self.exp_info = dict(user_input)
        self.keys = keys
        self.experiment_name = experiment_name
        self.instructions = instructions

        merged_eyetracker_config = dict(DEFAULT_EYETRACKER_CONFIG)
        if eyetracker_config is not None:
            merged_eyetracker_config.update(eyetracker_config)
        self.eyetracker_config = merged_eyetracker_config

        self.eye_max_dist = float(self.eyetracker_config["eye_max_dist"])
        self.tracked_eye = str(self.eyetracker_config["tracked_eye"]).upper()
        if self.tracked_eye not in ("LEFT", "RIGHT", "BOTH"):
            raise ValueError("tracked_eye must be LEFT, RIGHT, or BOTH.")
        self.realtime_eyetrack_enabled = do_realtime_eyetracking
        self.do_realtime = False
        self.rejection_counter = {key: 0 + min_redos for key in conditions}
        self.row_rejected = 0
        self.experiment_window: Any = None
        self.tracker: Any = None
        self.port: Any = None

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
        """
        if self.tracker is None:
            print("Eye tracker not initialized.")
            return False
        elif functionality is not None and not hasattr(self.tracker, functionality):
            print(f"Eye tracker does not have '{functionality}' functionality.")
            return False
        else:
            return True

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
            "color": self.bg_color,
            "colorSpace": "hex",
            "units": "deg",
            "allowGUI": False,
        }
        window_kwargs.update(kwargs)
        self.experiment_window = visual.Window(**window_kwargs)

        self.fixation = FixationCross(self.experiment_monitor, self.experiment_window, self.bg_color)
        # Register a global emergency quit key available across screens/tasks.
        global_keys = cast(Any, event.globalKeys)
        try:
            global_keys.remove("escape")
        except Exception:
            pass
        global_keys.add(key="escape", func=self.quit_experiment)

    def quit_experiment(self):
        """Close the window (if open) and terminate the process."""
        if self.experiment_window is not None:
            self.experiment_window.close()
        print("The experiment has ended")
        sys.exit(0)

    def display_text_screen(
        self,
        text="",
        text_color="#000000",
        text_height=36,
        bg_color=None,
        keyList=["space"],
        min_wait=0.2,
        show_fixation=False,
        **kwargs,
    ):
        """Draw a centered text screen and wait for a key response.

        Parameters
        ----------
        text : str, optional
            Message to display.
        text_color : str, optional
            HEX text color.
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
        **kwargs
            Extra arguments forwarded to `psychopy.visual.TextStim`.

        Returns
        -------
        list[str] | None
            Value returned by `psychopy.event.waitKeys`.
        """

        if bg_color is None:
            bg_color = self.bg_color

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
        self.experiment_window.flip()

        keys = []
        core.wait(min_wait)  # Prevents accidental key presses
        keys = event.waitKeys(keyList=keyList)
        return keys

    def display_image_screen(
        self,
        image,
        bg_color=None,
        keyList=["space"],
        min_wait=0.2,
        show_fixation=False,
        image_units="pix",
        image_size=None,
        pos=(0, 0),
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
        pos : tuple[float, float], optional
            Image position in ``image_units``.
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
        image_stim = visual.ImageStim(
            self.experiment_window,
            image=str(image),
            pos=pos,
            units=image_units,
            **image_kwargs,
        )

        background_rect.draw()
        image_stim.draw()
        self.experiment_window.flip()

        keys = []
        core.wait(min_wait)
        keys = event.waitKeys(keyList=keyList)
        return keys

    def display_fixation(self, wait_time=np.inf, text=None, keyList=None, show=True):
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

        Returns
        -------
        bool | tuple | None
            Returns realtime rejection output when `self.do_realtime` is true;
            otherwise returns `None`.
        """
        # wait_time = wait_time / 1000 # convert ms to s
        if text:
            visual.TextStim(win=self.experiment_window, text=text, pos=[0, 1], color="#FF0000", colorSpace="hex").draw()
        if show:
            self.fixation.show()
        else:
            self.fixation.hide()

        if self.do_realtime:
            reject = self.realtime_eyetrack(wait_time=wait_time)
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

        # Modifies experiment_info dict directly.
        # Cast suppresses incomplete type hints for PsychoPy dialog kwargs like `screen`.
        dlg_from_dict = cast(Any, gui.DlgFromDict)
        exp_info = dlg_from_dict(
            self.exp_info,
            title=self.experiment_name,
            tip={"Unique subject Identifier": "From the cronus log"},
            screen=screen,
        )
        self.exp_info = exp_info.dictionary

        self.sub_num = int(self.exp_info["Subject"])
        if save_info:
            output_path = info_path or f"sub{self.sub_num:02d}_info.csv"
            self.save_experiment_info_csv(output_path, overwrite=overwrite_info)

        return exp_info.OK

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
        """
        experiment_data_dir = Path(data_root) / self.experiment_name

        while True:
            ok = self.get_experiment_info_from_dialog(screen=screen, save_info=False)
            if not ok:
                return None

            subject_tag = f"{subject_prefix}{self.sub_num:02d}"
            subject_data_dir = experiment_data_dir / subject_tag
            has_existing_data = subject_data_dir.exists() and any(subject_data_dir.iterdir())
            overwrite = False

            if has_existing_data:
                dlg = cast(Any, gui.Dlg)
                conflict_dlg = dlg(title="Existing Subject Data", screen=screen)
                conflict_dlg.addText(
                    f"Data already exists for {subject_tag}.\n"
                    "Choose whether to overwrite or change Subject ID."
                )
                conflict_dlg.addField(
                    "Action",
                    choices=["Overwrite existing data", "Change Subject ID"],
                )
                # Hide PsychoPy's default "required fields" helper text for this simple selector dialog.
                if hasattr(conflict_dlg, "requiredMsg"):
                    conflict_dlg.requiredMsg.hide()
                conflict_dlg.show()

                if not conflict_dlg.OK:
                    return None

                if conflict_dlg.data[0] == "Change Subject ID":
                    continue
                overwrite = True

            subject_data_dir.mkdir(parents=True, exist_ok=True)
            info_file = subject_data_dir / f"{subject_tag}_info.csv"
            self.save_experiment_info_csv(info_file, overwrite=overwrite)
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
        tracker.set_offline_mode()
        tracker.close_edf()
        tracker.transfer_edf(new_filename=new_filename)
        tracker.close_connection()

    def realtime_eyetrack(self, wait_time, s_rate=0.01):
        """Monitor gaze online and raise `EyeMovementError` if fixation is broken.

        Parameters
        ----------
        wait_time : float
            Duration in seconds to monitor gaze.
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

        if not self.do_realtime:
            core.wait(wait_time)
            return False
        if not self.is_eyetracking_active("gaze_data_both"):
            core.wait(wait_time)
            return False

        start_time = core.getTime()
        while core.getTime() < start_time + wait_time:
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

            # get the x,y pixel values relative to the center of the screen
            winx, winy = self.experiment_window.size / 2
            x -= winx
            y -= winy

            dist = np.linalg.norm(np.array([x, y]))

            if dist > self.pix_radius:
                tracker.stop_recording()

                raise EyeMovementError(f"Eye movement detected at {x},{y}", x, y)

            core.wait(s_rate)

    def display_eyemovement_feedback(self, eyes):
        """Display eye-movement rejection feedback and wait for space.

        Parameters
        ----------
        eyes : tuple[float, float]
            Eye position (pixels, centered coordinates) to mark on screen.
        """

        visual.TextStim(
            win=self.experiment_window,
            text="Eye Movement Detected.\nPress space to continue.",
            pos=[0, 1],
            color="#FF0000",
            colorSpace="hex",
        ).draw()
        visual.TextStim(self.experiment_window, text="+", color="#000000", colorSpace="hex").draw()

        visual.Circle(win=self.experiment_window, radius=8, pos=eyes, fillColor="#FF0000", colorSpace="hex", units="pix").draw()

        self.experiment_window.flip()
        event.waitKeys(keyList=["space"])

    def do_rejection(self, reject, condition=None):
        """Update rejection counters and show prompt after repeated rejections.

        Parameters
        ----------
        reject : bool
            Whether the current trial was rejected.
        condition : str | None, optional
            Condition label used to increment `self.rejection_counter`.
        """
        if reject is False:
            self.row_rejected = 0
        else:
            self.rejection_counter[condition] += 1
            self.row_rejected += 1
            print(f"# of rejected {condition} trials:{self.rejection_counter[condition]}")

        if self.row_rejected >= 5:
            self.row_rejected = 0
            self.display_text_screen(
                text="Rejected 5 in row. Continue?", keyList=["y"], bg_color="#0000FF", text_color="#FFFFFF"
            )

    def instruct(self):
        """Present each instruction page in `self.instructions` sequentially."""

        for instruction in self.instructions:
            print(instruction)

            self.display_text_screen(text=instruction, keyList=["space"])

    ## EEG Helper functions
    def setup_eeg(self):
        """Connect to the parallel port used for EEG trigger output."""
        try:
            print("Connecting to parallel port for EEG port codes")
            self.port = parallel.ParallelPort(address=53328)
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

        if self.port and self.is_eyetracking_active("send_message"):
            self.port.setData(code)
            core.wait(0.005)
            self.port.setData(0)
            self.tracker.send_message(message)


# Backward compatibility alias
BaseTrackerExperiment = BaseTrackerExp
BaseEyeTrackingExperiment = BaseTrackerExp
