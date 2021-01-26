#!/usr/bin/env python3

from transitions import Machine
from transitions import State
from transitions.extensions.states import add_state_features, Timeout
from icecream import ic
import logging
from datetime import datetime
import os
from gpiozero import PWMLED, LED, Button
import logging.config
import pysistence, collections
import socket
import importlib
import colorama
import warnings
import scipy.io 
from colorama import Fore, Style

# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

# import your task class here
from kelly_task import KellyTask

try:

    # import session and mouse info, contingent upon the dates matching
    full_module_name = 'session_info_' + datetime.now().strftime("%Y-%m-%d")
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info   = tempmod.mouse_info

    if session_info['manual_date'] != session_info['date']:  # check if file is updated
        print('wrong date!!')
        raise RuntimeError('manual_date field in session_info file is not updated')


    # make data directory and initialize logfile
    os.makedirs( session_info['dirname'] )
    os.chdir( session_info['dirname'] )
    filename = session_info['mouse_name'] + "_" + session_info['datetime'] + ".log" 
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        # datefmt=('%Y-%m-%d,%H:%M:%S'),
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(filename),
            logging.StreamHandler()
        ]
    )

    # initiate task object
    # task = KellyTask("fentanyl_task", session_info['mouse_name'], session_info['dirname'], session_info['config'])
    task = KellyTask("fentanyl_task", session_info)


    # start session
    task.start_session()
    scipy.io.savemat('mouse_info.mat', {'mouse_info': mouse_info})
    scipy.io.savemat('session_info.mat', {'session_info': session_info})

    # loop over trials
    for i in range(3):


        logging.info("starting_trial")

        task.trial_start()

        while task.trial_running:
            task.run()

    task.end_session()
    raise SystemExit

# graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now' + Style.RESET_ALL)
    # save dicts to disk
    import scipy.io 
    scipy.io.savemat('mouse_info.mat', {'mouse_info': mouse_info})
    scipy.io.savemat('session_info.mat', {'session_info': session_info})


# # exit because of error
# except (RuntimeError) as ex:
#     print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
#     # save dicts to disk
#     import scipy.io 
#     scipy.io.savemat('mouse_info.mat', {'mouse_info': mouse_info})
#     scipy.io.savemat('session_info.mat', {'session_info': session_info})




