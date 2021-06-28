# Kelly recording task
# This task is designed for recording freely moving animal behavioral task

import logging
from datetime import datetime
import os
from colorama import Fore, Style
import logging.config

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)
# all modules above this line will have logging disabled

import behavbox
class KellyRecordTask(object):
    def __init__(self, **kwargs):  # name and session_info should be provided as kwargs

        # if no name or session, make fake ones (for testing purposes)
        if kwargs.get("name", None) is None:
            self.name = "name"
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no name supplied; making fake one"
                + Style.RESET_ALL
            )
        else:
            self.name = kwargs.get("name", None)

        if kwargs.get("session_info", None) is None:
            print(
                Fore.RED
                + Style.BRIGHT
                + "Warning: no session_info supplied; making fake one"
                + Style.RESET_ALL
            )
            from fake_session_info import fake_session_info

            self.session_info = fake_session_info
        else:
            self.session_info = kwargs.get("session_info", None)
        print(self.session_info)

        # initialize behavior box
        self.box = behavbox.BehavBox(self.session_info)

    def start_session(self):
        print("Start recording video")
        self.box.video_start()

    def end_session(self):
        print("Stop recording video")
        self.box.video_stop()
