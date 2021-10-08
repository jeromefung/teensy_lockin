import tkinter as tk
import subprocess
import sys
import serial

'''
Notes:
need to create a widget then attach it, always use those two steps
'''

class lockInDetection(tk.Frame):
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
        frequencyEntry.grid(row=4, columnspan=4, sticky=tk.W+tk.E)
        frequencyLabel = tk.Label(self.parent, text="Internal Reference Frequency:")
        frequencyLabel.grid(row=3, columnspan=4, sticky=tk.W+tk.E)

        internalButton = tk.Radiobutton(self.parent, text="Internal Reference", variable=self.refSelect, value=0)
        internalButton.deselect()
        internalButton.grid(row=1, columnspan=4, sticky=tk.W+tk.E)
        externalButton = tk.Radiobutton(self.parent, text="External Reference", variable=self.refSelect, value=1)
        externalButton.deselect()
        externalButton.grid(row=2, columnspan=4, sticky=tk.W+tk.E)

        quitButton = tk.Button(self.parent, text="Quit", command=self.parent.destroy)
        quitButton.grid(row = 5, column=2, columnspan=2, sticky=tk.W+tk.E)

        startButton = tk.Button(self.parent, text="Start", command=lambda : self.startArduino(frequencyEntry))
        startButton.grid(row = 5, column=0, columnspan=2, sticky=tk.W+tk.E)
    
    def startArduino(self, refFreq):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        if self.refSelect.get() == 0: #internal reference selected
            try:
                refFreq = int(refFreq.get())
            except:
                return False
            #need to figure out how to send refFreq to arduino (maybe through serial?)
            #need to update top of teensy sketches as well
            filename = "C:\\Users\\chris\\OneDrive\\Documents\\College\\Spring 2021\\teensy\\teensy_lockin\\LockInInternalReference\\LockInInternalReference\\LockInInternalReference.ino"
            self.sendToArduino(filename, refFreq)
        elif self.refSelect.get() == 1: #external reference selected
            filename = "C:\\Users\\chris\\OneDrive\\Documents\\College\\Spring 2021\\teensy\\teensy_lockin\\LockInExternalReference\\LockInExternalReference.ino"
            self.sendToArduino(filename)
        self.processData()
        return True

    def sendToArduino(self, filename, refFreq=-1):
        '''
        Code is taken from https://forum.arduino.cc/t/upload-sketches-directly-from-geany/286641
        And modified by Chris Weil
        '''
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
            ser.write(str(refFreq).encode()) #make sure that this is correct

    def processData(self):
        data = ser.readline()
        return None

def main():
    global ser
    ser = serial.Serial('COM3', 38400)
    root = tk.Tk()
    lockInDetection(root)
    root.mainloop()

if __name__ == '__main__':
    main()