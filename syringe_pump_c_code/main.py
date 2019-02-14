import ctypes

ll = ctypes.cdll.LoadLibrary
lib = ll("./main.so")
lib.Init_IOs(10, 10, 10, 1000, 1000, 1000, ctypes.c_double(0.1), ctypes.c_double(0.1), ctypes.c_double(0.1))
print("Initialized Finished")
while True:
    lib.join()
