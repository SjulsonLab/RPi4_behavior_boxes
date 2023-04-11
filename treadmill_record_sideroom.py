# run treadmill recording task
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

import behavbox

try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run
    # There should be a session_info module corresponding to this before running this file

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    full_module_name = 'session_info_' + datestr
    import sys

    task_info_path = '/home/pi/experiment_info/treadmill_task/session_info'
    sys.path.insert(0, task_info_path)
    tempmod = importlib.import_module(full_module_name)
    session_info = tempmod.session_info
    mouse_info = tempmod.mouse_info

    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']
    session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
    basename = session_info['basename']
    session_info['dir_name'] = session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info[
        'datetime']

    if session_info['manual_date'] != session_info['date']:  # check if file is updated
        print('wrong date!!')
        raise RuntimeError('manual_date field in session_info file is not updated')

    box = behavbox.BehavBox(session_info)

    print("start_session")
    duration_buffer = 10  # it takes 8 seconds for the camera and the video_start function to be set up
    duration = int(input("Enter the time in seconds: ")) + duration_buffer
    try:
        box.flipper.flip()
    except Exception as error_message:
        print("flipper can't run\n")
        print(str(error_message))
    # Treadmill initiation
    try:
        box.treadmill.start()
    except Exception as error_message:
        print("treadmill can't run\n")
        print(str(error_message))

    # start initiating the dumping of the session information when available
    scipy.io.savemat(hd_dir + "/" + basename + '_session_info.mat', {'session_info': session_info})
    print("dumping session_info")
    pickle.dump(session_info, open(hd_dir + "/" + basename + '_session_info.pkl', "wb"))
    sleep(duration)

    try:  # try to stop recording the treadmill
        box.treadmill.close()
    except:
        pass
    
    # now stop the flipper after the video stopped recording
    try:  # try to stop the flipper
        box.flipper.close()
    except:
        pass
    time.sleep(2)

    base_dir = session_info['external_storage'] + '/'
    hd_dir = base_dir + basename

    scipy.io.savemat(hd_dir + "/" + basename + '_session_info.mat', {'session_info': session_info})
    print("dumping session_info")
    pickle.dump(session_info, open(hd_dir + "/" + basename + '_session_info.pkl', "wb"))
