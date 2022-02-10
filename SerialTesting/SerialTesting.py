import serial
import time

def main():
    
    stringToSend = "0:1000:10000F"
    ser = serial.Serial('COM5', 38400, timeout=5, write_timeout=10)
    ser.write(stringToSend.encode('utf-8'))
    time.sleep(10)
    ser.close()

main()