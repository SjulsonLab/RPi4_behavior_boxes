import numpy as np

# Configuration
total_channels = 40
adc1_index = 32  # PPS
adc2_index = 33  # IRIG
sample_rate = 30000

# File paths
input_file = 'continuous.dat'
pps_output = 'pps_binary.bin'
irig_output = 'irig_binary.bin'

# Process in chunks
chunk_size = 1000000  # Samples per chunk

print("Processing file with bit-packing...")

def pack_bits_to_file(binary_data, file_handle):
    """Pack binary data (0s and 1s) into bits and write to file"""
    # Pad to multiple of 8
    padded_length = ((len(binary_data) + 7) // 8) * 8
    if len(binary_data) % 8 != 0:
        padding = np.zeros(padded_length - len(binary_data), dtype=np.uint8)
        padded_data = np.concatenate([binary_data, padding])
    else:
        padded_data = binary_data
    
    # Pack 8 bits into each byte
    packed = np.packbits(padded_data)
    file_handle.write(packed.tobytes())
    return len(packed)

with open(pps_output, 'wb') as pps_file, open(irig_output, 'wb') as irig_file:
    with open(input_file, 'rb') as f:
        chunk_num = 0
        total_samples = 0
        pps_bytes_written = 0
        irig_bytes_written = 0
        
        while True:
            # Calculate byte positions for the channels we need
            # Each sample is 2 bytes (int16) * total_channels
            bytes_per_sample = 2 * total_channels
            chunk_bytes = chunk_size * bytes_per_sample
            
            # Read chunk
            raw_chunk = f.read(chunk_bytes)
            if len(raw_chunk) == 0:
                break
                
            # Convert to int16 array
            int16_data = np.frombuffer(raw_chunk, dtype=np.int16)
            samples_in_chunk = len(int16_data) // total_channels
            
            if samples_in_chunk == 0:
                break
                
            # Reshape and extract only the channels we need
            int16_data = int16_data[:samples_in_chunk * total_channels]
            chunk_data = int16_data.reshape(samples_in_chunk, total_channels)
            
            # Extract only ADC1 and ADC2
            pps_raw = chunk_data[:, adc2_index]
            irig_raw = chunk_data[:, adc1_index]
            
            # Convert to binary
            pps_binary = (pps_raw > 0).astype(np.uint8)
            irig_binary = (irig_raw > 0).astype(np.uint8)
            
            # Pack and write to files
            pps_bytes_written += pack_bits_to_file(pps_binary, pps_file)
            irig_bytes_written += pack_bits_to_file(irig_binary, irig_file)
            
            total_samples += samples_in_chunk
            chunk_num += 1
            
            if chunk_num % 100 == 0:
                print(f"Processed chunk {chunk_num}, samples: {total_samples:,}")
                print(f"  PPS file: {pps_bytes_written:,} bytes")
                print(f"  IRIG file: {irig_bytes_written:,} bytes")

print(f"\nProcessing complete!")
print(f"Total samples: {total_samples:,}")
print(f"Duration: {total_samples / sample_rate:.2f} seconds")
print(f"Output files (bit-packed):")
print(f"  PPS: {pps_output} ({pps_bytes_written:,} bytes, {pps_bytes_written/1024/1024:.1f} MB)")
print(f"  IRIG: {irig_output} ({irig_bytes_written:,} bytes, {irig_bytes_written/1024/1024:.1f} MB)")
print(f"Compression: 8x smaller than uint8, 320x smaller than original")

# To read the data back later:
print(f"\nTo read back:")
print(f"pps_packed = np.fromfile('{pps_output}', dtype=np.uint8)")
print(f"pps_data = np.unpackbits(pps_packed)")