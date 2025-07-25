// Define feature test macros before any includes
#define _POSIX_C_SOURCE 199309L
#define _GNU_SOURCE
#define _DEFAULT_SOURCE
#define _DARWIN_C_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <math.h>
#include <pthread.h>
#include <stdbool.h>
#include <signal.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <errno.h>
#include <stdint.h>

// BCM2835/BCM2711 GPIO register definitions
#define BCM2708_PERI_BASE_RPI1  0x20000000
#define BCM2708_PERI_BASE_RPI2  0x3F000000
#define BCM2708_PERI_BASE_RPI4  0xFE000000
#define GPIO_BASE_OFFSET        0x200000

#define BLOCK_SIZE (4*1024)

// GPIO register offsets
#define GPFSEL0   0x00  // GPIO Function Select 0
#define GPFSEL1   0x04  // GPIO Function Select 1
#define GPFSEL2   0x08  // GPIO Function Select 2
#define GPSET0    0x1C  // GPIO Pin Output Set 0
#define GPCLR0    0x28  // GPIO Pin Output Clear 0
#define GPLEV0    0x34  // GPIO Pin Level 0

// GPIO access macros
static volatile unsigned *gpio_map = NULL;
static int gpio_mem_fd = -1;

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

// Constants
#define SENDING_BIT_LENGTH 1.0
#define MEASURED_DELAY 0.0
// Threshold for switching from sleep to busy wait (in nanoseconds)
#define BUSY_WAIT_THRESHOLD_NS 1000000L  // 1 millisecond

// Pre-calculated constants to avoid runtime computation
static const uint64_t NS_PER_SEC = 1000000000ULL;
static uint64_t bit_length_ns;
static uint64_t measured_delay_ns;
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
    pthread_t sender_thread;
    bool running;
    double_array_t encoded_times;
    double_array_t sending_starts;
    char timestamp_filename[256];
    
    // Pre-calculated optimization data
    irig_bit_t current_frame[60];
    irig_bit_t next_frame[60];
    double pulse_lengths[60];
    uint64_t bit_start_times[60];
    struct timespec frame_start_time;
    volatile unsigned *gpio_set_reg;
    volatile unsigned *gpio_clr_reg;
    uint32_t gpio_mask;
} irig_h_sender_t;

// Function declarations
void init_timing_constants(void);
uint64_t timespec_to_ns(const struct timespec *ts);
void ultra_wait_until_ns(uint64_t target_ns);

// Signal handler for clean shutdown
volatile sig_atomic_t running = 1;

void signal_handler(int sig) {
    printf("Received signal %d, shutting down gracefully...\n", sig);
    running = 0;
}

// GPIO Hardware Access Functions
int detect_pi_model() {
    FILE *fp = fopen("/proc/device-tree/model", "r");
    if (!fp) return 2; // Default to Pi 2/3
    
    char model[256];
    if (fgets(model, sizeof(model), fp)) {
        fclose(fp);
        if (strstr(model, "Raspberry Pi 4") || strstr(model, "Raspberry Pi 400")) {
            return 4;
        } else if (strstr(model, "Raspberry Pi 2") || strstr(model, "Raspberry Pi 3")) {
            return 2;
        } else {
            return 1;
        }
    }
    fclose(fp);
    return 2; // Default
}

int gpio_init() {
    int pi_model = detect_pi_model();
    unsigned gpio_base;
    
    switch (pi_model) {
        case 1:
            gpio_base = BCM2708_PERI_BASE_RPI1 + GPIO_BASE_OFFSET;
            break;
        case 4:
            gpio_base = BCM2708_PERI_BASE_RPI4 + GPIO_BASE_OFFSET;
            break;
        default:
            gpio_base = BCM2708_PERI_BASE_RPI2 + GPIO_BASE_OFFSET;
            break;
    }
    
    printf("Detected Raspberry Pi model %d, using GPIO base 0x%08X\n", pi_model, gpio_base);
    
    // Open /dev/mem
    gpio_mem_fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (gpio_mem_fd < 0) {
        printf("Error: Cannot open /dev/mem. Are you running as root?\n");
        return -1;
    }
    
    // Map GPIO registers
    gpio_map = (volatile unsigned *)mmap(
        NULL,                    // Any address in our space will do
        BLOCK_SIZE,              // Map length
        PROT_READ | PROT_WRITE,  // Enable reading & writing
        MAP_SHARED,              // Shared with other processes
        gpio_mem_fd,             // File to map
        gpio_base                // Offset to GPIO registers
    );
    
    if (gpio_map == MAP_FAILED) {
        printf("Error: mmap failed: %s\n", strerror(errno));
        close(gpio_mem_fd);
        return -1;
    }
    
    printf("GPIO memory mapped successfully\n");
    return 0;
}

void gpio_cleanup() {
    if (gpio_map != NULL && gpio_map != MAP_FAILED) {
        munmap((void*)gpio_map, BLOCK_SIZE);
        gpio_map = NULL;
    }
    if (gpio_mem_fd >= 0) {
        close(gpio_mem_fd);
        gpio_mem_fd = -1;
    }
}

void gpio_set_output(int pin) {
    if (gpio_map == NULL) return;
    
    int reg = pin / 10;
    int shift = (pin % 10) * 3;
    
    // Clear the bits first
    *(gpio_map + reg) &= ~(7 << shift);
    // Set as output (001)
    *(gpio_map + reg) |= (1 << shift);
    
    printf("GPIO %d set as output\n", pin);
}

void gpio_write(int pin, int value) {
    if (gpio_map == NULL) return;
    
    if (value) {
        // Set pin high
        *(gpio_map + GPSET0/4) = 1 << pin;
    } else {
        // Set pin low
        *(gpio_map + GPCLR0/4) = 1 << pin;
    }
}

// Initialize cached GPIO register pointers for ultra-fast access
void init_gpio_cache(irig_h_sender_t *sender) {
    if (gpio_map == NULL) return;
    
    // Cache direct register pointers
    sender->gpio_set_reg = gpio_map + GPSET0/4;
    sender->gpio_clr_reg = gpio_map + GPCLR0/4;
    sender->gpio_mask = 1 << sender->sending_gpio_pin;
}

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

void free_double_array(double_array_t *arr) {
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

void generate_irig_h_frame(irig_h_sender_t *sender, struct tm *time_info, irig_bit_t *frame) {
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
    
    // Build IRIG-H frame (60 bits total)
    int pos = 0;
    frame[pos++] = IRIG_P; // Bit 00: Frame marker
    
    for (int i = 0; i < 4; i++) frame[pos++] = seconds_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 01-04
    frame[pos++] = IRIG_ZERO; // 05: Unused
    for (int i = 4; i < 7; i++) frame[pos++] = seconds_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 06-08
    frame[pos++] = IRIG_P; // 09: P1
    
    for (int i = 0; i < 4; i++) frame[pos++] = minutes_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 10-13
    frame[pos++] = IRIG_ZERO; // 14: Unused
    for (int i = 4; i < 7; i++) frame[pos++] = minutes_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 15-17
    frame[pos++] = IRIG_ZERO; // 18: Unused
    frame[pos++] = IRIG_P; // 19: P2
    
    for (int i = 0; i < 4; i++) frame[pos++] = hours_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 20-23
    frame[pos++] = IRIG_ZERO; // 24: Unused
    for (int i = 4; i < 6; i++) frame[pos++] = hours_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 25-26
    frame[pos++] = IRIG_ZERO; frame[pos++] = IRIG_ZERO; // 27-28: Unused
    frame[pos++] = IRIG_P; // 29: P3
    
    for (int i = 0; i < 4; i++) frame[pos++] = day_of_year_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 30-33
    frame[pos++] = IRIG_ZERO; // 34: Unused
    for (int i = 4; i < 8; i++) frame[pos++] = day_of_year_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 35-38
    frame[pos++] = IRIG_P; // 39: P4
    for (int i = 8; i < 10; i++) frame[pos++] = day_of_year_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 40-41
    
    frame[pos++] = IRIG_ZERO; frame[pos++] = IRIG_ZERO; frame[pos++] = IRIG_ZERO; // 42-44: Unused
    for (int i = 0; i < 4; i++) frame[pos++] = deciseconds_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 45-48
    frame[pos++] = IRIG_P; // 49: P5
    
    for (int i = 0; i < 4; i++) frame[pos++] = year_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 50-53
    frame[pos++] = IRIG_ZERO; // 54: Unused
    for (int i = 4; i < 8; i++) frame[pos++] = year_bcd[i] ? IRIG_ONE : IRIG_ZERO; // 55-58
    frame[pos++] = IRIG_P; // 59: P6
}

// Eliminated - no longer needed due to pre-calculated timing

// Initialize timing constants
void init_timing_constants(void) {
    bit_length_ns = (uint64_t)(SENDING_BIT_LENGTH * NS_PER_SEC);
    measured_delay_ns = (uint64_t)(MEASURED_DELAY * NS_PER_SEC);
}

// Convert timespec to nanoseconds
uint64_t timespec_to_ns(const struct timespec *ts) {
    return (uint64_t)ts->tv_sec * NS_PER_SEC + (uint64_t)ts->tv_nsec;
}

// Ultra-precise wait until specific nanosecond timestamp - optimized for sub-100ns
void ultra_wait_until_ns(uint64_t target_ns) {
    struct timespec current_time;
    uint64_t current_ns;
    int64_t remaining_ns;
    
    // Tight loop - no nanosleep, pure busy wait for maximum precision
    do {
        clock_gettime(CLOCK_REALTIME, &current_time);
        current_ns = timespec_to_ns(&current_time);
        remaining_ns = (int64_t)(target_ns - current_ns);
        
        // Break immediately when target reached
        if (remaining_ns <= 0) break;
        
    } while (running);
}

double calculate_pulse_length(irig_bit_t bit) {
    switch (bit) {
        case IRIG_P: return 0.8 * SENDING_BIT_LENGTH;
        case IRIG_ONE: return 0.5 * SENDING_BIT_LENGTH;
        case IRIG_ZERO:
        default: return 0.2 * SENDING_BIT_LENGTH;
    }
}

// Ultra-fast GPIO pulse with pre-calculated timing
void ultra_fast_pulse(irig_h_sender_t *sender, uint64_t pulse_duration_ns) {
    struct timespec start_time, current_time;
    uint64_t start_ns, target_ns;
    
    // Single clock_gettime call at start
    clock_gettime(CLOCK_REALTIME, &start_time);
    start_ns = timespec_to_ns(&start_time);
    target_ns = start_ns + pulse_duration_ns;
    
    // Direct register write - fastest possible
    *(sender->gpio_set_reg) = sender->gpio_mask;
    
    // Tight busy loop for precise timing
    do {
        clock_gettime(CLOCK_REALTIME, &current_time);
    } while (timespec_to_ns(&current_time) < target_ns && running);
    
    // Direct register write to clear
    *(sender->gpio_clr_reg) = sender->gpio_mask;
}

// Pre-calculate next frame during 200ms window
void precalculate_next_frame(irig_h_sender_t *sender, time_t target_second) {
    struct tm *time_info = localtime(&target_second);
    generate_irig_h_frame(sender, time_info, sender->next_frame);
    
    // Pre-calculate pulse lengths and timing
    uint64_t frame_start_ns = (uint64_t)target_second * NS_PER_SEC;
    for (int i = 0; i < 60; i++) {
        sender->pulse_lengths[i] = calculate_pulse_length(sender->next_frame[i]);
        sender->bit_start_times[i] = frame_start_ns + (i * NS_PER_SEC);
    }
}

void* continuous_irig_sending(void *arg) {
    irig_h_sender_t *sender = (irig_h_sender_t*)arg;
    struct timespec current_time;
    time_t current_second, next_second;
    bool frame_ready = false;
    
    // Initialize timing constants once
    static int constants_initialized = 0;
    if (!constants_initialized) {
        init_timing_constants();
        constants_initialized = 1;
    }
    
    printf("IRIG-H continuous transmission thread started\n");
    
    // Get initial time and prepare first frame
    clock_gettime(CLOCK_REALTIME, &current_time);
    current_second = current_time.tv_sec;
    next_second = current_second + 1;
    precalculate_next_frame(sender, next_second);
    
    while (sender->running && running) {
        clock_gettime(CLOCK_REALTIME, &current_time);
        
        // Check if we're in the 200ms calculation window (800ms - 1000ms)
        long ns_into_second = current_time.tv_nsec;
        if (ns_into_second >= 800000000L && !frame_ready) {
            // Pre-calculate the frame for the NEXT second
            time_t upcoming_second = current_time.tv_sec + 1;
            precalculate_next_frame(sender, upcoming_second);
            frame_ready = true;
        }
        
        // At second boundary, start transmission immediately
        if (current_time.tv_sec > current_second) {
            current_second = current_time.tv_sec;
            
            // Copy pre-calculated frame to current
            memcpy(sender->current_frame, sender->next_frame, sizeof(sender->current_frame));
            
            // Record start time
            double start_time_double = (double)current_second + (double)current_time.tv_nsec * 1e-9;
            append_double(&sender->sending_starts, start_time_double);
            
            // Send all 60 bits with ultra-precise timing
            for (int i = 0; i < 60 && sender->running && running; i++) {
                // Pre-position just before bit transmission
                uint64_t bit_start_target = sender->bit_start_times[i];
                uint64_t preposition_target = bit_start_target - 50; // 50ns early
                
                // Wait until 50ns before bit start
                ultra_wait_until_ns(preposition_target);
                
                // Final precise wait to exact nanosecond
                struct timespec current;
                do {
                    clock_gettime(CLOCK_REALTIME, &current);
                } while (timespec_to_ns(&current) < bit_start_target && running);
                
                // Print system time when bit is sent
                printf("Bit %d sent at system time: %ld.%09ld\n", i, current.tv_sec, current.tv_nsec);
                
                // Send pulse with pre-calculated duration
                uint64_t pulse_ns = (uint64_t)(sender->pulse_lengths[i] * NS_PER_SEC);
                ultra_fast_pulse(sender, pulse_ns);
            }
            
            frame_ready = false;
        }
        
        // Short sleep to prevent excessive CPU usage
        usleep(1000); // 1ms
    }
    
    printf("IRIG-H transmission thread stopping\n");
    return NULL;
}

irig_h_sender_t* create_irig_h_sender(int gpio_pin) {
    irig_h_sender_t *sender = malloc(sizeof(irig_h_sender_t));
    
    sender->sending_gpio_pin = gpio_pin;
    sender->running = false;
    
    sender->encoded_times.data = malloc(sizeof(double) * 100);
    sender->encoded_times.length = 0;
    sender->encoded_times.capacity = 100;
    
    sender->sending_starts.data = malloc(sizeof(double) * 100);
    sender->sending_starts.length = 0;
    sender->sending_starts.capacity = 100;
    
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    strftime(sender->timestamp_filename, sizeof(sender->timestamp_filename), 
             "irig_output_timestamps_%Y-%m-%d_%H-%M-%S.csv", tm_info);
    
    // Initialize GPIO hardware access
    if (gpio_init() < 0) {
        printf("Failed to initialize GPIO hardware access\n");
        free(sender->encoded_times.data);
        free(sender->sending_starts.data);
        free(sender);
        return NULL;
    }
    
    // Set GPIO pin as output
    gpio_set_output(sender->sending_gpio_pin);
    
    // Initialize cached GPIO registers for ultra-fast access
    init_gpio_cache(sender);
    
    // Ensure pin starts low
    gpio_write(sender->sending_gpio_pin, 0);
    
    return sender;
}

void start_irig_sender(irig_h_sender_t *sender) {
    sender->running = true;
    pthread_create(&sender->sender_thread, NULL, continuous_irig_sending, sender);
}

void write_timestamps_to_file(irig_h_sender_t *sender) {
    FILE *file = fopen(sender->timestamp_filename, "w");
    if (!file) {
        printf("Could not open file for writing: %s\n", sender->timestamp_filename);
        return;
    }
    
    fprintf(file, "Encoded times,Sending starts\n");
    size_t min_length = (sender->encoded_times.length < sender->sending_starts.length) 
                       ? sender->encoded_times.length : sender->sending_starts.length;
    
    for (size_t i = 0; i < min_length; i++) {
        fprintf(file, "%f,%f\n", sender->encoded_times.data[i], sender->sending_starts.data[i]);
    }
    
    fclose(file);
    printf("Timestamps written to %s\n", sender->timestamp_filename);
}

void finish_irig_sender(irig_h_sender_t *sender) {
    sender->running = false;
    pthread_join(sender->sender_thread, NULL);
    
    // Commented to disable file writing
    // write_timestamps_to_file(sender);
    
    // Ensure GPIO is low
    gpio_write(sender->sending_gpio_pin, 0);
    
    // Cleanup GPIO
    gpio_cleanup();
    
    free(sender->encoded_times.data);
    free(sender->sending_starts.data);
    free(sender);
}


// Main function for continuous operation
int main() {
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);
    
    printf("IRIG-H Timecode Sender starting on GPIO 6...\n");
    printf("Using direct hardware register access\n");
    
    irig_h_sender_t *sender = create_irig_h_sender(6);
    if (!sender) {
        printf("Failed to initialize IRIG-H sender\n");
        return 1;
    }
    
    printf("IRIG-H sender initialized successfully\n");
    start_irig_sender(sender);
    printf("IRIG-H transmission started on GPIO 6\n");
    
    while (running) {
        sleep(1);
    }
    
    printf("Stopping IRIG-H sender...\n");
    finish_irig_sender(sender);
    printf("IRIG-H sender stopped\n");
    
    return 0;
}