import tkinter as tk
from tkinter import filedialog
import serial
import pandas as pd
import matplotlib.pyplot as plt
import sys
import time

class IORedirector(object):
    '''A general class for redirecting I/O to this Text widget.'''
    def __init__(self,text_area):
        self.text_area = text_area

class StdoutRedirector(IORedirector):
    '''A class for redirecting stdout to this Text widget.'''
    def write(self,str):
        self.text_area.insert(tk.END,str)

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
        r = 1

        #serial port
        serPortLabel = tk.Label(self.parent, text="Serial Port:")
        serPortLabel.grid(row=r, column=0, columnspan=1, sticky=tk.W+tk.E)
        serPort = tk.Entry(self.parent)
        serPort.grid(row=r, column=1, sticky=tk.W+tk.E)
        r += 1

        #change options based off reference mode
        self.frequencyLabel = tk.Label(self.parent, text="Internal Reference Frequency:")
        def internal():
            self.frequencyLabel = tk.Label(self.parent, text="Internal Reference Frequency:")
            self.frequencyLabel.grid(row=freqLabelRow, columnspan=4, sticky=tk.W+tk.E)
        def external():
            self.frequencyLabel = tk.Label(self.parent, text="External Reference Frequency Count Duration (default 5000 ms):")
            self.frequencyLabel.grid(row=freqLabelRow, columnspan=4, sticky=tk.W+tk.E)

        #reference signal
        internalButton = tk.Radiobutton(self.parent, text="Internal Reference", variable=self.refSelect, value=0, command=lambda: internal())
        internalButton.select()
        internalButton.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1
        externalButton = tk.Radiobutton(self.parent, text="External Reference", variable=self.refSelect, value=1, command=lambda: external())
        externalButton.deselect()
        externalButton.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1

        #internal or external ref freq
        self.frequencyLabel.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        freqLabelRow = r
        r += 1
        frequencyEntry = tk.Entry(self.parent)
        frequencyEntry.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1

        #sampling rate
        sampleLabel = tk.Label(self.parent, text="Sampling Rate (default 10,000):") #maybe change to dropdown menu in the future
        sampleLabel.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1
        sampleEntry = tk.Entry(self.parent)
        sampleEntry.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1

        #number of data points
        numPointsLabel = tk.Label(self.parent, text="Number of Points to Measure (default 10,000):")
        numPointsLabel.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1
        numPointsEntry = tk.Entry(self.parent)
        numPointsEntry.grid(row = r, columnspan = 6, sticky=tk.W+tk.E)
        r += 1

        #scale bar for number of points to average
        percentLabel = tk.Label(self.parent, text="Percent of Points used to Average:")
        percentLabel.grid(row = r, column=0, sticky=tk.W+tk.E)
        self.percent = tk.IntVar()
        percentBar = tk.Scale(self.parent, variable=self.percent, from_ = 0, to = 100, orient = tk.HORIZONTAL)
        percentBar.grid(row = r, column=1, sticky=tk.W+tk.E)
        percentBar.set(75)
        r += 1

        #low pass filter
        filterCutoffLabel = tk.Label(self.parent, text="LP Cutoff Freq (default 5):")
        filterCutoffLabel.grid(row=r, column = 0, sticky=tk.W+tk.E)
        filterCutoffEntry = tk.Entry(self.parent)
        filterCutoffEntry.grid(row=r, column=1, sticky=tk.W+tk.E)
        filterStageLabel = tk.Label(self.parent, text="Filter Order:")
        filterStageLabel.grid(row = r, column = 2, sticky=tk.W+tk.E)
        filterStageOptions = [1, 2, 3, 4]
        filterStageSelected = tk.IntVar()
        filterStageSelected.set(1)
        filterStageMenu = tk.OptionMenu(self.parent, filterStageSelected, *filterStageOptions)
        filterStageMenu.grid(row=r, column = 3, sticky=tk.W+tk.E)
        r += 1

        #start button
        startButton = tk.Button(self.parent, text="Run", command=lambda: self.startTeensy(frequencyEntry, sampleEntry, numPointsEntry, filterCutoffEntry, filterStageSelected, 0, serPort))
        startButton.grid(row=r, column=0, columnspan=2, sticky=tk.W+tk.E)
        startButtonFast = tk.Button(self.parent, text="Run Fast Mode", command=lambda: self.startTeensy(frequencyEntry, sampleEntry, numPointsEntry, filterCutoffEntry, filterStageSelected, 1, serPort))
        startButtonFast.grid(row=r, column=2, columnspan=2, sticky=tk.W+tk.E)
        r += 1

        #save button
        saveButton = tk.Button(self.parent, text="Save Data", command=lambda: self.saveData())
        saveButton.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        r += 1

        #output
        output = tk.Text(self.parent)
        output.grid(row=r, columnspan=4, sticky=tk.W+tk.E)
        sys.stdout = StdoutRedirector(output)

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

    def startTeensy(self, refFreqOrDur, sampRate, numPoints, filterCutoff, filterStage, fastMode, serPort):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        try:
            print() #for separation in output
            self.startSerial(serPort) #start the serial port
            self.ser.reset_output_buffer()
            self.ser.reset_input_buffer()
            try:
                sampRate = int(sampRate.get()) #get sample rate
            except:
                sampRate = 10000
            try:
                numPoints = int(numPoints.get())
            except:
                numPoints = 10000
            try:
                filterCutoff = int(filterCutoff.get())
            except:
                filterCutoff = 5
            filterStage = filterStage.get()
            if self.refSelect.get() == 0:  # internal reference selected
                try:
                    refFreqOrDur = int(refFreqOrDur.get())
                except:
                    return False
            else:
                try:
                    refFreqOrDur = int(refFreqOrDur.get())
                except:
                    refFreqOrDur = 5000
            stringToSend = str(self.refSelect.get()) + ":" + str(refFreqOrDur) + ":" + str(sampRate) + ":" + str(numPoints) + ":" + str(filterCutoff) + ":" + str(filterStage) + ":" + str(fastMode) + "F"
            #send data
            try:
                self.ser.write(str(stringToSend).encode('utf-8'))
            except:
                print("writing timed out")
            if fastMode == 0:
                self.processData(numPoints)
            else:
                self.processFastData(numPoints)
            return True
        except:
            print("Failed in startTeensy")
            return False
        
    def processFastData(self, numPoints):
        try:
            while self.ser.in_waiting == 0:
                pass
            
            #again this needs to be tested
            if self.refSelect.get() == 1:
                externalRefFreq = str(self.ser.readline().strip())
                externalRefFreq = externalRefFreq.strip("b'")
                print("Measured External Reference Frequency [Hz]:", externalRefFreq)
            
            d = ''
            while True:
                temp = self.ser.read()
                temp = str(temp)[2:-1]
                if (temp != 'E'):
                    d = d + temp
                else:
                    break
            d = d.split(',')
            print("Average Amplitude:", d[0], "Average Phase:", d[1])            
        except:
            print("Fast Mode Failed")

    def processData(self, numPoints):
        '''
        Processes the data, returns true if successful, false if otherwise
        '''
        try:
            data = []
            count = 0
            while self.ser.in_waiting == 0: #while nothing in serial do nothing
                pass
            
            #unsure if this will work for getting external ref freq - needs to be tested
            if self.refSelect.get() == 1:
                externalRefFreq = str(self.ser.readline().strip())
                externalRefFreq = externalRefFreq.strip("b'")
                print("Measured External Reference Frequency [Hz]:", externalRefFreq)
            
            d = ''
            if numPoints > 100:
                cutoff = numPoints - 100
            else:
                cutoff = numPoints
            #use a timer to prevent infinite loops
            start = time.time()
            while count < cutoff: #expecting 10000 lines of data right now
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
            self.displayAverages()
            return True
        except Exception as e:
            print("Failed in processData")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_type, exc_tb.tb_lineno)
            print(dataDf.head())
            return False

    def displayAverages(self):
        try:
            amplitudeAverage = 0
            phaseAverage = 0
            startIdx = int((self.percent.get() / 100) * len(self.DataDf["R"]))
            for amp in self.DataDf["R"][startIdx:]:
                amplitudeAverage += (2*amp*3.3/4096)
            print("Average Measured Amplitude:", amplitudeAverage/len(self.DataDf["R"][startIdx:]))
            for phase in self.DataDf["Phi"][startIdx:]:
                phaseAverage += phase
            print("Average Measured Phase:", phaseAverage/len(self.DataDf["Phi"][startIdx:]))
        except:
            print("Error in calculating Averages")
    
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
    sys.stdout = sys.__stdout__


if __name__ == '__main__':
    main()
