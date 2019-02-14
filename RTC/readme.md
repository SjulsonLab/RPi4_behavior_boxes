The Pi RTC is based on the clock chip DS1307, it can provide a real-time clock(RTC) for raspberry pi via the I2C interface. Real-time clock of this module counts seconds,minutes, hours, date of the month,month, day of the week, and year with leap-year compensation valid up to 2100. The clock operates in either the 24-hour or 12-hour format with AM/PM indicator. If you want to keep this module timing when the Raspberry Pi is powered off, you need to put a 3-Volt CR1225 lithium cell in the battery-holder.

To startup the RTC module on the extend board of RPi. We can use the library from Seeed Studio.

Tap the following command in your terminal
```python
git clone https://github.com/Seeed-Studio/pi-hats.git
cd pi-hats/tools
sudo ./install.sh -u rtc_ds1307
sudo roboot

#Test the RTC module：
su
sudo hwclock –r # Read hardware clock and print result
sudo hwclock –s # Set the system time from the hardware clock
sudo hwclock –w # Set the hardware clock from the current system time
```
