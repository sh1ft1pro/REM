void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // Ждем, пока Питон что-то пришлет
  if (Serial.available() > 0) {
    String packet = Serial.readStringUntil('\n');
    packet.trim(); // Убираем \r

    if (packet.length() > 0 && packet.startsWith(":")) {
      digitalWrite(LED_BUILTIN, HIGH);
      
      // Отправляем этот же пакет обратно
      Serial.print(packet);
      Serial.print("\r\n"); 
      
      delay(50);
      digitalWrite(LED_BUILTIN, LOW);
    }
  }
}