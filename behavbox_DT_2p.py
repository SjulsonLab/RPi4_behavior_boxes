# Merged behavior box file built from behavbox_DT_test and behavbox_DT.
# Goal: keep the behavior-side structure from DT_test while preserving
# the camera SSH-key support from DT, without the self-SSH / self-pkill issue.

from gpiozero import PWMLED, LED, Button
import os
import socket
import time
import shlex
import subprocess
from collections import deque
from icecream import ic
import pygame
import logging
from colorama import Fore, Style
import pysistence, collections
# from visualstim import VisualStim
from visualstim_go import VisualStim_go
from visualstim_nogo import VisualStim_nogo

import scipy.io, pickle

import Treadmill
import ADS1x15

from fake_session_info import fake_session_info

# for the flipper
from FlipperOutput import FlipperOutput


class BehavBox(object):
    # keep a class attribute for compatibility, but reset per instance in __init__
    event_list = deque()

    def __init__(self, session_info):
        # fresh event queue for each session / instance
        self.event_list = deque()

        # keep a local absolute path for local file operations,
        # while preserving session_info['dir_name'] for remote video commands
        self.session_info = session_info
        self.local_dir_name = os.path.abspath(self.session_info['dir_name'])

        try:
            # set up the external hard drive path for the flipper output
            storage_path = self.session_info['external_storage'] + '/' + self.session_info['basename']
            self.session_info['flipper_filename'] = (
                storage_path + '/' + self.session_info['basename'] + '_flipper_output'
            )

            # make data directory and initialize logfile
            os.makedirs(self.local_dir_name, exist_ok=True)
            self.session_info['file_basename'] = os.path.join(
                self.local_dir_name,
                self.session_info['mouse_name'] + "_" + self.session_info['datetime'],
            )
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s.%(msecs)03d,[%(levelname)s],%(message)s",
                datefmt=('%H:%M:%S'),
                handlers=[
                    logging.FileHandler(self.session_info['file_basename'] + '.log'),
                    logging.StreamHandler(),  # sends copy of log output to screen
                ],
            )
            os.chdir(self.local_dir_name)
            logging.info(";" + str(time.time()) + "; behavior_box_initialized")
        except Exception as error_message:
            print("Logging error")
            print(str(error_message))

        from subprocess import check_output

        try:
            # safer than decode(... )[:-2]; hostname -I can contain multiple addresses
            self.IP_address = check_output(['hostname', '-I']).decode('ascii').strip().split()[0]
        except Exception:
            self.IP_address = socket.gethostbyname(socket.gethostname())

        # Camera/video Pi IP selection:
        # 1) prefer explicit override in session_info
        # 2) otherwise use DT_test behavior: change final octet to 2
        explicit_video_ip = self.session_info.get('video_ip') or self.session_info.get('IP_address_video')
        if explicit_video_ip:
            self.IP_address_video = explicit_video_ip
        else:
            ip_parts = self.IP_address.split('.')
            if len(ip_parts) == 4 and ip_parts[-1]:
                # Preserve the DT_test behavior exactly: change only the final digit
                # of the final octet (for example 192.168.1.151 -> 192.168.1.152).
                ip_parts[-1] = ip_parts[-1][:-1] + '2'
                self.IP_address_video = '.'.join(ip_parts)
            else:
                ip_chars = list(self.IP_address)
                if ip_chars:
                    ip_chars[-1] = '2'
                self.IP_address_video = ''.join(ip_chars)

        self.ssh_user = self.session_info.get('video_ssh_user', 'pi')
        self.ssh_key_path = self.session_info.get('ssh_key_path', '/home/pi/.ssh/id_ed25519')
        self.use_ssh_key = bool(self.session_info.get('force_ssh_key', True)) and os.path.exists(self.ssh_key_path)
        self.run_preview = self.session_info.get('run_preview', True)

        if self.IP_address_video == self.IP_address:
            print(
                Fore.YELLOW
                + "Warning: IP_address_video matches local IP. "
                  "video_start/video_stop will refuse to run so this file does not kill the behavior process. "
                  "Set session_info['video_ip'] if your camera Pi uses a different address.\n"
                + Style.RESET_ALL
            )

        ###############################################################################################
        # below are all the pin numbers for Yi's breakout board
        # cue LEDs - setting PWM frequency of 200 Hz
        ###############################################################################################
        self.cueLED1 = BoxLED(22, frequency=200)
        self.cueLED2 = BoxLED(18, frequency=200)
        self.cueLED3 = BoxLED(17, frequency=200)
        self.cueLED4 = BoxLED(14, frequency=200)

        ###############################################################################################
        # digital I/O's - used for cue LED
        # cue for animals
        # DIO 1 and 2 are reserved for the audio board
        ###############################################################################################
        # self.DIO3 = LED(9)  # reserved for vacuum function
        self.DIO4 = LED(10)
        self.DIO5 = LED(11)
        # there is a DIO6, but that is the same pin as the camera strobe

        ###############################################################################################
        # IR detection (for licks)
        ###############################################################################################
        self.IR_rx1 = Button(5, None, True)  # None, True inverts the signal so poke=True, no-poke=False
        self.IR_rx2 = Button(6, None, True)
        self.IR_rx3 = Button(12, None, True)
        # self.IR_rx4 = Button(13, None, True)  # (optional, reserved for future use)
        # self.IR_rx5 = Button(16, None, True)  # (optional, reserved for future use)

        # link nosepoke event detections to callbacks (exit and entry are opposite to pressed and release)
        self.IR_rx1.when_pressed = self.left_IR_exit
        self.IR_rx2.when_pressed = self.center_IR_exit
        self.IR_rx3.when_pressed = self.right_IR_exit
        self.IR_rx1.when_released = self.left_IR_entry
        self.IR_rx2.when_released = self.center_IR_entry
        self.IR_rx3.when_released = self.right_IR_entry

        ###############################################################################################
        # Closed circuit detection for lick
        self.lick1 = Button(26, None, True)
        self.lick2 = Button(27, None, True)
        self.lick3 = Button(15, None, True)

        # Link lick detection event to callbacks
        self.lick1.when_pressed = self.left_exit
        self.lick2.when_pressed = self.right_exit
        self.lick3.when_pressed = self.center_exit

        self.lick1.when_released = self.left_entry
        self.lick2.when_released = self.right_entry
        self.lick3.when_released = self.center_entry

        ###############################################################################################
        # Optional frame-sync support. The current run_go_nogo_first_rule file calls
        # flush_frame_events() during every trial loop, so this BehavBox must always
        # expose that method even if frame sync is not actively used.
        ###############################################################################################
        self.enable_frame_sync = bool(self.session_info.get('enable_frame_sync', False))
        self.frame_sync_pin = self.session_info.get('frame_sync_pin', 16)
        self.frame_events = deque()
        self.frame_counter = 0
        self.frame_sync = None
        self.frame_log_path = self.session_info['file_basename'] + '_frame_sync.csv'

        if self.enable_frame_sync:
            try:
                self.frame_sync = Button(self.frame_sync_pin, pull_up=False)
                self.frame_sync.when_pressed = self.frame_sync_rise
                if not os.path.exists(self.frame_log_path):
                    with open(self.frame_log_path, 'w') as frame_log_file:
                        frame_log_file.write('timestamp_monotonic_ns,frame_number\n')
            except Exception as error_message:
                print('frame_sync issue\n')
                print(str(error_message))
                self.enable_frame_sync = False
                self.frame_sync = None

        ###############################################################################################
        # sound: audio board DIO - pins sending TTL to the Tsunami soundboard via SMA connectors
        ###############################################################################################
        # pins originally reserved for the lick detection is now used for audio board TTL input signal
        # NEW EDIT: switch sound to lick
        # self.sound1 = LED(26)  # originally lick1
        # self.sound2 = LED(27)  # originally lick2
        # self.sound3 = LED(15)  # originally lick3
        self.sound1 = LED(23)
        self.sound2 = self.sound1
        # self.sound1 = LED(23)  # new_lick modification
        # self.sound2 = LED(24)  # new_lick modification
        self.sound1.off()
        self.sound2.off()

        #################################################################################################
        # pump: trigger signal output to a driver board induce the solenoid valve to deliver reward
        # ###############################################################################################
        self.pump = Pump()
        self.pump.all_off()

        ###############################################################################################
        # flipper strobe signal
        ###############################################################################################
        # initializing flipper object
        try:
            self.flipper = FlipperOutput(self.session_info, pin=4)
        except Exception as error_message:
            print("flipper issue\n")
            print(str(error_message))
            self.flipper = None

        ###############################################################################################
        # visual stimuli initiation
        ###############################################################################################
        try:
            # self.visualstim = VisualStim(self.session_info)
            self.visualstim_go = VisualStim_go(self.session_info)
            self.visualstim_nogo = VisualStim_nogo(self.session_info)
        except Exception as error_message:
            print("visualstim issue\n")
            print(str(error_message))

        ###############################################################################################
        # ADC (Adafruit_ADS1x15) setup
        ###############################################################################################
        try:
            self.ADC = ADS1x15.ADS1015
        except Exception as error_message:
            print("ADC issue\n")
            print(str(error_message))

        # ###############################################################################################
        # Treadmill setup
        # ###############################################################################################
        if session_info.get('treadmill', False) is True:
            try:
                self.treadmill = Treadmill.Treadmill(self.session_info)
            except Exception as error_message:
                print("treadmill issue\n")
                print(str(error_message))
                self.treadmill = False
        else:
            self.treadmill = False
            print("No treadmill I2C connected detected!")

    def _ssh_base(self):
        cmd = ['ssh']
        if self.use_ssh_key:
            cmd.extend(['-i', self.ssh_key_path])
        cmd.append(f"{self.ssh_user}@{self.IP_address_video}")
        return cmd

    def _ssh_command_string(self, remote_cmd):
        parts = ['ssh']
        if self.use_ssh_key:
            parts.extend(['-i', self.ssh_key_path])
        parts.append(f"{self.ssh_user}@{self.IP_address_video}")
        parts.append(remote_cmd)
        return ' '.join(shlex.quote(part) for part in parts)

    def _run_remote(self, remote_cmd, check=True, allow_fail=False, description='remote command'):
        result = subprocess.run(self._ssh_base() + [remote_cmd])
        if check and result.returncode != 0 and not allow_fail:
            raise RuntimeError(
                f"{description} failed with exit code {result.returncode}: {remote_cmd}"
            )
        return result.returncode

    def _run_local(self, cmd, check=True, allow_fail=False, description='local command'):
        result = subprocess.run(cmd)
        if check and result.returncode != 0 and not allow_fail:
            raise RuntimeError(
                f"{description} failed with exit code {result.returncode}: {' '.join(cmd)}"
            )
        return result.returncode

    def _force_outputs_low(self):
        try:
            self.DIO4.off()
        except Exception:
            pass
        try:
            self.DIO5.off()
        except Exception:
            pass
        try:
            self.sound1.off()
        except Exception:
            pass
        try:
            self.sound2.off()
        except Exception:
            pass
        try:
            self.pump.all_off()
        except Exception:
            pass
        for led_name in ('cueLED1', 'cueLED2', 'cueLED3', 'cueLED4'):
            try:
                getattr(self, led_name).off()
            except Exception:
                pass

    def _dump_session_info(self, hd_dir, basename):
        scipy.io.savemat(os.path.join(hd_dir, basename + '_session_info.mat'), {'session_info': self.session_info})
        print("dumping session_info")
        with open(os.path.join(hd_dir, basename + '_session_info.pkl'), 'wb') as f:
            pickle.dump(self.session_info, f)

    ###############################################################################################
    # methods to start and stop video
    # These work with fake video files but haven't been tested with real ones
    ###############################################################################################
    def video_start(self):
        IP_address_video = self.IP_address_video
        dir_name = self.session_info['dir_name']
        basename = self.session_info['basename']
        file_name = dir_name + "/" + basename

        # create directory on the external storage
        base_dir = self.session_info['external_storage'] + '/'
        hd_dir = base_dir + basename
        os.makedirs(hd_dir, exist_ok=True)

        print(Fore.YELLOW + "Killing any python process prior to this session!\n" + Style.RESET_ALL)
        try:
            if IP_address_video == self.IP_address:
                raise RuntimeError(
                    "Refusing to run video_start because IP_address_video matches the local IP. "
                    "Set session_info['video_ip'] to the camera Pi address."
                )

            self._force_outputs_low()

            self._run_remote(
                'mkdir -p ~/video',
                check=True,
                allow_fail=True,
                description='ensure remote ~/video directory exists',
            )
            self._run_remote(
                'touch ~/video/videolog.log',
                check=True,
                allow_fail=True,
                description='ensure remote videolog exists',
            )

            # allow_fail=True because pkill exits nonzero when nothing is running
            self._run_remote('pkill python', check=True, allow_fail=True, description='pre-session pkill')
            if self.run_preview:
                print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
                print(Fore.RED + "\n CRTL + C to quit previewing and start recording" + Style.RESET_ALL)

                # Use os.system here to preserve the original DT_test behavior: Ctrl+C should
                # stop the remote preview and then return control to this Python process.
                preview_cmd = self._ssh_command_string('/home/pi/RPi4_behavior_boxes/start_preview.py')
                try:
                    os.system(preview_cmd)
                except KeyboardInterrupt:
                    print(Fore.YELLOW + "Preview interrupted locally; continuing to recording." + Style.RESET_ALL)
            else:
                print(Fore.YELLOW + "Preview skipped by default; set session_info['run_preview'] = True to enable it." + Style.RESET_ALL)

            print(Fore.GREEN + "\nKilling any python process before start recording!" + Style.RESET_ALL)
            self._run_remote('pkill python', check=True, allow_fail=True, description='pre-record pkill')
            time.sleep(2)

            # Prepare the path for recording
            self._run_remote(
                'mkdir -p ' + shlex.quote(dir_name),
                description='create remote recording directory',
            )
            self._run_remote(
                'date >> ~/video/videolog.log',
                description='append date to remote videolog',
            )

            acquisition_cmd = (
                'nohup /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py '
                + shlex.quote(file_name)
                + ' >> ~/video/videolog.log 2>&1 &'
            )

            # start the flipper before the recording start
            try:
                if self.flipper is not None:
                    self.flipper.flip()
            except Exception as error_message:
                print("flipper can't run\n")
                print(str(error_message))

            # Treadmill initiation
            if self.treadmill is not False:
                try:
                    self.treadmill.start()
                except Exception as error_message:
                    print("treadmill cannot run\n")
                    print(str(error_message))

            # start recording
            print(Fore.GREEN + "\nStart Recording!" + Style.RESET_ALL)
            self._run_remote(acquisition_cmd, description='start acquisition')
            time.sleep(1)
            print(
                Fore.RED
                + Style.BRIGHT
                + "Please verify that camera recording started. Cancel the session if it did not."
                + Style.RESET_ALL
            )

            # start initiating the dumping of the session information when available
            self._dump_session_info(hd_dir, basename)

        except Exception as e:
            print(e)
            try:
                logging.exception('video_start failed')
            except Exception:
                pass
            self._force_outputs_low()
            try:
                if self.flipper is not None:
                    self.flipper.close()
            except Exception:
                pass
            try:
                if self.treadmill is not False:
                    self.treadmill.close()
            except Exception:
                pass

    def video_stop(self):
        # Get the basename from the session information
        basename = self.session_info['basename']
        dir_name = self.session_info['dir_name']
        # Get the ip address for the box video:
        IP_address_video = self.IP_address_video
        try:
            if IP_address_video == self.IP_address:
                raise RuntimeError(
                    "Refusing to run video_stop because IP_address_video matches the local IP. "
                    "Set session_info['video_ip'] to the camera Pi address."
                )

            # Run the stop_video script in the box video
            self._run_remote(
                '/home/pi/RPi4_behavior_boxes/video_acquisition/stop_acquisition.sh',
                check=True,
                allow_fail=True,
                description='stop acquisition',
            )
            time.sleep(2)

            # now stop the flipper after the video stopped recording
            try:
                if self.flipper is not None:
                    self.flipper.close()
            except Exception:
                pass
            time.sleep(2)

            if self.treadmill is not False:
                try:
                    self.treadmill.close()
                except Exception:
                    pass

            self._force_outputs_low()

            hostname = socket.gethostname()
            print("Moving video files from " + hostname + "video to " + hostname + ":")

            # Create a directory for storage on the hard drive mounted on the box behavior
            base_dir = self.session_info['external_storage'] + '/'
            hd_dir = base_dir + basename
            os.makedirs(hd_dir, exist_ok=True)

            self._dump_session_info(hd_dir, basename)

            rsync_video_cmd = ['rsync', '-av', '--progress', '--remove-source-files']
            if self.use_ssh_key:
                rsync_video_cmd.extend(['-e', f'ssh -i {self.ssh_key_path}'])

            # Move the video + log from the box_video SD card to the box_behavior external hard drive
            remote_dir_exists = self._run_remote(
                'test -d ' + shlex.quote(dir_name),
                check=False,
                allow_fail=True,
                description='check remote video directory',
            ) == 0

            if remote_dir_exists:
                self._run_local(
                    rsync_video_cmd
                    + [f'{self.ssh_user}@{IP_address_video}:{dir_name}/', hd_dir],
                    check=True,
                    allow_fail=True,
                    description='rsync remote video directory',
                )
            else:
                print('Skipping remote video rsync because the remote session directory was not created.')

            remote_logs_exist = self._run_remote(
                'bash -lc ' + shlex.quote('compgen -G ~/video/*.log > /dev/null'),
                check=False,
                allow_fail=True,
                description='check remote video logs',
            ) == 0

            if remote_logs_exist:
                self._run_local(
                    rsync_video_cmd
                    + [f'{self.ssh_user}@{IP_address_video}:~/video/*.log', hd_dir],
                    check=True,
                    allow_fail=True,
                    description='rsync remote video logs',
                )
            else:
                print('Skipping remote video log rsync because no remote video logs were found.')

            self._run_local(
                ['rsync', '-arvz', '--progress', '--remove-source-files', self.local_dir_name + '/', hd_dir],
                check=True,
                allow_fail=True,
                description='rsync local session directory',
            )
            print('rsync finished!')

        except Exception as e:
            print(e)
            try:
                logging.exception('video_stop failed')
            except Exception:
                pass
            self._force_outputs_low()

    def frame_sync_rise(self):
        if not self.enable_frame_sync:
            return
        ts_ns = time.monotonic_ns()
        self.frame_counter += 1
        self.frame_events.append((ts_ns, self.frame_counter))

    def flush_frame_events(self):
        if not self.enable_frame_sync:
            return
        if not self.frame_events:
            return
        try:
            with open(self.frame_log_path, 'a') as frame_log_file:
                while self.frame_events:
                    ts_ns, frame_number = self.frame_events.popleft()
                    frame_log_file.write(f'{ts_ns},{frame_number}\n')
        except Exception as error_message:
            print('frame_sync flush issue\n')
            print(str(error_message))

    ###############################################################################################
    # callbacks
    ###############################################################################################
    def left_IR_entry(self):
        self.event_list.append('left_IR_entry')
        logging.info(str(time.time()) + ', left_IR_entry')

    def center_IR_entry(self):
        self.event_list.append('center_IR_entry')
        logging.info(str(time.time()) + ', center_IR_entry')

    def right_IR_entry(self):
        self.event_list.append('right_IR_entry')
        logging.info(str(time.time()) + ', right_IR_entry')

    def left_IR_exit(self):
        self.event_list.append('left_IR_exit')
        logging.info(str(time.time()) + ', left_IR_exit')

    def center_IR_exit(self):
        self.event_list.append('center_IR_exit')
        logging.info(str(time.time()) + ', center_IR_exit')

    def right_IR_exit(self):
        self.event_list.append('right_IR_exit')
        logging.info(str(time.time()) + ', right_IR_exit')

    def left_entry(self):
        self.event_list.append('left_entry')
        logging.info(str(time.time()) + ', left_entry')

    def center_entry(self):
        self.event_list.append('center_entry')
        logging.info(str(time.time()) + ', center_entry')

    def right_entry(self):
        self.event_list.append('right_entry')
        logging.info(str(time.time()) + ', right_entry')

    def left_exit(self):
        self.event_list.append('left_exit')
        logging.info(str(time.time()) + ', left_exit')

    def center_exit(self):
        self.event_list.append('center_exit')
        logging.info(str(time.time()) + ', center_exit')

    def right_exit(self):
        self.event_list.append('right_exit')
        logging.info(str(time.time()) + ', right_exit')


# this is for the cue LEDs. BoxLED.value is the intensity value (PWM duty cycle, from 0 to 1)
# currently. BoxLED.set_value is the saved intensity value that determines how bright the
# LED will be if BoxLED.on() is called. This is better than the original PWMLED class.
class BoxLED(PWMLED):
    set_value = 1  # the intensity value, ranging from 0-1

    def on(
        self,
    ):  # unlike PWMLED, here the on() function sets the intensity to set_value,
        # not to full intensity
        self.value = self.set_value


class Pump(object):
    def __init__(self):
        self.pump1 = LED(19)  # for testing only - the correct pin number is 19
        self.pump2 = LED(20)
        self.pump3 = LED(21)
        self.pump4 = LED(7)
        self.pump_air = LED(8)
        self.pump_vacuum = LED(25)

    def all_off(self):
        self.pump1.off()
        self.pump2.off()
        self.pump3.off()
        self.pump4.off()
        self.pump_air.off()
        self.pump_vacuum.off()

    def reward(self, which_pump, on_time, off_time, numtimes):
        # coefficient_fit = np.array([8.78674242e-04, 7.33609848e-02, 1.47535000e+00]) # further calibration is needed
        # coefficient_1 = coefficient_fit[-1]
        # coefficient_2 = coefficient_fit[-2]
        # coefficient_3 = coefficient_fit[-3] - reward_size
        tube_fit = 0.11609  # ml/s
        # discriminant = coefficient_2 ** 2 - 4 * coefficient_1 * coefficient_3
        # # find solution, i.e. duration of pulse, by calculating the solution for the quadratic equation
        # solution = np.array([(-coefficient_2 + np.sqrt(discriminant)) / (2 * coefficient_1),
        #                      (-coefficient_2 - np.sqrt(discriminant)) / (2 * coefficient_1)])

        # With two solution, get the positive value
        # solution_positive = solution[(solution > 0).nonzero()[0][0]]
        # round to the second decimal
        # duration = round(solution_positive, 3) * (10**-3)

        duration_vacuum = 0.1  # in seconds

        if which_pump == '1':
            self.pump1.blink(on_time, off_time, numtimes, background=True)
            logging.info(str(time.time()) + ', pump1_reward')
        elif which_pump == '2':
            self.pump2.blink(on_time, off_time, numtimes, background=True)
            logging.info(str(time.time()) + ', pump2_reward')
        elif which_pump == '3':
            self.pump3.blink(on_time, off_time, numtimes, background=True)
            logging.info(str(time.time()) + ', pump3_reward')
        elif which_pump == '4':
            self.pump4.blink(on_time, off_time, numtimes, background=True)
            logging.info(str(time.time()) + ', pump4_reward')
        elif which_pump == 'air_puff':
            self.pump_air.blink(on_time, off_time, numtimes, background=True)
            logging.info(str(time.time()) + ', air_puff')
        elif which_pump == 'vacuum':
            self.pump_vacuum.blink(on_time, off_time, numtimes, background=True)
            logging.info(str(time.time()) + ', vacuum')
