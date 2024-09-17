#Test file from https://github.com/bill-connelly/rpg 
################
import rpg

# Define the "Go" stimulus as a black circle
options_go = {"shape": "circle", "color": (0, 0, 0), "angle": 0, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3, "percent_diameter": 50, "percent_center_left": 50, "percent_center_top": 50}
rpg.build_grating("~/first_grating_go_shape.dat", options_go)

# Define the "No-Go" stimulus as a black square
options_nogo = {
    "shape": "square",               # Defining it as a square
    "color": (0, 0, 0),              # Black color
    "angle": 0,                      # Set to 0 for an upright square
    "spac_freq": 0.1,                # Spatial frequency in cycles per degree
    "temp_freq": 0.3                 # Temporal frequency in cycles per second
    "duration": 3,                  
    "percent_size": 30,              # Size of the square as a percentage of the screen
    "percent_center_left": 50,       # Center of the square in x
    "percent_center_top": 50         # Center of the square in y
}
rpg.build_grating("~/first_grating_nogo_shape.dat", options_nogo)


# Running both "Go" (circle) and "No-Go" (square) stimuli

with rpg.Screen() as myscreen:
    grating_go = myscreen.load_grating("~/first_grating_go_shape.dat")
    myscreen.display_grating(grating_go)
  
    grating_nogo = myscreen.load_grating("~/first_grating_nogo_shape.dat")
    myscreen.display_grating(grating_nogo)
