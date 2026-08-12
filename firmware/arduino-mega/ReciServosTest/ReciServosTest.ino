// ============================================================
// RECI · Prueba segura de compuertas
// Arduino Mega 2560
// 1 servo MG90S para VIDRIO
// 1 servo original para PLÁSTICO
//
// Monitor Serial a 9600 baudios:
// V = abrir vidrio
// P = abrir plástico
// C = cerrar ambas compuertas
// ============================================================

#include <Servo.h>

namespace {

constexpr uint8_t kServoVidrioPin = 3;
constexpr uint8_t kServoPlasticoPin = 4;

// Calibración física
constexpr uint8_t kVidrioCerrado = 45;
constexpr uint8_t kVidrioAbierto = 166;

constexpr uint8_t kPlasticoCerrado = 30;
constexpr uint8_t kPlasticoAbierto = 180;

constexpr unsigned long kTiempoAbiertoMs = 2000UL;
constexpr unsigned long kSerialBaud = 9600UL;

// Rango de pulsos del MG90S
constexpr int kMg90sPulsoMinUs = 600;
constexpr int kMg90sPulsoMaxUs = 2300;

Servo servoVidrio;
Servo servoPlastico;

bool hayCompuertaAbierta = false;
unsigned long cerrarEn = 0;

void cerrarCompuertas() {
  servoVidrio.write(kVidrioCerrado);
  servoPlastico.write(kPlasticoCerrado);

  hayCompuertaAbierta = false;

  Serial.println(F("SERVOS: compuertas cerradas."));
}

void abrirVidrio() {
  // Mantener plástico cerrado
  servoPlastico.write(kPlasticoCerrado);

  // Abrir vidrio con MG90S
  servoVidrio.write(kVidrioAbierto);

  hayCompuertaAbierta = true;
  cerrarEn = millis() + kTiempoAbiertoMs;

  Serial.println(F("VIDRIO: abierto por 2 segundos."));
}

void abrirPlastico() {
  // Mantener vidrio cerrado
  servoVidrio.write(kVidrioCerrado);

  // Abrir plástico con servo original
  servoPlastico.write(kPlasticoAbierto);

  hayCompuertaAbierta = true;
  cerrarEn = millis() + kTiempoAbiertoMs;

  Serial.println(F("PLASTICO: abierto por 2 segundos."));
}

void leerMonitorSerial() {
  while (Serial.available() > 0) {
    char comando = Serial.read();

    if (comando == 'V' || comando == 'v') {
      abrirVidrio();
    }

    if (comando == 'P' || comando == 'p') {
      abrirPlastico();
    }

    if (comando == 'C' || comando == 'c') {
      cerrarCompuertas();
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);

  // MG90S conectado al pin 3
  servoVidrio.attach(
    kServoVidrioPin,
    kMg90sPulsoMinUs,
    kMg90sPulsoMaxUs
  );

  // Servo original conectado al pin 4
  servoPlastico.attach(kServoPlasticoPin);

  cerrarCompuertas();

  Serial.println(F("RECI: prueba de servos lista."));
  Serial.println(F("Escribe V para vidrio."));
  Serial.println(F("Escribe P para plastico."));
  Serial.println(F("Escribe C para cerrar."));
  Serial.println(F("MG90S vidrio: cerrado 45, abierto 166."));
}

void loop() {
  leerMonitorSerial();

  if (hayCompuertaAbierta &&
      static_cast<long>(millis() - cerrarEn) >= 0) {
    cerrarCompuertas();
  }
}