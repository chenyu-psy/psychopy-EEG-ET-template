"""Runtime settings for exp1."""

import numpy as np

MONITOR = {
    "name": "Monitor01", 
    "distance": 90, 
    "resolution": [1920, 1080], 
    "width": 53,
    "fullscr": False,  # set False for windowed mode during testing
    }

RESPONSES = {
    "CORRECT": "z",
    "INCORRECT": "slash"
}

COLORS = {
    "background": "#7F7F7F",
    "item": "#FFFFFF",
    "uncued": "#F46D43",
    "cued": "#4FB99F",
}

SIZE = {
    "font": 1.2,
    "fixation": 0.6,
    "underscore_width": 2.0,
    "underscore_length_scale": 0.8,
    "underscore_offset_scale": 0.6,
}

EYE_TRACKING = {
    "eye_max_dist": 1.25,  # in degrees visual angle, distance from fixation point to be considered a fixation
    "tracked_eye": "BOTH",  # one of: "LEFT", "RIGHT", "BOTH"
}

DESIGN = {
    "N_trials": 100,
    "N_practice": 10,
    "break": 60,  # show a break screen every N experiment trials
    "condition": {
        "block": {"interruption": ["irr", "rel"]},
        "mixed": {"setsize": ["ss2", "ss4"]},
    },
}

CODE = {
    "TRIAL_START": 1,
    "DELAY": 2,
    "INTERRUPTION": 3,
    "TEST_DELAY": 4,
    "RESPONSE_START": 5,
    "TRIAL_END": 6,
    "SS2/IRR":21,
    "SS2/REL":22,
    "SS4/IRR":41,
    "SS4/REL":42
}

EXPERIMENT_NAME = "exp1"

TIMING = {
    "ITI": [0.5, 0.8],  # in seconds, duration of inter-trial interval
    "fixation": 0.3,  # in seconds, range for random fixation duration
    "sample": 0.5,  # in seconds, duration of sample stimulus
    "intervention": 1,  # in seconds, duration of inter-event interval
    "delay": 1,  # in seconds, duration of delay period
    "test_delay": 1,  # in seconds, duration of delay before response
    "test": np.inf,  # in seconds, duration of test period (until response)
}

REALTIME_TRACKER = False
REALTIME_EEG = False
