#Test file from https://github.com/bill-connelly/rpg 
################
import rpg
options_go = {"duration": 3, "angle": 45, "spac_freq": 1, "temp_freq": 6.66}
rpg.build_grating("~/first_grating_go_diag.dat", options_go)

options_nogo = {"duration": 3, "angle": 135, "spac_freq": 1, "temp_freq":6.66}
rpg.build_grating("~/first_grating_nogo_diag.dat", options_nogo)

with rpg.Screen() as myscreen:
 grating_go = myscreen.load_grating("~/first_grating_go_diag.dat")
 myscreen.display_grating(grating_go)
 grating_nogo = myscreen.load_grating("~/first_grating_nogo_diag.dat")
 myscreen.display_grating(grating_nogo)
