// Diagnóstico aislado ESP32-CAM -> Arduino Mega 2560.
// ESP32 GPIO14/TX -> Mega D17/RX2, GND -> GND. Mega D16 queda libre.

constexpr unsigned long kUsbBaud = 9600UL;
constexpr unsigned long kUartBaud = 9600UL;

void setup() {
  Serial.begin(kUsbBaud);
  Serial2.begin(kUartBaud);
  delay(300);
  Serial.println(F("TEST RX2 9600: esperando ESP32 GPIO14/TX en Mega D17/RX2"));
}

void loop() {
  while (Serial2.available() > 0) {
    Serial.write(Serial2.read());
  }
}
