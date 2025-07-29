import numpy as np

# Configuration
n_neural_channels = 32
n_adc_channels = 8
total_channels = 40
sample_rate = 3000

# ADC channel indices
adc1_index = 32  # ADC1 (PPS)
adc2_index = 33  # ADC2 (IRIG)

# File paths
input_file = 'continuous.dat'
pps_output = 'pps_binary.bin'
irig_output = 'irig_binary.bin'

# Process in chunks to avoid memory issues
chunk_size = 1000000  # Process 1M samples at a time (adjust if needed)

print("Processing file in chunks...")

# Open output files
with open(pps_output, 'wb') as pps_file, open(irig_output, 'wb') as irig_file:
    
    # Open input file
    with open(input_file, 'rb') as f:
        chunk_num = 0
        total_samples = 0
        pps_edges = 0
        irig_transitions = 0
        
        while True:
            # Read chunk of data
            chunk_bytes = chunk_size * total_channels * 2  # 2 bytes per int16
            raw_chunk = f.read(chunk_bytes)
            
            if len(raw_chunk) == 0:
                break  # End of file
                
            # Convert to numpy array and reshape
            chunk_data = np.frombuffer(raw_chunk, dtype=np.int16)
            
            # Handle partial chunks at end of file
            samples_in_chunk = len(chunk_data) // total_channels
            if samples_in_chunk == 0:
                break
                
            chunk_data = chunk_data[:samples_in_chunk * total_channels]
            chunk_data = chunk_data.reshape(samples_in_chunk, total_channels)
            
            # Extract ADC channels
            pps_raw = chunk_data[:, adc1_index]
            irig_raw = chunk_data[:, adc2_index]
            
            # Convert to binary
            pps_binary = (pps_raw > 0).astype(np.uint8)
            irig_binary = (irig_raw > 0).astype(np.uint8)
            
            # Write to files
            pps_file.write(pps_binary.tobytes())
            irig_file.write(irig_binary.tobytes())
            
            # Count edges/transitions for statistics
            if chunk_num > 0:  # Skip first chunk for edge counting
                pps_edges += np.sum(np.diff(pps_binary.astype(int)) > 0)
                irig_transitions += np.sum(np.diff(irig_binary.astype(int)) != 0)
            
            total_samples += samples_in_chunk
            chunk_num += 1
            
            if chunk_num % 100 == 0:
                print(f"Processed chunk {chunk_num}, total samples: {total_samples:,}")

print(f"\nProcessing complete!")
print(f"Total samples processed: {total_samples:,}")
print(f"Recording duration: {total_samples / sample_rate:.2f} seconds")
print(f"PPS rising edges detected: {pps_edges}")
print(f"IRIG transitions detected: {irig_transitions}")
print(f"Files saved:")
print(f"  PPS: {pps_output} ({total_samples} bytes)")
print(f"  IRIG: {irig_output} ({total_samples} bytes)")