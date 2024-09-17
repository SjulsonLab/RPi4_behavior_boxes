#Piece of code removed from bill-connelly and modified to build a square maksk

import rpg

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
