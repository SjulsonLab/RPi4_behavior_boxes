#!/usr/bin/env python
# coding: utf-8

#!/usr/bin/env -S ipython3 -i

"""
author: Matthew Chin
date: 2023-11-10
name: main.py
"""

from icecream import ic
import traceback
from datetime import datetime
import os
import scipy.io, pickle
import pygame
from colorama import Fore, Style
import time
import sys
import logging
import logging.config
from pathlib import Path
from session_info import make_session_info
from subprocess import check_output
import re


sys.path.insert(0, './essential')  # essential holds behavbox and equipment classes
sys.path.insert(0, '.')

# debug_enable = False
# if debug_enable:
#     # enabling debugger
#     from IPython import get_ipython
#     ipython = get_ipython()
#     ipython.magic("pdb on")
#     ipython.magic("xmode Vezrbose")


# all modules above this line will have logging disabled
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})


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


def set_session_time():
    time = 0
    while time == 0:
        try:
            time = int(input("Enter the time in minutes: "))
        except ValueError:
            print("Invalid input, please enter an integer number")
    return time


def close_logs():
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()
    ic('All logs closed!')


def main():
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
        if session_info['debug']:
            from essential import dummy_box as behavbox
        else:
            from essential import behavbox

        # query user to confirm current options
        options_correct = False
        while not options_correct:
            options_correct = confirm_options(session_info)

        # if (session_info['mouse_name'] == 'test_mouse' or session_info['weight'] == 0) and not debug_task:
        #     print(Fore.RED + Style.BRIGHT + 'ERROR: Mouse info not set! Exiting now' + Style.RESET_ALL)
        #     quit()

        session_info['date'] = datestr
        session_info['time'] = timestr
        session_info['datetime'] = session_info['date'] + '_' + session_info['time']
        if session_info['debug']:
            session_info['session_name'] = ''  # previously this was 'basename'
            session_info['output_dir'] = "./outputs/"
        else:
            session_info['session_name'] = session_info['mouse_name'] + '_' + session_info['datetime']
            session_info['output_dir'] = session_info['buffer_dir'] + '/' + session_info['session_name']
            session_info['external_storage_dir'] = session_info['external_storage'] + '/' + session_info['session_name']
            session_info['flipper_filename'] = session_info['output_dir'] + '/' + session_info['session_name'] + '_flipper_output'
            # session_info['flipper_filename'] = session_info['external_storage_dir'] + '/' + session_info['session_name'] + '_flipper_output'
            ic(session_info['output_dir'])
            ic(session_info['flipper_filename'])
            ic(session_info['external_storage_dir'])

        # check for presence of external hd
        storage = check_output('lsblk')
        if re.search(r'sda', storage.decode('utf-8')):
            print('[***] External storage found [***]')
        else:
            raise RuntimeError('External storage not found')

        if session_info['debug']:
            session_info['file_basename'] = 'test_debug'
        else:
            session_info['file_basename'] = session_info['output_dir'] + '/' + session_info['session_name']

        log_path = Path(session_info['output_dir']) / (session_info['file_basename'] + '.log')
        # if not debugging, stop if log path exists
        if session_info['debug']:
            pass
        elif os.path.exists(log_path):
            print(Fore.RED + Style.BRIGHT + 'ERROR: Log file already exists! Exiting now' + Style.RESET_ALL)
            quit()

        session_info_path = Path(session_info['output_dir']) / (session_info['file_basename'] + '_session_info.pkl')
        mat_path = Path(session_info['output_dir']) / (session_info['file_basename'] + '_session_info.mat')
        session_info['log_path'] = str(log_path)

        if not os.path.exists(session_info['output_dir']):
            os.makedirs(session_info['output_dir'])

        if not os.path.exists(session_info['external_storage_dir']):
            os.makedirs(session_info['external_storage_dir'])

        # set up logging
        # logger = logging.getLogger(__name__)
        # stdout_handler = logging.StreamHandler(stream=sys.stdout)
        # stdout_handler.setLevel(logging.INFO)
        # file_handler = logging.FileHandler(log_path)
        # file_handler.setLevel(logging.INFO)
        #
        # format = logging.Formatter(fmt="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
        #                            datefmt='%H:%M:%S')
        # stdout_handler.setFormatter(format)
        # file_handler.setFormatter(format)
        # logger.addHandler(stdout_handler)
        # logger.addHandler(file_handler)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
            datefmt=('%H:%M:%S'),
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler()  # sends copy of log output to screen
            ]
        )

        box = behavbox.BehavBox(session_info=session_info)
        gui = GUI(session_info=session_info)
        pump = behavbox.Pump(session_info=session_info)

        ### allow different tasks to be loaded ###
        task_type = session_info['task_config']
        if task_type == 'alternating_latent':
            from task_protocol.alternating_latent import alternating_latent_model, alternating_latent_presenter
            task = alternating_latent_model.AlternatingLatentModel(session_info=session_info)
            Presenter = alternating_latent_presenter.AlternatingLatentPresenter
            # name = 'alternating_latent_task'
        elif task_type == 'A_B_task':
            pass
        elif task_type == 'C1_C2_task':
            pass
        elif task_type == 'A_B_C1_C2_task':
            pass
        elif task_type == 'latent_inference':
            from task_protocol.latent_inference_forage import latent_inference_model, latent_inference_presenter
            task = latent_inference_model.LatentInferenceModel(session_info=session_info)
            Presenter = latent_inference_presenter.LatentInferencePresenter
            # name = 'latent_inference_task'
        elif task_type == 'latent_inference_with_stimuli':
            from task_protocol.latent_inference_with_stimuli import stimulus_inference_model, stimulus_inference_presenter
            task = stimulus_inference_model.StimulusInferenceModel(session_info=session_info)
            Presenter = stimulus_inference_presenter.StimulusInferencePresenter
            # name = 'latent_inference_with_stimuli'
        elif task_type == 'flush':
            from task_protocol.flush import flush_model, flush_presenter
            task = flush_model.FlushModel(session_info=session_info)
            Presenter = flush_presenter.FlushPresenter
            # name = 'flush'
        else:
            raise RuntimeError('[***] Specified task not recognized!! [***]')

        presenter = Presenter(model=task,
                              box=box,
                              pump=pump,
                              gui=gui,
                              session_info=session_info)
        box.set_callbacks(presenter=presenter)

        # save session info in buffer
        scipy.io.savemat(mat_path, session_info)
        with open(session_info_path, 'wb') as f:
            pickle.dump(session_info, f)

        # save session info in external storage
        # scipy.io.savemat(session_info['external_storage_dir'] + "/" + session_info['session_name'] + '_session_info.mat',
        #                  {'session_info': session_info})
        # with open(session_info['external_storage_dir'] + "/" + session_info['session_name'] + '_session_info.pkl', "wb") as f:
        #     pickle.dump(session_info, f)

        presenter.start_session()
        t_minute = set_session_time()
        t_end = time.time() + 60 * t_minute

        run = True
        presenter.print_controls()
        task.start_task()
        while run:
            if time.time() < t_end:
                if session_info['control']:
                    presenter.run_control()
                else:
                    presenter.run()
            else:
                run = False
                print("Time's up, finishing up")

        raise SystemExit

    # graceful exit
    except (KeyboardInterrupt, SystemExit):
        print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
        close_logs()
        if 'presenter' in locals():
            try:
                ic('Calling end_session()')
                presenter.end_session()
                ic('Call to end_session() was successful')
            except Exception as ex:
                ic('could not call end_session()')
                traceback.print_exc()
        else:
            pass

        ic('Saving files to disk')
        scipy.io.savemat(mat_path, session_info)
        with open(session_info_path, 'wb') as f:
            pickle.dump(session_info, f)

        box.transfer_files_to_external_storage()
        pygame.quit()

    # exit because of error
    except RuntimeError as ex:
        print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
        print(ex)

        ic('Saving files to disk')
        close_logs()
        # scipy.io.savemat(mat_path, {'session_info': session_info})
        scipy.io.savemat(mat_path, session_info)
        with open(session_info_path, 'wb') as f:
            pickle.dump(session_info, f)


        presenter.end_session()
        box.transfer_files_to_external_storage()
        pygame.quit()


if __name__ == '__main__':
    main()
