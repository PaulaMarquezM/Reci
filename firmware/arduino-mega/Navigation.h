// ============================================================
// Reci · Navigation.h — seguir la cinta y saber cuándo llegó
// ============================================================
// Ver docs/PROPUESTA-NAVEGACION-AUTONOMA.md para el porqué de este diseño
// (línea de cinta + franja perpendicular de parada, sin SLAM ni GPS).
//
// ⚠️⚠️ ANTES DE CONECTAR NADA: docs/CONEXIONES.md (ETAPA 3, diagrama físico)
// y el código real de ReciMega.ino NO coinciden. El código usa D3/D4 para
// los servos de las compuertas y D5-D12 para motores como 8 pines
// digitales simples (sin PWM). CONEXIONES.md documenta D2/D3 para IN1/IN2
// del L298N#1 y D6/D7 conectados a ENA/ENB (control por PWM) — sin
// mencionar los servos ahí. D3 no puede ser servo y motor a la vez: uno de
// los dos quedó desactualizado respecto al robot físico real. Esta clase
// sigue el pin map del CÓDIGO actual (D5-D12, sin PWM) por ser lo que de
// verdad corre hoy — verifica con multímetro/continuidad cuál pin mapping
// coincide con tu robot ANTES de energizar los motores, y actualiza
// CONEXIONES.md con lo que encuentres.
//
// Hardware que asume:
//   - Módulo sensor de línea IR de 5 canales, salida DIGITAL por canal
//     (HIGH = ve línea oscura — si el tuyo es al revés, cambia kLineaActiva).
//     NO comprado todavía — ver el documento de propuesta para el modelo.
//   - Motores en ON/OFF simple, sin PWM (ENA/ENB en jumper fijo del L298N,
//     asumiendo que el código actual —no CONEXIONES.md— es el correcto).
//
// Pines usados (libres en el resto del firmware — si cambian, actualiza
// también docs/CONEXIONES.md):
//   D30..D34 -> sensores IR 1..5, de izquierda a derecha
//   D5..D12  -> motores (los mismos 8 pines que ya reservaba ReciMega.ino;
//               esta clase pasa a ser la única dueña de esos pines)
//
// ⚠️ Antes de probar con el chasis en el piso: prueba primero con las
// ruedas LEVANTADAS. Si un lado gira al revés (se ve "avanzar" pero en
// realidad retrocede), invierte kInvertirIzquierda o kInvertirDerecha
// abajo — no hace falta recablear nada.
//
// Uso:
//   ReciNavigation nav;
//   void setup() { nav.begin(); }
//   void loop()  {
//     if (siguiendoLinea && nav.tick() == ReciNavigation::Estado::Llegada) {
//       siguiendoLinea = false;  // encontró la franja de parada
//     }
//   }
// ============================================================

#ifndef RECI_NAVIGATION_H
#define RECI_NAVIGATION_H

#include <Arduino.h>

class ReciNavigation {
 public:
  enum class Estado : uint8_t {
    Siguiendo,   // todo normal, ya corrigió o iba derecho
    Llegada,     // los 5 sensores vieron línea a la vez -> franja de parada
    LineaPerdida // ningún sensor ve línea hace rato -> se detuvo por seguridad
  };

  void begin();

  // Llamar en cada loop() mientras el robot deba estar siguiendo la línea.
  // Lee los sensores, corrige el rumbo, y devuelve el estado resultante.
  // En Llegada y LineaPerdida ya deja los motores detenidos — no hace
  // falta llamar detener() aparte.
  Estado tick();

  void detener();

 private:
  // Pines individuales en vez de un array `static constexpr`: algunos
  // compiladores AVR (C++11/14) piden una definición fuera de la clase
  // para arrays estáticos así, y se presta a un error de link tonto.
  static constexpr uint8_t kNumSensores = 5;
  static constexpr uint8_t kPinSensor0 = 30;  // extremo izquierdo
  static constexpr uint8_t kPinSensor1 = 31;
  static constexpr uint8_t kPinSensor2 = 32;  // centro
  static constexpr uint8_t kPinSensor3 = 33;
  static constexpr uint8_t kPinSensor4 = 34;  // extremo derecho

  static constexpr uint8_t kIzqIn1 = 5;
  static constexpr uint8_t kIzqIn2 = 6;
  static constexpr uint8_t kIzqIn3 = 7;
  static constexpr uint8_t kIzqIn4 = 8;
  static constexpr uint8_t kDerIn1 = 9;
  static constexpr uint8_t kDerIn2 = 10;
  static constexpr uint8_t kDerIn3 = 11;
  static constexpr uint8_t kDerIn4 = 12;

  // HIGH = el sensor ve la línea oscura. Cambia a false si tu módulo es
  // al revés (algunos módulos IR baratos invierten la salida).
  static constexpr bool kLineaActiva = true;

  // Si un lado gira al revés al probar con las ruedas levantadas, cambia
  // esto a true en vez de recablear — invierte solo la lógica, no los pines.
  static constexpr bool kInvertirIzquierda = false;
  static constexpr bool kInvertirDerecha = false;

  // Cuánto tiempo sin ver la línea en NINGÚN sensor antes de rendirse y
  // parar (evita que el robot siga de largo a ciegas si la cinta se cortó).
  static constexpr unsigned long kLineaPerdidaMs = 800;

  unsigned long _ultimaLineaVistaEn = 0;

  bool leerSensor(uint8_t indice) const;
  void avanzarLado(bool esIzquierda, bool retroceder);
  void detenerLado(bool esIzquierda);
};

#endif  // RECI_NAVIGATION_H
