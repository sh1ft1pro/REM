#define x_pin A0
#define y_pin A1
#define pin_right 11
#define pin_left 12
//#define button 8

int right_read_last = 0;
int left_read_last = 0;
 
void setup() {  
 
  pinMode(x_pin, INPUT);
  pinMode(y_pin, INPUT);
 
  pinMode(pin_right, INPUT_PULLUP);
  pinMode(pin_left, INPUT_PULLUP); 
  //pinMode(button, INPUT_PULLUP);   
 
  Serial.begin(9600);
 
  right_read_last = digitalRead(pin_right);
  left_read_last = digitalRead(pin_left);
 
}
 
void loop() {  
 
  if (analogRead(x_pin) > 1020){ 
    Serial.println(1);    
  }
 
  else if (analogRead(x_pin) < 20){ 
    Serial.println(0);      
  }
  else{ 
    Serial.println(2);
  }
 
  if (analogRead(y_pin) > 1020){ 
    Serial.println(1);    
  }
 
  else if (analogRead(y_pin) < 20){
    Serial.println(0);      
  }
  else{
    Serial.println(2); 
  }
 
 
  Serial.println(digitalRead(pin_right));
  Serial.println(digitalRead(pin_left));
  //Serial.println(digitalRead(button));
 
  delay(200); 
}