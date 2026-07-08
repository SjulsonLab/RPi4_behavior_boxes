
"""Run continuous baseline 2P behavior imaging.

This script mirrors the session-info loading and camera control pattern of
the existing 2P run scripts, but it performs no trial logic. The session
runs continuously until Ctrl+C, while lick callbacks from the behavior box
are logged in real time.
"""

debug_enable = False

from icecream import ic
from datetime import datetime
import importlib
import logging
import logging.config
import os
import pickle
import scipy.io
import time
from colorama import Fore, Style

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})

if debug_enable:
    from IPython import get_ipython
    ipython = get_ipython()
    ipython.magic("pdb on")
    ipython.magic("xmode Verbose")

from go_nogo_baseline_2p import go_nogo_baseline


if __name__ == "__main__":
    try:
        datestr = datetime.now().strftime("%Y-%m-%d")
        timestr = datetime.now().strftime('%H%M%S')
        full_module_name = 'go_nogo_session_info_' + datestr

        import sys
        task_info_path = '/home/pi/experiment_info/go_nogo_task/session_info'
        sys.path.insert(0, task_info_path)
        tempmod = importlib.import_module(full_module_name)
        session_info = tempmod.session_info
        mouse_info = tempmod.mouse_info

        animal_ID = input("Enter animal ID (ex DT000):\n")
        session_info['mouse_name'] = animal_ID
        animal_weight = input("Enter animal weight (ex 19.5):\n")
        session_info['weight'] = animal_weight
        session_info['training_phase'] = 'baseline_2p'

        session_info['date'] = datestr
        session_info['time'] = timestr
        session_info['datetime'] = session_info['date'] + '_' + session_info['time']
        session_info['basename'] = session_info['mouse_name'] + '_' + session_info['datetime']
        session_info['dir_name'] = (
            session_info['basedir'] + "/" + session_info['mouse_name'] + "_" + session_info['datetime']
        )
        session_info['frame_sync_pin'] = session_info.get('frame_sync_pin', 16)

        if session_info['manual_date'] != session_info['date']:
            print('wrong date!!')
            raise RuntimeError('manual_date field in session_info file is not updated')

        os.makedirs(session_info['dir_name'])
        os.chdir(session_info['dir_name'])
        session_info['file_basename'] = (
            session_info['mouse_name'] + "_baseline_2p_" + session_info['datetime']
        )

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
            datefmt=('%H:%M:%S'),
            handlers=[
                logging.FileHandler(session_info['file_basename'] + '.log'),
                logging.StreamHandler()
            ]
        )

        task = go_nogo_baseline(name="go_nogo_baseline", session_info=session_info)

        task.start_session()
        scipy.io.savemat(
            session_info['file_basename'] + '_session_info.mat',
            {'session_info': session_info}
        )
        pickle.dump(
            session_info,
            open(session_info['file_basename'] + '_session_info.pkl', "wb")
        )

        print("Baseline running. Press Ctrl+C to stop.")
        logging.info(str(time.time()) + ", baseline_running")

        while True:
            task.run_baseline_once()
            try:
                task.box.flush_frame_events()
            except Exception:
                pass
            time.sleep(0.01)

    except (KeyboardInterrupt, SystemExit):
        print(Fore.RED + Style.BRIGHT + 'Exiting now...' + Style.RESET_ALL)
        ic('about to call end_session()')
        try:
            task.box.flush_frame_events()
        except Exception:
            pass
        task.end_session()
        try:
            task.box.flush_frame_events()
        except Exception:
            pass
        ic('just called end_session()')
        scipy.io.savemat(
            session_info['file_basename'] + '_session_info.mat',
            {'session_info': session_info}
        )
        pickle.dump(
            session_info,
            open(session_info['file_basename'] + '_session_info.pkl', "wb")
        )
