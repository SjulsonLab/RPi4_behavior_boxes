import rpg
import time
import threading
from pathlib import Path
from icecream import ic
import sys
sys.path.append('/home/pi/RPi4_behavior_boxes')
from essential.visualstim import VisualStim
from essential.visual_stimuli.visualstim_concurrent import VisualStimThreaded, VisualStimMultiprocess
from session_info import make_session_info


def repeat_stimulus(stimulus_path: str, t_stimulus: int):
    with rpg.Screen() as myscreen:
        grating = myscreen.load_grating(stimulus_path)
        for _ in range(t_stimulus):
            ic("Stimulus on")
            myscreen.display_grating(grating)

            ic("Gray screen on")
            myscreen.display_greyscale(0)
            time.sleep(.5)


def alternate_process(t_stimulus: int):
    st = time.perf_counter()
    while time.perf_counter() - st < t_stimulus:
        ic(time.perf_counter() - st, 'sec elapsed')
        time.sleep(.5)


def repeat_stimulus_process(visualstim: VisualStim, stimulus_name: str, t_stimulus: float):
    visualstim.loop_grating_process(stimulus_name, t_stimulus)


def repeat_grayscreen(visualstim: VisualStim, t_stimulus: int):
    with rpg.Screen() as myscreen:
        for _ in range(t_stimulus):
            ic("Gray screen on")
            visualstim.myscreen.display_greyscale(40)
            time.sleep(1)
            ic("Gray screen off")
            myscreen.display_greyscale(0)
            time.sleep(1)


# def run_multithreading():
#     t_stimulus = 10
#     gratings_dir = Path('/home/pi/gratings')
#     grating = gratings_dir / "vertical_grating_0.5s.dat"
#
#     tstart = time.perf_counter()
#     t_stim = threading.Thread(target=repeat_stimulus, args=(grating, t_stimulus))
#     t_stim.start()
#     alternate_process(t_stimulus=t_stimulus)
#     # t_iter = threading.Thread(target=alternate_process, args=(t_stimulus,))
#     # t_iter.start()
#
#     t_stim.join()
#     ic("Total time elapsed:", time.perf_counter() - tstart)


def run_multithreading():
    t_stimulus = 10

    session_info = make_session_info()
    visualstim = VisualStimThreaded(session_info)
    grating_name = 'vertical_grating_{}s.dat'.format(session_info['grating_duration'])

    tstart = time.perf_counter()
    visualstim.loop_grating(grating_name, t_stimulus)
    alternate_process(t_stimulus=t_stimulus)

    visualstim.end_gratings_process()
    ic("Total time elapsed:", time.perf_counter() - tstart)
    ic(visualstim.presenter_commands.pop())


def run_multiprocessing():
    t_stimulus = 10

    session_info = make_session_info()
    visualstim = VisualStimMultiprocess(session_info)
    grating_name = 'vertical_grating_{}s.dat'.format(session_info['grating_duration'])

    tstart = time.perf_counter()
    visualstim.loop_grating(grating_name, t_stimulus)
    alternate_process(t_stimulus=t_stimulus)

    visualstim.end_gratings_process()
    ic("Total time elapsed:", time.perf_counter() - tstart)
    ic(visualstim.presenter_commands.get())



def main():
    run_multithreading()
    run_multiprocessing()

    # threading.Thread(target=repeat_grayscreen, args=(t_stimulus,)).start()
    # repeat_stimulus_process(visualstim, "vertical_grating_0.5s.dat", t_stimulus)


if __name__ == '__main__':
    main()
