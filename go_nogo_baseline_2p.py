
"""Baseline 2P behavior task.

This task keeps the 2P behavior-box interface used by the existing scripts,
but does not present stimuli, sounds, or rewards. It simply starts the
session hardware, allows lick callbacks to be logged by the behavior box,
and drains the event queue so the deque does not grow indefinitely.
"""

import logging
import logging.config
import time
from typing import Optional

import numpy as np
from icecream import ic
from colorama import Fore, Style

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)

import behavbox_DT_2p as behavbox_DT


class go_nogo_baseline(object):
    """Continuous baseline session with lick detection only.

    Inputs
    ------
    kwargs : dict
        Keyword arguments containing:
        - name : str
            User-facing task name.
        - session_info : dict
            Session metadata dictionary used by BehavBox.

    Attributes
    ----------
    box : behavbox_DT.BehavBox
        Hardware interface object for camera, lick sensors, and logging.
    lick_times : np.ndarray, shape (n_licks,)
        Lick timestamps in seconds relative to session start.
    session_start_time : float
        Absolute UNIX timestamp in seconds.
    """

    def __init__(self, **kwargs):
        """Initialize the baseline task wrapper.

        Inputs
        ------
        kwargs : dict
            Keyword arguments containing optional keys:
            - name : str
            - session_info : dict

        Returns
        -------
        None
        """
        if kwargs.get("name", None) is None:
            self.name = "go_nogo_baseline"
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no name supplied; using default baseline task name"
                + Style.RESET_ALL
            )
        else:
            self.name = kwargs.get("name", None)

        self.session_info = kwargs.get("session_info", None)
        if self.session_info is None:
            raise RuntimeError("session_info must be provided for baseline sessions")

        ic(self.session_info)

        self.box = behavbox_DT.BehavBox(self.session_info)
        self.pump = self.box.pump
        self.treadmill = self.box.treadmill
        self.lick_times = np.array([])
        self.session_start_time = time.time()

    def _record_lick_event(self, event_name: str) -> None:
        """Record lick timing for lick-entry events.

        Inputs
        ------
        event_name : str
            Event name popped from the behavior-box event queue.

        Returns
        -------
        None
        """
        if event_name in {"left_entry", "center_entry", "right_entry"}:
            self.lick_times = np.append(
                self.lick_times,
                time.time() - self.session_start_time,
            )

    def run_baseline_once(self) -> Optional[str]:
        """Process one pending box event and return it.

        Inputs
        ------
        None

        Returns
        -------
        Optional[str]
            The event name if one was present, otherwise None.
        """
        if self.box.event_list:
            event_name = self.box.event_list.popleft()
            self._record_lick_event(event_name)
            return event_name
        return None

    def start_session(self) -> None:
        """Start the camera/video session.

        Inputs
        ------
        None

        Returns
        -------
        None
        """
        logging.info(str(time.time()) + ", baseline_session_start")
        self.session_start_time = time.time()
        self.box.video_start()

    def end_session(self) -> None:
        """Stop the camera/video session and close the visual screen.

        Inputs
        ------
        None

        Returns
        -------
        None
        """
        logging.info(str(time.time()) + ", baseline_session_end")
        self.box.video_stop()
        self.box.visualstim_go.myscreen.close()
