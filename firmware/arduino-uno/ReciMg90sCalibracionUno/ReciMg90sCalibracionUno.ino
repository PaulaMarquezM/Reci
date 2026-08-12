// ============================================================
// RECI · Calibración de un servo MG90S (posición, no 360°)
// Arduino UNO · señal en D4
//
// A y C van a posiciones fijas. El servo llega y se queda allí;
// no gira por tiempo. Probar primero con el horn libre.
// ============================================================

#include <Servo.h>

namespace {

constexpr uint8_t kServoPin = 4;

// Punto de partida seguro para calibrar. Ajusta solo estos dos valores
// después de observar la tapa, siempre entre 0 y 180.
constexpr uint8_t kPosicionCerrada = 90;
constexpr uint8_t kPosicionAbierta = 60;

Servo servo;

void cerrar() {
  servo.write(kPosicionCerrada);
  Serial.println(F("MG90S: posicion CERRADA (90 grados)."));
}

void abrir() {
  servo.write(kPosicionAbierta);
  Serial.println(F("MG90S: posicion ABIERTA (60 grados)."));
}

void leerMonitorSerial() {
  while (Serial.available() > 0) {
    const char comando = static_cast<char>(Serial.read());
    if (comando == 'A' || comando == 'a') abrir();
    if (comando == 'C' || comando == 'c') cerrar();
  }
}

}  // namespace

void setup() {
  Serial.begin(9600);
  servo.attach(kServoPin);
  cerrar();
  Serial.println(F("MG90S listo. A=abrir, C=cerrar. Baud: 9600."));
}

void loop() {
  leerMonitorSerial();
}
