// Diagnóstico aislado del UART2 del Arduino Mega 2560.
// Con el Mega apagado, conectar D16/TX2 directamente a D17/RX2.
// No conectar la ESP32-CAM durante esta prueba.

constexpr unsigned long kUsbBaud = 9600UL;
constexpr unsigned long kUartBaud = 9600UL;
constexpr unsigned long kIntervalMs = 1000UL;

unsigned long nextSendAt = 0;
uint32_t sequence = 0;

void setup() {
  Serial.begin(kUsbBaud);
  Serial2.begin(kUartBaud);
  delay(300);
  Serial.println(F("TEST SERIAL2: D16/TX2 -> D17/RX2"));
}

void loop() {
  if (static_cast<long>(millis() - nextSendAt) >= 0) {
    nextSendAt = millis() + kIntervalMs;
    Serial2.print(F("LOOPBACK:"));
    Serial2.println(sequence++);
  }

  while (Serial2.available() > 0) {
    Serial.write(Serial2.read());
  }
}
