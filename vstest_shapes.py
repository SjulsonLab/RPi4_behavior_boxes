#Test file from https://github.com/bill-connelly/rpg 
################
import rpg

# Define the "Go" stimulus as a black circle
options_go = {"shape": "circle", "color": (0, 0, 0), "angle": 0, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3, "percent_diameter": 50, "percent_center_left": 50, "percent_center_top": 50}
rpg.build_grating("~/first_grating_go_shape.dat", options_go)

# Define the "No-Go" stimulus as a black square
options_nogo = {"shape": "square", "color": (0, 0, 0), "angle": 0, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3, "percent_size": 30, "percent_center_left": 50, "percent_center_top": 50}
rpg.build_grating("~/first_grating_nogo_shape.dat", options_nogo)


# Running both "Go" (circle) and "No-Go" (square) stimuli

with rpg.Screen() as myscreen:
    grating_go = myscreen.load_grating("~/first_grating_go_shape.dat")
    myscreen.display_grating(grating_go)
  
    grating_nogo = myscreen.load_grating("~/first_grating_nogo_shape.dat")
    myscreen.display_grating(grating_nogo)
