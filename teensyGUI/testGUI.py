import tkinter as tk
import subprocess
import serial
import pandas as pd
import matplotlib.pyplot as plt

class lockInDetection(tk.Frame):
    '''
    GUI for lock in detection with teensy microcontroller
    Properties:
    parent - the frame object for gui organization
    refSelect - determines if using the internal or external reference frequency (0 for internal, 1 for external)
    ser - the serial connection for communicating with the teensy (unsure if will need to reset it when wanting to run lock in again without closing gui)
    '''
    def __init__(self, parent):
        '''Initialize Frame'''
        tk.Frame.__init__(self, parent)
        self.parent = parent
        self.initialize()
    
    def initialize(self):
        '''Initialize the frame parameters and create their widgets'''
        self.parent.title("Lock in Detector")
        self.refSelect = tk.IntVar()
        self.createWidgets()
        #need to figure out window sizing and placement of widgets

    def createWidgets(self):
        '''Creates all the widgets needed for the GUI'''
        frequencyEntry = tk.Entry(self.parent)
        frequencyEntry.grid(row=5, columnspan=4, sticky=tk.W+tk.E)
        frequencyLabel = tk.Label(self.parent, text="Internal Reference Frequency:")
        frequencyLabel.grid(row=4, columnspan=4, sticky=tk.W+tk.E)

        internalButton = tk.Radiobutton(self.parent, text="Internal Reference", variable=self.refSelect, value=0)
        internalButton.deselect()
        internalButton.grid(row=2, columnspan=4, sticky=tk.W+tk.E)
        externalButton = tk.Radiobutton(self.parent, text="External Reference", variable=self.refSelect, value=1)
        externalButton.deselect()
        externalButton.grid(row=3, columnspan=4, sticky=tk.W+tk.E)

        serStartButton = tk.Button(self.parent, text="Start Serial", command=lambda : self.startSerial())
        serStartButton.grid(row = 1, column=0, columnspan=2, sticky=tk.W+tk.E)

        serEndButton = tk.Button(self.parent, text="Close Serial", command=lambda : self.endSerial())
        serEndButton.grid(row = 1, column=2, columnspan=2, sticky=tk.W+tk.E)

        startButton = tk.Button(self.parent, text="Start", command=lambda : self.startTeensy(frequencyEntry))
        startButton.grid(row = 6, columnspan=4, sticky=tk.W+tk.E)
    
    def startSerial(self):
        '''Opens serial port'''
        self.ser = serial.Serial('COM6', 38400, timeout=None)
    
    def endSerial(self):
        '''Closes serial port'''
        self.ser.close()
    
    def startTeensy(self, refFreq):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        #try:
        if self.refSelect.get() == 0: #internal reference selected
            try:
                refFreq = int(refFreq.get())
            except:
                return False
            #need to update top of teensy sketches as well
            arduinoFilename = "C:\\Users\\chris\\OneDrive\\Documents\\College\\Spring 2021\\teensy\\teensy_lockin\\LockInInternalReference\\LockInInternalReference.ino.TEENSY35.hex"
            self.sendToTeensy(arduinoFilename, refFreq)
        elif self.refSelect.get() == 1: #external reference selected
            arduinoFilename = "C:\\Users\\chris\\OneDrive\\Documents\\College\\Spring 2021\\teensy\\teensy_lockin\\LockInExternalReference\\LockInExternalReference.ino.TEENSY35.hex"
            self.sendToTeensy(arduinoFilename)
        self.processData()
        return True
        #except:
        #    print("Failed in startTeensy")
        #    return False

    def sendToTeensy(self, filename, refFreq=-1):
        try:
            command = "teensy_loader_cli --mcu=mk64fx512 -w " + filename
            subprocess.run(command)
            return True
        
        except:
            print("Failed in sendToTeensy")
            return False

    def processData(self):
        '''
        Processes the data, returns true if successful, false if otherwise
        '''
        try:
            while self.ser.in_waiting != 0: #not sure if this will work
                bytesToRead = self.ser.in_waiting
                data = self.ser.read(bytesToRead)
            rows = data.split("\n")
            data2D = []
            for i in range(len(rows)):
                data2D.append(float(rows[i].split(",")))
            dataDf = pd.DataFrame(data2D, columns = ["Signal", "I", "Q", "R", "Phi"])
            plt.tick_params(axis = "x", which = "both", bottom = False, top = False)
            plt.xticks(dataDf.index, " ")
            fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
            ax1.plot(dataDf.index, 2*dataDf["R"]*3.3/4096)
            ax1.set_ylabel("Amplitude (V)", fontsize=20)
            ax1.set_title("Lock-in Detection Results", fontsize = 25)
            ax2.plot(dataDf.index, dataDf["Phi"])
            ax2.set_ylabel("Phase (radians)", fontsize=20)
            return True
        except:
            print("Failed in processData")
            return False

def main():
    root = tk.Tk()
    lockInDetection(root)
    root.mainloop()

if __name__ == '__main__':
    main()