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

    # initiate task object\
    task = KellyRecordTask(name="fentanyl_task", session_info=session_info)

    # start session
    print("start_session")
    duration_buffer = 10 # it takes 8 seconds for the camera and the video_start function to be set up
    duration = int(input("Enter the time in seconds: ")) + duration_buffer
    task.start_session()
    sleep(duration)
    task.end_session()
    dir_name = session_info['dir_name']
    basename = session_info['basename']
    file_name = dir_name + "/" + basename
    base_dir = '/mnt/hd/'
    hd_dir = base_dir + basename

    # Per Kelly's request, remove all the files except the video file from the hard drive
#    print("Remove mat - ")
#    os.system("rm -r " + hd_dir + "/*.mat")
#    print("Remove pkl - ")
#    os.system("rm -r " + hd_dir + "/*.pkl")
#    print("Remove log -")
#    os.system("rm -r " + hd_dir + "/*.log")

# graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
    task.end_session()
    # # save dicts to disk
    # scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    # pickle.dump( session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
    # # pygame.quit()


# exit because of error
except (RuntimeError) as ex:
    print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
    # # save dicts to disk
    # scipy.io.savemat(session_info['file_basename'] + '_session_info.mat', {'session_info' : session_info})
    # pickle.dump( session_info, open( session_info['file_basename'] + '_session_info.pkl', "wb" ) )
