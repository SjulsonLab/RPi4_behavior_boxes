###############################################################################################
# methods to start and stop video - use if RPG gets upgraded to 1. support 2 screens 2. support recent Pi OS versions
###############################################################################################
def video_start(self):
    if self.session_info['ephys_rig']:
        try:
            print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
            print(Fore.RED + "\nCRTL + C to quit previewing and start recording" + Style.RESET_ALL)
            start_preview.main()

            # start recording
            print(Fore.GREEN + "\nStart Recording!" + Style.RESET_ALL)
            shell_output = subprocess.run(
                ['sh', './start_acquisition.sh', self.session_info['video_dir'],
                 self.session_info['file_basename']])

            if shell_output.returncode == 0:
                print("Recording started!")
            else:
                print("Recording failed to start!")
                print(shell_output.stderr)
                raise RuntimeError("Recording failed to start!")

            print(Fore.RED + Style.BRIGHT + "Please check if the preview screen is on! "
                                            "Cancel the session if it's not!" + Style.RESET_ALL)

        except Exception as error_message:
            print("ephys rig can't run camera\n")
            print(str(error_message))

    else:
        print(Fore.YELLOW + "Killing any python process prior to this session!\n" + Style.RESET_ALL)
        try:
            os.system("ssh pi@" + self.IP_address_video + " pkill python")

            # Preview check
            print(Fore.CYAN + "\nStart Previewing ..." + Style.RESET_ALL)
            print(Fore.RED + "\n CRTL + C to quit previewing and start recording" + Style.RESET_ALL)
            os.system("ssh pi@" + self.IP_address_video + " '/home/pi/RPi4_behavior_boxes/start_preview.py'")

            # Kill any python process before start recording
            print(Fore.GREEN + "\nKilling any python process before start recording!" + Style.RESET_ALL)
            os.system("ssh pi@" + self.IP_address_video + " pkill python")
            time.sleep(2)

            # Prepare the path for recording
            os.system("ssh pi@" + self.IP_address_video + " mkdir " + self.session_info['output_dir'])
            os.system("ssh pi@" + self.IP_address_video + " 'date >> ~/video/videolog.log' ")  # I/O redirection
            tempstr = (
                    "ssh pi@" + self.IP_address_video + " 'nohup /home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition.py "
                    + self.session_info['file_basename']
                    + " >> ~/video/videolog.log 2>&1 & ' "  # file descriptors
            )

            # start recording
            print(Fore.GREEN + "\nStart Recording!" + Style.RESET_ALL)
            os.system(tempstr)
            print(Fore.RED + Style.BRIGHT + "Please check if the preview screen is on! Cancel the session if it's not!" + Style.RESET_ALL)

        except Exception as e:
            print(e)

def video_stop(self):
    if self.session_info['ephys_rig']:
        try:
            os.system("sh ./video_acquisition/stop_acquisition.sh")
        except Exception as error_message:
            print("ephys rig can't stop camera\n")
            print(str(error_message))

    else:
        try:
            os.system(
                "ssh pi@" + self.IP_address_video + " /home/pi/RPi4_behavior_boxes/video_acquisition/stop_acquisition.sh")

        except Exception as e:
            print(e)