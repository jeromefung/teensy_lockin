'''
Calculate LUT for a sine for 12-bit DAC output on Teensy 3.5.

The bus clock for this 120 MHz processor is 60 MHz. (See cores/kinetis.h in the 
Teensy core library.)
Having 300 samples means that a 100 kHz sine wave ges triggered every 2 
bus clocks.

Since output ranges from 0 - 4095, center the output at 2048.
Put the amplitude at 2047 so we don't clip.
'''

import numpy as np
from numpy import sin, arange, pi

N_samples = 300
idx = np.arange(N_samples)
amplitude = 2047
offset = 2048

vals = np.rint(sin(idx / N_samples * 2 * pi) * amplitude + offset).astype(int)
print(vals.dtype)
# reshape to be less clunky for humans to read, 10 cols separated by commas
vals = vals.reshape((-1, 10))
np.savetxt('sine_lut.txt', vals, fmt = '%d', delimiter = ',', newline = ',\n')

