
from typing import List, Literal, Generator
import csv
import os
from irig_h_gpio import decode_full_measurement
irig_file = "irig_decoding/data/binary/irig_binary.bin"
pps_file = "irig_decoding/data/binary/pps_binary.bin"

error_filename = 'irig_decoding/data/indexes_of_error.csv'
decoded_filename = 'irig_decoding/data/decoded_timecodes.csv'


def byte_unpack_generator(file_path: str, chunk_size: int = 1024*1024) -> Generator[bool, None, None]:
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            for byte in chunk:
                for i in range(7, -1, -1):
                    yield (byte >> i) & 0x01

def find_errors(irig: Generator[bool, None, None], pps: Generator[bool, None, None]) -> List[int]: 
    errors_index_length = []
    tracking_length = 0
    processed_bits = 0
    for irig_bit, pps_bit in zip(irig, pps):
        if pps_bit == 1:
            if irig_bit == 0:
                tracking_length += 1
            else:
                errors_index_length.append(tracking_length)
                tracking_length = 0
    
        processed_bits += 1
        if processed_bits % 24000000 == 0:  # Progress every ~8MB of bits
            print(f'Processed {processed_bits} bits, found {len(errors_index_length)} errors')

    print(f'Processing complete. Total bits: {processed_bits}, errors found: {len(errors_index_length)}')
    return errors_index_length

def error_analysis():
    print('Unpacking irig bytes into bits.')
    irig_gen = byte_unpack_generator(irig_file)
    print('Unpacking pps bytes into bits.')
    pps_gen = byte_unpack_generator(pps_file)

    print('Unpacking done. Calculating errors...')
    # This means, the amount of samples taken where the PPS pulse has started and the IRIG timecode has not.
    errors = find_errors(irig_gen, pps_gen)

    # errors_seconds = [error * 1/3000 for error in errors]

    print('Error calculations done. Writing to file...')

    with open(error_filename, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(errors)

    print('File writing done. Enjoy!')

def decode_analysis():
    irig_gen = byte_unpack_generator(irig_file)
    decoded = decode_full_measurement(irig_gen)
    with open(decoded_filename, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        for tuple in decoded:
            csv_writer.writerow(tuple)


irig_size = os.path.getsize(irig_file)
pps_size = os.path.getsize(pps_file)
min_size = min(irig_size, pps_size)

print(f'File sizes - IRIG: {irig_size}, PPS: {pps_size}, processing: {min_size} bytes')

decode_analysis()

