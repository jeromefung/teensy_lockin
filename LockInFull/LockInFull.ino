#include "SineLUT.h"
#include <DMAChannel.h>
#include <ADC.h>
#include <math.h>
#include <FreqCount.h>

// from Audio library pdb.h
#define PDB_CONFIG (PDB_SC_TRGSEL(15) | PDB_SC_PDBEN | PDB_SC_CONT | PDB_SC_PDBIE | PDB_SC_DMAEN)

// **************************************************************
// Pin configurations
// Connect signal to be measured to analog pins A10/A11 (differential channel 3)
const uint8_t pinP = A10;
const uint8_t pinN = A11;

// **************************************************************

// **************************************************************
// Global variables -- user set
const unsigned long countPeriod_ms = 5000; // Count duration for reference frequency measurement
const int measPeriod_us = 100; // 10 kHz sampling for signal acquisition
const int nPts = 10000;
const int cutoffFreq = 1.0;                   // for LP filtering, in Hz
// **************************************************************

// **************************************************************
// Other global variables
unsigned long edgeCounts;
int samplingRate = 1000000 / measPeriod_us; // in Hz
const int analogOutPin = A21;
long sinFreq;
int referenceFreq;

short mySignal[nPts]; // the raw digitized signal of interest
ADC *adc = new ADC(); // create ADC object
volatile bool daqDone = false;
bool validDiff;
int measCtr = 0;
int refVal, lastVal;

const int numInstructChars = 32; //number of characters in each instruction sent to arduino
char instruct[numInstructChars]; //array to store instruction in

IntervalTimer myTimer;

DMAChannel dma1(true);

// LP filter coefficients
const int numCoeffs = 2;
double a[numCoeffs];
double b[numCoeffs];
// **************************************************************

void setup()
{
    // put your setup code here, to run once:
    Serial.begin(38400);
    pinMode(pinP, INPUT);
    pinMode(pinN, INPUT);

    // ADC setup
    adc->adc0->differentialMode(); // TODO: is this needed? not sure.
    adc->adc0->setResolution(13);  // A10, A11 connected to ADC1 only
    adc->adc0->setAveraging(0);
    adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED); // changes ADC clock
    adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::LOW_SPEED);      // change the sampling speed
    validDiff = adc->adc1->checkDifferentialPins(pinP, pinN);
    delay(1000);
}

void loop()
{
  Serial.flush(); //clear the input and output serial buffers
  serialFlush();

  while(!Serial.available()){} //wait for instruction to be sent
  char receivedChar;
  int index = 0;
  while(Serial.available() && receivedChar != "F"){
    receivedChar = Serial.read();
    instruct[index] = receivedChar;
    index++;
  }

  //interpret the instruction
  char* com = strtok(instruct, ":");
  if (com == "0"){ //if internal reference
    com = strtok(NULL, ":");
    sinFreq = (long) atoi(com);
    com = strtok(NULL, "F");
    samplingRate = atoi(com);
    referenceFreq = (double) sinFreq;
    generateReferenceWave();
  }
  else{
    com = strtok(NULL, "F");
    samplingRate = atoi(com);
  }
  delay(1000);

  measureLockIn(); //function to do lock in calculations and send data back to computer
}

void serialFlush(){
  while(Serial.available() > 0) {
    char t = Serial.read();
  }
}

void generateReferenceWave()
{

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
    for (int16_t i = 0; i <= 2048; i += 8)
    {
        *(int16_t *)&(DAC0_DAT0L) = i;
        delay(1);
    }

    // Use Teensy DMAChannel library
    dma1.begin(true);
    dma1.disable(); // disable DMA
    dma1.sourceBuffer(waveTable, LUT_SIZE * sizeof(uint16_t));
    dma1.transferSize(2);                                  // each value is 2 bytes
    dma1.destination(*(volatile uint16_t *)&(DAC0_DAT0L)); // send to DAC
    dma1.triggerAtHardwareEvent(DMAMUX_SOURCE_PDB);        // set trigger to PDB
    dma1.enable();

    // Now set up PDB
    SIM_SCGC6 |= SIM_SCGC6_PDB; // Enable PDB clock. Again, see manual and kinetis.h

    // Calculate period between outputs
    uint32_t mod = F_BUS / (sinFreq * LUT_SIZE);
    delay(500);
    //Serial.println(mod);

    // See manual p. 935, sec 39.3.2 for PDB0_MOD register
    // Modulus of 1 actually means a period of 2 (counter resets back to 0 when it reaches PDB0_MOD)
    PDB0_MOD = (uint16_t)(mod - 1);
    PDB0_IDLY = 0;                        // no delay
    PDB0_SC = PDB_CONFIG | PDB_SC_LDOK;   // load registers from buffers
    PDB0_SC = PDB_CONFIG | PDB_SC_SWTRIG; // reset and restart
    PDB0_CH0C1 = 0x0101;                  // Enable pre-trigger
}

void measureLockIn()
{

    // Clear data array
    for (int i = 0; i < nPts; i++)
    {
        mySignal[i] = 0;
    }

    // Reset flag and signal array index
    daqDone = false;
    measCtr = 0;

    // Digitize the signal
    myTimer.begin(digitizeSignal, measPeriod_us);
    // wait for measurements to complete
    // check flag set by measureSignal()
    while (daqDone == false)
    {
        // do nothing
    }
    // Now disable timer
    myTimer.end();

    // Set up filter coefficients
    calcFilterCoeffs();

    // Mix and filter the signal, a point at a time
    mixAndFilter();
}

// Function called by IntervalTimer
void digitizeSignal()
{
    int result = adc->adc0->analogReadDifferential(pinP, pinN);
    if (measCtr < nPts)
    {
        mySignal[measCtr] = (short)result;
        measCtr++;
    }
    else
    {
        // stop measuring if we fill up the array by setting flag
        daqDone = true;
    }
}

void calcFilterCoeffs()
{
    // Implement 1-stage single-pole recursive filtering
    // See http://www.dspguide.com/ch19/2.htm
    double filterX = exp(-2 * PI * cutoffFreq / samplingRate);
    a[0] = 1 - filterX;
    a[1] = 0;
    b[0] = 0; // for simplicity
    b[1] = filterX;
}

void mixAndFilter()
{
    // Registers for X and Y channels, default initialized to 0
    double yregX[numCoeffs];
    double yregY[numCoeffs];
    double ynX, ynY, sinTerm, cosTerm, R, phi;

    for (int n = 0; n < nPts; n++)
    {
        ynX = 0;
        ynY = 0;
        for (int coeffCtr = 0; coeffCtr < numCoeffs; coeffCtr++)
        {
            sinTerm = sin(TWO_PI * referenceFreq * (n - coeffCtr) / samplingRate);
            cosTerm = cos(TWO_PI * referenceFreq * (n - coeffCtr) / samplingRate);
            ynX = ynX + a[coeffCtr] * (double)mySignal[n - coeffCtr] * sinTerm + b[coeffCtr] * yregX[coeffCtr];
            ynY = ynY + a[coeffCtr] * (double)mySignal[n - coeffCtr] * cosTerm + b[coeffCtr] * yregY[coeffCtr];
        }
        // Update registers, going backwards
        for (int coeffCtr = numCoeffs - 1; coeffCtr > 0; coeffCtr--)
        {
            if (coeffCtr == 1)
            {
                yregX[coeffCtr] = ynX;
                yregY[coeffCtr] = ynY;
            }
            else
            {
                yregX[coeffCtr] = yregX[coeffCtr - 1];
                yregY[coeffCtr] = yregY[coeffCtr - 1];
            }
        }
        // Calculate final values and print
        R = sqrt(ynX * ynX + ynY * ynY);
        phi = atan2(ynY, ynX);
        Serial.print(mySignal[n]);//print data to serial
        Serial.print(", ");
        Serial.print(ynX);//in phase
        Serial.print(", ");
        Serial.print(ynY);//quadrature
        Serial.print(", ");
        Serial.print(R); // amplitude - will be 0.5 as much as input amplitude
        Serial.print(", ");
        Serial.println(phi); // phase
    }
}
