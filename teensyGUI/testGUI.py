#########
# TODO: Make sample frequency a user controlled variable
#There is still a reading issue with getting the data from the teensy
#########################################################

import tkinter as tk
from tkinter import filedialog
import time
import serial
import pandas as pd
import matplotlib.pyplot as plt


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
        frequencyEntry.grid(row=5, columnspan=4, sticky=tk.W+tk.E)
        frequencyLabel = tk.Label(
            self.parent, text="Internal Reference Frequency:")
        frequencyLabel.grid(row=4, columnspan=4, sticky=tk.W+tk.E)

        sampleEntry = tk.Entry(self.parent)
        sampleEntry.grid(row=7, columnspan=4, sticky=tk.W+tk.E)
        sampleLabel = tk.Label(self.parent, text="Sampling Rate:")
        sampleLabel.grid(row=6, columnspan=4, sticky=tk.W+tk.E)

        internalButton = tk.Radiobutton(
            self.parent, text="Internal Reference", variable=self.refSelect, value=0)
        internalButton.deselect()
        internalButton.grid(row=2, columnspan=4, sticky=tk.W+tk.E)
        externalButton = tk.Radiobutton(
            self.parent, text="External Reference", variable=self.refSelect, value=1)
        externalButton.deselect()
        externalButton.grid(row=3, columnspan=4, sticky=tk.W+tk.E)

        serStartButton = tk.Button(
            self.parent, text="Start Serial", command=lambda: self.startSerial())
        serStartButton.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E)

        serEndButton = tk.Button(
            self.parent, text="Close Serial", command=lambda: self.endSerial())
        serEndButton.grid(row=1, column=2, columnspan=2, sticky=tk.W+tk.E)

        startButton = tk.Button(self.parent, text="Start",
                                command=lambda: self.startTeensy(frequencyEntry, sampleEntry))
        startButton.grid(row=8, columnspan=4, sticky=tk.W+tk.E)

        saveButton = tk.Button(self.parent, text="Save Data",
                                command=lambda: self.saveData())
        saveButton.grid(row=9, columnspan=4, sticky=tk.W+tk.E)

    def startSerial(self):
        '''Opens serial port'''
        self.ser = serial.Serial('COM6', 38400, timeout=5, write_timeout=10)
        print("Successful")

    def endSerial(self):
        '''Closes serial port'''
        self.ser.close()

    def startTeensy(self, refFreq, sampRate):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        try:
            self.ser.reset_output_buffer()
            self.ser.reset_input_buffer()
            if self.refSelect.get() == 0:  # internal reference selected
                try:
                    refFreq = int(refFreq.get())
                    sampRate = int(sampRate.get())
                    print(refFreq)
                except:
                    return False
                # I think these are currently timing out??? - need to look up why
                try:
                    mode = 1
                    # tell teensy using internal reference frequency, unsure if \n will be written too or not
                    self.ser.write(str(mode).encode('utf-8'))
                    time.sleep(5)
                except:
                    print("writing timed out")
                try:
                    self.ser.write(str(refFreq).encode('utf-8'))
                    time.sleep(5)
                except:
                    print("Writing timed out")
                # need to update top of teensy sketches as well
            elif self.refSelect.get() == 1:  # external reference selected
                mode = 0
                self.ser.write(str(mode).encode('utf-8'))
                time.sleep(5)
            
            #send sampling rate to teensy
            try:
                sampRate = 100000 #just for testing rn
                self.ser.write(str(sampRate).encode('utf-8'))
                time.sleep(5)
            except:
                print("Writing timed out")
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
            while self.ser.in_waiting == 0: #while nothing in serial do nothing
                pass
            while self.ser.in_waiting != 0:  #when things in serial read them all
                data = self.ser.readlines() #NOTE: MAKE SURE THAT DO NOT NEED TO CONVERT FROM BYTES - maybe convert number to string in teensy before printing
            data2D = []
            for i in range(len(data)):
                temp = str(data[i])[2:-1]
                row = temp.split(", ")
                for j in range(len(row)):
                    try:
                        row[j] = float(row[j]) #convert each value to a float
                    except:
                        row[j] = 0.0 #just do this for now, come up with better fix for ovf and inf later
                data2D.append(row) #add the data to rows of 2D list
            #print(data2D)
            dataDf = pd.DataFrame(data2D) #convert to pandas dataframe
            dataDf = dataDf.loc[:, [0,1,2,3,4]] #get only the columns we care about
            #print(dataDf.head())
            dataDf.columns = ["Signal", "I", "Q", "R", "Phi"] #set columns labels
            #plt.tick_params(axis= "x", which = "both", bottom = False, top = False)
            #plt.xticks(dataDf.index, " ")
            fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True) #plot the data
            ax1.plot(dataDf.index, 2*dataDf["R"]*3.3/4096)
            ax1.set_ylabel("Amplitude (V)", fontsize=20)
            ax1.set_title("Lock-in Detection Results", fontsize= 25)
            ax2.plot(dataDf.index, dataDf["Phi"])
            ax2.set_ylabel("Phase (radians)", fontsize=20)
            plt.show()
            print(dataDf.head())
            self.DataDf = dataDf
            return True
        except:
            print("Failed in processData")
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
    #root.geometry("500x400")
    frame = lockInDetection(root)
    frame.grid()
    # maybe change so that different types of elements are grouped in different frames instead of one large frame
    root.mainloop()


if __name__ == '__main__':
    main()
