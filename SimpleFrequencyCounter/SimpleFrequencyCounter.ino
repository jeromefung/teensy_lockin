/*
 * Frequency counting measurement -- general
 * 
 * There is the Teensy FreqCount library but it requires
 * driving a specific pin and may need a buffer (since that pin 
 * also drives an LED).
 * 
 * Our requirements aren't so extreme (we're just counting)
 * so dealing with interrupts is probably OK.
 */

// needed for interrupts to work
// see https://www.pjrc.com/teensy/interrupts.html
#include <avr/io.h> 
#include <avr/interrupt.h>

// Connect one terminal of NO pushbutton to pin 23
// and the other terminal to ground.
const uint8_t buttonPin = 23;
// Connect signal to pin 32.
const uint8_t signalPin = 32;

volatile unsigned long edgeCounts;
unsigned long measPeriod_us = 10000000;
double signalFreq; 

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600); 
  pinMode(buttonPin, INPUT_PULLUP); // use internal pullup 
  pinMode(signalPin, INPUT);

  // Wait for button press
  while (digitalRead(buttonPin) == 1) {
    // do nothing
  }

  // set up interrupt
  attachInterrupt(digitalPinToInterrupt(signalPin), edge, RISING);
  // might need to raise interrupt priority, see forum discussion at
  // https://forum.pjrc.com/threads/48101-PMT-pulse-counting-using-Teensy-3-2
  NVIC_SET_PRIORITY(IRQ_PORTA, 0); 
  cli(); // disable interrupts

  edgeCounts = 0; // clear

  elapsedMicros runTime;
  sei(); // enable interrupts

  while (runTime < measPeriod_us) {
    // do nothing, wait
  }

  cli(); // disable interrupts

  Serial.print("Counts: ");
  Serial.println(edgeCounts);
  Serial.print("Frequency (Hz): ");
  Serial.println(edgeCounts / (double) measPeriod_us * 1000000);
  
}

// ISR
void edge() {
  // Increment every time ISR is called
  edgeCounts = edgeCounts + 1;
}

void loop() {
  // put your main code here, to run repeatedly:

}
