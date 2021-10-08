import tkinter as tk
import subprocess
import sys
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
        self.ser = serial.Serial('COM3', 38400, timeout=None)
        self.createWidgets()
        #need to figure out window sizing and placement of widgets

    def createWidgets(self):
        '''Creates all the widgets needed for the GUI'''
        frequencyEntry = tk.Entry(self.parent)
        frequencyEntry.grid(row=4, columnspan=4, sticky=tk.W+tk.E)
        frequencyLabel = tk.Label(self.parent, text="Internal Reference Frequency:")
        frequencyLabel.grid(row=3, columnspan=4, sticky=tk.W+tk.E)

        internalButton = tk.Radiobutton(self.parent, text="Internal Reference", variable=self.refSelect, value=0)
        internalButton.deselect()
        internalButton.grid(row=1, columnspan=4, sticky=tk.W+tk.E)
        externalButton = tk.Radiobutton(self.parent, text="External Reference", variable=self.refSelect, value=1)
        externalButton.deselect()
        externalButton.grid(row=2, columnspan=4, sticky=tk.W+tk.E)

        quitButton = tk.Button(self.parent, text="Quit", command=lambda : self.quitGUI())
        quitButton.grid(row = 5, column=2, columnspan=2, sticky=tk.W+tk.E)

        startButton = tk.Button(self.parent, text="Start", command=lambda : self.startTeensy(frequencyEntry))
        startButton.grid(row = 5, column=0, columnspan=2, sticky=tk.W+tk.E)
    
    def quitGUI(self):
        '''Closes serial port and GUI'''
        self.ser.close()
        self.parent.destroy
    
    def startTeensy(self, refFreq):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        try:
            if self.refSelect.get() == 0: #internal reference selected
                try:
                    refFreq = int(refFreq.get())
                except:
                    return False
                #need to update top of teensy sketches as well
                arduinoFilename = "C:\\Users\\chris\\OneDrive\\Documents\\College\\Spring 2021\\teensy\\teensy_lockin\\LockInInternalReference\\LockInInternalReference.ino"
                self.sendToTeensy(arduinoFilename, refFreq)
            elif self.refSelect.get() == 1: #external reference selected
                arduinoFilename = "C:\\Users\\chris\\OneDrive\\Documents\\College\\Spring 2021\\teensy\\teensy_lockin\\LockInExternalReference\\LockInExternalReference.ino"
                self.sendToTeensy(arduinoFilename)
            self.processData()
            return True
        except:
            print("Failed in startTeensy")
            return False

    def sendToTeensy(self, filename, refFreq=-1):
        '''
        Code is taken from https://forum.arduino.cc/t/upload-sketches-directly-from-geany/286641
        And modified by Chris Weil
        Returns true if sucesesful, false otherwise
        '''
        try:
            print("Uploading...")
            arduinoProg = filename

            projectFile = sys.argv[1]

            codeFile = open(projectFile, 'r')
            startLine = codeFile.readline()[3:].strip()
            actionLine = codeFile.readline()[3:].strip()
            boardLine = codeFile.readline()[3:].strip()
            portLine = codeFile.readline()[3:].strip()
            endLine = codeFile.readline()[3:].strip()
            codeFile.close()

            #~ print projectFile
            #~ print startLine
            #~ print actionLine
            #~ print boardLine
            #~ print portLine
            #~ print endLine

            if (startLine != "python-build-start" or endLine != "python-build-end"):
                print("Sorry, can't process file")
                sys.exit()

            arduinoCommand = arduinoProg + " --" + actionLine + " --board " + boardLine + " --port " + portLine + " " + projectFile

            print("\n\n -- Arduino Command --")
            print(arduinoCommand)

            print("-- Starting %s --\n" %(actionLine))

            presult = subprocess.call(arduinoCommand, shell=True)

            if presult != 0:
                print("\n Failed - result code = %s --" %(presult))
            else:
                print("\n-- Success --")
            
            if refFreq != -1:
                self.ser.write(str(refFreq).encode('utf-8')) #need to update arduino file to read this from serial before doing anything else
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
            ax2.set_ylabel("Phase (radians)")
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