/*
 * Sine wave generator using PDB and DMA to reduce CPU usage.
 * 
 * Inspired by https://gist.github.com/samyk/6273cf9a45d63a50c38c8b50a39a8f52
 * and
 * https://www.damianolodi.com/blog/how-to-dma-teensy-3-6-dac-waveforms/
 * 
 * Also, need to consult manual for Kinetis K64 microcontroller in T 3.5 at 
 * https://www.pjrc.com/teensy/K64P144M120SF5RM.pdf
 */
 

// Include LUT
#include "SineLUT.h"
#include <DMAChannel.h>

// from Audio library pdb.h
#define PDB_CONFIG (PDB_SC_TRGSEL(15) | PDB_SC_PDBEN | PDB_SC_CONT | PDB_SC_PDBIE | PDB_SC_DMAEN)

const int analogOutPin = A21;
long sinFreq = 10000; // Hz

DMAChannel dma1(true);

void setup() {
  // put your setup code here, to run once:

  Serial.begin(9600);

  // Set up clock gate for DAC0 (connected to A21)
  // See Sec. 12.2.9 (p. 308) of manual.
  // Also see values defined in kinetis.h
  // Note |= is a C bitwise or
  SIM_SCGC2 |= SIM_SCGC2_DAC0;

  // Enable DAC0
  // See manual p. 912, Sec. 37.4.4 and kinetis.h
  DAC0_C0 = DAC_C0_DACEN | DAC_C0_DACRFS;

  // Teensy Audio library ramps up to DC slowly (I guess this is better than slamming the DAC?)
  // slowly ramp up to DC voltage, approx 1/4 second
  for (int16_t i=0; i<=2048; i+=8) {
    *(int16_t *)&(DAC0_DAT0L) = i;
    delay(1);
  }
  
  // Use Teensy DMAChannel library
  dma1.begin(true);
  dma1.disable(); // disable DMA
  dma1.sourceBuffer(waveTable, LUT_SIZE * sizeof(uint16_t));
  dma1.transferSize(2); // each value is 2 bytes
  dma1.destination(*(volatile uint16_t *)&(DAC0_DAT0L)); // send to DAC
  dma1.triggerAtHardwareEvent(DMAMUX_SOURCE_PDB); // set trigger to PDB
  dma1.enable();

  // Now set up PDB
  SIM_SCGC6 |= SIM_SCGC6_PDB; // Enable PDB clock. Again, see manual and kinetis.h

  // Calculate period between outputs
  uint32_t mod = F_BUS / (sinFreq * LUT_SIZE) ;
  delay(500);
  Serial.println(mod);

  // See manual p. 935, sec 39.3.2 for PDB0_MOD register
  // Modulus of 1 actually means a period of 2 (counter resets back to 0 when it reaches PDB0_MOD)
  PDB0_MOD = (uint16_t)(mod - 1); 
  PDB0_IDLY = 0; // no delay
  PDB0_SC = PDB_CONFIG | PDB_SC_LDOK; // load registers from buffers
  PDB0_SC = PDB_CONFIG | PDB_SC_SWTRIG; // reset and restart
  PDB0_CH0C1 = 0x0101; // Enable pre-trigger
  
}

void loop() {
  // put your main code here, to run repeatedly:
  //Serial.println("Hello world");
  //delay(500);
}
