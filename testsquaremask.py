#Piece of code removed from bill-connelly and modified to build a square mask 
import rpg
import _rpigratings as rg

# Define the "Go" stimulus - white circle, black background

options_go = {"angle": 90, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3,  "contrast": 0, "percent_diameter": 50, "percent_center_left": 50, "percent_center_top": 50, "background": 0}
rpg.build_masked_grating("~/first_grating_go_smask.dat", options_go)

# Create a Square Mask

import numpy as np
import math

# Constants for colormode, waveform, etc.
RGB888MODE = 0
RGB565MODE = 1
OUTSIDEMASK = 0
INSIDEMASK = 1
SQUARE = 0
SINE = 1
FULLSCREEN = 0
SQUARE_SHAPE = 1
GABOR = 2
DEGREES_SUBTENDED = 1  # Placeholder value for your environment

# Function to simulate pixel creation based on RGB values (can use more advanced methods)
def rgb_to_uint_24bit(r, g, b):
    return (r << 16) | (g << 8) | b

def rgb_to_uint_16bit(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

# Placeholder for waveform functions
def squarewave(x, y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode):
    # Simplified example - adjust according to your needs
    return rgb_to_uint_24bit(contrast, contrast, contrast)

def sinewave(x, y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode):
    # Simplified example - adjust according to your needs
    return rgb_to_uint_24bit(contrast, contrast, contrast)

def gabor(x, y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode):
    # Simplified example - adjust according to your needs
    return rgb_to_uint_24bit(contrast, contrast, contrast)

def square_shape(waveform, square_shape_size, padding, point_x, point_y, center_x, center_y, t, wavelength, speed, 
                 angle, cosine, sine, weight, contrast, background, colormode):
    
    left_boundary = center_x - (square_shape_size / 2) - padding
    right_boundary = center_x + (square_shape_size / 2) + padding
    top_boundary = center_y - (square_shape_size / 2) - padding
    bottom_boundary = center_y + (square_shape_size / 2) + padding

    if point_x < left_boundary or point_x > right_boundary or point_y < top_boundary or point_y > bottom_boundary:
        square_shape_case = OUTSIDEMASK
    else:
        square_shape_case = INSIDEMASK
        weight = 1

    if colormode == RGB888MODE:
        if square_shape_case == OUTSIDEMASK:
            return rgb_to_uint_24bit(background, background, background)
        elif square_shape_case == INSIDEMASK:
            if waveform == SQUARE:
                return squarewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode)
            elif waveform == SINE:
                return sinewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode)
    elif colormode == RGB565MODE:
        if square_shape_case == OUTSIDEMASK:
            return rgb_to_uint_16bit(background, background, background)
        elif square_shape_case == INSIDEMASK:
            if waveform == SQUARE:
                return squarewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode)
            elif waveform == SINE:
                return sinewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode)

def gaussian(x, sigma):
    return math.exp(-(x ** 2) / (2 * sigma ** 2)) if sigma != 0 else 1

def build_frame(t, angle, framebuffer, wavelength, speed, waveform, contrast, background, center_j, center_i, sigma, square_shape_size, padding, colormode):
    angle = math.radians(angle)
    sine = math.sin(angle)
    cosine = math.cos(angle)
    
    array_start = np.zeros((framebuffer['height'], framebuffer['width'], 3), dtype=np.uint8)

    for i in range(framebuffer['height']):
        for j in range(framebuffer['width']):
            left_boundary = center_j - (square_shape_size / 2) - padding
            right_boundary = center_j + (square_shape_size / 2) + padding
            top_boundary = center_i - (square_shape_size / 2) - padding
            bottom_boundary = center_i + (square_shape_size / 2) + padding
            
            square_shape_weight = 1 if (j >= left_boundary and j <= right_boundary and i >= top_boundary and i <= bottom_boundary) else 0
            gauss_weight = gaussian(0, sigma) 

            pixel_value = None
            if square_shape_weight:
                pixel_value = square_shape(waveform, square_shape_size, padding, j, i, center_j, center_i, t, wavelength, speed, angle, cosine, sine, square_shape_weight, contrast, background, colormode)
            else:
                pixel_value = rgb_to_uint_24bit(background, background, background)

            array_start[i, j] = [pixel_value >> 16 & 0xFF, pixel_value >> 8 & 0xFF, pixel_value & 0xFF]

    return array_start

def build_square_shape_grating(filename, options):
    fps = 60  # Placeholder for refresh rate
    print(f"Refresh rate measured as: {fps} hz")

    width, height = options['width'], options['height']
    colormode = options['colormode']

    fb0 = {'width': width, 'height': height, 'depth': 24 if colormode == RGB888MODE else 16, 'size': width * height * 3}

    wavelength = (fb0['width'] / DEGREES_SUBTENDED) / options['spac_freq']
    speed = wavelength * options['temp_freq'] / fps
    speed = max(1, speed)

    side_length = fb0['width'] * options['percent_side_length'] / 100
    center_j = fb0['width'] * options['percent_center_left'] / 100
    center_i = fb0['height'] * options['percent_center_top'] / 100
    padding = side_length * options['percent_padding'] / 100

    frame_count = int(options['duration'] * fps)
    for t in range(frame_count):
        frame = build_frame(t, options['angle'], fb0, wavelength, speed, options['waveform'], options['contrast'], options['background'], center_j, center_i, 0, side_length, padding, colormode)

        with open(filename, 'ab') as f:
            frame.tofile(f)

# Define the "No Go" stimulus - black square, white background

options_nogo = {
    "angle": 90, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3, "contrast": 0, "colormode": RGB888MODE,
    "percent_side_length": 50, "percent_center_left": 50, "percent_center_top": 50, "background": 255, 
    "width": 800, "height": 600, "percent_padding": 1, "waveform": SQUARE 
}
    
rpg.build_grating("~/first_grating_nogo_smask.dat", options_nogo)



with rpg.Screen() as myscreen:
    grating_go = myscreen.load_grating("~/first_grating_go_smask.dat")
    myscreen.display_grating(grating_go)
  
    grating_nogo = myscreen.load_grating("~/first_grating_nogo_smask.dat")
    myscreen.display_grating(grating_nogo)
