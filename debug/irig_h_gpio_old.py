from typing import List, Tuple, Literal
import pigpio
import time
from datetime import datetime as dt
import datetime
# import pandas as pd
import io

# Constants for timecode sending
SENDING_GPIO_PIN = 6 
SENDING_BIT_LENGTH = 1 # in seconds
SENDING_LOOP_PERIOD = 1 / 5000 # 5 kHz. decrease for less CPU usage

IRIG_BIT = Literal[0,1,'P'] # type for IRIG-H bits
BINARY_BIT = Literal[0,1] # type for binary bits

# Constants for timecode measuring
DECODE_BIT_PERIOD = 1 / 25_000 # for now frame rate is 25 kHz
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

base_path = 'irig_output'
initialization_dt = str(dt.now().strftime("%Y-%m-%d_%H-%M-%S"))
TIMESTAMP_FILE_NAME = base_path + "_timestamps_" + initialization_dt + ".csv"

# Connect to pigpio daemon
pi = pigpio.pi()
if not pi.connected:
    raise RuntimeError("Could not connect to pigpio daemon. Is 'pigpiod' running?")

pi.set_mode(SENDING_GPIO_PIN, pigpio.OUTPUT)

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

# ------------------------- IRIG GENERATION ------------------------- #

encoded_times = []

def generate_irig_h_frame() -> List[IRIG_BIT]:
    """
    Generates a 60-bit list-represented IRIG-H timecode basd on the current hardware time.
    Includes seconds, minutes, hours, day of year, tenths of seconds, and year.
    'P' is used for position identifiers.
    """

    now = dt.now() # Get the current local time
    encoded_times.append(now.timestamp())

    seconds_bcd = bcd_encode(now.second, SECONDS_WEIGHTS)
    minutes_bcd = bcd_encode(now.minute, MINUTES_WEIGHTS)
    hours_bcd = bcd_encode(now.hour, HOURS_WEIGHTS)
    day_of_year_bcd = bcd_encode(now.timetuple().tm_yday, DAY_OF_YEAR_WEIGHTS)
    deciseconds_bcd = bcd_encode(now.microsecond // 100000, DECISECONDS_WEIGHTS)
    year_bcd = bcd_encode(now.year % 100, YEARS_WEIGHTS)

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

def decode_to_irig_h(binary_list: List[bool]) -> List[IRIG_BIT]:
    """
    Decodes a list of measured pulse lengths (in seconds) to a list-represented IRIG-H frame.
    """

    if len(binary_list) < 2:
        print("Inputted data set is too short.")
        return []
    
    def identify_pulse_length(length):
        if length > P_THRESHOLD:
            return 'P'
        if length > ONE_THRESHOLD:
            return 1
        if length > ZERO_THRESHOLD:
            return 0
        else: 
            return None

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
    return dt.combine(datetime.date(year, 1, 1) + datetime.timedelta(days=(day_of_year - 1)), datetime.time(hours, minutes, seconds, deciseconds * 10_000))

def irig_h_to_posix(irig_list: List[IRIG_BIT]) -> float:
    """
    Converts a list-represented IRIG-H frame into a POSIX timecode (Measured in seconds since 00:00:00 UTC, January 1st, 1970).
    Since IRIG does not encode century, this code assumes that the IRIG timecode is being sent in the same century as when this function is called.
    """
    return irig_h_to_datetime(irig_list).timestamp()

def find_timecode_starts(binary_list: List[bool]) -> List[int]:
    """
    Finds all the indexes in the measured list of booleans for where a timecode starts.
    Keep in mind that this assumes that there is NO noise. 
    If there is an incomplete timecode at the end, it will still return a start for that timecode.
    """

    if len(binary_list) < 2:
        print("Inputted data set is too short.")
        return []
    
    starts = [0] if binary_list[0] else [] # list of indexes for when the timecodes start
    flips = 1 if binary_list[0] else 0     # if its already recieving timcodes at the start, change starting behavior

    for i in range(1, len(binary_list)):
        if binary_list[i] != binary_list[i-1]:
            flips += 1
            if (flips - 1) % 120 == 0:
                starts.append(i)
    return starts

def splice_binary_list(binary_list: List[bool]) -> List[Tuple[List[bool], float]]:
    """
    Uses the timecode starts to splice the binary list into segments that can be decoded from IRIG-H.
    Returns a list of 2-tuples containing a timestamp (in seconds) of recording as well as the splice.
    """

    starts = find_timecode_starts(binary_list)
    return [(binary_list[starts[i]:starts[i+1]], starts[i] * DECODE_BIT_PERIOD) for i in range(len(starts) - 1)]

def decode_full_measurement(binary_list: List[bool]) -> List[Tuple[float, float]]:
    """
    Decodes the full binary measurement into a list of 2-tuples containing the time that was sent by the IRIG-H timecode as well as the time of measurement.
    """

    spliced = splice_binary_list(binary_list)
    start_time_seconds = irig_h_to_posix(decode_to_irig_h(spliced[0][0])) if spliced else 0
    return [((irig_h_to_posix(decode_to_irig_h(spliced[i][0])) - start_time_seconds), spliced[i][1]) for i in range(len(spliced))]
    

# ------------------------- IRIG SENDING ------------------------- #

sending_starts = []

def send_irig_h_frame(frame: List[IRIG_BIT]):
    """
    Sends a full IRIG-H timecode through the GPIO pin.
    """
    sending_starts.append(dt.now().timestamp())
    for i, bit in enumerate(frame):
        # print bit info
        if bit == 'P':
            print(f"Bit {i:02d}: P")
            pi.write(SENDING_GPIO_PIN, 1)
            time.sleep(SENDING_BIT_LENGTH * 0.8)
            pi.write(SENDING_GPIO_PIN, 0)
            time.sleep(SENDING_BIT_LENGTH * 0.2)
        elif bit == 1:
            print(f"Bit {i:02d}: 1")
            pi.write(SENDING_GPIO_PIN, 1)
            time.sleep(SENDING_BIT_LENGTH * 0.5)
            pi.write(SENDING_GPIO_PIN, 0)
            time.sleep(SENDING_BIT_LENGTH * 0.5)
        else:
            print(f"Bit {i:02d}: 0")
            pi.write(SENDING_GPIO_PIN, 1)
            time.sleep(SENDING_BIT_LENGTH * 0.2)
            pi.write(SENDING_GPIO_PIN, 0)
            time.sleep(SENDING_BIT_LENGTH * 0.8)

def send_irig_h_frame2(frame: List[IRIG_BIT]):
    """
    Sends a full IRIG-H timecode through the GPIO pin using a while loop that checks the current time and sends the correct bit at the correct time.
    This method is more accurate than the first method (no time.sleep() is used), but also more CPU-intensive.
    """

    start_time = dt.now()
    sending_starts.append(start_time.timestamp())

    frame_time_length = datetime.timedelta(seconds=len(frame)*SENDING_BIT_LENGTH)
    while dt.now() < start_time + frame_time_length:
        delta_t_seconds = (dt.now() - start_time).total_seconds()
        bit = frame[int(delta_t_seconds // SENDING_BIT_LENGTH)]
        bit_time_seconds = (delta_t_seconds % SENDING_BIT_LENGTH)

        if bit == 'P':
            pi.write(SENDING_GPIO_PIN, 1 if bit_time_seconds < 0.8 * SENDING_BIT_LENGTH else 0)
        elif bit == 1:
            pi.write(SENDING_GPIO_PIN, 1 if bit_time_seconds < 0.5 * SENDING_BIT_LENGTH else 0)
        else:
            pi.write(SENDING_GPIO_PIN, 1 if bit_time_seconds < 0.2 * SENDING_BIT_LENGTH else 0)
        
        time.sleep(SENDING_LOOP_PERIOD)

def generate_and_send_irig_h(): 
    """
    Generates a full IRIG-H frame for when this is called, then sends it over the course of a frame interval.
    """

    frame = generate_irig_h_frame()
    send_irig_h_frame2(frame) # using method 2
    print(f"Frame complete; restarting next {SENDING_BIT_LENGTH * 60 * 1000} milliseconds...")

def start_irig_sending():
    """
    Continuously sends irig timecodes in an unending while loop.
    """
    while True:
        generate_and_send_irig_h()

def write_timestamps_to_file(filename: str):
    data = zip(encoded_times, sending_starts)
    # df = pd.DataFrame(data, columns=['Encoded times','Sending starts'])
    # df.to_csv(TIMESTAMP_FILE_NAME, index=False)

    with io.open(filename, 'w') as f:
        f.write('Encoded times, Sending starts\n')
        for entry in data:
            f.write('%f,%f\n' % entry)

def finish(filename: str):
    """
    Something to run when timecode sending is finished; resets the sending GPIO pin and stops pigpio.
    """
    write_timestamps_to_file(filename)
    pi.write(SENDING_GPIO_PIN, 0)
    pi.stop()


class IRIGHTimecodeSender:
    """
    Class for sending IRIG-H timecodes using a GPIO pin.
    """

    def __init__(self, pin: int = SENDING_GPIO_PIN):
        self.pin = pin
        self._stop_flag = False
        self.encoded_times = []
        self.sending_starts = []

        self.flip_state = 0
        self.state_change = pigpio.wait_for_edge(self.pin, pigpio.FALLING_EDGE)
        pi.set_mode(self.pin, pigpio.OUTPUT)

    def stop(self):
        self._stop_flag = True

    def send_irig_h_frame2(self, frame: List[IRIG_BIT]):
        """
        Sends a full IRIG-H timecode through the GPIO pin using a while loop that checks the current time and sends the correct bit at the correct time.
        This method is more accurate than the first method (no time.sleep() is used), but also more CPU-intensive.
        """

        start_time = dt.now()
        self.sending_starts.append(start_time.timestamp())

        frame_time_length = datetime.timedelta(seconds=len(frame) * SENDING_BIT_LENGTH)
        while dt.now() < start_time + frame_time_length:
            delta_t_seconds = (dt.now() - start_time).total_seconds()
            bit = frame[int(delta_t_seconds // SENDING_BIT_LENGTH)]
            bit_time_seconds = (delta_t_seconds % SENDING_BIT_LENGTH)

            if bit == 'P':
                pi.write(SENDING_GPIO_PIN, 1 if bit_time_seconds < 0.8 * SENDING_BIT_LENGTH else 0)
            elif bit == 1:
                pi.write(SENDING_GPIO_PIN, 1 if bit_time_seconds < 0.5 * SENDING_BIT_LENGTH else 0)
            else:
                pi.write(SENDING_GPIO_PIN, 1 if bit_time_seconds < 0.2 * SENDING_BIT_LENGTH else 0)

            time.sleep(SENDING_LOOP_PERIOD)

    def generate_and_send_irig_h(self,):
        """
        Generates a full IRIG-H frame for when this is called, then sends it over the course of a frame interval.
        """

        frame = generate_irig_h_frame()
        send_irig_h_frame2(frame)  # using method 2
        print(f"Frame complete; restarting next {SENDING_BIT_LENGTH * 60 * 1000} milliseconds...")

    def start_irig_sending(self):
        """
        Continuously sends irig timecodes in an unending while loop.
        """
        while True:
            generate_and_send_irig_h()

    def write_timestamps_to_file(self, filename: str):
        data = zip(encoded_times, sending_starts)
        # df = pd.DataFrame(data, columns=['Encoded times','Sending starts'])
        # df.to_csv(TIMESTAMP_FILE_NAME, index=False)

        with io.open(filename, 'w') as f:
            f.write('Encoded times, Sending starts\n')
            for entry in data:
                f.write('%f,%f\n' % entry)

    def finish(self, filename: str):
        """
        Something to run when timecode sending is finished; resets the sending GPIO pin and stops pigpio.
        """
        write_timestamps_to_file(filename)
        pi.write(SENDING_GPIO_PIN, 0)
        pi.stop()
