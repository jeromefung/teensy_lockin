#include <FreqCount.h>
#include <ADC.h>
#include <math.h>

// **************************************************************
// Pin configurations
// NO pushbutton to start operation. Connect 1 terminal to 23, the other to ground.
const uint8_t buttonPin = 23;
// FreqCount library used for frequency measuement requires reference signal
// to be connected to pin 13.
const uint8_t referencePin = 13;

// Connect signal to be measured to analog pins A10/A11 (differential channel 3)
const uint8_t pinP = A10;
const uint8_t pinN = A11;

// **************************************************************

// **************************************************************
// Global variables -- user set
const unsigned long countPeriod_ms = 5000; // Count duration for reference frequency measurement
const int measPeriod_us = 100; // 10 kHz sampling for signal acquisition
const int nPts = 10000;
const int cutoffFreq = 1.0; // for LP filtering, in Hz
// **************************************************************


// **************************************************************
// Other global variables
unsigned long edgeCounts;
double referenceFreq;
int samplingRate = 1000000/measPeriod_us; // in Hz

short mySignal[nPts]; // the raw digitized signal of interest
ADC *adc = new ADC(); // create ADC object
volatile bool daqDone = false;
bool validDiff;
int measCtr = 0;
int refVal, lastVal;

IntervalTimer myTimer;

// LP filter coefficients
const int numCoeffs = 2;
double a[numCoeffs];
double b[numCoeffs]; 
// **************************************************************


void setup() {
  // put your setup code here, to run once:
  Serial.begin(38400);
  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(pinP, INPUT);
  pinMode(pinN, INPUT);

  // ADC setup
  adc->adc0->differentialMode(); // TODO: is this needed? not sure.
  adc->adc0->setResolution(13); // A10, A11 connected to ADC1 only
  adc->adc0->setAveraging(0);
  adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED) ; // changes ADC clock
  adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::LOW_SPEED); // change the sampling speed
  validDiff = adc->adc1->checkDifferentialPins(pinP, pinN);
}

void loop() {
  // put your main code here, to run repeatedly:
  // Wait for button to be pressed
  //while (digitalRead(buttonPin) == 1) {
    // do nothing
  //}
  //Serial.println("Button Pressed");

  delay(1000);

  // Fold out measurement into a function that can be called repeatedly
  measureLockIn();
}

void measureLockIn() {

  // Clear data array
  for (int i = 0; i < nPts; i++) {
    mySignal[i] = 0;
  }

  // Reset flag and signal array index
  daqDone = false;
  measCtr = 0;

  // Measure reference frequency
  FreqCount.begin(countPeriod_ms);
  while (FreqCount.available() == false) {
    // Wait; do nothing
  }
  FreqCount.end();
  edgeCounts = FreqCount.read();
  referenceFreq = edgeCounts / (double) countPeriod_ms * 1000; // convert to get Hz

  // Wait for rising edge of reference signal before starting digitization.
  // Otherwise phase info is meaningless.
  lastVal = digitalRead(referencePin);
  while (true) {
    refVal = digitalRead(referencePin);
    if ((refVal == 1) && (lastVal ==0)) {
      break;
    }
    else{
      lastVal = refVal;
    }
  }
 
  // Digitize the signal
  myTimer.begin(digitizeSignal, measPeriod_us);
  // wait for measurements to complete
  // check flag set by measureSignal()
  while (daqDone == false) {
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
void digitizeSignal() {
  int result = adc->adc0->analogReadDifferential(pinP, pinN);
  if (measCtr < nPts) {
    mySignal[measCtr] = (short) result;
    measCtr++;
  }
  else {
    // stop measuring if we fill up the array by setting flag
    daqDone = true;
  }
}

void calcFilterCoeffs() {
  // Implement 1-stage single-pole recursive filtering
  // See http://www.dspguide.com/ch19/2.htm
  double filterX = exp(-2*PI*cutoffFreq/samplingRate);
  a[0] = 1 - filterX;
  a[1] = 0;
  b[0] = 0; // for simplicity
  b[1] = filterX;
}

void mixAndFilter() {
  // Registers for X and Y channels, default initialized to 0
  double yregX[numCoeffs];
  double yregY[numCoeffs];
  double ynX, ynY, sinTerm, cosTerm, R, phi;

  for (int n=0; n < nPts; n++) {
    ynX = 0;
    ynY = 0;
    for (int coeffCtr = 0; coeffCtr < numCoeffs; coeffCtr++){
      sinTerm = sin(TWO_PI * referenceFreq * (n - coeffCtr) / samplingRate);
      cosTerm = cos(TWO_PI * referenceFreq * (n - coeffCtr) / samplingRate);
      ynX = ynX + a[coeffCtr] * (double) mySignal[n - coeffCtr] * cosTerm  + b[coeffCtr] * yregX[coeffCtr];
      ynY = ynY + a[coeffCtr] * (double) mySignal[n - coeffCtr] * sinTerm  + b[coeffCtr] * yregY[coeffCtr];
    }
    // Update registers, going backwards
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
    // Calculate final values and print
    R = sqrt(ynX*ynX + ynY*ynY);
    phi = atan2(ynY, ynX);
    Serial.print(mySignal[n]);
    Serial.print(", ");
    Serial.print(ynX);
    Serial.print(", ");
    Serial.print(ynY);
    Serial.print(", ");
    Serial.print(R);
    Serial.print(", ");
    Serial.println(phi);
  }
  
}
