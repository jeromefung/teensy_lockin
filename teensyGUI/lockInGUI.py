import tkinter as tk
from tkinter import filedialog
import serial
import pandas as pd
import matplotlib.pyplot as plt
import sys
import time

class lockInDetection(tk.Frame):
    '''
    Frame object to be use in GUI for lock in detection with teensy microcontroller
    Properties:
    parent - the frame object for gui organization
    refSelect - determines if using the internal or external reference frequency (0 for internal, 1 for external)
    ser - the serial connection for communicating with the teensy (unsure if will need to reset it when wanting to run lock in again without closing gui)
    '''

    def __init__(self, parent):
        '''Initialize Frame'''
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.DataDf = pd.DataFrame()
        self.initialize()

    def initialize(self):
        '''Initialize the frame parameters and create their widgets'''
        self.parent.title("Lock in Detector")
        self.refSelect = tk.IntVar()
        self.createWidgets()
        # need to figure out window sizing and placement of widgets

    def createWidgets(self):
        '''Creates all the widgets needed for the GUI'''
        frequencyEntry = tk.Entry(self.parent)
        frequencyEntry.grid(row=5, columnspan=6, sticky=tk.W+tk.E)
        frequencyLabel = tk.Label(
            self.parent, text="Internal Reference Frequency:")
        frequencyLabel.grid(row=4, columnspan=6, sticky=tk.W+tk.E)

        sampleEntry = tk.Entry(self.parent)
        sampleEntry.grid(row=7, columnspan=6, sticky=tk.W+tk.E)
        sampleLabel = tk.Label(self.parent, text="Sampling Rate (if unsure leave empty):") #maybe change to dropdown menu in the future
        sampleLabel.grid(row=6, columnspan=6, sticky=tk.W+tk.E)

        internalButton = tk.Radiobutton(
            self.parent, text="Internal Reference", variable=self.refSelect, value=0)
        internalButton.deselect()
        internalButton.grid(row=2, columnspan=6, sticky=tk.W+tk.E)
        externalButton = tk.Radiobutton(
            self.parent, text="External Reference", variable=self.refSelect, value=1)
        externalButton.deselect()
        externalButton.grid(row=3, columnspan=6, sticky=tk.W+tk.E)

        serPort = tk.Entry(self.parent)
        serPort.grid(row=1, column=1, sticky=tk.W+tk.E)

        serPortLabel = tk.Label(self.parent, text="Serial Port Number (1-256):")
        serPortLabel.grid(row=1, column=0, columnspan=1, sticky=tk.W+tk.E)

        #serStartButton = tk.Button(
        #    self.parent, text="Start Serial", command=lambda: self.startSerial(serPort))
        #serStartButton.grid(row=1, column=2, sticky=tk.W+tk.E)

        #serEndButton = tk.Button(
        #    self.parent, text="Close Serial", command=lambda: self.endSerial())
        #serEndButton.grid(row=1, column=4, sticky=tk.W+tk.E)

        startButton = tk.Button(self.parent, text="Start",
                                command=lambda: self.startTeensy(frequencyEntry, sampleEntry, serPort))
        startButton.grid(row=8, columnspan=6, sticky=tk.W+tk.E)

        saveButton = tk.Button(self.parent, text="Save Data",
                                command=lambda: self.saveData())
        saveButton.grid(row=9, columnspan=6, sticky=tk.W+tk.E)

    def startSerial(self, serPort):
        '''Opens serial port'''
        try:
            port = serPort.get()
        except:
            print("Serial Port Not Specified")
        #port = "COM" + port
        try:
            self.ser = serial.Serial(port, 38400, timeout=None, write_timeout=10)
            self.ser.set_buffer_size(rx_size= 100000, tx_size=4096)
            print("Successful")
        except:
            print("Could not connect to serial port, " + port)

    def endSerial(self):
        '''Closes serial port'''
        try:
            self.ser.close()
        except:
            print("No serial port open")

    def startTeensy(self, refFreq, sampRate, serPort):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        try:
            self.startSerial(serPort) #start the serial port
            self.ser.reset_output_buffer()
            self.ser.reset_input_buffer()
            if self.refSelect.get() == 0:  # internal reference selected
                try:
                    refFreq = int(refFreq.get())
                except:
                    return False
                try:
                    sampRate = int(sampRate.get()) #get sample rate
                except:
                    sampRate = 10000
                #make instruction string
                stringToSend = "0:" + str(refFreq) + ":" + str(sampRate) + "F"
            else:
                try:
                    sampRate = int(sampRate.get()) #get sample rate
                except:
                    sampRate = 10000
                #make instruction string
                stringToSend = "1:" + str(sampRate) + "F"
            
            #send data
            try:
                self.ser.write(str(stringToSend).encode('utf-8'))
            except:
                print("writing timed out")
            self.processData()
            return True
        except:
            print("Failed in startTeensy")
            return False

    def processData(self):
        '''
        Processes the data, returns true if successful, false if otherwise
        '''
        try:
            data = []
            count = 0
            while self.ser.in_waiting == 0: #while nothing in serial do nothing
                pass
            d = ''
            #use a timer to prevent infinite loops
            start = time.time()
            while count < 9900: #expecting 10000 lines of data right now
                temp = self.ser.read()
                temp = str(temp)[2:-1]
                if (temp != 'E'):
                    d = d + temp
                else:
                    data.append(d)
                    d = ''
                    count += 1  
                    if count % 1000 == 0:
                        print(count, "lines read of 10000")
                if (time.time() - start > 30): #if taking longer than 30 seconds
                    print("Could not read all lines")
                    break    
            data = data[:-1] #cutout last data point since is not actual data
            print("lines read:", len(data))
            data2D = []
            for i in range(len(data)): #convert from bytes to floats for each data point
                try:
                    temp = data[i]
                    temp = temp.split(', ')
                    for j in range(len(temp)):
                        temp[j] = float(temp[j])
                    data2D.append(temp)
                except:
                    pass
            dataDf = pd.DataFrame(data2D[2:]) #put data into dataframe - get rid of first line since left over from previous run
            dataDf.columns = ["Signal", "I", "Q", "R", "Phi"] #set dataframe column names
            #plt.tick_params(axis= "x", which = "both", bottom = False, top = False)
            #plt.xticks(dataDf.index, " ")
            plt.figure()
            plt.plot(dataDf.index[:200], dataDf["Signal"][:200]*3.3/4096)
            plt.ylabel("Voltage (V)", fontsize=20)
            plt.title("Measured Signal", fontsize = 25)
            plt.show(block=False)
            fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True) #plot the data
            ax1.plot(dataDf.index, 2*dataDf["R"]*3.3/4096)
            ax1.set_ylabel("Amplitude (V)", fontsize=20)
            ax1.set_title("Lock-in Detection Results", fontsize= 25)
            ax2.plot(dataDf.index, dataDf["Phi"])
            ax2.set_ylabel("Phase (radians)", fontsize=20)
            plt.show(block=False)
            print(dataDf.head())
            self.DataDf = dataDf
            self.endSerial()
            return True
        except Exception as e:
            print("Failed in processData")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_type, exc_tb.tb_lineno)
            print(dataDf.head())
            return False

    
    def saveData(self):
        files = [('CSV (Comma Delimited)', '*.csv'),
             ('All Files', '*.*'), 
             ('Python Files', '*.py'),
             ('Text Document', '*.txt')]
        f = filedialog.asksaveasfile(mode = 'w', filetypes = files, defaultextension = files)
        try:
            f.write(self.DataDf.to_csv())
            print("file saved")
        except:
            pass


def main():
    root = tk.Tk()
    frame = lockInDetection(root)
    frame.grid()
    root.mainloop()


if __name__ == '__main__':
    main()
