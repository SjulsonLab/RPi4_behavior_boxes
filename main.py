#!/usr/bin/env python
# coding: utf-8

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
import argparse

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
from essential.gui import PygameGUI


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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--camera-dry-run',
        action='store_true',
        help='Verify camera/network connectivity for all configured camera nodes and exit.',
    )
    return parser.parse_args()


def print_camera_dry_run_report(report: dict):
    print("\nCamera verification results:")
    for result in report['results']:
        status = "PASS" if result['status'] == 'pass' else "FAIL"
        required_str = "required" if result['required'] else "optional"
        print(
            f"[{status}] {result['camera_id']} ({result['host']}) "
            f"[{required_str}] backend={result['backend']}"
        )
        for file_check in result.get('file_checks', []):
            if file_check['present'] is True:
                file_status = "present"
            elif file_check['present'] is False:
                file_status = "missing"
            else:
                file_status = "not checked"
            print(
                f"       {file_check['label']}: {file_status} "
                f"({file_check['path']})"
            )
        if result['status'] != 'pass':
            print(f"       reason: {result['error']}")

    if report['all_required_passed']:
        print("\nAll required cameras verified.")
    else:
        print("\nVerification failed for one or more required cameras.")


def configure_session_output_paths(session_info: dict, datestr: str, timestr: str) -> dict:
    """Populate per-session output paths.

    Data contract:
    - Inputs:
      - `session_info`: `dict` with at least `debug`, `mouse_name`, `buffer_dir`, and `external_storage`.
      - `datestr`: `str`, session date formatted as `YYYY-MM-DD`.
      - `timestr`: `str`, session start time formatted as `HHMMSS`.
    - Output:
      - Returns the same `dict` populated with `date`, `time`, `datetime`, `session_name`,
        `output_dir`, `video_dir`, `external_storage_dir`, `flipper_filename`,
        `treadmill_filename`, and `file_basename`.
    """
    session_info['date'] = datestr
    session_info['time'] = timestr
    session_info['datetime'] = session_info['date'] + '_' + session_info['time']

    if session_info['debug']:
        session_info['session_name'] = ''
        session_info['output_dir'] = "./outputs/buffer"
        session_info['video_dir'] = session_info['output_dir'] + '/video'
        session_info['external_storage'] = "./outputs/external"
        session_info['external_storage_dir'] = session_info['external_storage'] + '/' + session_info['session_name']
        session_info['flipper_filename'] = session_info['output_dir'] + '/' + session_info['session_name'] + '_flipper_output'
        session_info['treadmill_filename'] = session_info['output_dir'] + '/' + session_info['session_name'] + "_treadmill"
        session_info['file_basename'] = 'test_debug'
    else:
        session_info['session_name'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['output_dir'] = session_info['buffer_dir'] + '/' + session_info['session_name']
        session_info['video_dir'] = session_info['output_dir'] + '/video'
        session_info['external_storage_dir'] = session_info['external_storage'] + '/' + session_info['session_name']
        session_info['flipper_filename'] = session_info['output_dir'] + '/' + session_info['session_name'] + '_flipper_output'
        session_info['treadmill_filename'] = session_info['output_dir'] + '/' + session_info['session_name'] + "_treadmill"
        session_info['file_basename'] = session_info['output_dir'] + '/' + session_info['session_name']

    return session_info


def run_program(session_info: dict = None, camera_dry_run: bool = False) -> int:
    exit_code = 0
    session_cleanup_done = False
    try:
        # load in session_info file, check that dates are correct, put in automatic
        # time and date stamps for when the experiment was run

        datestr = datetime.now().strftime("%Y-%m-%d")
        timestr = datetime.now().strftime('%H%M%S')
        if session_info is None:
            session_info = make_session_info()
        if session_info['debug'] and not camera_dry_run:
            from essential import dummy_box as behavbox
        else:
            from essential import behavbox

            if not camera_dry_run:
                # check for presence of external hd
                storage = check_output('lsblk')
                if re.search(r'sda', storage.decode('utf-8')):
                    print('[***] External storage found [***]')
                else:
                    raise RuntimeError('External storage not found')

        if camera_dry_run:
            box = behavbox.BehavBox(session_info=session_info)
            report = box.camera_dry_run()
            print_camera_dry_run_report(report)
            if not report['all_required_passed']:
                raise RuntimeError("One or more required camera nodes failed verification.")
            return 0

        # query user to confirm current options
        options_correct = False
        while not options_correct:
            options_correct = confirm_options(session_info)

        # if (session_info['mouse_name'] == 'test_mouse' or session_info['weight'] == 0) and not debug_task:
        #     print(Fore.RED + Style.BRIGHT + 'ERROR: Mouse info not set! Exiting now' + Style.RESET_ALL)
        #     quit()

        session_info = configure_session_output_paths(session_info, datestr, timestr)

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

        box = behavbox.BehavBox(session_info=session_info)  # gets this far then quits
        if session_info['visual_stimulus'] and getattr(box, 'visualstim', None) is None:
            raise RuntimeError(
                'Visual stimulus initialization failed. The Raspberry Pi display backend is not available. '
                'Check that /dev/fb0 exists and that rpg.Screen() can open it.'
            )
        gui = PygameGUI(session_info=session_info)
        # gui = GUI(session_info=session_info)

        pump = behavbox.Pump(session_info=session_info)

        ### allow different tasks to be loaded ###
        task_type = session_info['task_config']
        if task_type == 'alternating_latent':
            from task_protocol.alternating_latent import alternating_latent_model, alternating_latent_presenter
            task = alternating_latent_model.AlternatingLatentModel(session_info=session_info)
            Presenter = alternating_latent_presenter.AlternatingLatentPresenter
            # name = 'alternating_latent_task'
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

        presenter.start_session()
        t_minute = set_session_time()
        t_end = time.time() + 60 * t_minute

        task.presenter_commands.clear()
        if session_info['visual_stimulus'] and getattr(box, 'visualstim', None) is not None:
            box.visualstim.empty_presenter_queue()
            box.visualstim.empty_stimulus_queue()

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
                session_cleanup_done = True
                ic('Call to end_session() was successful')
            except Exception as ex:
                ic('could not call end_session()')
                traceback.print_exc()
        else:
            pass
        exit_code = 0

    # exit because of error
    except RuntimeError as ex:
        print(Fore.RED + Style.BRIGHT + 'ERROR: Exiting now' + Style.RESET_ALL)
        print(ex)

        close_logs()
        if 'presenter' in locals():
            presenter.end_session()
            session_cleanup_done = True
        elif 'box' in locals() and not camera_dry_run:
            box.video_stop()
            session_cleanup_done = True
        exit_code = 1

    finally:
        if (not camera_dry_run
                and session_info is not None
                and session_info.get('debug') is False
                and 'box' in locals()):
            if not session_cleanup_done:
                box.video_stop()
            if session_info['visual_stimulus'] and getattr(box, 'visualstim', None) is not None:
                box.visualstim.myscreen.close()
            time.sleep(2)
            box.transfer_files_to_external_storage()

        pygame.display.quit()
        pygame.quit()
        print("Exiting now...")
    return exit_code


if __name__ == '__main__':
    args = parse_args()
    sys.exit(run_program(camera_dry_run=args.camera_dry_run))
