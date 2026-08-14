// Diagnostico aislado de la salida UART del ESP32-CAM.
// GPIO14/TX -> Mega D17/RX2 y GND -> GND.

#include <Arduino.h>

constexpr uint32_t kUsbBaud = 115200UL;
constexpr uint32_t kMegaBaud = 9600UL;
constexpr int kMegaRxPin = 13;
constexpr int kMegaTxPin = 14;

HardwareSerial mega(1);
uint32_t sequence = 0;
String receivedLine;

void setup() {
  Serial.begin(kUsbBaud);
  mega.begin(kMegaBaud, SERIAL_8N1, kMegaRxPin, kMegaTxPin);
  delay(500);
  Serial.println("TEST UART14: transmitiendo por GPIO14 a 9600");
}

void loop() {
  mega.print("UART14:");
  mega.println(sequence);
  Serial.print("UART14:");
  Serial.println(sequence);

  const uint32_t deadline = millis() + 250UL;
  while (millis() < deadline) {
    while (mega.available() > 0) {
      const char value = static_cast<char>(mega.read());
      if (value == '\n') {
        receivedLine.trim();
        Serial.print("LOOPBACK GPIO14->GPIO13: ");
        Serial.println(receivedLine);
        receivedLine = "";
      } else {
        receivedLine += value;
      }
    }
  }

  ++sequence;
  delay(750);
}
