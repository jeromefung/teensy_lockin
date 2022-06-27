
/*  FastDifferentialRead
 *
 *   Jerome Fung
 *
 *   Use pedvide ADC library to quickly read the analog input on a Teensy upon button press.
 *   Then write the output to serial (could be read by a program).
 *
 *   The differential pair on T3.5 is A10 and A11.
 *   They're on the back side of the board, but are accessible via through
 *   holes if you solder on
 *   some female header pins.
 *
 *   See
 *   https://github.com/pedvide/ADC/blob/master/examples/analogRead/analogRead.ino
 *   for example.
 *
 *   Currently: we read in the signal and then apply a single-pole low-pass filter
 */

#include <ADC.h>

// Pins
uint8_t buttonPin = 23;
// Connect 1 terminal of NO pushbutton to 23, other terminal to ground
const uint8_t pinP = A10; // Analog pins A10/A11
const uint8_t pinN = A11;

// **************************************************
// Timing and DAQ -- User adjust these

const int measPeriod_us = 1000; // 1 kHz sampling
const int nPts = 2000; // Teensy 3.5 integers are 4-byte; short are 16 bits
const double cutoffFreq = 1.0; // in Hz
// **************************************************

int samplingRate = 1000000 / measPeriod_us ; // in Hz

short myData[nPts];
IntervalTimer myTimer;
ADC *adc = new ADC(); // adc object
volatile bool daqDone = false;
int measCtr = 0;
bool validDiff;

// IIR filter order
const int numCoeffs = 3;
double a[numCoeffs];
double b[numCoeffs];

void setup() {
  // put your setup code here, to run once:
  Serial.begin(38400); // Faster serial connection!
  pinMode(buttonPin, INPUT_PULLUP); // use internal pullup
  pinMode(pinP, INPUT); //Diff Channel 3 Positive
  pinMode(pinN, INPUT); //Diff Channel 3 Negative

  // ADC setup
  //adc->adc0->differentialMode(); // TODO: is this needed? not sure.
  adc->adc0->setResolution(13); // A10, A11 connected to ADC1 only
  adc->adc0->setAveraging(0);
  adc->adc0->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED) ; // changes ADC clock
  adc->adc0->setSamplingSpeed(ADC_SAMPLING_SPEED::LOW_SPEED); // change the sampling speed

  // Wait for button to be pressed
  while (digitalRead(buttonPin) == 1) {
    // do nothing
  }

  validDiff = adc->adc1->checkDifferentialPins(pinP, pinN);
  //Serial.println(validDiff);

  myTimer.begin(measureSignal, measPeriod_us);

  // wait for measurements to complete
  // check flag set by measureSignal()
  while (daqDone == false) {
    // do nothing
  }

  // Now disable timer
  myTimer.end();

  // Print the raw data
  for(int i = 0; i < nPts; i++){
    double temp = myData[i] ;
    Serial.println(temp, 16);
  }
  
  // Print some dividing lines
  for (int i = 0; i < 10; i++){
    Serial.println("Filtered data follows");
  }

  // Calculate coefficients and filter the signal
  calcFilterCoeffs();
  filterSignal();
  
  for (int i = 0; i < 10; i++){
    Serial.println("EOF");
  }
}

// Function called by IntervalTimer
void measureSignal() {
  int result = adc->adc0->analogReadDifferential(pinP, pinN);
  if (measCtr < nPts) {
    myData[measCtr] = (short) result;
    measCtr++;
  }
  else {
    // stop measuring if we fill up the array by setting flag
    daqDone = true;
  }
}

void calcFilterCoeffs() {
  // Currently, implement single-pole recursive filtering. See
  // http://www.dspguide.com/ch19/2.htm
  //double filterX = exp(-2*PI*cutoffFreq/samplingRate);
  //a[0] = 1 - filterX;
  //a[1] = 0;
  //a[2] = 0;
  //b[0] = 0; // Keep 0 for simplicity
  //b[1] = filterX;
  //b[2] = 0;

  // Try a Chebyshev set at f_c/f_sampling = 0.01, which is 10 Hz here.
  a[0] = 8.663387e-4 ;
  a[1] = 1.733678e-3 ;
  a[2] = 8.663387e-4 ;
  b[0] = 0;
  b[1] = 1.919129;
  b[2] = -9.225943e-1;
  
}

void filterSignal(){
  double y_reg[numCoeffs]; //make y registry and preload it with 0's
  // y_reg[0] is 0, y_reg[1] is y[n-1], y_reg[2] is y[n-2], etc.
  // To not initialize with 0, we'd set y_reg to other values here (e.g., first value of input)
  for (int i=0;i<numCoeffs;i++){
    y_reg[i] = 0;
  }

  for (int n=0; n < nPts; n++){
    double yn = 0;
    for (int coeffCtr = 0; coeffCtr < numCoeffs; coeffCtr++){
      yn = yn + a[coeffCtr] * (double) myData[n - coeffCtr] + b[coeffCtr] * y_reg[coeffCtr];
    }
    // Update register, going backwards
    for (int coeffCtr = numCoeffs - 1; coeffCtr > 0; coeffCtr--){
      if (coeffCtr == 1){
        y_reg[coeffCtr] = yn;
      }
      else{
        y_reg[coeffCtr] = y_reg[coeffCtr - 1];
      }
    }
    Serial.println(yn, 16);
  }
}



void loop() {
  // put your main code here, to run repeatedly:
  // Do nothing
}
