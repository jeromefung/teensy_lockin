//Serial read stuff
void setup(){
    Serial.begin(38400);
    pinMode(13, OUTPUT);
    digitalWrite(13, LOW);
    delay(10000);
    for (int i=1000;i<1005;i++){
      Serial.println(String(i));
    }
}

void loop(){
  //Serial.println(String(1000));

  /*

    Serial.flush();
    serialFlush();
    while(Serial.available()==0){
      
    }

    String data;
    while(Serial.available()){
      data = Serial.readString();
    }
    int test = data.toInt();
    if(test==1){
      digitalWrite(13, HIGH);
        delay(100);
        digitalWrite(13, LOW);
    }
    while(Serial.available()==1){
      
    }

    while(Serial.available()){
      data = Serial.readString();
    }
    test = data.toInt();
    if (test == 1000){
      for (int i=0; i<4; i++){
        digitalWrite(13, HIGH);
        delay(100);
        digitalWrite(13, LOW);
        delay(100);
      }
    }*/
}

void serialFlush(){
  while(Serial.available() > 0) {
    char t = Serial.read();
  }
}


//Serial write stuff
/*int i=0;
void setup(){
  Serial.begin(38400);
}

void loop(){
  while (i < 10){
    Serial.println(i);
    delay(1000);
    i++;
  }
}
*/
