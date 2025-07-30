from typing import List, Tuple, Literal
import pigpio
import time
from datetime import datetime as dt
import datetime
import pandas as pd
from threading import Thread
import math

IRIG_BIT = Literal[0,1,'P'] # type for IRIG-H bits
BINARY_BIT = Literal[0,1] # type for binary bits

SENDING_BIT_LENGTH = 1 # seconds

# Constants for timecode sending
MEASURED_DELAY = 0 # The constant delay between GPS PPS and the RPi PPS in seconds (positive means GPS is ahead)
SENDING_HEAD_START = 0.01 # seconds in advance to stop sleeping and start busy waiting

# Constants for timecode measuring
DECODE_BIT_PERIOD = 1 / 30_000 # for now frame rate is 25 kHz
# pulse length thresholds (in seconds). 
P_THRESHOLD = 0.75 * SENDING_BIT_LENGTH # for pulse length of 0.8b
ONE_THRESHOLD = 0.45 * SENDING_BIT_LENGTH # for pulse length of 0.5b
ZERO_THRESHOLD = 0.05 * SENDING_BIT_LENGTH # for pulse length of 0.2b. This is to make sure error isnt recorded

# Weights for the encoding values in an IRIG-H timecode
SECONDS_WEIGHTS = [1, 2, 4, 8, 10, 20, 40]
MINUTES_WEIGHTS = [1, 2, 4, 8, 10, 20, 40]
HOURS_WEIGHTS = [1, 2, 4, 8, 10, 20]
DAY_OF_YEAR_WEIGHTS = [1, 2, 4, 8, 10, 20, 40, 80, 100, 200]
DECISECONDS_WEIGHTS = [1, 2, 4, 8]
YEARS_WEIGHTS = [1, 2, 4, 8, 10, 20, 40, 80]

# ------------------------- BCD UTILITIES ------------------------- #
# These are used for encoding and decoding IRIG-H timecodes.

def bcd_encode(value: int, weights: List[int]) -> List[BINARY_BIT]:
    """
    Encodes an integer value into Binary Coded Decimal (BCD) format using specified weights.
    This method assumes that the value is representable as a sum of a subset of the weights.
    """

    bcd_list = [0] * len(weights)
    for i in reversed(range(len(weights))):
        if weights[i] <= value:
            bcd_list[i] = 1
            value -= weights[i]
    return bcd_list

def bcd_decode(binary: List[BINARY_BIT], weights: List[int]) -> int:
    """
    Decodes a Binary Coded Decimal (BCD) format using a dot product with the binary list and the weights.
    This method assumes that the value is representable as a sum of a subset of the weights.
    """

    total = 0
    for weight, bit in zip(weights, binary):
        total += bit * weight
    return total

# ------------------------- IRIG DECODING ------------------------- #

def find_pulse_length(binary_list: List[bool]) -> List[float]:
    """
    Decodes a sample of measured electrical signals into a list of pulse lengths (in seconds).
    """

    if len(binary_list) < 2:
        print("Inputted data set is too short.")
        return []
    
    pulse_length_list = []
    length = 0
    for i in binary_list:
        if i:
            length += DECODE_BIT_PERIOD
        elif length == 0:
            continue
        else:
            pulse_length_list.append(length)
            length = 0
    if length != 0:
        pulse_length_list.append(length)

    return pulse_length_list

def identify_pulse_length(length):
    if length > P_THRESHOLD:
        return 'P'
    if length > ONE_THRESHOLD:
        return 1
    if length > ZERO_THRESHOLD:
        return 0
    else: 
        return None

def decode_to_irig_h(binary_list: List[bool]) -> List[IRIG_BIT]:
    """
    Decodes a list of measured pulse lengths (in seconds) to a list-represented IRIG-H frame.
    """

    if len(binary_list) < 2:
        print("Inputted data set is too short.")
        return []

    return [bit for bit in [identify_pulse_length(length) for length in find_pulse_length(binary_list)] if bit != None]

def irig_h_to_datetime(irig_list: List[IRIG_BIT]) -> dt:
    """
    Converts a list-represented IRIG-H frame into a Python datetime.
    Since IRIG does not encode century, this code assumes that the IRIG timecode is being sent in the same century as when this function is called.
    """

    if len(irig_list) != 60:
        print("Length of irig timecode is not 60.")
        return dt.min
    seconds = bcd_decode(irig_list[1:5], SECONDS_WEIGHTS[0:4]) + bcd_decode(irig_list[6:9], SECONDS_WEIGHTS[4:7])
    minutes = bcd_decode(irig_list[10:14], MINUTES_WEIGHTS[0:4]) + bcd_decode(irig_list[15:18], MINUTES_WEIGHTS[4:7])
    hours = bcd_decode(irig_list[20:24], HOURS_WEIGHTS[0:4]) + bcd_decode(irig_list[25:27], HOURS_WEIGHTS[4:6])
    day_of_year = bcd_decode(irig_list[30:34], DAY_OF_YEAR_WEIGHTS[0:4]) + bcd_decode(irig_list[35:39], DAY_OF_YEAR_WEIGHTS[4:8]) + bcd_decode(irig_list[40:42], DAY_OF_YEAR_WEIGHTS[8:10])
    deciseconds = bcd_decode(irig_list[45:49], DECISECONDS_WEIGHTS)
    year = bcd_decode(irig_list[50:54], YEARS_WEIGHTS[0:4]) + bcd_decode(irig_list[55:59], YEARS_WEIGHTS[4:8]) + (dt.now().year // 100) * 100 # add in century
    return dt.combine(datetime.date(year, 1, 1) + datetime.timedelta(days=(day_of_year - 1)), datetime.time(hours, minutes, seconds, deciseconds * 100_000))

def irig_h_to_posix(irig_list: List[IRIG_BIT]) -> float:
    """
    Converts a list-represented IRIG-H frame into a POSIX timecode (Measured in seconds since 00:00:00 UTC, January 1st, 1970).
    Since IRIG does not encode century, this code assumes that the IRIG timecode is being sent in the same century as when this function is called.
    """
    return irig_h_to_datetime(irig_list).timestamp()

def find_timecode_starts(binary_list) -> List[int]:
    """
    Finds all the indexes in the measured list of booleans for where a timecode starts.
    Keep in mind that this assumes that there is NO noise. 
    If there is an incomplete timecode at the end, it will still return a start for that timecode.
    Works with both lists and generators.
    """
    
    binary_iter = iter(binary_list)
    try:
        first_bit = next(binary_iter)
    except StopIteration:
        return []
    
    starts = [0] if first_bit else [] # list of indexes for when the timecodes start
    flips = 1 if first_bit else 0     # if its already recieving timcodes at the start, change starting behavior
    
    prev_bit = first_bit
    i = 1
    
    for current_bit in binary_iter:
        if current_bit != prev_bit:
            flips += 1
            if (flips - 1) % 120 == 0:
                starts.append(i)
        prev_bit = current_bit
        i += 1
    return starts

def splice_binary_generator(binary_list):
    """
    Generator that yields segments of binary data that represent complete IRIG-H frames.
    Returns a generator of 2-tuples containing a timestamp (in seconds) and the segment as a list.
    Memory efficient for large datasets.
    """
    
    binary_iter = iter(binary_list)
    try:
        first_bit = next(binary_iter)
    except StopIteration:
        return
    
    # Track state for finding timecode starts
    flips = 1 if first_bit else 0
    prev_bit = first_bit
    current_segment = [first_bit]
    segment_start_index = 0
    current_index = 1
    
    for current_bit in binary_iter:
        current_segment.append(current_bit)
        
        if current_bit != prev_bit:
            flips += 1
            # Check if this marks a new timecode start (every 120 flips)
            if (flips - 1) % 120 == 0 and len(current_segment) > 1:
                # Yield the completed segment (excluding the current bit which starts the next segment)
                yield (current_segment[:-1], segment_start_index * DECODE_BIT_PERIOD)
                # Start new segment with the current bit
                current_segment = [current_bit]
                segment_start_index = current_index
        
        prev_bit = current_bit
        current_index += 1
    
    # Yield any remaining segment
    if len(current_segment) > 1:
        yield (current_segment, segment_start_index * DECODE_BIT_PERIOD)

def splice_binary_list(binary_list) -> List[Tuple[List[bool], float]]:
    """
    Uses the timecode starts to splice the binary list into segments that can be decoded from IRIG-H.
    Returns a list of 2-tuples containing a timestamp (in seconds) of recording as well as the splice.
    Works with both lists and generators.
    """
    
    # For generators, use the memory-efficient streaming approach
    if hasattr(binary_list, '__iter__') and not hasattr(binary_list, '__getitem__'):
        return list(splice_binary_generator(binary_list))
    
    # For lists, use the original efficient slicing approach
    starts = find_timecode_starts(binary_list)
    return [(binary_list[starts[i]:starts[i+1]], starts[i] * DECODE_BIT_PERIOD) for i in range(len(starts) - 1)]

def decode_full_measurement(binary_list) -> List[Tuple[float, float]]:
    """
    Decodes the full binary measurement into a list of 2-tuples containing the time that was sent by the IRIG-H timecode as well as the time of measurement.
    Works with both lists and generators.
    """

    spliced = splice_binary_list(binary_list)
    timecode_start_seconds = 0 #irig_h_to_posix(decode_to_irig_h(spliced[0][0])) if spliced else 0
    timestamp_start_seconds = 0 #spliced[0][1] if spliced else 0
    return [((irig_h_to_posix(decode_to_irig_h(spliced[i][0])) - timecode_start_seconds), spliced[i][1] - timestamp_start_seconds) for i in range(len(spliced))]
    
class IrigHSender:

    base_path = 'irig_output'
    initialization_dt = str(dt.now().strftime("%Y-%m-%d_%H-%M-%S"))
    TIMESTAMP_FILE_NAME = base_path + "_timestamps_" + initialization_dt + ".csv"

    def __init__(self, sending_gpio_pin, sending_loop_period=1/5000):
        # Constants for timecode sending
        self.sending_gpio_pin = sending_gpio_pin # (6)
        self.sending_loop_period = sending_loop_period # default 5 kHz. decrease for less CPU usage

        # Connect to pigpio daemon
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon. Is 'pigpiod' running?")

        self.pi.set_mode(self.sending_gpio_pin, pigpio.OUTPUT)
        
        self.encoded_times = []
        self.sending_starts = []

        self.sender_thread = Thread(target=self.continuous_irig_sending, daemon=True)

    # ------------------------- IRIG GENERATION ------------------------- #
    
    def generate_irig_h_frame(self, time: dt) -> List[IRIG_BIT]:
        """
        Generates a 60-bit list-represented IRIG-H timecode based on the given time.
        Includes seconds, minutes, hours, day of year, tenths of seconds, and year.
        'P' is used for position identifiers.
        """
        self.encoded_times.append(time.timestamp())

        seconds_bcd = bcd_encode(time.second + 1, SECONDS_WEIGHTS)
        minutes_bcd = bcd_encode(time.minute, MINUTES_WEIGHTS)
        hours_bcd = bcd_encode(time.hour, HOURS_WEIGHTS)
        day_of_year_bcd = bcd_encode(time.timetuple().tm_yday, DAY_OF_YEAR_WEIGHTS)
        deciseconds_bcd = bcd_encode(0, DECISECONDS_WEIGHTS) # since always encoding at the advent of a second
        year_bcd = bcd_encode(time.year % 100, YEARS_WEIGHTS)

        irig_h_list = []

        # i had to write this all manually bc chatgpt is too stupid to do it i guess

        # Bit 00: Pr (Frame marker)
        irig_h_list.append('P')

        # Bits 01-04: Seconds (Units) - Weights: 1, 2, 4, 8
        irig_h_list.extend(seconds_bcd[0:4])
        # Bit 05: Unused (0)
        irig_h_list.append(0)
        # Bits 06-08: Seconds (Tens) - Weights: 10, 20, 40
        irig_h_list.extend(seconds_bcd[4:7])

        # Bit 09: P1 (Position identifier)
        irig_h_list.append('P')

        # Bits 10-13: Minutes (Units) - Weights: 1, 2, 4, 8
        irig_h_list.extend(minutes_bcd[0:4])
        # Bit 14: Unused (0)
        irig_h_list.append(0)
        # Bits 15-17: Minutes (Tens) - Weights: 10, 20, 40
        irig_h_list.extend(minutes_bcd[4:7])
        # Bit 18: Unused (0)
        irig_h_list.append(0)

        # Bit 19: P2 (Position identifier)
        irig_h_list.append('P')

        # Bits 20-23: Hours (Units) - Weights: 1, 2, 4, 8
        irig_h_list.extend(hours_bcd[0:4])
        # Bir 24: Unused (0)
        irig_h_list.append(0)
        # Bits 25-26: Hours (Tens) - Weights: 10, 20
        irig_h_list.extend(hours_bcd[4:6]) # Only 2 bits for tens (10, 20)
        # Bit 27-28: Unused (0)
        irig_h_list.extend([0,0])

        # Bit 29: P3 (Position identifier)
        irig_h_list.append('P')

        # Bits 30-33: Day of year (Units) - Weights: 1, 2, 4, 8
        irig_h_list.extend(day_of_year_bcd[0:4])
        # Bit 34: Unused (0)
        irig_h_list.append(0)
        # Bits 35-38: Day of year (Tens) - Weights: 10, 20, 40, 80
        irig_h_list.extend(day_of_year_bcd[4:8])
        # Bit 39: P4 (Position identifier)
        irig_h_list.append('P')
        # Bits 40-41: Day of year (Hundreds) - Weights: 100, 200
        irig_h_list.extend(day_of_year_bcd[8:10])

        # Bits 42-44: Unused (0)
        irig_h_list.extend([0,0,0])

        # Bits 45-48: Deciseconds - Weights: 1, 2, 4, 8
        irig_h_list.extend(deciseconds_bcd[0:4])

        # Bit 49: P5 (Position identifier)
        irig_h_list.append('P')

        # Bits 50-53: Years (Units) - Weights: 1, 2, 4, 8
        irig_h_list.extend(year_bcd[0:4])
        # Bit 54: Unused (0)
        irig_h_list.append(0)
        # Bit 55-58: Years (Tens) - Weights: 10, 20, 40, 80
        irig_h_list.extend(year_bcd[4:8])

        # Bit 59: P6 (Position identifier)
        irig_h_list.append('P')

        return irig_h_list

    # ------------------------- IRIG SENDING ------------------------- #

    def precise_wait_until(self, wake_time: float):
        """
        Sleeps until a head start before the wake time, then busy waits until then. Method ends when busy waiting is finished.
        """
        now = time.time()
        if wake_time - now > SENDING_HEAD_START:
            time.sleep(wake_time - now - SENDING_HEAD_START)
        while time.time() < wake_time:
             time.sleep(self.sending_loop_period)
            

    def calculate_pulse_length(self, bit: IRIG_BIT) -> float:
            if bit == 'P':
                return 0.8 * SENDING_BIT_LENGTH
            elif bit == 1:
                return 0.5 * SENDING_BIT_LENGTH
            else:
                return 0.2 * SENDING_BIT_LENGTH
        
    def flip_for_time(self, pulse_time: float):
            """
            Flips the sending GPIO pin to HIGH for a certain amount of time.
            """
            print(f'Flipping for {pulse_time} seconds at {time.time()}')
            self.pi.write(self.sending_gpio_pin, 1)
            time.sleep(pulse_time)
            self.pi.write(self.sending_gpio_pin, 0)

    def continuous_irig_sending(self):
        """
        Continuously sends irig timecodes in an unending while loop.
        """

        while True:
            now = dt.now()

            start_time = math.ceil(now.timestamp())
            self.sending_starts.append(start_time)

            frame = self.generate_irig_h_frame(now)
            
            for bit in frame:
                pulse_time = self.calculate_pulse_length(bit)

                self.precise_wait_until(start_time - MEASURED_DELAY)
                print(f'start time: {start_time}')
                self.flip_for_time(pulse_time)

                start_time += SENDING_BIT_LENGTH


    def start(self):
        self.sender_thread.start()

    def write_timestamps_to_file(self):
        data = zip(self.encoded_times, self.sending_starts)
        df = pd.DataFrame(data, columns=['Encoded times','Sending starts'])
        df.to_csv(self.TIMESTAMP_FILE_NAME, index=False)

    def close_thread(self):
        self.sender_thread.join()
        self.sender_thread = None

    def finish(self):
        """
        Something to run when timecode sending is finished; resets the sending GPIO pin and stops pigpio.
        """
        self.write_timestamps_to_file()
        self.pi.write(self.sending_gpio_pin, 0)
        self.pi.stop()
        self.close_thread()
        
