# teensy_lockin

Perform phase-sensitive detection using a [Teensy 3.5](https://www.pjrc.com/store/teensy35.html) or [Teensy 4.0](https://www.pjrc.com/store/teensy35.html) microcontroller.

## Overview

teensy_lockin uses an analog-to-digital converter on a Teensy microcontroller to digitize a signal of interest and measure the amplitude and phase (relative to a reference signal) of the frequency component of the signal of interest at the reference signal frequency. (See [the following](https://en.wikipedia.org/wiki/Lock-in_amplifier) for an overview of phase-sensitive detection, also known as lock-in detection.) A [graphical user interface](teensy_lockin_gui.py) controls data acquisition.

With a Teensy 3.5, signals are digitized with 12-bit resolution, and phase-sensitive detection can be performed with either an externally-generated reference signal or an internal reference signal generated by the Teensy. With a Teensy 4.0, signals are digitized with 10-bit resolution, and only external reference signals are supported because the Teensy 4.0 has no on-board digital-to-analog converters.

For more details, please see the [documentation](docs/) and [Fung & Weil, *American Journal of Physics* (2023)](https://doi.org/10.1119/5.0126691), which contains extensive test data using a Teensy 3.5.

teensy_lockin has been tested on both Windows and Mac OS.


## Dependencies

* [Teensyduino](https://www.pjrc.com/teensy/teensyduino.html) and the following core libraries installed by default with Teensyduino:
    * [FreqCount](https://www.pjrc.com/teensy/td_libs_FreqCount.html)
    * DMAChannel (for [Teensy 3.5](https://github.com/PaulStoffregen/cores/blob/master/teensy3/DMAChannel.h) or [Teensy 4.0](https://github.com/PaulStoffregen/cores/blob/master/teensy4/DMAChannel.h))
    * [ADC](https://github.com/pedvide/ADC)


* Python 3
* [PySerial](https://github.com/pyserial/pyserial)
* [Pandas](https://pandas.pydata.org/)
* [Matplotlib](https://matplotlib.org/)

Binary executables for the graphical user interface (which could be used without installing Python) are currently not available. If you are interested in binaries, please open an issue.

## Installation and usage

Compile and upload `teensy_lockin.ino` to your Teensy. Make the [hardware connections](docs/hardware.md) you want. Then execute the GUI with

```bash
python teensy_lockin_gui.py
```

For more details on using `teensy_lockin_gui.py`, please see its [documentation](docs/software.md).


## Contributing
Pull requests are welcome. If you would like to make major changes, please discuss first by opening an issue.


## License
[MIT](LICENSE.md)
