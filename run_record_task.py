#!/usr/bin/env -S ipython3 -i

debug_enable = False

import logging
from datetime import datetime
import os
import logging.config
import socket
import importlib
import colorama
from colorama import Fore, Style
import scipy.io, pickle
from time import sleep

# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

if debug_enable:
    # enabling debugger
    from IPython import get_ipython
    ipython = get_ipython()
    ipython.magic("pdb on")
    ipython.magic("xmode Verbose")

# import your task class here
from kelly_record_task import KellyRecordTask

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run
    # There should be a session_info module corresponding to this before running this file

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info = tempmod.mouse_info

    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']
    session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
    session_info['dir_name'] = session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']

    if session_info['manual_date'] != session_info['date']:  # check if file is updated
        print('wrong date!!')
        raise RuntimeError('manual_date field in session_info file is not updated')


    # make data directory and initialize logfile
    os.makedirs(session_info['dir_name'])
    os.chdir(session_info['dir_name'])
    session_info['file_basename'] = session_info['mouse_name'] + "_" + session_info['datetime']
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(session_info['file_basename'] + '.log'),
            logging.StreamHandler() # sends copy of log output to screen
        ]
    )

    # initiate task object\
    task = KellyRecordTask(name="fentanyl_task", session_info=session_info)

    # start session
    print("start_session")
    duration = int(input("Enter the time in seconds: "))
    task.start_session()
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    print("dumping session_info")
    pickle.dump(session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
    sleep(duration)
    task.start_session()
    task.end_session()
# graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
    task.end_session()
    # save dicts to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    pickle.dump( session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
    # pygame.quit()


# exit because of error
except (RuntimeError) as ex:
    print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
    # save dicts to disk
    scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    pickle.dump( session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
