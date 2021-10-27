#Test file from https://github.com/bill-connelly/rpg 
################
import rpg
options = {"duration": 3, "angle": 45, "spac_freq": 0.4, "temp_freq": 2}
rpg.build_grating("~/second_grating.dat", options)
with rpg.Screen() as myscreen:
 grating = myscreen.load_grating("~/second_grating.dat")  
 myscreen.display_grating(grating)
