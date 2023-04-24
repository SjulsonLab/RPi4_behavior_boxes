"""
1. import the pre-trained model
2. detect region of interest and configure the camera to focus on the region
3. model estimation and calibration/refine to the region. Might require user manually correction if needed
4. set threshold and detection frame rate, calibrate with manual delivery of reward and close circuit detection
5. run the experiment, establish a parallel process, in which, a program checks the input ROI for lick behavior given
a pre-defined time interval
"""