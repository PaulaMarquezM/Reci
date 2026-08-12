// ============================================================
// RECI · Configuración de servos con Arduino UNO
// Solo para calibrar los brazos/horns mientras la LiPo está descargada.
// No controla motores, sensores ni pantallas.
// ============================================================

#include <Servo.h>

namespace {

// Pines de señal en el Arduino UNO para esta prueba temporal.
constexpr uint8_t kServoVidrioPin = 9;
constexpr uint8_t kServoPlasticoPin = 10;

// Cada compuerta tiene su propio rango mecánico.
constexpr uint8_t kVidrioCerrado = 90;
constexpr uint8_t kVidrioAbierto = 45;
// Plástico empieza más abajo y abre bastante más.
constexpr uint8_t kPlasticoCerrado = 0;
constexpr uint8_t kPlasticoAbierto = 70;
constexpr unsigned long kTiempoAbiertoMs = 2000UL;

Servo servoVidrio;
Servo servoPlastico;
bool hayCompuertaAbierta = false;
unsigned long cerrarEn = 0;

void cerrarCompuertas() {
  servoVidrio.write(kVidrioCerrado);
  servoPlastico.write(kPlasticoCerrado);
  hayCompuertaAbierta = false;
  Serial.println(F("SERVOS: cerrados a 90 grados."));
}

void abrirVidrio() {
  servoPlastico.write(kPlasticoCerrado);
  servoVidrio.write(kVidrioAbierto);
  hayCompuertaAbierta = true;
  cerrarEn = millis() + kTiempoAbiertoMs;
  Serial.println(F("VIDRIO: abre de 90 a 45 grados por 2 segundos."));
}

void abrirPlastico() {
  servoVidrio.write(kVidrioCerrado);
  servoPlastico.write(kPlasticoAbierto);
  hayCompuertaAbierta = true;
  cerrarEn = millis() + kTiempoAbiertoMs;
  Serial.println(F("PLASTICO: abre de 0 a 70 grados por 2 segundos."));
}

void leerMonitorSerial() {
  while (Serial.available() > 0) {
    const char comando = static_cast<char>(Serial.read());
    if (comando == 'V' || comando == 'v') abrirVidrio();
    if (comando == 'P' || comando == 'p') abrirPlastico();
    if (comando == 'C' || comando == 'c') cerrarCompuertas();
  }
}

}  // namespace

void setup() {
  Serial.begin(9600);
  servoVidrio.attach(kServoVidrioPin);
  servoPlastico.attach(kServoPlasticoPin);
  cerrarCompuertas();

  Serial.println(F("RECI Servos Config UNO listo."));
  Serial.println(F("V=vidrio, P=plastico, C=cerrar. Baud: 9600."));
}

void loop() {
  leerMonitorSerial();
  if (hayCompuertaAbierta && static_cast<long>(millis() - cerrarEn) >= 0) {
    cerrarCompuertas();
  }
}
