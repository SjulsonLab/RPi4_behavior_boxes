#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <math.h>
#include <pthread.h>
#include <pigpio.h>
#include <stdbool.h>

// Type definitions
typedef enum {
    IRIG_ZERO = 0,
    IRIG_ONE = 1,
    IRIG_P = 2
} irig_bit_t;

typedef struct {
    double *data;
    size_t length;
    size_t capacity;
} double_array_t;

typedef struct {
    int *data;
    size_t length;
    size_t capacity;
} int_array_t;

typedef struct {
    irig_bit_t *data;
    size_t length;
    size_t capacity;
} irig_array_t;

typedef struct {
    bool *data;
    size_t length;
    size_t capacity;
} bool_array_t;

typedef struct {
    double sent_time;
    double measured_time;
} time_pair_t;

typedef struct {
    bool_array_t binary_data;
    double timestamp;
} binary_splice_t;

// Constants
#define SENDING_BIT_LENGTH 1.0
#define MEASURED_DELAY 0.0
#define SENDING_HEAD_START 0.01
#define DECODE_BIT_PERIOD (1.0 / 25000.0)
#define P_THRESHOLD (0.75 * SENDING_BIT_LENGTH)
#define ONE_THRESHOLD (0.45 * SENDING_BIT_LENGTH)
#define ZERO_THRESHOLD (0.05 * SENDING_BIT_LENGTH)

// Weight arrays
static const int SECONDS_WEIGHTS[] = {1, 2, 4, 8, 10, 20, 40};
static const int MINUTES_WEIGHTS[] = {1, 2, 4, 8, 10, 20, 40};
static const int HOURS_WEIGHTS[] = {1, 2, 4, 8, 10, 20};
static const int DAY_OF_YEAR_WEIGHTS[] = {1, 2, 4, 8, 10, 20, 40, 80, 100, 200};
static const int DECISECONDS_WEIGHTS[] = {1, 2, 4, 8};
static const int YEARS_WEIGHTS[] = {1, 2, 4, 8, 10, 20, 40, 80};

// IRIG-H Sender structure
typedef struct {
    int sending_gpio_pin;
    double sending_loop_period;
    pthread_t sender_thread;
    bool running;
    double_array_t encoded_times;
    double_array_t sending_starts;
    char timestamp_filename[256];
} irig_h_sender_t;

// Dynamic array functions
double_array_t* create_double_array(size_t initial_capacity) {
    double_array_t *arr = malloc(sizeof(double_array_t));
    arr->data = malloc(sizeof(double) * initial_capacity);
    arr->length = 0;
    arr->capacity = initial_capacity;
    return arr;
}

void append_double(double_array_t *arr, double value) {
    if (arr->length >= arr->capacity) {
        arr->capacity *= 2;
        arr->data = realloc(arr->data, sizeof(double) * arr->capacity);
    }
    arr->data[arr->length++] = value;
}

int_array_t* create_int_array(size_t initial_capacity) {
    int_array_t *arr = malloc(sizeof(int_array_t));
    arr->data = malloc(sizeof(int) * initial_capacity);
    arr->length = 0;
    arr->capacity = initial_capacity;
    return arr;
}

void append_int(int_array_t *arr, int value) {
    if (arr->length >= arr->capacity) {
        arr->capacity *= 2;
        arr->data = realloc(arr->data, sizeof(int) * arr->capacity);
    }
    arr->data[arr->length++] = value;
}

irig_array_t* create_irig_array(size_t initial_capacity) {
    irig_array_t *arr = malloc(sizeof(irig_array_t));
    arr->data = malloc(sizeof(irig_bit_t) * initial_capacity);
    arr->length = 0;
    arr->capacity = initial_capacity;
    return arr;
}

void append_irig_bit(irig_array_t *arr, irig_bit_t value) {
    if (arr->length >= arr->capacity) {
        arr->capacity *= 2;
        arr->data = realloc(arr->data, sizeof(irig_bit_t) * arr->capacity);
    }
    arr->data[arr->length++] = value;
}

void free_double_array(double_array_t *arr) {
    if (arr) {
        free(arr->data);
        free(arr);
    }
}

void free_int_array(int_array_t *arr) {
    if (arr) {
        free(arr->data);
        free(arr);
    }
}

void free_irig_array(irig_array_t *arr) {
    if (arr) {
        free(arr->data);
        free(arr);
    }
}

// BCD Utilities
void bcd_encode(int value, const int *weights, int weight_count, int *result) {
    memset(result, 0, weight_count * sizeof(int));
    for (int i = weight_count - 1; i >= 0; i--) {
        if (weights[i] <= value) {
            result[i] = 1;
            value -= weights[i];
        }
    }
}

int bcd_decode(const int *binary, const int *weights, int length) {
    int total = 0;
    for (int i = 0; i < length; i++) {
        total += binary[i] * weights[i];
    }
    return total;
}

// IRIG Decoding Functions
double_array_t* find_pulse_length(const bool *binary_list, size_t length) {
    if (length < 2) {
        printf("Inputted data set is too short.\n");
        return NULL;
    }
    
    double_array_t *pulse_lengths = create_double_array(100);
    double current_length = 0;
    
    for (size_t i = 0; i < length; i++) {
        if (binary_list[i]) {
            current_length += DECODE_BIT_PERIOD;
        } else if (current_length == 0) {
            continue;
        } else {
            append_double(pulse_lengths, current_length);
            current_length = 0;
        }
    }
    
    if (current_length != 0) {
        append_double(pulse_lengths, current_length);
    }
    
    return pulse_lengths;
}

irig_bit_t identify_pulse_length(double length) {
    if (length > P_THRESHOLD) {
        return IRIG_P;
    } else if (length > ONE_THRESHOLD) {
        return IRIG_ONE;
    } else if (length > ZERO_THRESHOLD) {
        return IRIG_ZERO;
    } else {
        return -1; // Invalid
    }
}

irig_array_t* decode_to_irig_h(const bool *binary_list, size_t length) {
    if (length < 2) {
        printf("Inputted data set is too short.\n");
        return NULL;
    }
    
    double_array_t *pulse_lengths = find_pulse_length(binary_list, length);
    if (!pulse_lengths) return NULL;
    
    irig_array_t *irig_bits = create_irig_array(pulse_lengths->length);
    
    for (size_t i = 0; i < pulse_lengths->length; i++) {
        irig_bit_t bit = identify_pulse_length(pulse_lengths->data[i]);
        if (bit != -1) {
            append_irig_bit(irig_bits, bit);
        }
    }
    
    free_double_array(pulse_lengths);
    return irig_bits;
}

struct tm irig_h_to_datetime(const irig_bit_t *irig_list, size_t length) {
    struct tm result = {0};
    
    if (length != 60) {
        printf("Length of irig timecode is not 60.\n");
        return result;
    }
    
    // Convert irig_bit_t to int for BCD decode
    int binary_temp[10];
    
    // Seconds
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[1 + i] == IRIG_ONE) ? 1 : 0;
    int seconds_units = bcd_decode(binary_temp, SECONDS_WEIGHTS, 4);
    
    for (int i = 0; i < 3; i++) binary_temp[i] = (irig_list[6 + i] == IRIG_ONE) ? 1 : 0;
    int seconds_tens = bcd_decode(binary_temp, &SECONDS_WEIGHTS[4], 3);
    
    result.tm_sec = seconds_units + seconds_tens;
    
    // Minutes
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[10 + i] == IRIG_ONE) ? 1 : 0;
    int minutes_units = bcd_decode(binary_temp, MINUTES_WEIGHTS, 4);
    
    for (int i = 0; i < 3; i++) binary_temp[i] = (irig_list[15 + i] == IRIG_ONE) ? 1 : 0;
    int minutes_tens = bcd_decode(binary_temp, &MINUTES_WEIGHTS[4], 3);
    
    result.tm_min = minutes_units + minutes_tens;
    
    // Hours
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[20 + i] == IRIG_ONE) ? 1 : 0;
    int hours_units = bcd_decode(binary_temp, HOURS_WEIGHTS, 4);
    
    for (int i = 0; i < 2; i++) binary_temp[i] = (irig_list[25 + i] == IRIG_ONE) ? 1 : 0;
    int hours_tens = bcd_decode(binary_temp, &HOURS_WEIGHTS[4], 2);
    
    result.tm_hour = hours_units + hours_tens;
    
    // Day of year
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[30 + i] == IRIG_ONE) ? 1 : 0;
    int day_units = bcd_decode(binary_temp, DAY_OF_YEAR_WEIGHTS, 4);
    
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[35 + i] == IRIG_ONE) ? 1 : 0;
    int day_tens = bcd_decode(binary_temp, &DAY_OF_YEAR_WEIGHTS[4], 4);
    
    for (int i = 0; i < 2; i++) binary_temp[i] = (irig_list[40 + i] == IRIG_ONE) ? 1 : 0;
    int day_hundreds = bcd_decode(binary_temp, &DAY_OF_YEAR_WEIGHTS[8], 2);
    
    result.tm_yday = day_units + day_tens + day_hundreds;
    
    // Year
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[50 + i] == IRIG_ONE) ? 1 : 0;
    int year_units = bcd_decode(binary_temp, YEARS_WEIGHTS, 4);
    
    for (int i = 0; i < 4; i++) binary_temp[i] = (irig_list[55 + i] == IRIG_ONE) ? 1 : 0;
    int year_tens = bcd_decode(binary_temp, &YEARS_WEIGHTS[4], 4);
    
    time_t now = time(NULL);
    struct tm *current_time = localtime(&now);
    int century = (current_time->tm_year + 1900) / 100 * 100;
    
    result.tm_year = (century + year_units + year_tens) - 1900;
    
    // Convert day of year to month and day
    struct tm temp = result;
    temp.tm_mon = 0;
    temp.tm_mday = result.tm_yday;
    mktime(&temp);
    result.tm_mon = temp.tm_mon;
    result.tm_mday = temp.tm_mday;
    
    return result;
}

double irig_h_to_posix(const irig_bit_t *irig_list, size_t length) {
    struct tm dt = irig_h_to_datetime(irig_list, length);
    return (double)mktime(&dt);
}

int_array_t* find_timecode_starts(const bool *binary_list, size_t length) {
    if (length < 2) {
        printf("Inputted data set is too short.\n");
        return NULL;
    }
    
    int_array_t *starts = create_int_array(100);
    int flips = binary_list[0] ? 1 : 0;
    
    if (binary_list[0]) {
        append_int(starts, 0);
    }
    
    for (size_t i = 1; i < length; i++) {
        if (binary_list[i] != binary_list[i-1]) {
            flips++;
            if ((flips - 1) % 120 == 0) {
                append_int(starts, i);
            }
        }
    }
    
    return starts;
}

// IRIG-H Sender Implementation
void generate_irig_h_frame(irig_h_sender_t *sender, struct tm *time_info, irig_bit_t *frame) {
    // Add encoded time
    append_double(&sender->encoded_times, (double)mktime(time_info));
    
    // BCD encoding
    int seconds_bcd[7], minutes_bcd[7], hours_bcd[6];
    int day_of_year_bcd[10], deciseconds_bcd[4], year_bcd[8];
    
    bcd_encode(time_info->tm_sec + 1, SECONDS_WEIGHTS, 7, seconds_bcd);
    bcd_encode(time_info->tm_min, MINUTES_WEIGHTS, 7, minutes_bcd);
    bcd_encode(time_info->tm_hour, HOURS_WEIGHTS, 6, hours_bcd);
    bcd_encode(time_info->tm_yday, DAY_OF_YEAR_WEIGHTS, 10, day_of_year_bcd);
    bcd_encode(0, DECISECONDS_WEIGHTS, 4, deciseconds_bcd);
    bcd_encode((time_info->tm_year + 1900) % 100, YEARS_WEIGHTS, 8, year_bcd);
    
    // Build IRIG-H frame
    int pos = 0;
    
    // Bit 00: Pr (Frame marker)
    frame[pos++] = IRIG_P;
    
    // Bits 01-04: Seconds (Units)
    for (int i = 0; i < 4; i++) frame[pos++] = seconds_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 05: Unused
    frame[pos++] = IRIG_ZERO;
    
    // Bits 06-08: Seconds (Tens)
    for (int i = 4; i < 7; i++) frame[pos++] = seconds_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 09: P1
    frame[pos++] = IRIG_P;
    
    // Bits 10-13: Minutes (Units)
    for (int i = 0; i < 4; i++) frame[pos++] = minutes_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 14: Unused
    frame[pos++] = IRIG_ZERO;
    
    // Bits 15-17: Minutes (Tens)
    for (int i = 4; i < 7; i++) frame[pos++] = minutes_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 18: Unused
    frame[pos++] = IRIG_ZERO;
    
    // Bit 19: P2
    frame[pos++] = IRIG_P;
    
    // Bits 20-23: Hours (Units)
    for (int i = 0; i < 4; i++) frame[pos++] = hours_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 24: Unused
    frame[pos++] = IRIG_ZERO;
    
    // Bits 25-26: Hours (Tens)
    for (int i = 4; i < 6; i++) frame[pos++] = hours_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bits 27-28: Unused
    frame[pos++] = IRIG_ZERO;
    frame[pos++] = IRIG_ZERO;
    
    // Bit 29: P3
    frame[pos++] = IRIG_P;
    
    // Bits 30-33: Day of year (Units)
    for (int i = 0; i < 4; i++) frame[pos++] = day_of_year_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 34: Unused
    frame[pos++] = IRIG_ZERO;
    
    // Bits 35-38: Day of year (Tens)
    for (int i = 4; i < 8; i++) frame[pos++] = day_of_year_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 39: P4
    frame[pos++] = IRIG_P;
    
    // Bits 40-41: Day of year (Hundreds)
    for (int i = 8; i < 10; i++) frame[pos++] = day_of_year_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bits 42-44: Unused
    frame[pos++] = IRIG_ZERO;
    frame[pos++] = IRIG_ZERO;
    frame[pos++] = IRIG_ZERO;
    
    // Bits 45-48: Deciseconds
    for (int i = 0; i < 4; i++) frame[pos++] = deciseconds_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 49: P5
    frame[pos++] = IRIG_P;
    
    // Bits 50-53: Years (Units)
    for (int i = 0; i < 4; i++) frame[pos++] = year_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 54: Unused
    frame[pos++] = IRIG_ZERO;
    
    // Bits 55-58: Years (Tens)
    for (int i = 4; i < 8; i++) frame[pos++] = year_bcd[i] ? IRIG_ONE : IRIG_ZERO;
    
    // Bit 59: P6
    frame[pos++] = IRIG_P;
}

void precise_wait_until(double wake_time, double loop_period) {
    struct timespec ts;
    double now = time(NULL);
    
    if (wake_time - now > SENDING_HEAD_START) {
        ts.tv_sec = (time_t)(wake_time - now - SENDING_HEAD_START);
        ts.tv_nsec = ((wake_time - now - SENDING_HEAD_START) - ts.tv_sec) * 1000000000;
        nanosleep(&ts, NULL);
    }
    
    while (time(NULL) < wake_time) {
        ts.tv_sec = 0;
        ts.tv_nsec = loop_period * 1000000000;
        nanosleep(&ts, NULL);
    }
}

double calculate_pulse_length(irig_bit_t bit) {
    switch (bit) {
        case IRIG_P:
            return 0.8 * SENDING_BIT_LENGTH;
        case IRIG_ONE:
            return 0.5 * SENDING_BIT_LENGTH;
        case IRIG_ZERO:
        default:
            return 0.2 * SENDING_BIT_LENGTH;
    }
}

void flip_for_time(irig_h_sender_t *sender, double pulse_time) {
    printf("Flipping for %f seconds at %f\n", pulse_time, time(NULL));
    gpioWrite(sender->sending_gpio_pin, 1);
    
    struct timespec ts;
    ts.tv_sec = (time_t)pulse_time;
    ts.tv_nsec = (pulse_time - ts.tv_sec) * 1000000000;
    nanosleep(&ts, NULL);
    
    gpioWrite(sender->sending_gpio_pin, 0);
}

void* continuous_irig_sending(void *arg) {
    irig_h_sender_t *sender = (irig_h_sender_t*)arg;
    irig_bit_t frame[60];
    
    while (sender->running) {
        time_t now = time(NULL);
        struct tm *time_info = localtime(&now);
        
        double start_time = ceil((double)now);
        append_double(&sender->sending_starts, start_time);
        
        generate_irig_h_frame(sender, time_info, frame);
        
        for (int i = 0; i < 60; i++) {
            double pulse_time = calculate_pulse_length(frame[i]);
            
            precise_wait_until(start_time - MEASURED_DELAY, sender->sending_loop_period);
            printf("start time: %f\n", start_time);
            flip_for_time(sender, pulse_time);
            
            start_time += SENDING_BIT_LENGTH;
        }
    }
    
    return NULL;
}

irig_h_sender_t* create_irig_h_sender(int gpio_pin, double loop_period) {
    irig_h_sender_t *sender = malloc(sizeof(irig_h_sender_t));
    
    sender->sending_gpio_pin = gpio_pin;
    sender->sending_loop_period = loop_period;
    sender->running = false;
    
    // Initialize dynamic arrays
    sender->encoded_times.data = malloc(sizeof(double) * 100);
    sender->encoded_times.length = 0;
    sender->encoded_times.capacity = 100;
    
    sender->sending_starts.data = malloc(sizeof(double) * 100);
    sender->sending_starts.length = 0;
    sender->sending_starts.capacity = 100;
    
    // Generate filename
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    strftime(sender->timestamp_filename, sizeof(sender->timestamp_filename), 
             "irig_output_timestamps_%Y-%m-%d_%H-%M-%S.csv", tm_info);
    
    // Initialize pigpio
    if (gpioInitialise() < 0) {
        printf("Could not initialize pigpio\n");
        free(sender);
        return NULL;
    }
    
    gpioSetMode(sender->sending_gpio_pin, PI_OUTPUT);
    
    return sender;
}

void start_irig_sender(irig_h_sender_t *sender) {
    sender->running = true;
    pthread_create(&sender->sender_thread, NULL, continuous_irig_sending, sender);
}

void write_timestamps_to_file(irig_h_sender_t *sender) {
    FILE *file = fopen(sender->timestamp_filename, "w");
    if (!file) {
        printf("Could not open file for writing\n");
        return;
    }
    
    fprintf(file, "Encoded times,Sending starts\n");
    size_t min_length = (sender->encoded_times.length < sender->sending_starts.length) 
                       ? sender->encoded_times.length : sender->sending_starts.length;
    
    for (size_t i = 0; i < min_length; i++) {
        fprintf(file, "%f,%f\n", sender->encoded_times.data[i], sender->sending_starts.data[i]);
    }
    
    fclose(file);
}

void finish_irig_sender(irig_h_sender_t *sender) {
    sender->running = false;
    pthread_join(sender->sender_thread, NULL);
    
    write_timestamps_to_file(sender);
    gpioWrite(sender->sending_gpio_pin, 0);
    gpioTerminate();
    
    free(sender->encoded_times.data);
    free(sender->sending_starts.data);
    free(sender);
}

// Example usage
int main() {
    irig_h_sender_t *sender = create_irig_h_sender(6, 1.0/5000.0);
    if (!sender) {
        return 1;
    }
    
    start_irig_sender(sender);
    
    // Run for some time...
    sleep(10);
    
    finish_irig_sender(sender);
    
    return 0;
}