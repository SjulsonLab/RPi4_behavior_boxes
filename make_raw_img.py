# This script loads an example image from the scipy library
# and then converts it to a format suitable for conversion
# with rpg.convert_raw(). Use this as a basis for converting
# your own raw data

import rpg
from scipy import misc
import numpy as np

#import an image
face = misc.face()

#face is a 3D numpy array of uint8
#face.shape is (768,1024,3)

#Preallocate a single dimension numpy array to hold the reordered data
flatim = np.zeros(np.size(face), dtype=np.uint8)

#Place all of the red data at index 0, and every 3rd index from then
flatim[0::3] = face[:,:,0].flatten()
#Place all of the blue data at index 1, and every 3rd index from then
flatim[1::3] = face[:,:,1].flatten()
#Place all of the green data at index 2 and every 3rd index from then
flatim[2::3] = face[:,:,2].flatten()

#save the data to drive in this format, making doubly sure to save it as uint8
with open("simpleraw.raw", mode="wb") as fh:
    flatim.astype(np.uint8).tofile(fh)

#use RPG to convert it
rpg.convert_raw("simpleraw.raw", "simpleraw_c.raw", 1, 1024, 768, 100)

#Display it when done, just to be sure.
with rpg.Screen(resolution=(1024,768)) as myscreen:
  raw = myscreen.load_raw("simpleraw_c.raw")
  myscreen.display_raw(raw)

