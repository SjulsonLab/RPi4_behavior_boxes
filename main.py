#!/usr/bin/env python
# coding: utf-8

#!/usr/bin/env -S ipython3 -i

"""
author: Matthew Chin
date: 2023-11-10
name: main.py
"""

from icecream import ic
from datetime import datetime
import os
import importlib
import scipy.io, pickle
import pygame
from colorama import Fore, Style
import time
import sys
import logging
import logging.config
from pathlib import Path
from session_params import make_session_info


sys.path.insert(0, './essential')  # essential holds behavbox and equipment classes
sys.path.insert(0, '.')

debug_startup = False
debug_task = False
if debug_startup or debug_task:
    from essential import dummy_box as behavbox
else:
    from essential import behavbox

debug_enable = False


# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})


# if debug_enable:
#     # enabling debugger
#     from IPython import get_ipython
#     ipython = get_ipython()
#     ipython.magic("pdb on")
#     ipython.magic("xmode Verbose")

# import your task class here
sys.path.insert(0,'./task_protocol')
from essential.gui import PygameGUI as GUI


def confirm_options(session_info: dict) -> bool:
    print("The following options are set for this session:")
    print("Mouse name: " + session_info['mouse_name'])
    print("Task type: " + session_info['task_config'])
    print("Is this correct? (y/n)")

    correct = False
    user_input = input()
    if user_input in ['n', 'N']:
        print("Please edit the session_info file and try again")
        quit()
    elif user_input in ['y', 'Y']:
        correct = True
        print("Starting session")
    else:
        print("Invalid input")
    return correct


try:
    # load in session_info file, check that dates are correct, put in automatic
    # time and date stamps for when the experiment was run

    datestr = datetime.now().strftime("%Y-%m-%d")
    timestr = datetime.now().strftime('%H%M%S')
    # full_module_name = 'session_info_' + datestr
    full_module_name = 'session_info'

    # want to edit this bit for debugging
    session_info_path = './'
    sys.path.insert(0, session_info_path)
    # tempmod = importlib.import_module(full_module_name)
    # session_info = tempmod.session_info
    # mouse_info = tempmod.mouse_info

    session_info = make_session_info()
    if (session_info['mouse_name'] == 'test_mouse' or session_info['weight'] == 0) and not (debug_startup or debug_task):
        print(Fore.RED + Style.BRIGHT + 'ERROR: Mouse info not set! Exiting now' + Style.RESET_ALL)
        quit()

    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']
    if debug_startup or debug_task:
        session_info['basename'] = ''
        session_info['dir_name'] = "./outputs/"
    else:
        session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['dir_name'] = session_info['basedir'] + "/" + session_info['basename']

    # make data directory and initialize logfile
    if not os.path.exists(session_info['dir_name']):
        os.makedirs(session_info['dir_name'])

    if debug_startup or debug_task:
        session_info['file_basename'] = 'test_debug'
    else:
        session_info['file_basename'] = session_info['dir_name'] + '/' + session_info['basename']

    log_path = Path(session_info['dir_name']) / (session_info['file_basename'] + '.log')
    # if not debugging, stop if log path exists
    if debug_startup or debug_task:
        pass
    elif os.path.exists(log_path):
        print(Fore.RED + Style.BRIGHT + 'ERROR: Log file already exists! Exiting now' + Style.RESET_ALL)
        quit()

    session_info_path = Path(session_info['dir_name']) / (session_info['file_basename'] + '_session_info.pkl')
    mat_path = Path(session_info['dir_name']) / (session_info['file_basename'] + '_session_info.mat')
    session_info['log_path'] = str(log_path)

    logger = logging.getLogger(__name__)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        datefmt=('%H:%M:%S'),
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()  # sends copy of log output to screen
        ]
    )

    # query user to confirm current options
    options_correct = False
    while not options_correct:
        options_correct = confirm_options(session_info)

    gui = GUI(session_info=session_info)

    # make dummy box and pump objects for testing, all functions should say "pass"
    box = behavbox.BehavBox(session_info=session_info)
    pump = behavbox.Pump(session_info=session_info)

    ### allow different tasks to be loaded ###
    task_type = session_info['task_config']
    if task_type == 'alternating_latent':
        from task_protocol.alternating_latent import alternating_latent_model, alternating_latent_presenter
        task = alternating_latent_model.AlternateLatent(session_info=session_info)
        Presenter = alternating_latent_presenter.AlternatingLatentPresenter
        name = 'alternating_latent_task'
    elif task_type == 'A_B_task':
        pass
    elif task_type == 'C1_C2_task':
        pass
    elif task_type == 'A_B_C1_C2_task':
        pass
    elif task_type == 'latent_inference_forage':
        from task_protocol.latent_inference_forage import latent_inference_forage_model, latent_inference_forage_presenter
        task = latent_inference_forage_model.LatentInferenceForageModel(session_info=session_info)
        Presenter = latent_inference_forage_presenter.LatentInferenceForagePresenter
        name = 'latent_inference_forage_task'
    else:
        raise RuntimeError('[***] Specified task not recognized!! [***]')

    presenter = Presenter(model=task,
                          box=box,
                          pump=pump,
                          gui=gui,
                          session_info=session_info)
    box.set_callbacks(presenter=presenter)

    # start session
    scipy.io.savemat(mat_path, session_info)
    with open(session_info_path, 'wb') as f:
        pickle.dump(session_info, f)

    presenter.start_session()
    if debug_startup:
        pass
    else:
        # time.sleep(5)
        # loop over trials
        # Set a timer
        t_minute = int(input("Enter the time in minutes: "))
        t_end = time.time() + 60 * t_minute

        run = True
        presenter.print_controls()
        task.start_task()
        while run:
            if time.time() < t_end:
                presenter.run()
            else:
                run = False
                print("Times up, finishing up")

    raise SystemExit

# graceful exit
except (KeyboardInterrupt, SystemExit):
    print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
    if 'presenter' in locals():
        try:
            ic('Calling end_session()')
            presenter.end_session()
            ic('Call to end_session() was successful')
        except:
            ic('could not call end_session()')
    else:
        pass

    # save dicts to disk
    ic('Saving files to disk')
    scipy.io.savemat(mat_path, session_info)
    with open(session_info_path, 'wb') as f:
        pickle.dump(session_info, f)
    pygame.quit()

# exit because of error
except RuntimeError as ex:
    print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
    print(ex)
    # save dicts to disk
    # scipy.io.savemat(mat_path, {'session_info': session_info})
    scipy.io.savemat(mat_path, session_info)
    with open(session_info_path, 'wb') as f:
        pickle.dump(session_info, f)
    presenter.end_session()

