// ============================================================
// RECI · Calibración de servo de rotación continua (360°)
// Arduino UNO · señal en D4
//
// No usa ángulos: mueve el servo por tiempo y luego lo detiene.
// Primero probar con el brazo/horn libre, sin forzar una compuerta.
// ============================================================

#include <Servo.h>

namespace {

constexpr uint8_t kServoPin = 4;
constexpr uint8_t kDetener = 90;

// Si A gira hacia el lado que CIERRA en vez de ABRIR, intercambia estos dos
// valores. 90 siempre debe quedarse como detener.
constexpr uint8_t kAbrir = 70;
constexpr uint8_t kCerrar = 110;

// Empieza con recorridos cortos. Aumenta de 50 en 50 ms solo si hace falta.
constexpr unsigned long kTiempoAbrirMs = 300UL;
constexpr unsigned long kTiempoCerrarMs = 300UL;

Servo servo;
bool moviendo = false;
unsigned long detenerEn = 0;

void detener() {
  servo.write(kDetener);
  moviendo = false;
  Serial.println(F("SERVO: detenido."));
}

void mover(uint8_t velocidadDireccion, unsigned long duracion, const __FlashStringHelper* mensaje) {
  servo.write(velocidadDireccion);
  moviendo = true;
  detenerEn = millis() + duracion;
  Serial.println(mensaje);
}

void leerMonitorSerial() {
  while (Serial.available() > 0) {
    const char comando = static_cast<char>(Serial.read());
    if (comando == 'A' || comando == 'a') {
      mover(kAbrir, kTiempoAbrirMs, F("SERVO: apertura corta."));
    } else if (comando == 'C' || comando == 'c') {
      mover(kCerrar, kTiempoCerrarMs, F("SERVO: cierre corto."));
    } else if (comando == 'S' || comando == 's') {
      detener();
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(9600);
  servo.attach(kServoPin);
  detener();

  Serial.println(F("RECI Servo 360 listo."));
  Serial.println(F("A=abrir, C=cerrar, S=detener. Baud: 9600."));
}

void loop() {
  leerMonitorSerial();
  if (moviendo && static_cast<long>(millis() - detenerEn) >= 0) detener();
}
