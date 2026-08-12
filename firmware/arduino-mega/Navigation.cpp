#include "Navigation.h"

void ReciNavigation::begin() {
  pinMode(kPinSensor0, INPUT);
  pinMode(kPinSensor1, INPUT);
  pinMode(kPinSensor2, INPUT);
  pinMode(kPinSensor3, INPUT);
  pinMode(kPinSensor4, INPUT);

  pinMode(kIzqIn1, OUTPUT);
  pinMode(kIzqIn2, OUTPUT);
  pinMode(kIzqIn3, OUTPUT);
  pinMode(kIzqIn4, OUTPUT);
  pinMode(kDerIn1, OUTPUT);
  pinMode(kDerIn2, OUTPUT);
  pinMode(kDerIn3, OUTPUT);
  pinMode(kDerIn4, OUTPUT);

  detener();
  _ultimaLineaVistaEn = millis();
}

bool ReciNavigation::leerSensor(uint8_t indice) const {
  uint8_t pin;
  switch (indice) {
    case 0: pin = kPinSensor0; break;
    case 1: pin = kPinSensor1; break;
    case 2: pin = kPinSensor2; break;
    case 3: pin = kPinSensor3; break;
    default: pin = kPinSensor4; break;
  }
  const bool alto = digitalRead(pin) == HIGH;
  return kLineaActiva ? alto : !alto;
}

// esIzquierda selecciona el lado; retroceder=false avanza, true retrocede.
// Con motores sin PWM (ENA/ENB fijos), "detenerLado" es la única forma de
// bajar la velocidad de un lado — por eso el seguimiento es bang-bang
// (para/avanza), no un giro suave con velocidad intermedia.
void ReciNavigation::avanzarLado(bool esIzquierda, bool retroceder) {
  const bool invertir = esIzquierda ? kInvertirIzquierda : kInvertirDerecha;
  const bool haciaAdelante = retroceder ? invertir : !invertir;

  const uint8_t in1 = esIzquierda ? kIzqIn1 : kDerIn1;
  const uint8_t in2 = esIzquierda ? kIzqIn2 : kDerIn2;
  const uint8_t in3 = esIzquierda ? kIzqIn3 : kDerIn3;
  const uint8_t in4 = esIzquierda ? kIzqIn4 : kDerIn4;

  digitalWrite(in1, haciaAdelante ? HIGH : LOW);
  digitalWrite(in2, haciaAdelante ? LOW : HIGH);
  digitalWrite(in3, haciaAdelante ? HIGH : LOW);
  digitalWrite(in4, haciaAdelante ? LOW : HIGH);
}

void ReciNavigation::detenerLado(bool esIzquierda) {
  const uint8_t in1 = esIzquierda ? kIzqIn1 : kDerIn1;
  const uint8_t in2 = esIzquierda ? kIzqIn2 : kDerIn2;
  const uint8_t in3 = esIzquierda ? kIzqIn3 : kDerIn3;
  const uint8_t in4 = esIzquierda ? kIzqIn4 : kDerIn4;
  digitalWrite(in1, LOW);
  digitalWrite(in2, LOW);
  digitalWrite(in3, LOW);
  digitalWrite(in4, LOW);
}

void ReciNavigation::detener() {
  detenerLado(true);
  detenerLado(false);
}

ReciNavigation::Estado ReciNavigation::tick() {
  const bool s0 = leerSensor(0);
  const bool s1 = leerSensor(1);
  const bool s2 = leerSensor(2);
  const bool s3 = leerSensor(3);
  const bool s4 = leerSensor(4);

  const uint8_t vistos = s0 + s1 + s2 + s3 + s4;
  const unsigned long ahora = millis();

  // Franja de parada: una marca ancha que cruza los 5 sensores a la vez
  // (ver docs/PROPUESTA-NAVEGACION-AUTONOMA.md §4) — se distingue de la
  // línea normal (que solo activa 1-2 sensores) porque activa todos.
  if (vistos >= 4) {
    detener();
    return Estado::Llegada;
  }

  if (vistos == 0) {
    if (static_cast<long>(ahora - _ultimaLineaVistaEn) > static_cast<long>(kLineaPerdidaMs)) {
      detener();
      return Estado::LineaPerdida;
    }
    // Todavía dentro del margen de tolerancia (ej. un empalme del piso):
    // sigue derecho un instante más en vez de parar de golpe.
    avanzarLado(true, false);
    avanzarLado(false, false);
    return Estado::Siguiendo;
  }

  _ultimaLineaVistaEn = ahora;

  // Bang-bang: gira hacia el lado donde está la línea. s0 = extremo
  // izquierdo, s4 = extremo derecho (ver docs/CONEXIONES.md para el
  // sentido físico real una vez montado el sensor).
  if (s0 || (s1 && !s3)) {
    // Línea a la izquierda -> gira izquierda: frena el lado derecho,
    // el izquierdo sigue empujando.
    avanzarLado(true, false);
    detenerLado(false);
  } else if (s4 || (s3 && !s1)) {
    avanzarLado(false, false);
    detenerLado(true);
  } else {
    // s2 solo, o s1+s3 a la vez (línea bien centrada): derecho.
    avanzarLado(true, false);
    avanzarLado(false, false);
  }

  return Estado::Siguiendo;
}
