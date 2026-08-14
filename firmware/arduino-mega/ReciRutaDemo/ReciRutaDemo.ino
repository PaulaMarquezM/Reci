// ============================================================
// RECI · Ruta demo sin sensores de linea
// Arduino Mega 2560 + 2 L298N + 4 motores TT
//
// Ruta recta de demostración: BASE -> P1 -> P2
// El regreso a BASE se hace manualmente por seguridad: RECI no tiene un
// sensor trasero para retroceder de forma autónoma.
//
// IMPORTANTE
// - Este sketch NO se mueve al encender.
// - Coloca siempre el robot en BASE antes de probar una ruta.
// - Prueba primero con las ruedas levantadas.
// - Ajusta los tres tiempos de ruta despues de medir el circuito real.
// ============================================================

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include <qrcode.h>

namespace {

// Mapa confirmado por RECI_Guia_Armado_Electronico.docx.
constexpr uint8_t kIzqIn1 = 5;
constexpr uint8_t kIzqIn2 = 6;
constexpr uint8_t kIzqIn3 = 7;
constexpr uint8_t kIzqIn4 = 8;
constexpr uint8_t kDerIn1 = 9;
constexpr uint8_t kDerIn2 = 10;
constexpr uint8_t kDerIn3 = 11;
constexpr uint8_t kDerIn4 = 13;

// Si los dos motores del lado izquierdo giran al revés con F, cambia esta
// opción. Solo afecta al L298N controlado por D5-D8.
constexpr bool kInvertirLadoIzquierdo = true;

// Compuertas. Valores calibrados físicamente en la prueba de servos.
constexpr uint8_t kServoVidrioPin = 3;
constexpr uint8_t kServoPlasticoPin = 4;
constexpr uint8_t kVidrioCerrado = 45;
// -90 en un uint8_t se convierte en 166; se expresa así para conservar
// exactamente el movimiento calibrado, sin cambiarlo.
constexpr uint8_t kVidrioAbierto = 166;
constexpr uint8_t kPlasticoCerrado = 30;
constexpr uint8_t kPlasticoAbierto = 180;
constexpr unsigned long kCompuertaAbiertaMs = 2000UL;

Servo servoVidrio;
Servo servoPlastico;

// OLED SSD1306 128x64 por I2C: Mega SDA=20, SCL=21.
constexpr uint8_t kDireccionOled = 0x3C;
Adafruit_SSD1306 oled(128, 64, &Wire, -1);
bool oledDisponible = false;

// LCD 16x2 I2C: comparte SDA=20 y SCL=21 con la OLED.
// La mayoría de estos módulos usan 0x27; si no muestra texto, se confirma
// la dirección con un escáner I2C antes de cambiar esta constante.
constexpr uint8_t kDireccionLcd = 0x27;
LiquidCrystal_I2C lcd(kDireccionLcd, 16, 2);
bool lcdDisponible = false;

enum class CaraReci : uint8_t { SinDibujar, Lista, Movimiento, Feliz, Alerta };
CaraReci caraActual = CaraReci::SinDibujar;
bool qrVisible = false;

// HC-SR04 frontal: freno de seguridad mientras RECI esta en ruta.
constexpr uint8_t kTrigFrontal = 22;
constexpr uint8_t kEchoFrontal = 23;
constexpr unsigned long kDistanciaSeguraCm = 20;
constexpr unsigned long kRevisionObstaculoMs = 100UL;
constexpr unsigned long kEchoTimeoutUs = 25000UL;
// Tras detectar un obstáculo, el frente debe quedar libre este tiempo antes
// de continuar solo. Evita que una lectura aislada haga arrancar a RECI.
constexpr unsigned long kFrenteLibreAntesDeReanudarMs = 1000UL;

// PIR de bienvenida: el esquema de RECI conecta OUT al pin 28 del Mega.
// Solo genera un evento de presencia cuando el robot está detenido; nunca
// inicia un movimiento ni concede puntos por sí solo.
constexpr uint8_t kPirPin = 28;
constexpr unsigned long kEsperaPresenciaMs = 10000UL;

// CALIBRACION: reemplaza 0 por el tiempo medido en milisegundos.
// Mide cada tramo tres veces y usa el promedio. Los dos tramos son rectos,
// siempre en la dirección BASE -> P1 -> P2.
constexpr unsigned long kBaseAP1Ms = 8000UL;
constexpr unsigned long kP1AP2Ms = 8000UL;

constexpr unsigned long kSerialBaud = 9600UL;
// Los mensajes de la ESP32 incluyen, por ejemplo,
// "CMD:LCD:Hola, Pau|Soy RECI". Deja espacio suficiente para el saludo
// sin alterar los comandos cortos de movimiento.
constexpr size_t kComandoMax = 64;

// Por ahora las órdenes llegan solo desde el Monitor Serial por USB.
// Dejar RX2 flotando sin una ESP32-CAM conectada puede crear caracteres basura
// y mensajes de "comando inválido". Se activa al integrar la ESP32-CAM.
// Activado: la ESP32-CAM ya está conectada a RX2/TX2 con divisor de nivel.
constexpr bool kEsp32CamConectada = true;
// La presentación usa comunicación en ambos sentidos. D16/TX2 solo puede
// conectarse a GPIO13/RX mediante el divisor resistivo obligatorio de 5 V a
// 3,3 V (1 kΩ en serie y 2 kΩ a GND). Nunca unir esos pines directamente.
constexpr bool kEsp32CamBidireccional = true;

enum class Punto : uint8_t { Desconocido, Base, P1, P2 };
enum class Modo : uint8_t { Detenido, ManualAdelante, ManualAtras, ManualIzquierda,
                            ManualDerecha, EnRuta, Emergencia };
enum class CompuertaActiva : uint8_t { Ninguna, Vidrio, Plastico };

Punto puntoActual = Punto::Desconocido;
Punto destino = Punto::Desconocido;
Modo modo = Modo::Detenido;
unsigned long terminaTramoEn = 0;
unsigned long ultimoChequeoObstaculo = 0;
unsigned long tiempoRestantePausaMs = 0;
unsigned long frenteLibreDesde = 0;
unsigned long proximaPresenciaPermitidaEn = 0;
CompuertaActiva compuertaActiva = CompuertaActiva::Ninguna;
unsigned long cerrarCompuertaEn = 0;
Punto destinoPendienteCompuerta = Punto::Desconocido;
char comando[kComandoMax + 1] = {};
size_t longitudComando = 0;

bool i2cResponde(uint8_t direccion) {
  Wire.beginTransmission(direccion);
  return Wire.endTransmission() == 0;
}

void mostrarLcd(const char* linea1, const char* linea2) {
  if (!lcdDisponible) return;
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(linea1);
  lcd.setCursor(0, 1);
  lcd.print(linea2);
}

void mostrarRutaEnLcd(const char* accion, Punto punto) {
  if (punto == Punto::P1) {
    mostrarLcd(accion, "Punto 1");
  } else if (punto == Punto::P2) {
    mostrarLcd(accion, "Punto 2");
  } else {
    mostrarLcd(accion, "BASE");
  }
}

void informar(const __FlashStringHelper* texto);

// La carita se dibuja solo cuando cambia el estado; así no frena la lectura
// del ultrasónico ni el recorrido por estar redibujando constantemente.
void mostrarCara(CaraReci cara) {
  if (!oledDisponible || cara == caraActual) return;

  qrVisible = false;
  caraActual = cara;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  if (cara == CaraReci::Movimiento) {
    // Ojos concentrados mientras RECI avanza.
    oled.fillRoundRect(30, 16, 18, 14, 6, SSD1306_WHITE);
    oled.fillRoundRect(80, 16, 18, 14, 6, SSD1306_WHITE);
    oled.drawCircleHelper(64, 42, 11, 0x0C, SSD1306_WHITE);
    oled.drawCircleHelper(64, 41, 10, 0x0C, SSD1306_WHITE);
  } else if (cara == CaraReci::Feliz) {
    // Ojos ^ ^ y sonrisa grande: llegó o detectó a una persona.
    oled.drawLine(30, 29, 39, 20, SSD1306_WHITE);
    oled.drawLine(39, 20, 48, 29, SSD1306_WHITE);
    oled.drawLine(80, 29, 89, 20, SSD1306_WHITE);
    oled.drawLine(89, 20, 98, 29, SSD1306_WHITE);
    for (uint8_t grosor = 0; grosor < 3; grosor++) {
      oled.drawCircleHelper(64, 38, 18 - grosor, 0x0C, SSD1306_WHITE);
    }
  } else if (cara == CaraReci::Alerta) {
    // Ojos redondos y boca "o": hay un obstáculo al frente.
    oled.fillCircle(39, 23, 9, SSD1306_WHITE);
    oled.fillCircle(89, 23, 9, SSD1306_WHITE);
    oled.drawCircle(64, 46, 6, SSD1306_WHITE);
    oled.drawCircle(64, 46, 5, SSD1306_WHITE);
  } else {
    // Cara tranquila mientras espera en BASE/P1/P2.
    oled.fillRoundRect(30, 10, 18, 26, 9, SSD1306_WHITE);
    oled.fillRoundRect(80, 10, 18, 26, 9, SSD1306_WHITE);
    for (uint8_t grosor = 0; grosor < 3; grosor++) {
      oled.drawCircleHelper(64, 40, 15 - grosor, 0x0C, SSD1306_WHITE);
    }
  }

  oled.display();
}

void mostrarQrReal(const char* codigo) {
  if (!oledDisponible || codigo == nullptr || codigo[0] == '\0') return;

  // Un claim_code tiene 8 caracteres: cabe en QR version 1 con correccion
  // baja. Se dibuja negro sobre blanco y con margen de 4 modulos para que
  // la camara de la PWA pueda leerlo sin invertir la imagen.
  constexpr uint8_t kQrVersion = 1;
  constexpr uint8_t kEscala = 2;
  constexpr uint8_t kMargenModulos = 4;
  constexpr uint8_t kQrBufferBytes = 56;
  uint8_t datosQr[kQrBufferBytes] = {};
  QRCode qr;

  if (qrcode_initText(&qr, datosQr, kQrVersion, ECC_LOW, codigo) != 0) {
    informar(F("ERROR: no se pudo generar el QR."));
    return;
  }

  const uint8_t ladoTotal = (qr.size + 2 * kMargenModulos) * kEscala;
  const int16_t origenX = (oled.width() - ladoTotal) / 2;
  const int16_t origenY = (oled.height() - ladoTotal) / 2;

  oled.clearDisplay();
  oled.fillRect(origenX, origenY, ladoTotal, ladoTotal, SSD1306_WHITE);
  for (uint8_t y = 0; y < qr.size; ++y) {
    for (uint8_t x = 0; x < qr.size; ++x) {
      if (!qrcode_getModule(&qr, x, y)) continue;
      oled.fillRect(origenX + (x + kMargenModulos) * kEscala,
                    origenY + (y + kMargenModulos) * kEscala,
                    kEscala, kEscala, SSD1306_BLACK);
    }
  }
  oled.display();
  qrVisible = true;
  caraActual = CaraReci::SinDibujar;
}

void escribirLadoIzquierdo(bool adelante) {
  const bool sentido = kInvertirLadoIzquierdo ? !adelante : adelante;
  digitalWrite(kIzqIn1, sentido ? HIGH : LOW);
  digitalWrite(kIzqIn2, sentido ? LOW : HIGH);
  digitalWrite(kIzqIn3, sentido ? HIGH : LOW);
  digitalWrite(kIzqIn4, sentido ? LOW : HIGH);
}

void escribirLadoDerecho(bool adelante) {
  // Direcciones finales comprobadas durante la ruta:
  // D9/D10 (rueda delantera derecha) invertido; D11/D13 normal.
  const bool sentidoDelantero = !adelante;
  digitalWrite(kDerIn1, sentidoDelantero ? HIGH : LOW);
  digitalWrite(kDerIn2, sentidoDelantero ? LOW : HIGH);
  digitalWrite(kDerIn3, adelante ? HIGH : LOW);
  digitalWrite(kDerIn4, adelante ? LOW : HIGH);
}

void detenerMotores() {
  const uint8_t pines[] = {kIzqIn1, kIzqIn2, kIzqIn3, kIzqIn4,
                            kDerIn1, kDerIn2, kDerIn3, kDerIn4};
  for (uint8_t pin : pines) digitalWrite(pin, LOW);
}

void avanzar() {
  escribirLadoIzquierdo(true);
  escribirLadoDerecho(true);
}

void retroceder() {
  escribirLadoIzquierdo(false);
  escribirLadoDerecho(false);
}

void girarIzquierda() {
  escribirLadoIzquierdo(false);
  escribirLadoDerecho(true);
}

void girarDerecha() {
  escribirLadoIzquierdo(true);
  escribirLadoDerecho(false);
}

const __FlashStringHelper* nombrePunto(Punto punto) {
  switch (punto) {
    case Punto::Base: return F("BASE");
    case Punto::P1: return F("P1");
    case Punto::P2: return F("P2");
    default: return F("DESCONOCIDO");
  }
}

void informar(const __FlashStringHelper* texto) {
  Serial.print(F("RECI: "));
  Serial.println(texto);
}

void informarPunto(const __FlashStringHelper* prefijo, Punto punto) {
  Serial.print(F("RECI: "));
  Serial.print(prefijo);
  Serial.println(nombrePunto(punto));
}

void cerrarCompuertas() {
  servoVidrio.write(kVidrioCerrado);
  servoPlastico.write(kPlasticoCerrado);
  compuertaActiva = CompuertaActiva::Ninguna;
}

void irAPunto(Punto solicitado);

void abrirCompuerta(CompuertaActiva solicitada) {
  // Las tapas solo se abren cuando RECI está quieto en una parada.
  if (modo != Modo::Detenido) {
    informar(F("No abro compuerta mientras RECI se mueve."));
    return;
  }
  if (compuertaActiva != CompuertaActiva::Ninguna) {
    informar(F("Una compuerta ya esta abierta."));
    return;
  }

  if (solicitada == CompuertaActiva::Vidrio) {
    servoPlastico.write(kPlasticoCerrado);
    servoVidrio.write(kVidrioAbierto);
    mostrarLcd("Deposita vidrio", "Tapa abierta");
    informar(F("COMPUERTA: vidrio abierta."));
  } else {
    servoVidrio.write(kVidrioCerrado);
    servoPlastico.write(kPlasticoAbierto);
    mostrarLcd("Deposita plastico", "Tapa abierta");
    informar(F("COMPUERTA: plastico abierta."));
  }

  compuertaActiva = solicitada;
  cerrarCompuertaEn = millis() + kCompuertaAbiertaMs;
  mostrarCara(CaraReci::Feliz);
}

void actualizarCompuerta() {
  if (compuertaActiva == CompuertaActiva::Ninguna) return;
  if (static_cast<long>(millis() - cerrarCompuertaEn) < 0) return;

  cerrarCompuertas();
  // No borra el QR al cumplirse los 2 s de la compuerta: la persona debe
  // tener tiempo suficiente para escanearlo. Una ruta o estado nuevo sí lo
  // reemplazará mediante mostrarCara().
  if (!qrVisible) mostrarCara(CaraReci::Lista);
  mostrarLcd("Gracias!", "Tapa cerrada");
  informar(F("COMPUERTA: cerrada."));

  const Punto pendiente = destinoPendienteCompuerta;
  destinoPendienteCompuerta = Punto::Desconocido;
  if (pendiente != Punto::Desconocido) {
    informar(F("COMPUERTA: iniciando la ruta que estaba en espera."));
    irAPunto(pendiente);
  }
}

// Protocolo estable para la ESP32-CAM. Los textos amigables del Monitor
// Serial se mantienen separados de estos eventos para que la app no tenga
// que adivinar cuándo RECI arrancó, llegó o encontró un obstáculo.
void emitirEvento(const __FlashStringHelper* tipo, Punto punto) {
  if (!kEsp32CamBidireccional) return;
  Serial2.print(F("EVENT:"));
  Serial2.print(tipo);
  Serial2.print(':');
  Serial2.println(nombrePunto(punto));
}

void emitirObstaculo() {
  if (!kEsp32CamBidireccional) return;
  Serial2.println(F("EVENT:OBSTACLE"));
}

void actualizarPresencia() {
  if (modo != Modo::Detenido) return;
  if (static_cast<long>(millis() - proximaPresenciaPermitidaEn) < 0) return;
  if (digitalRead(kPirPin) != HIGH) return;

  proximaPresenciaPermitidaEn = millis() + kEsperaPresenciaMs;
  if (kEsp32CamBidireccional) Serial2.println(F("EVENT:PRESENCE"));
  informar(F("PRESENCIA: alguien se acerco"));
  if (!qrVisible) mostrarCara(CaraReci::Feliz);
  mostrarLcd("Hola, soy RECI", "Recicla aqui");
}

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

bool hayObstaculoFrontal() {
  const long distancia = distanciaFrontalCm();
  return distancia > 0 && distancia <= static_cast<long>(kDistanciaSeguraCm);
}

void detenerTodo(const __FlashStringHelper* motivo) {
  detenerMotores();
  destino = Punto::Desconocido;
  destinoPendienteCompuerta = Punto::Desconocido;
  modo = Modo::Detenido;
  mostrarCara(CaraReci::Lista);
  mostrarLcd("RECI detenido", "Listo para ti");
  informar(motivo);
}

bool tiemposConfigurados() {
  return kBaseAP1Ms > 0 && kP1AP2Ms > 0;
}

unsigned long tiempoSiguienteTramo(Punto desde) {
  switch (desde) {
    case Punto::Base: return kBaseAP1Ms;
    case Punto::P1: return kP1AP2Ms;
    default: return 0;
  }
}

Punto siguientePunto(Punto desde) {
  switch (desde) {
    case Punto::Base: return Punto::P1;
    case Punto::P1: return Punto::P2;
    default: return Punto::Desconocido;
  }
}

void iniciarSiguienteTramo() {
  const unsigned long duracion = tiempoSiguienteTramo(puntoActual);
  if (duracion == 0) {
    detenerTodo(F("ERROR: calibra T1 y T2 antes de usar P1/P2"));
    return;
  }

  const Punto proximo = siguientePunto(puntoActual);
  if (proximo == Punto::Desconocido) {
    detenerTodo(F("FIN DE RUTA: regresa RECI manualmente a BASE"));
    return;
  }
  avanzar();
  terminaTramoEn = millis() + duracion;
  modo = Modo::EnRuta;
  mostrarCara(CaraReci::Movimiento);
  mostrarRutaEnLcd("Voy hacia", proximo);
  emitirEvento(F("ROUTE_STARTED"), proximo);
  Serial.print(F("RECI: ruta "));
  Serial.print(nombrePunto(puntoActual));
  Serial.print(F(" -> "));
  Serial.println(nombrePunto(proximo));
}

void irAPunto(Punto solicitado) {
  if (puntoActual == Punto::Desconocido) {
    informar(F("ERROR: usa SET:BASE, SET:P1 o SET:P2 antes de una ruta"));
    return;
  }
  if (puntoActual == solicitado) {
    informarPunto(F("RECI ya esta en "), solicitado);
    mostrarRutaEnLcd("RECI ya esta en", solicitado);
    mostrarCara(CaraReci::Feliz);
    emitirEvento(F("ARRIVED"), solicitado);
    return;
  }
  if (!tiemposConfigurados()) {
    informar(F("ERROR: primero calibra los tiempos T1/T2"));
    return;
  }
  if (solicitado == Punto::Base && puntoActual != Punto::Base) {
    informar(F("La ruta recta no vuelve sola a BASE. Regresa RECI manualmente."));
    return;
  }
  if (puntoActual == Punto::P2) {
    informar(F("RECI ya termino la ruta. Regresalo manualmente a BASE."));
    return;
  }
  if (compuertaActiva != CompuertaActiva::Ninguna) {
    destinoPendienteCompuerta = solicitado;
    detenerMotores();
    mostrarLcd("Cierro compuerta", "Ruta en espera");
    informar(F("SEGURIDAD: ruta en espera hasta cerrar la compuerta."));
    return;
  }

  destino = solicitado;
  iniciarSiguienteTramo();
}

void actualizarRuta() {
  const unsigned long ahora = millis();

  // Pausa segura: RECI vuelve a andar solo cuando el ultrasónico lleva un
  // segundo entero sin ver ningún objeto a menos de 20 cm.
  if (modo == Modo::Emergencia) {
    if (hayObstaculoFrontal()) {
      frenteLibreDesde = 0;
      return;
    }

    if (frenteLibreDesde == 0) {
      frenteLibreDesde = ahora;
      mostrarLcd("Camino libre", "Reanudo pronto");
      return;
    }

    if (ahora - frenteLibreDesde < kFrenteLibreAntesDeReanudarMs) return;

    terminaTramoEn = ahora + tiempoRestantePausaMs;
    frenteLibreDesde = 0;
    avanzar();
    modo = Modo::EnRuta;
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Ruta reanudada", "Sigo la ruta");
    informar(F("Ruta reanudada automaticamente."));
    return;
  }

  if (modo != Modo::EnRuta) return;

  if (ahora - ultimoChequeoObstaculo >= kRevisionObstaculoMs) {
    ultimoChequeoObstaculo = ahora;
    if (hayObstaculoFrontal()) {
      detenerMotores();
      modo = Modo::Emergencia;
      tiempoRestantePausaMs =
          static_cast<long>(terminaTramoEn - ahora) > 0 ? terminaTramoEn - ahora : 0;
      frenteLibreDesde = 0;
      mostrarCara(CaraReci::Alerta);
      mostrarLcd("Obstaculo!", "Reanuda solo");
      emitirObstaculo();
      informar(F("EMERGENCIA: obstaculo frontal. Reanuda solo al despejar."));
      return;
    }
  }

  if (static_cast<long>(ahora - terminaTramoEn) < 0) return;

  detenerMotores();
  puntoActual = siguientePunto(puntoActual);
  mostrarCara(CaraReci::Feliz);
  mostrarRutaEnLcd("Llegue a", puntoActual);
  emitirEvento(F("ARRIVED"), puntoActual);
  informarPunto(F("Llegada estimada: "), puntoActual);

  if (puntoActual == destino) {
    destino = Punto::Desconocido;
    modo = Modo::Detenido;
    informar(F("RUTA COMPLETA"));
    return;
  }

  delay(250);  // pausa corta para estabilizar el chasis entre tramos.
  iniciarSiguienteTramo();
}

bool es(const char* texto, const char* esperado) {
  return strcmp(texto, esperado) == 0;
}

bool empiezaCon(const char* texto, const char* prefijo) {
  return strncmp(texto, prefijo, strlen(prefijo)) == 0;
}

bool permitirMovimientoManual() {
  if (compuertaActiva == CompuertaActiva::Ninguna) return true;

  detenerMotores();
  mostrarLcd("Cierra compuerta", "No puedo moverme");
  informar(F("SEGURIDAD: movimiento bloqueado; hay una compuerta abierta."));
  return false;
}

void procesarMensajeLcd(char* entrada) {
  // Formato enviado por la ESP32: CMD:LCD:linea 1|linea 2
  char* lineas = entrada + strlen("CMD:LCD:");
  char* separador = strchr(lineas, '|');
  if (separador == nullptr) {
    mostrarLcd(lineas, "");
    return;
  }
  *separador = '\0';
  mostrarLcd(lineas, separador + 1);
}

void procesarCaraEsp32(const char* entrada) {
  if (es(entrada, "CMD:FACE:happy")) {
    mostrarCara(CaraReci::Feliz);
  } else if (es(entrada, "CMD:FACE:thinking")) {
    mostrarCara(CaraReci::Movimiento);
  } else if (es(entrada, "CMD:FACE:confused")) {
    mostrarCara(CaraReci::Alerta);
  } else {
    // "idle" y cualquier valor futuro vuelven a la cara tranquila.
    mostrarCara(CaraReci::Lista);
  }
}

void procesarComando(char* entrada) {
  // Estos mensajes vienen de la ESP32-CAM. No mueven las ruedas; solo
  // actualizan las pantallas o abren una compuerta cuando RECI está quieto.
  if (empiezaCon(entrada, "CMD:LCD:")) {
    procesarMensajeLcd(entrada);
  } else if (empiezaCon(entrada, "CMD:FACE:")) {
    procesarCaraEsp32(entrada);
  } else if (empiezaCon(entrada, "CMD:QR:")) {
    mostrarLcd("Escanea el QR", "Para tus puntos");
    mostrarQrReal(entrada + strlen("CMD:QR:"));
  } else if (es(entrada, "VIDRIO") || es(entrada, "CMD:CLASSIFY:vidrio")) {
    abrirCompuerta(CompuertaActiva::Vidrio);
  } else if (es(entrada, "PLASTICO") || es(entrada, "CMD:CLASSIFY:plastico")) {
    abrirCompuerta(CompuertaActiva::Plastico);
  } else if (es(entrada, "F")) {
    if (!permitirMovimientoManual()) return;
    destino = Punto::Desconocido;
    avanzar();
    modo = Modo::ManualAdelante;
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Modo manual", "Adelante");
    informar(F("Manual: adelante"));
  } else if (es(entrada, "B")) {
    if (!permitirMovimientoManual()) return;
    destino = Punto::Desconocido;
    retroceder();
    modo = Modo::ManualAtras;
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Modo manual", "Atras");
    informar(F("Manual: atras"));
  } else if (es(entrada, "L")) {
    if (!permitirMovimientoManual()) return;
    destino = Punto::Desconocido;
    girarIzquierda();
    modo = Modo::ManualIzquierda;
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Modo manual", "Izquierda");
    informar(F("Manual: izquierda"));
  } else if (es(entrada, "R")) {
    if (!permitirMovimientoManual()) return;
    destino = Punto::Desconocido;
    girarDerecha();
    modo = Modo::ManualDerecha;
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Modo manual", "Derecha");
    informar(F("Manual: derecha"));
  } else if (es(entrada, "S")) {
    detenerTodo(F("DETENIDO"));
  } else if (es(entrada, "SET:BASE")) {
    puntoActual = Punto::Base;
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Hola, soy RECI", "Estoy en BASE");
    informar(F("Posicion confirmada: BASE"));
  } else if (es(entrada, "SET:P1")) {
    puntoActual = Punto::P1;
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Hola, soy RECI", "Estoy en P1");
    informar(F("Posicion confirmada: P1"));
  } else if (es(entrada, "SET:P2")) {
    puntoActual = Punto::P2;
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Hola, soy RECI", "Estoy en P2");
    informar(F("Posicion confirmada: P2"));
  } else if (es(entrada, "P1")) {
    irAPunto(Punto::P1);
  } else if (es(entrada, "P2")) {
    irAPunto(Punto::P2);
  } else if (es(entrada, "BASE")) {
    irAPunto(Punto::Base);
  } else if (es(entrada, "RESUME")) {
    if (modo != Modo::Emergencia) {
      informar(F("No hay una emergencia activa."));
    } else if (hayObstaculoFrontal()) {
      informar(F("El obstaculo sigue al frente."));
    } else if (destino == Punto::Desconocido) {
      modo = Modo::Detenido;
      informar(F("No hay ruta pendiente."));
    } else {
      terminaTramoEn = millis() + tiempoRestantePausaMs;
      frenteLibreDesde = 0;
      avanzar();
      modo = Modo::EnRuta;
      mostrarCara(CaraReci::Movimiento);
      mostrarLcd("Ruta reanudada", "Con cuidado");
      informar(F("Ruta reanudada."));
    }
  } else if (es(entrada, "STATUS")) {
    informarPunto(F("Posicion: "), puntoActual);
    informarPunto(F("Destino: "), destino);
  } else if (es(entrada, "HELP")) {
    Serial.println(F("F B L R S | SET:BASE/P1/P2 | P1 P2 | VIDRIO PLASTICO | STATUS"));
  } else {
    informar(F("ERROR: comando invalido. Escribe HELP."));
  }
}

void leerSerial(Stream& puerto) {
  while (puerto.available() > 0) {
    const char caracter = static_cast<char>(puerto.read());
    if (caracter == '\r') continue;
    if (caracter == '\n') {
      if (longitudComando > 0) {
        comando[longitudComando] = '\0';
        Serial.print(F("RX <- "));
        Serial.println(comando);
        procesarComando(comando);
        longitudComando = 0;
      }
      continue;
    }
    if (longitudComando >= kComandoMax) {
      longitudComando = 0;
      informar(F("ERROR: comando demasiado largo"));
      continue;
    }
    comando[longitudComando++] = caracter;
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);
  Serial2.begin(kSerialBaud);  // ESP32-CAM: Mega RX2=17, TX2=16.

  const uint8_t pinesMotor[] = {kIzqIn1, kIzqIn2, kIzqIn3, kIzqIn4,
                                kDerIn1, kDerIn2, kDerIn3, kDerIn4};
  for (uint8_t pin : pinesMotor) pinMode(pin, OUTPUT);
  detenerMotores();

  pinMode(kTrigFrontal, OUTPUT);
  pinMode(kEchoFrontal, INPUT);
  digitalWrite(kTrigFrontal, LOW);
  pinMode(kPirPin, INPUT);

  servoVidrio.attach(kServoVidrioPin);
  servoPlastico.attach(kServoPlasticoPin);
  cerrarCompuertas();

  Wire.begin();
  Wire.setClock(400000L);
  oledDisponible = oled.begin(SSD1306_SWITCHCAPVCC, kDireccionOled);
  if (oledDisponible) {
    mostrarCara(CaraReci::Lista);
    Serial.println(F("OLED: carita RECI lista."));
  } else {
    // El robot sigue operativo aunque la pantalla se desconecte.
    Serial.println(F("AVISO: OLED no encontrada en 0x3C."));
  }

  if (i2cResponde(kDireccionLcd)) {
    lcd.init();
    lcd.backlight();
    lcdDisponible = true;
    mostrarLcd("Hola, soy RECI", "Estoy listo");
    Serial.println(F("LCD: lista en 0x27."));
  } else {
    Serial.println(F("AVISO: LCD no encontrada en 0x27."));
  }

  Serial.println(F("RECI Ruta Demo lista. El robot esta detenido."));
  Serial.println(F("VERSION: OLED + LCD + AUTO-REANUDAR v2"));
  Serial.println(F("Primero: SET:BASE. Luego: F/B/L/R/S o P1/P2."));
  Serial.println(F("Ajusta T1/T2 antes de usar la ruta recta."));
}

void loop() {
  leerSerial(Serial);   // Pruebas por USB / Monitor Serial.
  if (kEsp32CamConectada) leerSerial(Serial2);  // Órdenes futuras de la ESP32-CAM.
  actualizarRuta();
  actualizarPresencia();
  actualizarCompuerta();
}
