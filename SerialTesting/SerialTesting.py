import serial
import time

def serialWriting():
    mode = 0
    while True:
        if mode == 0:
            mode = 1
        else:
            mode = 0
        try:
            ser.write(mode.to_bytes(1, "big"))
            time.sleep(1)
        except:
            print("write timeout")
            break

def serialReading():
    while ser.in_waiting == 0:
        pass
    while ser.in_waiting != 0:
        try:
            data = ser.readlines()
            print(data)
            for i in range(len(data)):
                print(float(data[i]))
            #print(float(data))
        except:
            print("error occurred reading from serial")
            break
        time.sleep(1)

def serialWriteTwo():
    mode = 1
    #ser.write(mode.to_bytes(1, "big"))
    ser.write(str(mode).encode('utf-8'))
    mode = 1000
    time.sleep(5)
    ser.write(str(mode).encode('utf-8'))

def main():
    global ser
    ser = serial.Serial('COM6', 38400, timeout=5, write_timeout=10)
    #serialWriting()
    serialReading()
    #serialWriteTwo()
    ser.close()

main()