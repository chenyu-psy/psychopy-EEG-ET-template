"""A module for managing the interaction between pylink and psychopy.

Author - Colin Quirk (cquirk@uchicago.edu)
Contributor - Chenyu Li

This class is designed to be used by the eyelinker module. If you use it, you won't need
to call any of these functions or change any of this code. If you prefer not to use eyelinker,
simply use `pl.openGraphicsEx(EyeLinkDisplay)` to connect pylink to psychopy. These
 functions are then called by interactions with the tracker.

Classes:
EyeLinkDisplay -- inherited from pylink.EyeLinkCustomDisplay. Defines how pylink events
 should be handled by psychopy.
"""

import array
import string
import warnings

import PIL

import pylink

from psychopy import event, visual
from psychopy.tools.monitorunittools import convertToPix

class EyeLinkDisplay(pylink.EyeLinkCustomDisplay):
    """Psychopy-backed custom display for the EyeLink pylink API.

    This class bridges `pylink.EyeLinkCustomDisplay` callbacks to PsychoPy drawing
    and input handling so that calibration/validation and camera images render in
    the PsychoPy window. It is intended to be used by the `eyelinker` module; if you
    wire it up manually, pass an instance to `pylink.openGraphicsEx`.

    Coordinate handling:
    - EyeLink delivers coordinates in display pixels with (0, 0) at the top-left.
    - PsychoPy uses the window center as (0, 0) by default.
    - Several methods translate and/or flip coordinates to match PsychoPy's space.

    Parameters
    ----------
    window : psychopy.visual.Window
        PsychoPy window used for all drawing operations.
    tracker : pylink.EyeLink
        Active EyeLink tracker instance.

    Notes
    -----
    - `record_abort_hide` is not implemented.
    - Crosshair drawing uses a fixed offset; see `draw_line` for details.

    Key Methods
    -----------
    setup_cal_display : Clear window and show calibration help text.
    exit_cal_display : Clear window on calibration exit.
    setup_image_display : Show mouse when camera images are visible.
    draw_image_line : Build camera image from scanlines and draw to the window.
    set_image_palette : Set the palette used to decode image scanlines.
    draw_cal_target : Draw the calibration target at a tracker pixel position.
    get_input_key : Translate PsychoPy keys into pylink key codes.
    get_mouse_state : Return mouse position and button state in tracker coords.
    """
    def __init__(self, window, tracker):
        pylink.EyeLinkCustomDisplay.__init__(self)
        self.window = window
        # adjusted to put center at (0,0)
        self.window_adj = [i / 2 for i in self.window.size]
        self.tracker = tracker

        self.pal = []
        self.image_buffer = array.array('I')

        if all(i >= 0.5 for i in self.window.color):
            self.text_color = "#000000"
        else:
            self.text_color = "#FFFFFF"

        self.colors = {
            pylink.CR_HAIR_COLOR: "#FFFFFF",
            pylink.PUPIL_HAIR_COLOR: "#FFFFFF",
            pylink.PUPIL_BOX_COLOR: "#00FF00",
            pylink.SEARCH_LIMIT_BOX_COLOR: "#FF0000",
            pylink.MOUSE_CURSOR_COLOR: "#FF0000",
        }

        self.keys = {
            'f1': pylink.F1_KEY,
            'f2': pylink.F2_KEY,
            'f3': pylink.F3_KEY,
            'f4': pylink.F4_KEY,
            'f5': pylink.F5_KEY,
            'f6': pylink.F6_KEY,
            'f7': pylink.F7_KEY,
            'f8': pylink.F8_KEY,
            'f9': pylink.F9_KEY,
            'f10': pylink.F10_KEY,
            'pageup': pylink.PAGE_UP,
            'pagedown': pylink.PAGE_DOWN,
            'up': pylink.CURS_UP,
            'down': pylink.CURS_DOWN,
            'left': pylink.CURS_LEFT,
            'right': pylink.CURS_RIGHT,
            'return': pylink.ENTER_KEY,
            'escape': pylink.ESC_KEY,
            'num_add': 43,
            'equal': 43,
            'num_subtract': 45,
            'minus': 45,
            'backspace': ord('\b'),
            'space': ord(' '),
            'tab': ord('\t')
        }

        self.mouse = event.Mouse(visible=False)

        self.image_title_object = visual.TextStim(
            self.window, text='', pos=(0, -200), height=20, units='pix', color=self.text_color, colorSpace="hex"
        )

        self.cal_target_outer = visual.Circle(
            self.window, units='pix', radius=18, lineColor="#000000", fillColor="#FFFFFF", colorSpace="hex"
        )

        self.cal_target_inner = visual.Circle(
            self.window, units='pix', radius=6, lineColor="#000000", fillColor="#000000", colorSpace="hex"
        )

    def setup_cal_display(self):
        """Prepare the calibration display.

        Clears the window and draws a short help string describing key actions
        (calibrate/validate/output/exit), then flips the buffer.
        """
        visual.TextStim(
            self.window,text='C: calibrate, V: Validate, O: output/record,ESC:exit',pos=(100,100),units='pix'
        ).draw()
        self.window.flip()

    def exit_cal_display(self):
        """Clear the calibration display and present a blank frame."""
        self.window.flip()

    def record_abort_hide(self):
        """No-op placeholder required by the pylink interface."""
        pass

    def setup_image_display(self, width, height):
        """Prepare the camera image display.

        Shows the mouse cursor and flips the window. The `width` and `height`
        parameters are provided by pylink but are not used here.
        """
        event.Mouse(visible=True)
        self.window.flip()

    def image_title(self, title):
        """Update the camera image title text (drawn on next frame)."""
        self.image_title_object.text = title

    def draw_image_line(self, width, line, totlines, buff):
        """Accumulate image scanlines and draw the full camera image.

        Parameters
        ----------
        width : int
            Image width in pixels.
        line : int
            Current scanline index (1-based in pylink callbacks).
        totlines : int
            Total number of scanlines for the frame.
        buff : iterable[int]
            Palette indices for the current scanline.
        """
        for i in buff:
            if i >= len(self.pal):
                self.image_buffer.append(self.pal[-1])
            else:
                self.image_buffer.append(self.pal[i])

        if line == totlines:
            bufferv = self.image_buffer.tostring()
            image = PIL.Image.frombytes("RGBX", (width, totlines), bufferv)

            psychopy_image = visual.ImageStim(self.window, image=image)

            psychopy_image.draw()
            self.draw_cross_hair()
            self.image_title_object.draw()
            self.window.flip()

            self.image_buffer = array.array('I')

    def set_image_palette(self, r, g, b):
        """Set the RGB palette used to decode camera image scanlines."""
        self.pal = []

        # Code taken from pylink docs and altered
        for r_, g_, b_ in zip(r, g, b):
            self.pal.append((b_ << 16) | g_ << 8 | r_)

    def exit_image_display(self):
        """Tear down the camera image display by hiding the mouse cursor."""
        event.Mouse(visible=False)
        self.window.flip()

    def clear_cal_display(self):
        """Clear any calibration graphics and present a blank frame."""
        self.window.flip()

    def erase_cal_target(self):
        """Erase a single calibration target by flipping a blank frame."""
        self.window.flip()

    def draw_cal_target(self, x, y):
        """Draw the calibration target at tracker pixel coordinates."""
        self.cal_target_outer.pos = (x - self.window_adj[0], y - self.window_adj[1])
        self.cal_target_inner.pos = (x - self.window_adj[0], y - self.window_adj[1])

        self.cal_target_outer.draw()
        self.cal_target_inner.draw()

        self.window.flip()

    def play_beep(self, beepid):
        """Optional audio feedback hook (currently disabled)."""
        pass

    def get_input_key(self):
        """Collect PsychoPy key events and map them to pylink key codes."""
        keys = []

        for keycode, modifiers in event.getKeys(modifiers=True):
            if keycode in self.keys:
                key = self.keys[keycode]
            elif keycode in string.ascii_letters:
                key = ord(keycode)
            else:
                key = pylink.JUNK_KEY

            mod = 256 if modifiers['alt'] else 0

            keys.append(pylink.KeyInput(key, mod))

        return keys

    def alert_printf(self, msg):
        """Emit a warning without aborting the session."""
        warnings.warn(msg, RuntimeWarning)

    def draw_line(self, x1, y1, x2, y2, colorindex):
        """Draw crosshair lines on the camera image overlay."""
        # For some reason the crosshairs need to be fixed like this
        if x1 < 0:
            x1, x2 = x1 + 767, x2 + 767
            y1, y2 = y1 + 639, y2 + 639

        if colorindex in self.colors:
            color = self.colors[colorindex]
        else:
            color = "#000000"

        # Adjustments are made so that center is (0,0) and y is flipped
        x1, x2 = x1 - 96, x2 - 96
        y1, y2 = (160 - y1 - 80), (160 - y2 - 80)

        visual.Line(
            self.window, units='pix', lineColor=color, colorSpace="hex", start=(x1, y1), end=(x2, y2)
        ).draw()

    def draw_lozenge(self, x, y, width, height, colorindex):
        """Draw an oval (lozenge) on the camera image overlay."""
        if colorindex in self.colors:
            color = self.colors[colorindex]
        else:
            color = "#000000"

        # Adjustments are made so that center is (0,0) and y is flipped
        x = round(x + (0.5 * width)) - 96
        y = round((160 - y) - (0.5 * height)) - 80

        visual.Circle(
            self.window, units='pix', lineColor=color, colorSpace="hex", pos=(x, y), size=(width, height)).draw()

    def get_mouse_state(self):
        """Return mouse position and button state in tracker coordinates."""
        mouse_pos = self.mouse.getPos()
        mouse_pos = convertToPix(
            mouse_pos, [0, 0], self.window.units, self.window
        )
        # Adjustments are made so that center is (0,0) and y is flipped
        mouse_pos = (mouse_pos[0] + 96, (160 - mouse_pos[1]) - 80)
        pressed = self.mouse.getPressed()
        left_pressed = pressed[0] if pressed else 0
        mouse_click = 1 if left_pressed else 0
        return (mouse_pos, mouse_click)
