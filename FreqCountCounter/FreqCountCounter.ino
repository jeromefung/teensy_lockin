/* 
 *  Probably works better: use the FreqCount library. 
 *  But this requires connecting input signal to pin 13
 *  only.
 */

#include <FreqCount.h>

int countPeriod_ms = 10000;
unsigned long edgeCounts;

// Connect one terminal of a NO pushbutton to pin 23
// and the other to ground.
const uint8_t buttonPin = 23;


void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600); 
  pinMode(buttonPin, INPUT_PULLUP);

  // Wait until button gets pressed
  while (digitalRead(buttonPin) == 1) {
    // wait, do nothing
  }
  
  // begin counting. Signal must be connected to pin 13!
  FreqCount.begin(countPeriod_ms);

  while (FreqCount.available() == false) {
    // wait, do nothing
  }

  FreqCount.end();
  edgeCounts = FreqCount.read();

  Serial.print("Counts: ");
  Serial.println(edgeCounts);
  Serial.print("Frequency (Hz): ");
  Serial.println(edgeCounts / (double) countPeriod_ms * 1000);
  
}

void loop() {
  // put your main code here, to run repeatedly:
  // do nothing
}
