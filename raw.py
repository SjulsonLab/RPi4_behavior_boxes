import rpg

#"Go" stimulus: triangle
convert_raw("~/home/pi/output_image.raw", "~/home/pi/gratings/triag_c.raw", 1, 1024, 768, 180)

with rpg.Screen() as myscreen:
 raw_go = myscreen.load_raw("~/triag_c.raw")
 myscreen.display_raw(raw_go)
  


