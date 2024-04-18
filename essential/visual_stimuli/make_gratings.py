import rpg
from pathlib import Path

gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'

# options = {"duration": 2, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating("~/test_grating.dat", options)
#
# options = {"duration": 2, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating("~/test_grating.dat", options)

options = {"duration": .5, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating(gratings_dir / "vertical_grating_pulse.dat", options)

options = {"duration": .5, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating(gratings_dir / "horizontal_grating_pulse.dat", options)

with rpg.Screen() as myscreen:
    grating = myscreen.load_grating("~/second_grating.dat")
    myscreen.display_grating(grating)

