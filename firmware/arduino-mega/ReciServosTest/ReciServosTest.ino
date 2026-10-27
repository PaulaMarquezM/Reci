// ============================================================
// RECI · Prueba segura de la compuerta única
// Arduino Mega 2560
// 1 servo en D3 que inclina la bandeja:
//   plástico -> gira a la IZQUIERDA
//   vidrio   -> gira a la DERECHA
//
// Monitor Serial a 9600 baudios:
// P = plástico (izquierda)
// V = vidrio (derecha)
// C = volver al centro
// Un número entre 0 y 180 + Enter = mover a ese ángulo para calibrar
// ============================================================

#include <Servo.h>

namespace {

constexpr uint8_t kServoCompuertaPin = 3;

// Calibración física. Copia los valores finales a ReciRutaDemo.ino.
constexpr uint8_t kServoCentro = 90;
constexpr uint8_t kServoIzquierda = 30;
constexpr uint8_t kServoDerecha = 150;

constexpr unsigned long kTiempoAbiertoMs = 2000UL;
constexpr unsigned long kSerialBaud = 9600UL;

Servo servoCompuerta;

bool compuertaInclinada = false;
unsigned long volverAlCentroEn = 0;

void volverAlCentro() {
  servoCompuerta.write(kServoCentro);
  compuertaInclinada = false;
  Serial.println(F("SERVO: centro."));
}

void inclinar(uint8_t angulo, const __FlashStringHelper* mensaje) {
  servoCompuerta.write(angulo);
  compuertaInclinada = true;
  volverAlCentroEn = millis() + kTiempoAbiertoMs;
  Serial.println(mensaje);
}

void leerMonitorSerial() {
  if (Serial.available() == 0) return;

  const char primero = static_cast<char>(Serial.peek());
  if (isDigit(primero)) {
    const int angulo = Serial.parseInt();
    if (angulo >= 0 && angulo <= 180) {
      servoCompuerta.write(angulo);
      compuertaInclinada = false;
      Serial.print(F("CALIBRACION: angulo "));
      Serial.println(angulo);
    }
    return;
  }

  const char comando = static_cast<char>(Serial.read());
  if (comando == 'P' || comando == 'p') {
    inclinar(kServoIzquierda, F("PLASTICO: izquierda por 2 segundos."));
  } else if (comando == 'V' || comando == 'v') {
    inclinar(kServoDerecha, F("VIDRIO: derecha por 2 segundos."));
  } else if (comando == 'C' || comando == 'c') {
    volverAlCentro();
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);

  servoCompuerta.attach(kServoCompuertaPin);
  volverAlCentro();

  Serial.println(F("RECI: prueba de compuerta unica lista."));
  Serial.println(F("P = plastico (izquierda), V = vidrio (derecha), C = centro."));
  Serial.println(F("Escribe un angulo 0-180 para calibrar."));
}

void loop() {
  leerMonitorSerial();

  if (compuertaInclinada &&
      static_cast<long>(millis() - volverAlCentroEn) >= 0) {
    volverAlCentro();
  }
}
