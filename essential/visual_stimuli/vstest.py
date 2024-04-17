#Test file from https://github.com/bill-connelly/rpg 
################
import rpg
import time
from pathlib import Path

gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'
# options = {"duration": 2, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating("~/second_grating.dat", options)

options = {"duration": 2, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating(gratings_dir / "test0_grating.dat", options)

options = {"duration": 2, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating(gratings_dir / "test1_grating.dat", options)

options = {"duration": .5, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating(gratings_dir / "test2_grating.dat", options)

options = {"duration": .5, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating(gratings_dir / "test3_grating.dat", options)

with rpg.Screen() as myscreen:
    grating = myscreen.load_grating(gratings_dir / "test0_grating.dat")
    myscreen.display_grating(grating)
    time.sleep(3)

    grating = myscreen.load_grating(gratings_dir / "test1_grating.dat")
    myscreen.display_grating(grating)
    time.sleep(3)

    grating = myscreen.load_grating(gratings_dir / "test2_grating.dat")
    myscreen.display_grating(grating)
    time.sleep(.5)

    grating = myscreen.load_grating(gratings_dir / "test3_grating.dat")
    myscreen.display_grating(grating)


 # grating = myscreen.load_grating("~/second_grating.dat")
 # myscreen.display_grating(grating)
