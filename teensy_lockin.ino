#include "src/SineLUT.h"
#include <DMAChannel.h>
#include <ADC.h>
#include <math.h>
#include <FreqCount.h>

// from Audio library pdb.h
#define PDB_CONFIG (PDB_SC_TRGSEL(15) | PDB_SC_PDBEN | PDB_SC_CONT | PDB_SC_PDBIE | PDB_SC_DMAEN)

// for restarting teensy
#define RESTART_ADDR       0xE000ED0C
#define READ_RESTART()     (*(volatile uint32_t *)RESTART_ADDR)
#define WRITE_RESTART(val) ((*(volatile uint32_t *)RESTART_ADDR) = (val))

// **************************************************************
// Pin configurations

// Teensy 3.5:
//    FreqCount reads pin 13 for external reference
//    Differential inputs A10/A11
// Teensy 4.0
//    FreqCount reads pin 9 for external reference
//    No differential input, use A0 (digital 14)

#if defined(ARDUINO_TEENSY40) //
  const uint8_t referencePin = 9;
  const uint8_t pinP = A0;
  const uint8_t pinN;
#else // Assume T3.5.
  const uint8_t referencePin = 13;
  // Connect signal to be measured to analog pins A10/A11 (differential channel 3)
  const uint8_t pinP = A10;
  const uint8_t pinN = A11;
#endif

// **************************************************************

// **************************************************************
// Global variables -- user set
// Note: FreqCount on T4.0 uses count period in microsceconds
unsigned long countPeriod_ms = 5000; // Count duration for reference frequency measurement
const int maxPts = 50000;
int nPts = 10000;
int cutoffFreq; // = 5.0; // for LP filtering, in Hz
// **************************************************************

// **************************************************************
// Other global variables
unsigned long edgeCounts;
int samplingRate; //in Hz
int measPeriod_us;
// Only T3.5 has analog out. T4.0 doesn't have A21 at all.
#if defined(ARDUINO_TEENSY40)
  const int analogOutPin;
#else  
  const int analogOutPin = A21;
#endif

long sinFreq;
double referenceFreq;
int filterPole;
int fastMode;

short mySignal[maxPts]; // the raw digitized signal of interest
ADC *adc = new ADC(); // create ADC object
volatile bool daqDone = false;
bool validDiff;
int measCtr = 0;
int refVal, lastVal;

const int numInstructChars = 32; // number of characters in each instruction sent to arduino
char instruct[numInstructChars]; // array to store instruction in
bool externalFlag;

IntervalTimer myTimer;

DMAChannel dma1(true);

// LP filter coefficients
const int numCoeffs = 5;
double a[numCoeffs];
double b[numCoeffs];
// **************************************************************

void setup()
{
    // put your setup code here, to run once:
    Serial.begin(38400);
    
    //pinMode(LED_BUILTIN, OUTPUT);
    #if defined(ARDUINO_TEENSY35)
        pinMode(pinP, INPUT);
        pinMode(pinN, INPUT);
    #else // T4.0
        // See forum discussions:
        // https://forum.pjrc.com/threads/34319-Analog-input-impedance-and-pull-up
        // https://forum.pjrc.com/threads/69671-Teensy-4-0-4-1-web-pages-need-a-warning-about-INPUT_DISABLE-on-Analog-Inputs
        pinMode(pinP, INPUT_DISABLE);
    #endif

    // ADC setup 
    #if defined(ARDUINO_TEENSY40)
      adc->adc0->setResolution(10);
    #else
      adc->adc0->differentialMode(); // TODO: is this needed? not sure.
      adc->adc0->setResolution(13);  // A10, A11 connected to ADC1 only
      validDiff = adc->adc1->checkDifferentialPins(pinP, pinN);
    #endif
    adc->adc0->setAveraging(0);
    adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED); // changes ADC clock
    adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::LOW_SPEED);      // change the sampling speed
  
     
    //get instruction from computer, program will not do anything until it knows what it needs to do
    while (!Serial.available())
    {
    } // wait for instruction to be sent
    char receivedChar;
    int index = 0;

    int maxWait = 0;

    while (Serial.available() && receivedChar != "F")
    {
        receivedChar = Serial.read();
        instruct[index] = receivedChar;
        index++;
    }

    // interpret the instruction
    char *com = strtok(instruct, ":");
    if (*com == '0')
    { // if internal reference
        externalFlag = false;
        com = strtok(NULL, ":");
        sinFreq = (long)atoi(com);
    }
    else
    {
        externalFlag = true;
        com = strtok(NULL, ":");
        countPeriod_ms = (unsigned long)atoi(com);
    }
    com = strtok(NULL, ":");
    samplingRate = atoi(com);
    com = strtok(NULL, ":");
    nPts = atoi(com);
    com = strtok(NULL, ":");
    cutoffFreq = atoi(com);
    com = strtok(NULL, ":");
    filterPole = atoi(com);
    com = strtok(NULL, "F");
    fastMode = atoi(com);

    if (!externalFlag)
    {
        //referenceFreq = (double)sinFreq;
        generateReferenceWave();
    }
    measPeriod_us = 1000000 / samplingRate;
    if (nPts > maxPts){
        nPts = maxPts;
    }
 
    measureLockIn();

    // Need to wait until host computer is able to read transmitted data
    // Set a max waiting time
    // Reset if max waiting time exceeded OR host signals successful read

    if (fastMode == 1){
      maxWait = 5000;
    }
    else{
      maxWait = nPts + 5000;
    }

    index = 0;
    elapsedMillis transmit_wait;

    while (transmit_wait < maxWait){
      if (Serial.available()) {
        receivedChar = Serial.read();
      }
      
      if (receivedChar == 'X') {
          break;
      }
    }
    
    WRITE_RESTART(0x5FA0004);
}

void loop()
{
}

void generateReferenceWave()
{
#if defined(ARDUINO_TEENSY35)
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
    // dma1.enable(); // Don't enable sine output until start of measurements

    // Now set up PDB
    SIM_SCGC6 |= SIM_SCGC6_PDB; // Enable PDB clock. Again, see manual and kinetis.h

    // Calculate period between outputs
    uint32_t mod = F_BUS / (sinFreq * LUT_SIZE);

    // Calculate actual frequency used
    referenceFreq = F_BUS / double(mod * LUT_SIZE) ;
    
    delay(500);
    // Serial.println(mod);

    // See manual p. 935, sec 39.3.2 for PDB0_MOD register
    // Modulus of 1 actually means a period of 2 (counter resets back to 0 when it reaches PDB0_MOD)
    PDB0_MOD = (uint16_t)(mod - 1);
    PDB0_IDLY = 0;                        // no delay
    PDB0_SC = PDB_CONFIG | PDB_SC_LDOK;   // load registers from buffers
    PDB0_SC = PDB_CONFIG | PDB_SC_SWTRIG; // reset and restart
    PDB0_CH0C1 = 0x0101;                  // Enable pre-trigger
#endif
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

    // Wait for rising edge of reference signal before starting digitization.
    // Otherwise phase info is meaningless.
    if(externalFlag){
      // Measure reference frequency
        #if defined(ARDUINO_TEENSY40) // T4.0 uses period in microseconds
          FreqCount.begin(countPeriod_ms * 1000);
        #else 
          FreqCount.begin(countPeriod_ms);
        #endif
        while (FreqCount.available() == false) {
            // Wait; do nothing
        }
        FreqCount.end();
        edgeCounts = FreqCount.read();
        referenceFreq = edgeCounts / (double) countPeriod_ms * 1000; // convert to get Hz
      //lastVal = digitalRead(referencePin);
      //while (true) {
      //  refVal = digitalRead(referencePin);
      //  if ((refVal == 1) && (lastVal ==0)) {
      //    break;
      //  }
      //  else{
      //    lastVal = refVal;
      //  }
      //}

      // use interrupt for precise timing of start of measurements
      attachInterrupt(digitalPinToInterrupt(referencePin), extMeasISR, RISING);
      
    }
    else { // internal reference mode
        dma1.enable();
        digitizeSignal();
        myTimer.begin(digitizeSignal, measPeriod_us); // digitize
    }

    // Digitize the signal
    //myTimer.begin(digitizeSignal, measPeriod_us);
    
    // wait for measurements to complete
    // check flag set by measureSignal()
    while (daqDone == false)
    {
        // do nothing
    }
    // Now disable timer
    myTimer.end();

    // Calculate the actual frequency used 
    if (!externalFlag)
    {
        
    }

    // Set up filter coefficients
    if (filterPole == 1){
        calcFilterCoeffs();
    }
    else if (filterPole == 2){
        calcFilterCoeffs2p();
    }
    else if (filterPole == 3){
        // for 3rd stage - 
        calcFilterCoeffs3p();
    }
    else{
        // for 4th stage - 
        calcFilterCoeffs4p();
    }

    // Display measured external reference right before mixing and filtering
    if (externalFlag){
        Serial.println(referenceFreq);
    }

    // Mix and filter the signal, a point at a time
    if (fastMode == 1){
        mixAndFilterFast();
    }
    else{
        mixAndFilter();
    }
}

// Start digitizing signal on rising edge of external reference signal
void extMeasISR() {
  detachInterrupt(digitalPinToInterrupt(referencePin));
  digitizeSignal();
  myTimer.begin(digitizeSignal, measPeriod_us);  
}

// Function called by IntervalTimer
void digitizeSignal()
{
    #if defined(ARDUINO_TEENSY35)
        int result = adc->adc0->analogReadDifferential(pinP, pinN); // 
    #else
        int result = adc->adc0->analogRead(pinP);
    #endif
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

void calcFilterCoeffs2p()
{
    // Implement 2-stage single-pole recursive filtering
    // See http://www.dspguide.com/ch19/2.htm
    double filterX = exp(-2 * PI * cutoffFreq / samplingRate);
    a[0] = pow(1 - filterX, 2);
    a[1] = 0;
    a[2] = 0;
    b[0] = 0; // for simplicity
    b[1] = 2 * filterX;
    b[2] = -pow(filterX, 2);
}


void mixAndFilterFast(){
    //n_pts already exists in variable nPts
    //do not need y since just print to serial
    //n_coeffs already exists in numCoeffs
    //x is signal, a is a, b is b
    
    //make a register for i and qthat is the number of coefficients long
    //need to preload with zeros

    //need to make variables to store averages in
    double rAvg = 0.0;
    double pAvg = 0.0;

    double yregX[numCoeffs];
    double yregY[numCoeffs];
    for (int i = 0; i < numCoeffs; i++){
        yregX[i] = 0.0;
        yregY[i] = 0.0;
    }

    //create sum variables and sine and cosine terms
    double ynX;
    double ynY;
    //need to loop over the number of points
    for (int n = numCoeffs - 1; n < nPts; n++){
        //need to initialize the sums
        ynX = 0;
        ynY = 0;
        double sinTerm;
        double cosTerm;
        //now loop over coefficients - need to multiply the signal by sine and cosine
        //need to figure out padding - from python - pad input circularly (e.g., x[-1]), and assume output y is initially 0.
        //what if start from n = 1 (or more generally numCoeffs - 1), output is already initialized to be 0
        for (int coeffCtr = 0; coeffCtr < numCoeffs; coeffCtr++){
            sinTerm = sin(2 * PI * referenceFreq * ((n - coeffCtr) / ((double)samplingRate)));
            cosTerm = cos(2 * PI * referenceFreq * ((n - coeffCtr) / ((double)samplingRate)));
            ynX = ynX + a[coeffCtr] * (double)mySignal[n - coeffCtr] * sinTerm + b[coeffCtr] * yregX[coeffCtr];
            ynY = ynY + a[coeffCtr] * (double)mySignal[n - coeffCtr] * cosTerm + b[coeffCtr] * yregY[coeffCtr];
        }

        //print output
        double R;
        double phi;
        R = sqrt(ynX * ynX + ynY * ynY);
        phi = atan2(ynY, ynX);

        rAvg = rAvg + R; //need to figure out a way to not add the first few points
        pAvg = pAvg + phi;

        //update registers by shifting yreg[n] to yreg[n+1]
        //this will need to be changed if we ever use more than 2 coeffs
        for (int coeffCtr = numCoeffs - 1; coeffCtr > 0; coeffCtr--){
            if (coeffCtr == 1){
                yregX[coeffCtr] = ynX;
                yregY[coeffCtr] = ynY;
            }
            else{
                yregX[coeffCtr] = yregX[coeffCtr - 1];
                yregY[coeffCtr] = yregY[coeffCtr - 1];
            }
        }
    }

    rAvg = rAvg / ((double)nPts);
    pAvg = pAvg / ((double)nPts);

    Serial.print(rAvg);
    Serial.print(", ");
    Serial.print(pAvg);
    Serial.print("E");

}


void calcFilterCoeffs3p()
{
    double filterX = exp(-2 * PI * cutoffFreq / samplingRate);  
    a[0] = pow(1 - filterX, 3);
    a[1] = 0;
    a[2] = 0;
    a[3] = 0;
    b[0] = 0;
    b[1] = 3 * filterX;
    b[2] = -3 * pow(filterX, 2);
    b[3] = pow(filterX, 3);
}

void calcFilterCoeffs4p()
{
    double filterX = exp(-2 * PI * cutoffFreq / samplingRate);  
    a[0] = pow(1 - filterX, 4);
    a[1] = 0;
    a[2] = 0;
    a[3] = 0;
    a[4] = 0;
    b[0] = 0;
    b[1] = 4 * filterX;
    b[2] = -6 * pow(filterX, 2);
    b[3] = 4 * pow(filterX, 3);
    b[4] = -pow(filterX, 4);
}


void mixAndFilter()
{   

    //n_pts already exists in variable nPts
    //do not need y since just print to serial
    //n_coeffs already exists in numCoeffs
    //x is signal, a is a, b is b
    
    //make a register for i and qthat is the number of coefficients long
    //need to preload with zeros
    double yregX[numCoeffs];
    double yregY[numCoeffs];
    for (int i = 0; i < numCoeffs; i++){
        yregX[i] = 0.0;
        yregY[i] = 0.0;
    }

    //create sum variables and sine and cosine terms
    double ynX;
    double ynY;
    //need to loop over the number of points
    for (int n = numCoeffs - 1; n < nPts; n++){
        //need to initialize the sums
        ynX = 0;
        ynY = 0;
        double sinTerm;
        double cosTerm;
        //now loop over coefficients - need to multiply the signal by sine and cosine
        //need to figure out padding - from python - pad input circularly (e.g., x[-1]), and assume output y is initially 0.
        //what if start from n = 1 (or more generally numCoeffs - 1), output is already initialized to be 0
        for (int coeffCtr = 0; coeffCtr < numCoeffs; coeffCtr++){
            sinTerm = sin(2 * PI * referenceFreq * ((n - coeffCtr) / ((double)samplingRate)));
            cosTerm = cos(2 * PI * referenceFreq * ((n - coeffCtr) / ((double)samplingRate)));
            ynX = ynX + a[coeffCtr] * (double)mySignal[n - coeffCtr] * sinTerm + b[coeffCtr] * yregX[coeffCtr];
            ynY = ynY + a[coeffCtr] * (double)mySignal[n - coeffCtr] * cosTerm + b[coeffCtr] * yregY[coeffCtr];
        }

        //print output
        double R;
        double phi;
        R = sqrt(ynX * ynX + ynY * ynY);
        phi = atan2(ynY, ynX);
        Serial.print(mySignal[n]); // print data to serial
        Serial.print(", ");
        Serial.print(ynX); // in phase
        Serial.print(", ");
        Serial.print(ynY); // quadrature
        Serial.print(", ");
        Serial.print(R); // amplitude - will be 0.5 as much as input amplitude
        Serial.print(", ");
        Serial.print(phi); // phase
        Serial.print("E");

        //update registers by shifting yreg[n] to yreg[n+1]
        //this will need to be changed if we ever use more than 2 coeffs
        for (int coeffCtr = numCoeffs - 1; coeffCtr > 0; coeffCtr--){
            if (coeffCtr == 1){
                yregX[coeffCtr] = ynX;
                yregY[coeffCtr] = ynY;
            }
            else{
                yregX[coeffCtr] = yregX[coeffCtr - 1];
                yregY[coeffCtr] = yregY[coeffCtr - 1];
            }
        }
        delayMicroseconds(150);
    }
}
