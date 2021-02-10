PRODUCT: ADS1015
Communicate: I2C
Chnanel: 4 


Source Install
To install from the source on Github connect to a terminal on the Raspberry Pi and run the following commands:

git clone https://github.com/adafruit/Adafruit_Python_ADS1x15.git
cd Adafruit_Python_ADS1x15
sudo python3 setup.py install

Library Usage
Change to that folder by running on the Pi:

cd ~/Adafruit_Python_ADS1x15/examples
sudo nano simpletest.py

commented line that instead creates an ADS1015 object to use the ADS1015 chip.  Uncomment the right line depending on the chip you're using.

# Create an ADS1115 ADC (16-bit) instance.
# adc = Adafruit_ADS1x15.ADS1115()
 
# Or create an ADS1015 ADC (12-bit) instance.
adc = Adafruit_ADS1x15.ADS1015()
 
# Note you can change the I2C address from its default (0x48), and/or the I2C
# bus by passing in these optional parameters:
#adc = Adafruit_ADS1x15.ADS1015(address=0x49, bus=1)

The last commented line shows more advanced usage like choosing a custom I2C address or bus number. You don't normally need to change these values.
Now save the file by pressing Ctrl-o, enter, then Ctrl-x to quit.  You can run the simpletest.py code by executing at the terminal:

sudo python3 simpletest.py
