import numpy as np

# Configuration  
total_channels = 40
adc1_index = 32  # Digital input 1 (IRIG)
adc2_index = 33  # Digital input 2 (PPS)

input_file = 'continuous.dat'

print("Analyzing digital input values...")

# Read a chunk to see the actual values
chunk_size = 100000
bytes_per_sample = 2 * total_channels
chunk_bytes = chunk_size * bytes_per_sample

with open(input_file, 'rb') as f:
    raw_chunk = f.read(chunk_bytes)
    int16_data = np.frombuffer(raw_chunk, dtype=np.int16)
    samples_in_chunk = len(int16_data) // total_channels
    chunk_data = int16_data[:samples_in_chunk * total_channels]
    chunk_data = chunk_data.reshape(samples_in_chunk, total_channels)
    
    # Extract digital channels
    irig_raw = chunk_data[:, adc1_index]  # Digital input 1
    pps_raw = chunk_data[:, adc2_index]   # Digital input 2
    
    print(f"\nDigital Input 1 (IRIG):")
    print(f"  Unique values: {np.unique(irig_raw)}")
    print(f"  Value counts: {np.bincount(irig_raw[irig_raw >= 0]) if len(np.unique(irig_raw)) < 10 else 'Too many unique values'}")
    
    print(f"\nDigital Input 2 (PPS):")  
    print(f"  Unique values: {np.unique(pps_raw)}")
    print(f"  Value counts: {np.bincount(pps_raw[pps_raw >= 0]) if len(np.unique(pps_raw)) < 10 else 'Too many unique values'}")