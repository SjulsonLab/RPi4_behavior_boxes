#Piece of code removed from bill-connelly and modified to build a square maksk - IN PROCESS

import RPG

# Define the "Go" stimulus - white circle, black background
options_go = {"angle": 90, "spac_freq": 0.1, "temp_freq": 0.3, "duration": 3,  "contrast": 0, "percent_diameter": 50, "percent_center_left": 50, "percent_center_top": 50, "background": 0}
rpg.build_masked_grating("~/first_grating_go_round.dat", options_go)

# Define the "No Go" stimulus - black square, white background

void* square(int waveform, int square_size, int padding, int point_x, int point_y, int center_x, int center_y, int t, int wavelength, int speed, 
             double angle, double cosine, double sine, double weight, double contrast, int background, int colormode){
    void* pixel_ptr;
    uint16_t* pixel_ptr_16;
    uint24_t* pixel_ptr_24;
    int square_case;

    // Define boundaries for the square based on its size and padding
    int left_boundary = center_x - (square_size / 2) - padding;
    int right_boundary = center_x + (square_size / 2) + padding;
    int top_boundary = center_y - (square_size / 2) - padding;
    int bottom_boundary = center_y + (square_size / 2) + padding;

    // Check if the point falls inside or outside the square mask
    if (point_x < left_boundary || point_x > right_boundary || point_y < top_boundary || point_y > bottom_boundary) {
        // Outside the square mask
        square_case = OUTSIDEMASK;
    } else if (point_x >= left_boundary && point_x <= right_boundary && point_y >= top_boundary && point_y <= bottom_boundary) {
        // Inside the square mask
        square_case = INSIDEMASK;
        weight = 1;
    }

    // Switch cases based on square_case and color mode
    switch(square_case | colormode | waveform){
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
#CONTINUE HERE 

int build_grating(char * filename, double duration, double angle, double sf, double tf, double contrast, int background, int width, int height, int waveform, double 
	percent_sigma, double percent_diameter, double percent_center_left, double percent_center_top, double percent_padding, int colormode){ 

  #int left_boundary = center_x - (square_size / 2) - padding;
    int right_boundary = center_x + (square_size / 2) + padding;
    int top_boundary = center_y - (square_size / 2) - padding;
    int bottom_boundary = center_y + (square_size / 2) + padding;

	int fps = get_refresh_rate();
        printf("Refresh rate measured as: %d hz\n", fps);
	fb_config fb0;
	fb0.width = width;
	fb0.height = height;
	fb0.depth = (colormode==RGB888MODE)?24:16;
	fb0.size = (fb0.height)*(fb0.depth)*(fb0.width)/8; //8 bits/byte
	FILE * file = fopen(filename, "wb");
	if(file == NULL){
		perror("File creation failed\n");
		PyErr_SetString(PyExc_OSError,"File creation failed.");
		return 1;
	}
	int wavelength = (fb0.width/DEGREES_SUBTENDED)/sf;

	int speed = wavelength*tf/fps;
	if(speed==0){
		speed = 1;
	}
	double actual_tf = ((double)(speed*fps)) / wavelength;
	int sigma = fb0.width * percent_sigma / 100;
	int radius = fb0.width * percent_diameter / 200;
	int center_j = fb0.width * percent_center_left / 100;
	int center_i = fb0.height * percent_center_top / 100;
	double padding = radius * percent_padding / 100;
	if(actual_tf!=tf){
		printf("Grating %s has a requested temporal frequency of %f, actual temporal frequency will be %f\n",filename,tf,actual_tf);
	}
