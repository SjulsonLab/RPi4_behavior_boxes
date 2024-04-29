#Test file from https://github.com/bill-connelly/rpg 
################
import rpg
options_go = {"duration": 3, "angle": 45, "spac_freq": 0.3, "temp_freq": 2}
rpg.build_grating("~/first_grating_go.dat", options_go)

options_nogo = {"duration": 3, "angle": 135, "spac_freq": 0.3, "temp_freq": 2}
rpg.build_grating("~/first_grating_nogo.dat", options_nogo)

with rpg.Screen() as myscreen:
 grating_go = myscreen.load_grating("~/first_grating_go.dat")
 myscreen.display_grating(grating_go)
 grating_nogo = myscreen.load_grating("~/first_grating_nogo.dat")
 myscreen.display_grating(grating_nogo)
