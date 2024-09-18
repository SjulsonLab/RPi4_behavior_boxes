#Piece of code removed from bill-connelly and modified to build a square maksk - IN PROCESS

import RPG

# Define the "Go" stimulus - white circle, black background

options_go = {"angle": 90, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3,  "contrast": 0, "percent_diameter": 50, "percent_center_left": 50, "percent_center_top": 50, "background": 0}
rpg.build_masked_grating("~/first_grating_go_smask.dat", options_go)

# Define the "No Go" stimulus - black square, white background

void* square_shape(int waveform, int square_shape_size, int padding, int point_x, int point_y, int center_x, int center_y, int t, int wavelength, int speed, 
             double angle, double cosine, double sine, double weight, double contrast, int background, int colormode)
{
    void* pixel_ptr;
    uint16_t* pixel_ptr_16;
    uint24_t* pixel_ptr_24;
    int square_shape_case;

    // Define boundaries for the square_shape based on its size and padding
    int left_boundary = center_x - (square_shape_size / 2) - padding;
    int right_boundary = center_x + (square_shape_size / 2) + padding;
    int top_boundary = center_y - (square_shape_size / 2) - padding;
    int bottom_boundary = center_y + (square_shape_size / 2) + padding;

    // Check if the point falls inside or outside the square_shape mask
    if (point_x < left_boundary || point_x > right_boundary || point_y < top_boundary || point_y > bottom_boundary) {
        // Outside the square_shape mask
        square_shape_case = OUTSIDEMASK;
    } else if (point_x >= left_boundary && point_x <= right_boundary && point_y >= top_boundary && point_y <= bottom_boundary) {
        // Inside the square_shape mask
        square_shape_case = INSIDEMASK;
        weight = 1;
    }

    // Switch cases based on square_shape_case and color mode
    switch(square_shape_case | colormode | waveform){
        case(OUTSIDEMASK | RGB888MODE | SQUARE):
        case(OUTSIDEMASK | RGB888MODE | SINE):
            pixel_ptr_24 = malloc(sizeof(uint24_t));
            *pixel_ptr_24 = rgb_to_uint_24bit(background, background, background);
            break;
        case(OUTSIDEMASK | RGB565MODE | SQUARE):
        case(OUTSIDEMASK | RGB565MODE | SINE):
            pixel_ptr_16 = malloc(sizeof(uint16_t));
            *pixel_ptr_16 = rgb_to_uint(background, background, background);
            break;
        case(INSIDEMASK | RGB888MODE | SQUARE):
            pixel_ptr_24 = squarewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode);
            break;
        case(INSIDEMASK | RGB888MODE | SINE):
            pixel_ptr_24 = sinewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode);
            break;
        case(INSIDEMASK | RGB565MODE | SQUARE):
            pixel_ptr_16 = squarewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode);
            break;
        case(INSIDEMASK | RGB565MODE | SINE):
            pixel_ptr_16 = sinewave(point_x, point_y, t, wavelength, speed, angle, cosine, sine, weight, contrast, background, colormode);
    }

    if(colormode == RGB888MODE){
        pixel_ptr = pixel_ptr_24;
    } else {
        pixel_ptr = pixel_ptr_16;
    }

    return pixel_ptr;
}

void * build_frame(int t, double angle, fb_config framebuffer, int wavelength, int speed, int waveform, 
                   double contrast, int background, int center_j, int center_i, int sigma, int square_size, int padding,
                   int colormode){

    angle = degrees_to_radians(angle);
    // Set frame-level flags...
    int grating_type;
    if (square_shape_size == 0 && sigma == 0){
        grating_type = FULLSCREEN;  // Fullscreen stimulus if no mask is applied
    } else if(sigma == 0){
        grating_type = SQUARE_SHAPE;  // Use square_shape mask
    } else {
        grating_type = GABOR;  // Gabor stimulus if sigma is set
    }
    
    double sine = sin(angle);
    double cosine = cos(angle);
    
    void* array_start = malloc(framebuffer.size);
    uint24_t *write_location_24, *read_location_24;
    uint16_t *write_location_16, *read_location_16;
    write_location_24 = write_location_16 = array_start;
    
    int i, j;
    for(i = 0; i < framebuffer.height; i++){ // For each row of pixels
        for(j = 0; j < framebuffer.width; j++){ // For each column of pixels
            // Check if pixel (i, j) is inside the square mask
            int left_boundary = center_j - (square_shape_size / 2) - padding;
            int right_boundary = center_j + (square_shape_size / 2) + padding;
            int top_boundary = center_i - (square_shape_size / 2) - padding;
            int bottom_boundary = center_i + (square_shape_size / 2) + padding;
            
            // Determine if the current point is inside the square_shape or outside
            double square_shape_weight = (j >= left_boundary && j <= right_boundary && i >= top_boundary && i <= bottom_boundary) 
                                   ? 1 : 0;  // Inside the square_shape mask
            
            double gauss_weight = gaussian(0, sigma);  // Not needed for square, but keep for other cases
            
            switch(grating_type | colormode | waveform){
                case(FULLSCREEN | SQUARE | RGB888MODE):
                    read_location_24 = squarewave(j, i, t, wavelength, speed, angle, cosine, sine, 1, contrast, background, colormode);
                    break;
                case(FULLSCREEN | SQUARE | RGB565MODE):
                    read_location_16 = squarewave(j, i, t, wavelength, speed, angle, cosine, sine, 1, contrast, background, colormode);
                    break;
                case(FULLSCREEN | SINE | RGB888MODE):
                    read_location_24 = sinewave(j, i, t, wavelength, speed, angle, cosine, sine, 1, contrast, background, colormode);
                    break;
                case(FULLSCREEN | SINE | RGB565MODE):
                    read_location_16 = sinewave(j, i, t, wavelength, speed, angle, cosine, sine, 1, contrast, background, colormode);
                    break;
                case(GABOR | SINE | RGB888MODE):
                    read_location_24 = gabor(j, i, t, wavelength, speed, angle, cosine, sine, gauss_weight, contrast, background, colormode);
                    break;
                case(GABOR | SINE | RGB565MODE):
                    read_location_16 = gabor(j, i, t, wavelength, speed, angle, cosine, sine, gauss_weight, contrast, background, colormode);
                    break;
                case(SQUARE_SHAPE | SQUARE | RGB888MODE):
                case(SQUARE_SHAPE | SINE | RGB888MODE):
                    read_location_24 = square_shape(
                        waveform, square_shape_size, padding, j, i, center_j, center_i, t, wavelength, speed, 
                        angle, cosine, sine, square_shape_weight, contrast, background, colormode);
                    break;
                case(SQUARE_SHAPE | SQUARE | RGB565MODE):
                case(SQUARE_SHAPE | SINE | RGB565MODE):
                    read_location_16 = square_shape(
                        waveform, square_shape_size, padding, j, i, center_j, center_i, t, wavelength, speed, 
                        angle, cosine, sine, square_shape_weight, contrast, background, colormode);
                    break;
                default:
                    printf("ERROR: Invalid tags encountered in build_frame function.\n");
                    return NULL;
            }
            
            if(colormode == RGB888MODE){
                *write_location_24 = *read_location_24;
                free(read_location_24);
            } else {
                *write_location_16 = *read_location_16;
                free(read_location_16);
            }
            write_location_24++;
            write_location_16++;
        }
    }
    
    // Return a pointer to the generated pixel data
    return (void *)array_start;
}

int build_grating(char * filename, double duration, double angle, double sf, double tf, double contrast, int background, int width, int height, int waveform, 
                  double percent_sigma, double percent_side_length, double percent_center_left, double percent_center_top, double percent_padding, int colormode){ 

    int fps = get_refresh_rate();
    printf("Refresh rate measured as: %d hz\n", fps);
    
    fb_config fb0;
    fb0.width = width;
    fb0.height = height;
    fb0.depth = (colormode == RGB888MODE)?24:16;
    fb0.size = (fb0.height) * (fb0.depth) * (fb0.width) / 8; // 8 bits/byte

    FILE * file = fopen(filename, "wb");
    if(file == NULL){
        perror("File creation failed\n");
        PyErr_SetString(PyExc_OSError, "File creation failed.");
        return 1;
    }

    int wavelength = (fb0.width / DEGREES_SUBTENDED) / sf;
    int speed = wavelength * tf / fps;
    if(speed == 0){
        speed = 1;
    }

    double actual_tf = ((double)(speed * fps)) / wavelength;

    int side_length = fb0.width * percent_side_length / 100; 
    int center_j = fb0.width * percent_center_left / 100;
    int center_i = fb0.height * percent_center_top / 100;
    double padding = side_length * percent_padding / 100;
    if(actual_tf != tf){
        printf("Grating %s has a requested temporal frequency of %f, actual temporal frequency will be %f\n", filename, tf, actual_tf);
    }

    int frame_count = (int)(duration * fps);
    for(int t = 0; t < frame_count; t++)
{
        void * frame = build_frame(t, angle, fb0, wavelength, speed, waveform, contrast, background, 
                                   center_j, center_i, 0, side_length, padding, colormode);
        
        fwrite(frame, 1, fb0.size, file);
        free(frame); // Free allocated memory for each frame
    }

    fclose(file);
    return 0;
}

options_nogo = {"angle": 90, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3,  "contrast": 0, "colormode": 0, "percent_side_length": 50, "percent_center_left": 50, "percent_center_top": 50, "background": 255}
rpg.build_square_shape_grating("~/first_grating_nogo_smask.dat", options_nogo)


with rpg.Screen() as myscreen:
    grating_go = myscreen.load_grating("~/first_grating_go_smask.dat")
    myscreen.display_grating(grating_go)
  
    grating_nogo = myscreen.load_grating("~/first_grating_nogo_smask.dat")
    myscreen.display_grating(grating_nogo)
