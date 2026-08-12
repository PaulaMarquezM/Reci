// ============================================================
// RECI · Prueba segura de sensores
// Arduino Mega 2560 + HC-SR04 frontal + PIR
//
// Este programa NO controla motores, L298N, servos, OLED ni LCD.
// Úsalo con la batería de motores DESCONECTADA.
// Después, vuelve a cargar ReciRutaDemo.ino para la demostración completa.
// ============================================================

namespace {

constexpr uint8_t kTrigFrontal = 22;
constexpr uint8_t kEchoFrontal = 23;
constexpr uint8_t kPirPin = 28;

constexpr unsigned long kSerialBaud = 9600UL;
constexpr unsigned long kPeriodoUltrasonicoMs = 300UL;
constexpr unsigned long kEchoTimeoutUs = 25000UL;

bool ultimoPir = false;
unsigned long proximaLecturaUltrasonico = 0;

long distanciaFrontalCm() {
  digitalWrite(kTrigFrontal, LOW);
  delayMicroseconds(2);
  digitalWrite(kTrigFrontal, HIGH);
  delayMicroseconds(10);
  digitalWrite(kTrigFrontal, LOW);

  const unsigned long duracion = pulseIn(kEchoFrontal, HIGH, kEchoTimeoutUs);
  if (duracion == 0) return -1;
  return static_cast<long>(duracion * 0.0343F / 2.0F);
}

void informarDistancia() {
  const long distancia = distanciaFrontalCm();
  if (distancia < 0) {
    Serial.println(F("ULTRASONICO: sin lectura. Revisa TRIG/ECHO/VCC/GND."));
    return;
  }

  Serial.print(F("ULTRASONICO: "));
  Serial.print(distancia);
  Serial.println(F(" cm"));
}

void revisarPir() {
  const bool hayMovimiento = digitalRead(kPirPin) == HIGH;
  if (hayMovimiento == ultimoPir) return;

  ultimoPir = hayMovimiento;
  if (hayMovimiento) {
    Serial.println(F("PIR: MOVIMIENTO DETECTADO"));
  } else {
    Serial.println(F("PIR: sin movimiento"));
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);

  pinMode(kTrigFrontal, OUTPUT);
  pinMode(kEchoFrontal, INPUT);
  digitalWrite(kTrigFrontal, LOW);
  pinMode(kPirPin, INPUT);

  Serial.println(F("RECI Sensores Test listo."));
  Serial.println(F("Espera 60 segundos para que el PIR se estabilice."));
  Serial.println(F("Pon una mano frente al ultrasonico y camina ante el PIR."));
}

void loop() {
  revisarPir();

  const unsigned long ahora = millis();
  if (static_cast<long>(ahora - proximaLecturaUltrasonico) >= 0) {
    proximaLecturaUltrasonico = ahora + kPeriodoUltrasonicoMs;
    informarDistancia();
  }
}
