import rpg
from pathlib import Path

gratings_dir = Path('/home/pi/gratings')  # './dummy_vis'

# options = {"duration": 2, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating("~/test_grating.dat", options)
#
# options = {"duration": 2, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating("~/test_grating.dat", options)

# options = {"duration": .5, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating(gratings_dir / "vertical_grating_.5s.dat", options)
#
# options = {"duration": .5, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
# rpg.build_grating(gratings_dir / "horizontal_grating_.5s.dat", options)

durations = [.5, 1, 2]

for duration in durations:
    options = {"duration": duration, "angle": 90, "spac_freq": 0.2, "temp_freq": 1}
    rpg.build_grating(gratings_dir / f"vertical_grating_{duration}s.dat", options)

    options = {"duration": duration, "angle": 0, "spac_freq": 0.2, "temp_freq": 1}
    rpg.build_grating(gratings_dir / f"horizontal_grating_{duration}s.dat", options)

