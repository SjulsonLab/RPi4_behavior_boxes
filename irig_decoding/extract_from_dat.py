import numpy as np

# Configuration
n_neural_channels = 32  # CH1 to CH32
n_adc_channels = 8      # ADC1 to ADC8
total_channels = n_neural_channels + n_adc_channels  # 40 total
sample_rate = 30000     # Adjust to your actual sample rate

# ADC channel indices
adc1_index = 32  # ADC1 (PPS)
adc2_index = 33  # ADC2 (IRIG)

# Input and output file paths
input_file = 'your_recording.dat'  # Change to your .dat file path
pps_output = 'pps_binary.bin'
irig_output = 'irig_binary.bin'

print("Loading data...")
# Load and reshape data
data = np.fromfile(input_file, dtype=np.int16)
data = data.reshape(-1, total_channels)

print(f"Loaded {data.shape[0]} samples with {data.shape[1]} channels")

# Extract ADC channels
print("Extracting ADC channels...")
pps_raw = data[:, adc1_index]    # ADC1
irig_raw = data[:, adc2_index]   # ADC2

# Convert to binary (adjust thresholds as needed)
print("Converting to binary...")
pps_binary = (pps_raw > 0).astype(np.uint8)
irig_binary = (irig_raw > 0).astype(np.uint8)

# Save to binary files
print("Saving binary files...")
pps_binary.tofile(pps_output)
irig_binary.tofile(irig_output)

# Print statistics
pps_edges = np.sum(np.diff(pps_binary.astype(int)) > 0)
irig_transitions = np.sum(np.diff(irig_binary.astype(int)) != 0)

print(f"\nResults:")
print(f"PPS rising edges detected: {pps_edges}")
print(f"IRIG transitions detected: {irig_transitions}")
print(f"Recording duration: {data.shape[0] / sample_rate:.2f} seconds")
print(f"Files saved:")
print(f"  PPS: {pps_output} ({len(pps_binary)} bytes)")
print(f"  IRIG: {irig_output} ({len(irig_binary)} bytes)")