import serial #this looks like it is reading things correctly, therefore there is an issue with the serial send and read
import pandas as pd
import matplotlib.pyplot as plt

ser = serial.Serial('COM6', 38400, timeout=5, write_timeout=10)

while ser.in_waiting == 0:
    pass
while ser.in_waiting != 0:  # not sure if this will work
    data = ser.readlines()
    data2D = []
    for i in range(len(data)):
        temp = str(data[i])[2:-1]
        row = temp.split(", ")
        for j in range(len(row)):
            try:
                row[j] = float(row[j])
            except:
                # just do this for now, come up with better fix for ovf and inf later
                row[j] = 0.0
        data2D.append(row)
    dataDf = pd.DataFrame(data2D)
    dataDf = dataDf.loc[:, [0, 1, 2, 3, 4]]
    print(dataDf)
    dataDf.columns = ["Signal", "I", "Q", "R", "Phi"]
    # plt.tick_params(axis= "x", which = "both", bottom = False, top = False)
    # plt.xticks(dataDf.index, " ")
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
    ax1.plot(dataDf.index, 2*dataDf["R"]*3.3/4096)
    ax1.set_ylabel("Amplitude (V)", fontsize=20)
    ax1.set_title("Lock-in Detection Results", fontsize=25)
    ax2.plot(dataDf.index, dataDf["Phi"])
    ax2.set_ylabel("Phase (radians)", fontsize=20)
    plt.show()
    print(sum(2*dataDf["R"]*3.3/4096)/len(dataDf["R"]))
ser.close()