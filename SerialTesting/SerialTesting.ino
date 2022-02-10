//https://www.oreilly.com/library/view/arduino-cookbook/9781449399368/ch04.html
//https://arduino.stackexchange.com/questions/1013/how-do-i-split-an-incoming-string

const int numChars = 32;
char str[numChars];

void setup(){
  Serial.begin(38400);
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  while(!Serial){}
}

void loop(){
  //char str[] = "0:1000:10000F";

  //need to test with pyton sending data now

  while(!Serial.available()){}
  char receivedChar;
  int index = 0;
  while(Serial.available() && receivedChar != "F"){
    receivedChar = Serial.read();
    str[index] = receivedChar;
    index++;
  }
  
  char* com = strtok(str, ":");
  int mode = atoi(com);
  com = strtok(NULL, ":");
  int freq = atoi(com);
  com = strtok(NULL, "F");
  int samp = atoi(com);
  //Serial.print(mode);
  //Serial.print(", ");
  //Serial.print(freq);
  //Serial.print(", ");
  //Serial.println(samp);
  
  if (mode == 0){
    digitalWrite(13, HIGH);
  }
  delay(1000);
  if (freq == 1000){
    digitalWrite(13, LOW);
  }
  delay(1000);
  if (samp == 10000){
    digitalWrite(13, HIGH);
  }
  delay(1000);
  
}
