
from typing import Literal, Generator
import csv
import os

def byte_unpack_generator(file_path: str, chunk_size: int = 1024*1024) -> Generator[Literal[0,1], None, None]:
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            for byte in chunk:
                for i in range(7, -1, -1):
                    yield (byte >> i) & 0x01

print("Starting chunked processing...")

irig_file = "irig_decoding/data/binary/irig_binary.bin"
pps_file = "irig_decoding/data/binary/pps_binary.bin"

irig_size = os.path.getsize(irig_file)
pps_size = os.path.getsize(pps_file)
min_size = min(irig_size, pps_size)

print(f'File sizes - IRIG: {irig_size}, PPS: {pps_size}, processing: {min_size} bytes')

errors_index_length = []
tracking_length = 0
processed_bits = 0

irig_gen = byte_unpack_generator(irig_file)
pps_gen = byte_unpack_generator(pps_file)

for irig_bit, pps_bit in zip(irig_gen, pps_gen):
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

# errors_seconds = [error * 1/3000 for error in errors_index_length]

print('Error calculations done. Writing to file...')

filename = 'irig_decoding/data/indexes_of_error.csv'

with open(filename, 'w', newline='') as file:
    csv_writer = csv.writer(file)
    csv_writer.writerow(errors_index_length)

print('File writing done. Enjoy!')