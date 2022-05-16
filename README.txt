Sketches for implementing phase-sensitive detection on a 
Teensy 3.5 microcontroller.

pinout for single supply op amp: https://www.ti.com/lit/ds/snosbt3i/snosbt3i.pdf?HQS=dis-mous-null-mousermode-dsf-pf-null-wwe&ts=1644952228380

The correct lock in code to upload to the teensy is LockInFullv2.ino
Teensyduino will need to be installed on the computer uploading to the teensy.

The code for the gui is lockInGUI.py

The GUI currently is only written for windows users, however the serial port connection code can be
easily modified to accomodate mac and linux users. (The start serial method port variable will need to be modified)

The python libraries needed to have the GUI run properly are as follows:
tkinter - the python library used for making gui's
pyserial - the python library for serial communication
pandas - useful for dealing with datasets, makes dataframes
matplotlib - used for creating graphs
time - used for ensuring the GUI does not get stuck when reading data from Teensy