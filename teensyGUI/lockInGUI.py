import tkinter as tk
from tkinter import filedialog
import serial
import serial.tools.list_ports
import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
import time

class IORedirector(object):
    '''A general class for redirecting I/O to this Text widget.'''
    def __init__(self,text_area):
        self.text_area = text_area

class StdoutRedirector(IORedirector):
    '''A class for redirecting stdout to this Text widget.'''
    def write(self,str):
        self.text_area.insert(tk.END,str)

class LockInDetection(tk.Frame):
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

        # Store some info about the Teensy here
        self.teensy_clock_freq = 120e6 # default 120 MHz
        self.sine_lut_length = 300

    def initialize(self):
        '''Initialize the frame parameters and create their widgets'''
        self.parent.title("Lock in Detector")
        self.refSelect = tk.IntVar()
        self.createWidgets()
        # need to figure out window sizing and placement of widgets

    def createWidgets(self):
        '''Creates all the widgets needed for the GUI'''
        self.createTitleWidgets()
        serialFrame = self.createSerialPortWidgets(tk.Frame(self.parent))
        aquisitionFrame = self.createAquisitionWidgets(tk.Frame(self.parent))
        filterFrame = self.createFilteringWidgets(tk.Frame(self.parent))
        postFrame = self.createPostWidgets(tk.Frame(self.parent))
        buttonFrame = self.createButtonWidgets(tk.Frame(self.parent))
        outFrame = self.createOutWidgets(tk.Frame(self.parent))
        serialFrame.grid(row=2, column = 1, padx = 10)
        aquisitionFrame.grid(row=2, column = 2, padx = 10)
        filterFrame.grid(row=2, column = 3, padx = 10)
        postFrame.grid(row=2, column = 4, padx = 10)
        buttonFrame.grid(row = 3, column = 1, columnspan = 2, padx = 10, pady=20)
        outFrame.grid(row=3, column = 3, columnspan = 2, padx = 10, pady=20)
    
    def createTitleWidgets(self):
        titleFrame = tk.Frame(self.parent)
        serialTitle = tk.Label(titleFrame, text = "Serial Port Settings", font=('Arial', 25))
        serialTitle.grid(row = 1, column = 1)
        titleFrame.grid(row=1, column=1, padx = 10)
        aquisitionFrame = tk.Frame(self.parent)
        aquisitionTitle = tk.Label(aquisitionFrame, text = "Aquisition Settings", font=('Arial', 25))
        aquisitionTitle.grid(row=1, column = 1)
        aquisitionFrame.grid(row=1, column=2, padx = 10)
        filterFrame = tk.Frame(self.parent)
        filterTitle = tk.Label(filterFrame, text = "Filtering Settings", font = ('Arial', 25))
        filterTitle.grid(row = 1, column = 1)
        filterFrame.grid(row=1, column=3, padx=10)
        postFrame = tk.Frame(self.parent)
        postTitle = tk.Label(postFrame, text="Post Processing Settings", font = ('Arial', 25))
        postTitle.grid(row=1, column=1)
        postFrame.grid(row=1, column=4, padx=10)

    def createSerialPortWidgets(self, frame):
        #serial port
        serPortLabel = tk.Label(frame, text="Serial Port:")
        serPortLabel.grid(row=2, column=0)
        self.serPort = tk.Entry(frame)
        self.serPort.grid(row=2, column=1)
        return frame
    
    def createAquisitionWidgets(self, frame):
        r=1
        self.freqDurVal = 1000
        #change options based off reference mode
        frequencyLabel = tk.Label(frame, text="Internal Reference Frequency: " + str(self.freqDurVal))
        def internal(val, d=False):
            self.freqDurVal = val
            frequencyLabel.config(text="Internal Reference Frequency: " + str(self.freqDurVal))
            if d:
                self.frequencyEntry.delete(0, tk.END)
        def external(val, d=False):
            self.freqDurVal = val
            frequencyLabel.config(text="External Reference Frequency Count Duration: " + str(self.freqDurVal))
            if d:
                self.frequencyEntry.delete(0, tk.END)

        #reference signal
        radioFrame = tk.Frame(frame)
        internalButton = tk.Radiobutton(radioFrame, text="Internal Reference", variable=self.refSelect, value=0, command=lambda: internal(1000, True))
        internalButton.select()
        internalButton.grid(row=1, column = 1, columnspan=4)
        externalButton = tk.Radiobutton(radioFrame, text="External Reference", variable=self.refSelect, value=1, command=lambda: external(5000, True))
        externalButton.deselect()
        externalButton.grid(row=1, column = 5, columnspan=4)
        radioFrame.grid(row = r, column=1, columnspan = 4)
        r+=1
        def updateRef(val):
            try:
                val = int(val)
                if self.refSelect.get() == 0:
                    internal(val)
                else:
                    external(val)
            except:
                pass
        #internal or external ref freq
        frequencyLabel.grid(row=r, column = 1, columnspan=4)
        r += 1
        self.frequencyEntry = tk.Entry(frame)
        self.frequencyEntry.grid(row=r, column = 1, columnspan=4)
        self.frequencyEntry.bind("<Return>", lambda event: updateRef(self.frequencyEntry.get()))
        r+=1

        def updateSamp(val):
            try:
                val = int(val)
                self.sampleVal = val
                sampleLabel.config(text="Sampling Rate: " + str(self.sampleVal))
            except:
                pass
        #sampling rate
        self.sampleVal = 10000
        sampleLabel = tk.Label(frame, text="Sampling Rate: " + str(self.sampleVal))
        sampleLabel.grid(row=r, column = 1, columnspan=4)
        r += 1
        self.sampleEntry = tk.Entry(frame)
        self.sampleEntry.grid(row=r, column = 1, columnspan=4)
        self.sampleEntry.bind("<Return>", lambda event: updateSamp(self.sampleEntry.get()))
        r += 1

        def updateNumPoints(val):
            try:
                val = int(val)
                if val > 15000:
                    val = 15000
                self.numPoints = val
                numPointsLabel.config(text="Number of Points to Measure: " + str(self.numPoints))
            except:
                pass
        #number of data points
        self.numPoints = 10000
        numPointsLabel = tk.Label(frame, text="Number of Points to Measure: " + str(self.numPoints))
        numPointsLabel.grid(row=r, column = 1, columnspan=4)
        r += 1
        self.numPointsEntry = tk.Entry(frame)
        self.numPointsEntry.grid(row = r, column = 1, columnspan = 4)
        self.numPointsEntry.bind("<Return>", lambda event: updateNumPoints(self.numPointsEntry.get()))
        return frame

    def createFilteringWidgets(self, frame):
        r=1
        #low pass filter
        def updateCutoff(val):
            try:
                val = int(val)
                self.cutoff = val
                filterCutoffLabel.config(text="Low Pass Cutoff Freq: " + str(self.cutoff))
            except:
                pass
        self.cutoff = 5
        filterCutoffLabel = tk.Label(frame, text="Low Pass Cutoff Freq: " + str(self.cutoff))
        filterCutoffLabel.grid(row=r, column = 1, columnspan=4)
        r+=1
        self.filterCutoffEntry = tk.Entry(frame)
        self.filterCutoffEntry.grid(row=r, column=1, columnspan=4)
        self.filterCutoffEntry.bind("<Return>", lambda event: updateCutoff(self.filterCutoffEntry.get()))
        r+=1
        filterStageLabel = tk.Label(frame, text="Filter Order:")
        filterStageLabel.grid(row = r, column = 2, sticky=tk.W+tk.E)
        filterStageOptions = [1, 2, 3, 4]
        self.filterStageSelected = tk.IntVar()
        self.filterStageSelected.set(1)
        filterStageMenu = tk.OptionMenu(frame, self.filterStageSelected, *filterStageOptions)
        filterStageMenu.grid(row=r, column = 3, sticky=tk.W+tk.E)
        return frame
    
    def createPostWidgets(self, frame):
        self.mode = 0
        normalButton = tk.Radiobutton(frame, text="Normal Mode", variable=self.mode, value=0)
        normalButton.select()
        normalButton.grid(row=1, column = 1)
        fastButton = tk.Radiobutton(frame, text="Fast Mode      ", variable=self.mode, value=1)
        fastButton.deselect()
        fastButton.grid(row=2, column = 1)
        #scale bar for number of points to average
        percentLabel = tk.Label(frame, text="Percent of Points used to Average:")
        percentLabel.grid(row = 1, column=2, columnspan=2, padx = 20)
        self.percent = tk.IntVar()
        percentBar = tk.Scale(frame, variable=self.percent, from_ = 0, to = 100, orient = tk.HORIZONTAL)
        percentBar.grid(row = 2, column=2, columnspan=2)
        percentBar.set(75)
        return frame

    def createButtonWidgets(self, frame):
        #start button
        startButton = tk.Button(frame, text="Run", font=('Arial', 15), width = 10, height = 4, command=lambda: self.startTeensy())
        startButton.grid(row=1, column=1, columnspan = 4, padx = 5)
        #save button
        saveButton = tk.Button(frame, text="Save Data", font=('Arial', 15), width = 10, height = 4, command=lambda: self.saveData())
        saveButton.grid(row=1, column = 5, columnspan = 4, padx = 5)
        return frame

    def createOutWidgets(self, frame):
        #output
        output = tk.Text(frame)
        output.grid(row=1, column = 1, padx = 50)
        sys.stdout = StdoutRedirector(output)
        return frame

    def checkVals(self):
        try:
            val = int(self.frequencyEntry.get())
            if val != self.freqDurVal:
                self.freqDurVal = val
        except:
            pass
        try:
            val = int(self.sampleEntry.get())
            if val != self.sampleVal:
                self.sampleVal = val
        except:
            pass
        try:
            val = int(self.numPointsEntry.get())
            if val > 15000:
                val = 15000
            if val != self.numPoints:
                self.numPoints = val
        except:
            pass
        try:
            val = int(self.filterCutoffEntry.get())
            if val != self.cutoff:
                self.cutoff = val
        except:
            pass

    def startSerial(self):
        '''Opens serial port'''
        try:
            port = self.serPort.get()
        except:
            print("Serial Port Not Specified")
        #port = "COM" + port
        try:
            self.ser = serial.Serial(port, 115200, timeout=None, write_timeout=10)
            if os.name == 'nt':
                # Implemented in Windows only
                self.ser.set_buffer_size(rx_size= 100000, tx_size=4096)
                
            print("Successful")
        except Exception as e:
            print("Could not connect to serial port, " + port)
            print(e)

    def endSerial(self):
        '''Closes serial port'''
        try:
            self.ser.close()
        except:
            print("No serial port open")

    def startTeensy(self):
        '''
        Uploads script to arduino and processes the data recieved
        Returns True if successful and false if not
        '''
        try:
            print("------------------------")
            self.startSerial(self.serPort) #start the serial port
            self.ser.reset_output_buffer()
            self.ser.reset_input_buffer()
            self.checkVals()
            if self.refSelect.get() == 0:  # internal reference selected
                # if internal ref, calculate and display actual frequency
                teensy_clk_periods = int(self.teensy_clock_freq / (self.freqDurVal * self.sine_lut_length)) # corresponds to mod in Teensy code
                actual_freq = self.teensy_clock_freq / (teensy_clk_periods
                                                            * self.sine_lut_length)
                print('Actual frequency: ', actual_freq, ' Hz')
            stringToSend = str(self.refSelect.get()) + ":" + str(self.freqDurVal) + ":" + str(self.sampleVal) + ":" + str(self.numPoints) + ":" + str(self.cutoff) + ":" + str(self.filterStageSelected) + ":" + str(self.mode) + "F"
            print("Instuction Sent:")
            print("Reference Mode: ", end="")
            if self.refSelect.get() == 0:
                print("Internal Reference")
                print("Reference Frequency: ", end="")
            else:
                print("External Reference")
                print("Frequency Count Duration: ", end="")
            print(self.freqDurVal)
            print("Sampling Rate:", self.sampleVal)
            print("Num Points:", self.numPoints)
            print("Filter Cutoff Frequency:", self.cutoff)
            print("Filter Order:", self.filterStageSelected)
            print("Mode: ", end="")
            if self.mode == 0:
                print("Normal Mode")
            else:
                print("Fast Mode")
            
            #send data
            try:
                self.ser.write(str(stringToSend).encode('utf-8'))
            except:
                print("writing timed out")
            
            if self.mode == 0:
                self.processData(self.numPoints)
            else:
                self.processFastData(self.numPoints)
            return True
        except:
            print("Failed in startTeensy")
            return False
        
    def processFastData(self):
        try:
            waitctr = 0
            while self.ser.in_waiting == 0:
                waitctr += 1

            print(waitctr)
            
            #again this needs to be tested
            if self.refSelect.get() == 1:
                externalRefFreq = str(self.ser.readline().strip())
                externalRefFreq = externalRefFreq.strip("b'")
                print("Measured External Reference Frequency [Hz]:", externalRefFreq)
            
            d = ''
            start = time.time()
            while True:
                temp = self.ser.read()
                temp = str(temp)[2:-1]
                if (temp != 'E'):
                    d = d + temp
                else:
                    break
                if (time.time()-start > 30): #prevent infinite loop
                    break
            d = d.split(',')
            print("Average Amplitude:", d[0], "Average Phase:", d[1])
            self.endSerial()
        except Exception as e:
            print(waitctr)
            print("Fast Mode Failed")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            print(e, exc_type, exc_tb.tb_lineno)

    def processData(self):
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
            if self.numPoints > 100:
                cutoff = self.numPoints - 100
            else:
                cutoff = self.numPoints
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
    port_list = list(serial.tools.list_ports.comports())
    for port in port_list:
        print(port)
    root = tk.Tk()
    frame = LockInDetection(root)
    frame.grid()
    root.mainloop()
    sys.stdout = sys.__stdout__


if __name__ == '__main__':
    main()
