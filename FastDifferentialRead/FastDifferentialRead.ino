
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
 */

#include <ADC.h>


// Pins
uint8_t buttonPin = 23; 
// Connect 1 terminal of NO pushbutton to 23, other terminal to ground
const uint8_t pinP = A10; // Analog pins A10/A11
const uint8_t pinN = A11;

// timing and DAQ
int measPeriod_us = 10; // 50 kHz sampling
const int nPts = 100000; // Teensy 3.5 integers are 4-byte; short are 16 bits
short myData[nPts];
IntervalTimer myTimer;
ADC *adc = new ADC(); // adc object

volatile bool daqDone = false;
int measCtr = 0;
bool validDiff;

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
  //while (digitalRead(buttonPin) == 1) {
    // do nothing
  //}
  delay(10000); //button is broken :(

  validDiff = adc->adc1->checkDifferentialPins(pinP, pinN);
  Serial.println(validDiff);

  myTimer.begin(measureSignal, measPeriod_us);

  // wait for measurements to complete
  // check flag set by measureSignal()  
  while (daqDone == false) {
    // do nothing
  }

  // Now disable timer
  myTimer.end();

  // Write results to serial
  for (int i = 0; i < nPts; i++) {
    Serial.println(myData[i]);
  }
  Serial.println("EOF");
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

void loop() {
  // put your main code here, to run repeatedly:
  // Do nothing
}
