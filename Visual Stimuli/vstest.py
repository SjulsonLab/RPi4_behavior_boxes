#Test file from https://github.com/bill-connelly/rpg 
################
import rpg
options = {"duration": 2, "angle": 45, "spac_freq": 0.2, "temp_freq": 1}
rpg.build_grating("~/first_grating.dat", options)
with rpg.Screen() as myscreen:
 grating = myscreen.load_grating("~/first_grating.dat")  
 myscreen.display_grating(grating)
