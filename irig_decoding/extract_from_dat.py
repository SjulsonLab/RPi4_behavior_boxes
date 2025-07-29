import numpy as np
import sys

# Configuration
total_channels = 40
adc1_index = 32  # IRIG
adc2_index = 33  # PPS
sample_rate = 30000

# Thresholds based on your debug output
irig_threshold = 10000  # Adjust if needed
pps_threshold = 10000   # Adjust if needed

# File paths
input_file = 'continuous.dat'  # Change to your .dat file path
pps_output = 'pps_binary.bin'
irig_output = 'irig_binary.bin'

# Process in chunks - smaller chunks for better I/O performance
chunk_size = 250000  # Samples per chunk (reduced from 1M)

print("Processing file with bit-packing and proper thresholds...")
print(f"Input file: {input_file}")
print(f"Chunk size: {chunk_size:,} samples")

def pack_bits_to_file(binary_data, file_handle):
    """Pack binary data (0s and 1s) into bits and write to file"""
    try:
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
    except Exception as e:
        print(f"Error in pack_bits_to_file: {e}")
        return 0

try:
    with open(pps_output, 'wb') as pps_file, open(irig_output, 'wb') as irig_file:
        with open(input_file, 'rb') as f:
            chunk_num = 0
            total_samples = 0
            pps_bytes_written = 0
            irig_bytes_written = 0
            pps_high_count = 0
            irig_high_count = 0
            
            while True:
                try:
                    # Calculate bytes to read
                    bytes_per_sample = 2 * total_channels
                    chunk_bytes = chunk_size * bytes_per_sample
                    
                    # Read chunk
                    raw_chunk = f.read(chunk_bytes)
                    if len(raw_chunk) == 0:
                        print("Reached end of file")
                        break
                        
                    # Convert to int16 array
                    int16_data = np.frombuffer(raw_chunk, dtype=np.int16)
                    samples_in_chunk = len(int16_data) // total_channels
                    
                    if samples_in_chunk == 0:
                        print("No complete samples in chunk")
                        break
                        
                    # Reshape and extract channels
                    int16_data = int16_data[:samples_in_chunk * total_channels]
                    chunk_data = int16_data.reshape(samples_in_chunk, total_channels)
                    
                    # Extract ADC channels
                    irig_raw = chunk_data[:, adc1_index]  # IRIG
                    pps_raw = chunk_data[:, adc2_index]   # PPS
                    
                    # Convert to binary using thresholds
                    irig_binary = (irig_raw > irig_threshold).astype(np.uint8)
                    pps_binary = (pps_raw > pps_threshold).astype(np.uint8)
                    
                    # Count high states for statistics
                    pps_high_count += np.sum(pps_binary)
                    irig_high_count += np.sum(irig_binary)
                    
                    # Pack and write to files
                    pps_bytes_written += pack_bits_to_file(pps_binary, pps_file)
                    irig_bytes_written += pack_bits_to_file(irig_binary, irig_file)
                    
                    # Force buffer flush to disk every chunk
                    pps_file.flush()
                    irig_file.flush()
                    
                    total_samples += samples_in_chunk
                    chunk_num += 1
                    
                    # More frequent progress updates
                    if chunk_num % 20 == 0:  # Every 20 chunks instead of 50
                        print(f"Chunk {chunk_num}: {total_samples:,} samples processed")
                        print(f"  PPS HIGH: {100*pps_high_count/total_samples:.1f}%")
                        print(f"  IRIG HIGH: {100*irig_high_count/total_samples:.1f}%")
                        sys.stdout.flush()
                        
                    # Heartbeat every 5 chunks (more frequent due to smaller chunks)
                    elif chunk_num % 5 == 0:
                        print(f"Chunk {chunk_num}... ", end="", flush=True)
                        
                except Exception as e:
                    print(f"Error processing chunk {chunk_num}: {e}")
                    print(f"Chunk size was: {len(raw_chunk)} bytes")
                    break

    print(f"\nProcessing complete!")
    print(f"Total samples: {total_samples:,}")
    print(f"Duration: {total_samples / sample_rate:.2f} seconds")
    print(f"PPS HIGH states: {100*pps_high_count/total_samples:.1f}%")
    print(f"IRIG HIGH states: {100*irig_high_count/total_samples:.1f}%")
    print(f"Output files (bit-packed):")
    print(f"  PPS: {pps_output} ({pps_bytes_written:,} bytes, {pps_bytes_written/1024/1024:.1f} MB)")
    print(f"  IRIG: {irig_output} ({irig_bytes_written:,} bytes, {irig_bytes_written/1024/1024:.1f} MB)")

    # Instructions for reading back
    print(f"\nTo read the data back:")
    print(f"pps_packed = np.fromfile('{pps_output}', dtype=np.uint8)")
    print(f"pps_data = np.unpackbits(pps_packed)[:total_samples]  # Trim padding")
    print(f"irig_packed = np.fromfile('{irig_output}', dtype=np.uint8)")
    print(f"irig_data = np.unpackbits(irig_packed)[:total_samples]  # Trim padding")

except Exception as e:
    print(f"Fatal error: {e}")
    import traceback
    traceback.print_exc()