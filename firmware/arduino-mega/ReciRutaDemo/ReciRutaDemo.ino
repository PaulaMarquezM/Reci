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
// El firmware completo atiende interrupciones de servos y UART; 25 ms evita
// falsos timeouts sin permitir que un bus I2C averiado congele el robot.
constexpr unsigned long kI2cTimeoutUs = 25000UL;
// El escaner y los dos modulos responden de forma estable a la velocidad
// I2C estandar. El bus compartido no es fiable a 400 kHz con este cableado.
constexpr unsigned long kI2cClockHz = 100000UL;
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
constexpr unsigned long kPirWarmupMs = 30000UL;
constexpr unsigned long kEsperaPresenciaMs = 10000UL;
// Tras confirmar la llegada, la ESP actualiza la llamada, la posición y el
// saludo. Esperamos antes de emitir PRESENCIA para que esos HTTP/pulsos no se
// solapen con el inicio automático de la cámara.
constexpr unsigned long kEsperaPresenciaTrasLlegadaMs = 6000UL;

// CALIBRACION: reemplaza 0 por el tiempo medido en milisegundos.
// Mide cada tramo tres veces y usa el promedio. Los dos tramos son rectos,
// siempre en la dirección BASE -> P1 -> P2.
constexpr unsigned long kBaseAP1Ms = 8000UL;
constexpr unsigned long kP1AP2Ms = 8000UL;

// El Monitor Serial USB se mantiene en 9600 para las pruebas manuales.
constexpr unsigned long kUsbSerialBaud = 9600UL;
// El regreso Mega -> ESP usa pulsos LOW por D16 hacia GPIO13. Es el mismo
// cable con divisor que antes llevaba UART, pero los pulsos son mucho más
// tolerantes al cableado largo y al ruido eléctrico del robot.
constexpr unsigned long kPulsoMegaLlegadaP1Ms = 1800UL;
constexpr unsigned long kPulsoMegaLlegadaP2Ms = 2400UL;
constexpr unsigned long kPulsoMegaPresenciaMs = 3000UL;
constexpr unsigned long kPulsoMegaPongMs = 3600UL;
// Confirmación corta de que el Mega aceptó la orden y escribió el ángulo del
// servo. La ESP espera esta confirmación antes de registrar puntos.
constexpr unsigned long kPulsoMegaCompuertaConfirmadaMs = 800UL;
// La ESP mantiene 300 ms de separación después de enviar @P/@V. Retrasar la
// confirmación garantiza que ya esté escuchando cuando empiece el pulso.
constexpr unsigned long kRetrasoConfirmacionCompuertaMs = 400UL;
constexpr unsigned long kSeparacionPulsoMegaMs = 200UL;
// Diagnóstico sin multímetro: conecta un jumper desde el mismo cable
// ESP GPIO14 -> Mega D17 hacia A8. A8 es solo entrada, por lo que no altera
// la comunicación ni entrega voltaje a la ESP32-CAM.
constexpr uint8_t kEspTxSensePin = A8;
// Para comparar contra la alimentación real de la ESP, conecta también
// ESP 3V3 -> Mega A9. A9 es únicamente entrada.
constexpr uint8_t kEsp3v3SensePin = A9;
constexpr uint8_t kMegaTx2Pin = 16;
// ESP GPIO14 llega directo a D17. En lugar de decodificarlo como UART, el
// Mega mide pulsos HIGH de varios cientos de milisegundos. Así una trama
// corrupta no puede convertirse en una orden del robot.
constexpr uint8_t kPulsoEspPin = 17;
constexpr unsigned long kIgnorarPulsosAlArrancarMs = 3500UL;
constexpr unsigned long kToleranciaPulsoMs = 120UL;
constexpr unsigned long kPulsoAnalizarMs = 300UL;
constexpr unsigned long kPulsoDesconocidoMs = 600UL;
constexpr unsigned long kPulsoPlasticoMs = 900UL;
constexpr unsigned long kPulsoVidrioMs = 1200UL;
constexpr unsigned long kPulsoP1Ms = 1500UL;
constexpr unsigned long kPulsoP2Ms = 1800UL;
constexpr unsigned long kPulsoSaludoMs = 2100UL;
constexpr unsigned long kPulsoBotellaMs = 2400UL;
constexpr unsigned long kPulsoListoMs = 2700UL;
constexpr unsigned long kPulsoErrorMs = 3000UL;
constexpr unsigned long kPulsoPuntosDirectosMs = 3300UL;
constexpr unsigned long kPulsoPuntosAppMs = 3600UL;
constexpr unsigned long kPulsoGraciasMs = 3900UL;
constexpr unsigned long kPulsoPruebaMs = 4200UL;
// Transporte del claim_code real hacia la OLED. El primer pulso abre una
// recepción de ocho caracteres; los ocho siguientes codifican 0-9 y A-Z por
// duración. Solo se interpreta esta familia mientras la recepción QR está
// activa, así nunca se convierte en órdenes de ruta o compuerta.
constexpr unsigned long kPulsoQrInicioMs = 4500UL;
constexpr unsigned long kPulsoQrCaracterBaseMs = 180UL;
constexpr unsigned long kPulsoQrCaracterPasoMs = 60UL;
constexpr unsigned long kToleranciaQrCaracterMs = 25UL;
constexpr unsigned long kTimeoutRecepcionQrMs = 3000UL;
constexpr char kAlfabetoCodigoQr[] = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
constexpr uint8_t kLongitudCodigoQr = 8;
constexpr uint8_t kEspTxSenseSamples = 32;
constexpr uint16_t kAdcFullScale = 1023U;
// Los mensajes de la ESP32 incluyen, por ejemplo,
// "CMD:LCD:Hola, Pau|Soy RECI". Deja espacio suficiente para el saludo
// sin alterar los comandos cortos de movimiento.
constexpr size_t kComandoMax = 64;

enum class Punto : uint8_t { Desconocido, Base, P1, P2 };
enum class Modo : uint8_t { Detenido, ManualAdelante, ManualAtras, ManualIzquierda,
                            ManualDerecha, EnRuta, Emergencia };
enum class CompuertaActiva : uint8_t { Ninguna, Vidrio, Plastico };

// La demostración se enciende con RECI físicamente colocado en BASE. Guardar
// ese estado desde el arranque permite que una llamada de la app salga sola,
// sin requerir escribir SET:BASE en el Monitor Serial. No mueve motores.
// Si alguna vez se enciende fuera de BASE, confirma la posición real con
// SET:P1 o SET:P2 antes de aceptar una llamada.
Punto puntoActual = Punto::Base;
Punto destino = Punto::Desconocido;
Modo modo = Modo::Detenido;
unsigned long terminaTramoEn = 0;
unsigned long ultimoChequeoObstaculo = 0;
unsigned long tiempoRestantePausaMs = 0;
unsigned long frenteLibreDesde = 0;
unsigned long proximaPresenciaPermitidaEn = 0;
bool pirListoParaNuevoEvento = false;
CompuertaActiva compuertaActiva = CompuertaActiva::Ninguna;
unsigned long cerrarCompuertaEn = 0;
Punto destinoPendienteCompuerta = Punto::Desconocido;
bool pulsoEspActivo = false;
unsigned long inicioPulsoEspEn = 0;
unsigned long habilitarPulsosEspEn = 0;
bool recibiendoCodigoQr = false;
char codigoQrRecibido[kLongitudCodigoQr + 1] = {};
uint8_t longitudCodigoQrRecibido = 0;
unsigned long ultimoCaracterQrEn = 0;

struct EntradaSerial {
  char comando[kComandoMax + 1] = {};
  size_t longitud = 0;
  // Si una trama llega dañada o supera el límite, se ignora hasta el salto
  // de línea. Así sus bytes restantes no se interpretan como comandos nuevos.
  bool descartarHastaNuevaLinea = false;
};

// El USB conserva un buffer de texto para las pruebas manuales.
EntradaSerial entradaUsb;

bool i2cResponde(uint8_t direccion) {
  Wire.clearWireTimeoutFlag();
  Wire.beginTransmission(direccion);
  const uint8_t estado = Wire.endTransmission();
  const bool expiro = Wire.getWireTimeoutFlag();
  Serial.print(F("DIAG I2C 0x"));
  if (direccion < 0x10) Serial.print('0');
  Serial.print(direccion, HEX);
  Serial.print(F(": estado="));
  Serial.print(estado);
  Serial.print(F(", timeout="));
  Serial.println(expiro ? F("si") : F("no"));
  Wire.clearWireTimeoutFlag();
  return !expiro && estado == 0;
}

void diagnosticarLineasI2c(const __FlashStringHelper* etapa) {
  Serial.print(F("DIAG LINEAS "));
  Serial.print(etapa);
  Serial.print(F(": SDA="));
  Serial.print(digitalRead(SDA));
  Serial.print(F(", SCL="));
  Serial.print(digitalRead(SCL));
  Serial.print(F(", IRQ="));
  Serial.println((SREG & _BV(SREG_I)) != 0 ? F("on") : F("off"));
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
// Se usan líneas y formas compactas, no arcos superpuestos: en esta OLED los
// tres arcos anteriores parecían rayas cuando se veía desde lejos.
void mostrarCara(CaraReci cara) {
  if (!oledDisponible || cara == caraActual) return;

  qrVisible = false;
  caraActual = cara;
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);

  if (cara == CaraReci::Movimiento) {
    // Mira hacia delante mientras avanza.
    oled.fillRoundRect(27, 15, 25, 18, 7, SSD1306_WHITE);
    oled.fillRoundRect(76, 15, 25, 18, 7, SSD1306_WHITE);
    oled.fillCircle(44, 24, 4, SSD1306_BLACK);
    oled.fillCircle(93, 24, 4, SSD1306_BLACK);
    oled.drawLine(51, 48, 77, 48, SSD1306_WHITE);
    oled.drawLine(51, 49, 77, 49, SSD1306_WHITE);
  } else if (cara == CaraReci::Feliz) {
    // Ojos ^ ^ y una sonrisa limpia: llegó o detectó a una persona.
    oled.drawLine(30, 29, 39, 20, SSD1306_WHITE);
    oled.drawLine(39, 20, 48, 29, SSD1306_WHITE);
    oled.drawLine(80, 29, 89, 20, SSD1306_WHITE);
    oled.drawLine(89, 20, 98, 29, SSD1306_WHITE);
    oled.drawLine(47, 43, 55, 51, SSD1306_WHITE);
    oled.drawLine(55, 51, 73, 51, SSD1306_WHITE);
    oled.drawLine(73, 51, 81, 43, SSD1306_WHITE);
    oled.drawLine(47, 44, 55, 52, SSD1306_WHITE);
    oled.drawLine(55, 52, 73, 52, SSD1306_WHITE);
    oled.drawLine(73, 52, 81, 44, SSD1306_WHITE);
  } else if (cara == CaraReci::Alerta) {
    // Ojos redondos y boca "o": hay un obstáculo al frente.
    oled.fillCircle(39, 23, 9, SSD1306_WHITE);
    oled.fillCircle(89, 23, 9, SSD1306_WHITE);
    oled.fillCircle(39, 23, 3, SSD1306_BLACK);
    oled.fillCircle(89, 23, 3, SSD1306_BLACK);
    oled.drawRoundRect(57, 40, 14, 16, 6, SSD1306_WHITE);
  } else {
    // Cara tranquila mientras espera en BASE/P1/P2.
    oled.fillRoundRect(27, 14, 25, 20, 8, SSD1306_WHITE);
    oled.fillRoundRect(76, 14, 25, 20, 8, SSD1306_WHITE);
    oled.fillCircle(39, 24, 4, SSD1306_BLACK);
    oled.fillCircle(88, 24, 4, SSD1306_BLACK);
    oled.drawLine(48, 43, 55, 50, SSD1306_WHITE);
    oled.drawLine(55, 50, 73, 50, SSD1306_WHITE);
    oled.drawLine(73, 50, 80, 43, SSD1306_WHITE);
    oled.drawLine(48, 44, 55, 51, SSD1306_WHITE);
    oled.drawLine(55, 51, 73, 51, SSD1306_WHITE);
    oled.drawLine(73, 51, 80, 44, SSD1306_WHITE);
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

bool abrirCompuerta(CompuertaActiva solicitada) {
  // Las tapas solo se abren cuando RECI está quieto en una parada.
  if (modo != Modo::Detenido) {
    informar(F("No abro compuerta mientras RECI se mueve."));
    return false;
  }
  if (compuertaActiva != CompuertaActiva::Ninguna) {
    informar(F("Una compuerta ya esta abierta."));
    return false;
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
  return true;
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

void enviarPulsoAEsp(unsigned long duracion,
                     const __FlashStringHelper* etiqueta) {
  // D16 queda normalmente HIGH. El divisor 1k/2k entrega ~3.3 V al GPIO13.
  // Un pulso LOW no puede sobrepasar el voltaje permitido por la ESP32.
  digitalWrite(kMegaTx2Pin, LOW);
  delay(duracion);
  digitalWrite(kMegaTx2Pin, HIGH);
  delay(kSeparacionPulsoMegaMs);

  Serial.print(F("RECI -> ESP: pulso "));
  Serial.print(etiqueta);
  Serial.print(F(" de "));
  Serial.print(duracion);
  Serial.println(F(" ms."));
}

void emitirLlegada(Punto punto) {
  if (punto == Punto::P1) {
    enviarPulsoAEsp(kPulsoMegaLlegadaP1Ms, F("LLEGADA P1"));
  } else if (punto == Punto::P2) {
    enviarPulsoAEsp(kPulsoMegaLlegadaP2Ms, F("LLEGADA P2"));
  }
  proximaPresenciaPermitidaEn = millis() + kEsperaPresenciaTrasLlegadaMs;
}

void actualizarPresencia() {
  const bool hayPresencia = digitalRead(kPirPin) == HIGH;
  if (!hayPresencia) {
    // Exigimos que el PIR vuelva a LOW antes de aceptar otra persona. Esto
    // evita iniciar varias clasificaciones mientras una misma señal sigue
    // activa durante varios segundos.
    pirListoParaNuevoEvento = true;
    return;
  }

  if (modo != Modo::Detenido) return;
  if (compuertaActiva != CompuertaActiva::Ninguna) return;
  if (!pirListoParaNuevoEvento) return;
  if (static_cast<long>(millis() - proximaPresenciaPermitidaEn) < 0) return;

  pirListoParaNuevoEvento = false;
  proximaPresenciaPermitidaEn = millis() + kEsperaPresenciaMs;
  enviarPulsoAEsp(kPulsoMegaPresenciaMs, F("PRESENCIA"));
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
    emitirLlegada(solicitado);
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
      informar(F("EMERGENCIA: obstaculo frontal. Reanuda solo al despejar."));
      return;
    }
  }

  if (static_cast<long>(ahora - terminaTramoEn) < 0) return;

  detenerMotores();
  puntoActual = siguientePunto(puntoActual);
  mostrarCara(CaraReci::Feliz);
  mostrarRutaEnLcd("Llegue a", puntoActual);
  emitirLlegada(puntoActual);
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

float leerPromedioAdc(uint8_t pin) {
  // Se descarta la primera lectura después de cambiar de canal ADC.
  static_cast<void>(analogRead(pin));
  delay(2);

  uint32_t suma = 0;
  for (uint8_t muestra = 0; muestra < kEspTxSenseSamples; ++muestra) {
    suma += static_cast<uint16_t>(analogRead(pin));
    delay(1);
  }
  return static_cast<float>(suma) / kEspTxSenseSamples;
}

void diagnosticarVoltajeEspTx() {
  const float lecturaGpio14 = leerPromedioAdc(kEspTxSensePin);
  const float lectura3v3 = leerPromedioAdc(kEsp3v3SensePin);
  if (lectura3v3 < 100.0F) {
    Serial.println(F("DIAG: falta conectar ESP 3V3 -> Mega A9."));
    return;
  }

  const float porcentaje3v3 = lecturaGpio14 * 100.0F / lectura3v3;

  Serial.print(F("DIAG GPIO14 A8="));
  Serial.print(lecturaGpio14, 0);
  Serial.print(F("/"));
  Serial.print(kAdcFullScale);
  Serial.print(F(" | ESP 3V3 A9="));
  Serial.print(lectura3v3, 0);
  Serial.print(F("/"));
  Serial.print(kAdcFullScale);
  Serial.print(F(" | GPIO14 equivale al "));
  Serial.print(porcentaje3v3, 0);
  Serial.println(F("% de 3V3"));
}

void rastrearSiA8SigueD16() {
  Serial.println(F("TRACE16 desactivado: D16 ahora envia pulsos a la ESP."));
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

// Protocolo compacto ESP32 -> Mega. Cada orden actualiza una pantalla y la
// carita en una sola operación; evita enviar "CMD:FACE" y "CMD:LCD" seguidos
// mientras la OLED aún está redibujándose por I2C.
void mostrarSaludoEsp32(const char* nombre) {
  char linea1[17] = "Hola, ";
  if (nombre != nullptr && nombre[0] != '\0') {
    const size_t espacio = sizeof(linea1) - strlen(linea1) - 1;
    strncat(linea1, nombre, espacio);
  }
  mostrarCara(CaraReci::Lista);
  mostrarLcd(linea1, "Soy RECI");
}

bool procesarComandoCompacto(char* entrada) {
  if (es(entrada, "@S")) {
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Hola, soy RECI", "Preparando camara");
  } else if (es(entrada, "@R")) {
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Hola, soy Reci", "Envia C para leer");
  } else if (es(entrada, "@H")) {
    mostrarCara(CaraReci::Feliz);
    mostrarLcd("Hola, soy RECI", "Recicla y gana");
  } else if (es(entrada, "@B")) {
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Ubica botella", "Frente a camara");
  } else if (es(entrada, "@A")) {
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Analizando residuo", "No lo retires");
  } else if (es(entrada, "@U")) {
    mostrarCara(CaraReci::Alerta);
    mostrarLcd("No estoy seguro", "Intenta de nuevo");
  } else if (es(entrada, "@P")) {
    abrirCompuerta(CompuertaActiva::Plastico);
  } else if (es(entrada, "@V")) {
    abrirCompuerta(CompuertaActiva::Vidrio);
  } else if (es(entrada, "@L")) {
    mostrarLcd("Gracias!", "Puntos agregados");
  } else if (es(entrada, "@O")) {
    mostrarLcd("Gracias!", "Tapa abierta");
  } else if (empiezaCon(entrada, "@G:")) {
    mostrarSaludoEsp32(entrada + strlen("@G:"));
  } else if (empiezaCon(entrada, "@Q:")) {
    mostrarLcd("Escanea el QR", "Para tus puntos");
    mostrarQrReal(entrada + strlen("@Q:"));
  } else {
    return false;
  }
  return true;
}

void procesarComando(char* entrada) {
  // Estos mensajes vienen de la ESP32-CAM. No mueven las ruedas; solo
  // actualizan las pantallas o abren una compuerta cuando RECI está quieto.
  if (procesarComandoCompacto(entrada)) {
    return;
  } else if (empiezaCon(entrada, "CMD:LCD:")) {
    procesarMensajeLcd(entrada);
  } else if (empiezaCon(entrada, "CMD:FACE:")) {
    procesarCaraEsp32(entrada);
  } else if (empiezaCon(entrada, "CMD:QR:")) {
    mostrarLcd("Escanea el QR", "Para tus puntos");
    mostrarQrReal(entrada + strlen("CMD:QR:"));
  } else if (es(entrada, "PING")) {
    // Diagnóstico del regreso Mega -> ESP sin mover ni abrir nada.
    mostrarLcd("PULSO A ESP", "Enviando prueba");
    enviarPulsoAEsp(kPulsoMegaPongMs, F("PONG"));
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
  } else if (es(entrada, "V14")) {
    diagnosticarVoltajeEspTx();
  } else if (es(entrada, "TRACE16")) {
    rastrearSiA8SigueD16();
  } else if (es(entrada, "STATUS")) {
    informarPunto(F("Posicion: "), puntoActual);
    informarPunto(F("Destino: "), destino);
  } else if (es(entrada, "HELP")) {
    Serial.println(F("F B L R S | SET:BASE/P1/P2 | P1 P2 | VIDRIO PLASTICO | V14 TRACE16 | STATUS"));
  } else {
    informar(F("ERROR: comando invalido. Escribe HELP."));
  }
}

bool coincidePulsoEsp(unsigned long duracion, unsigned long esperado) {
  const unsigned long minimo = esperado > kToleranciaPulsoMs
      ? esperado - kToleranciaPulsoMs
      : 0;
  return duracion >= minimo && duracion <= esperado + kToleranciaPulsoMs;
}

void iniciarRecepcionCodigoQr() {
  recibiendoCodigoQr = true;
  longitudCodigoQrRecibido = 0;
  codigoQrRecibido[0] = '\0';
  ultimoCaracterQrEn = millis();
  mostrarCara(CaraReci::Lista);
  mostrarLcd("Generando QR", "Espera un poco");
  informar(F("QR: inicio de codigo recibido."));
}

void cancelarRecepcionCodigoQr(const __FlashStringHelper* motivo) {
  recibiendoCodigoQr = false;
  longitudCodigoQrRecibido = 0;
  codigoQrRecibido[0] = '\0';
  mostrarCara(CaraReci::Alerta);
  mostrarLcd("QR no valido", "Intenta de nuevo");
  informar(motivo);
}

bool decodificarCaracterQr(unsigned long duracion, char& caracter) {
  if (duracion + kToleranciaQrCaracterMs < kPulsoQrCaracterBaseMs) return false;

  const unsigned long ajustado = duracion - kPulsoQrCaracterBaseMs;
  const uint8_t indice = static_cast<uint8_t>(
      (ajustado + (kPulsoQrCaracterPasoMs / 2)) / kPulsoQrCaracterPasoMs);
  const uint8_t totalCaracteres = sizeof(kAlfabetoCodigoQr) - 1;
  if (indice >= totalCaracteres) return false;

  const unsigned long esperado = kPulsoQrCaracterBaseMs +
      static_cast<unsigned long>(indice) * kPulsoQrCaracterPasoMs;
  const unsigned long diferencia = duracion > esperado
      ? duracion - esperado
      : esperado - duracion;
  if (diferencia > kToleranciaQrCaracterMs) return false;

  caracter = kAlfabetoCodigoQr[indice];
  return true;
}

void recibirCaracterCodigoQr(unsigned long duracion) {
  char caracter = '\0';
  if (!decodificarCaracterQr(duracion, caracter)) {
    cancelarRecepcionCodigoQr(F("QR: pulso de caracter invalido."));
    return;
  }

  codigoQrRecibido[longitudCodigoQrRecibido++] = caracter;
  codigoQrRecibido[longitudCodigoQrRecibido] = '\0';
  ultimoCaracterQrEn = millis();

  if (longitudCodigoQrRecibido < kLongitudCodigoQr) return;

  recibiendoCodigoQr = false;
  mostrarQrReal(codigoQrRecibido);
  mostrarLcd("Escanea el QR", "Para tus puntos");
  Serial.print(F("QR: codigo real listo: "));
  Serial.println(codigoQrRecibido);
}

void actualizarRecepcionCodigoQr() {
  if (!recibiendoCodigoQr) return;
  if (millis() - ultimoCaracterQrEn <= kTimeoutRecepcionQrMs) return;
  cancelarRecepcionCodigoQr(F("QR: tiempo agotado al recibir codigo."));
}

void procesarPulsoEsp(unsigned long duracion) {
  // Mientras se reciben los ocho símbolos QR, estas duraciones no son
  // comandos normales: son caracteres 0-9/A-Z.
  if (recibiendoCodigoQr) {
    recibirCaracterCodigoQr(duracion);
    return;
  }

  Serial.print(F("RECI: pulso ESP de "));
  Serial.print(duracion);
  Serial.println(F(" ms."));

  if (coincidePulsoEsp(duracion, kPulsoQrInicioMs)) {
    iniciarRecepcionCodigoQr();
  } else if (coincidePulsoEsp(duracion, kPulsoAnalizarMs)) {
    mostrarCara(CaraReci::Movimiento);
    mostrarLcd("Analizando residuo", "No lo retires");
  } else if (coincidePulsoEsp(duracion, kPulsoDesconocidoMs)) {
    mostrarCara(CaraReci::Alerta);
    mostrarLcd("No estoy seguro", "Intenta de nuevo");
  } else if (coincidePulsoEsp(duracion, kPulsoPlasticoMs)) {
    if (abrirCompuerta(CompuertaActiva::Plastico)) {
      delay(kRetrasoConfirmacionCompuertaMs);
      enviarPulsoAEsp(kPulsoMegaCompuertaConfirmadaMs,
                      F("COMPUERTA PLASTICO CONFIRMADA"));
    }
  } else if (coincidePulsoEsp(duracion, kPulsoVidrioMs)) {
    if (abrirCompuerta(CompuertaActiva::Vidrio)) {
      delay(kRetrasoConfirmacionCompuertaMs);
      enviarPulsoAEsp(kPulsoMegaCompuertaConfirmadaMs,
                      F("COMPUERTA VIDRIO CONFIRMADA"));
    }
  } else if (coincidePulsoEsp(duracion, kPulsoP1Ms)) {
    irAPunto(Punto::P1);
  } else if (coincidePulsoEsp(duracion, kPulsoP2Ms)) {
    irAPunto(Punto::P2);
  } else if (coincidePulsoEsp(duracion, kPulsoSaludoMs)) {
    mostrarCara(CaraReci::Feliz);
    mostrarLcd("Hola, soy RECI", "Recicla y gana");
  } else if (coincidePulsoEsp(duracion, kPulsoBotellaMs)) {
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Ubica botella", "Frente a camara");
  } else if (coincidePulsoEsp(duracion, kPulsoListoMs)) {
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Hola, soy RECI", "Listo para usar");
  } else if (coincidePulsoEsp(duracion, kPulsoErrorMs)) {
    mostrarCara(CaraReci::Alerta);
    mostrarLcd("Error de ESP", "Revisa camara");
  } else if (coincidePulsoEsp(duracion, kPulsoPuntosDirectosMs)) {
    mostrarCara(CaraReci::Feliz);
    mostrarLcd("Gracias!", "Puntos agregados");
  } else if (coincidePulsoEsp(duracion, kPulsoPuntosAppMs)) {
    mostrarCara(CaraReci::Lista);
    mostrarLcd("Abre la app", "Para tus puntos");
  } else if (coincidePulsoEsp(duracion, kPulsoGraciasMs)) {
    mostrarCara(CaraReci::Feliz);
    mostrarLcd("Gracias!", "Tapa cerrada");
  } else if (coincidePulsoEsp(duracion, kPulsoPruebaMs)) {
    mostrarLcd("PULSO ESP", "Mega recibe OK");
    informar(F("PULSO ESP -> Mega OK."));
  } else {
    informar(F("PULSO ESP desconocido; ignorado."));
  }
}

void actualizarPulsoEsp() {
  const bool nivelAlto = digitalRead(kPulsoEspPin) == HIGH;
  const unsigned long ahora = millis();

  // GPIO14 puede emitir niveles transitorios al arrancar la ESP32-CAM. Se
  // ignoran los primeros segundos para que nunca se interpreten como ruta o
  // apertura de compuerta.
  if (static_cast<long>(ahora - habilitarPulsosEspEn) < 0) {
    pulsoEspActivo = nivelAlto;
    if (nivelAlto) inicioPulsoEspEn = ahora;
    return;
  }

  if (nivelAlto && !pulsoEspActivo) {
    pulsoEspActivo = true;
    inicioPulsoEspEn = ahora;
    return;
  }

  if (!nivelAlto && pulsoEspActivo) {
    pulsoEspActivo = false;
    if (inicioPulsoEspEn < habilitarPulsosEspEn) return;
    procesarPulsoEsp(ahora - inicioPulsoEspEn);
  }
}

void leerSerial(Stream& puerto, EntradaSerial& entrada) {
  while (puerto.available() > 0) {
    const char caracter = static_cast<char>(puerto.read());
    if (caracter == '\r') continue;
    if (caracter == '\n') {
      if (!entrada.descartarHastaNuevaLinea && entrada.longitud > 0) {
        entrada.comando[entrada.longitud] = '\0';
        procesarComando(entrada.comando);
      }
      entrada.longitud = 0;
      entrada.descartarHastaNuevaLinea = false;
      continue;
    }
    if (entrada.descartarHastaNuevaLinea) continue;
    if (entrada.longitud >= kComandoMax) {
      entrada.longitud = 0;
      entrada.descartarHastaNuevaLinea = true;
      informar(F("ERROR: comando demasiado largo; trama descartada."));
      continue;
    }
    entrada.comando[entrada.longitud++] = caracter;
  }
}

}  // namespace

void setup() {
  Serial.begin(kUsbSerialBaud);
  delay(250);
  Serial.println(F("BOOT: Mega iniciado a 9600 baud."));
  Serial.println(F("POSICION INICIAL: BASE (modo demo)."));
  Serial.flush();
  pinMode(SDA, INPUT_PULLUP);
  pinMode(SCL, INPUT_PULLUP);
  delay(5);
  diagnosticarLineasI2c(F("al inicio"));
  // Comunicación bidireccional robusta por pulsos:
  //   ESP GPIO14 -> Mega D17 (HIGH)
  //   Mega D16 -> divisor -> ESP GPIO13 (LOW)
  pinMode(kMegaTx2Pin, OUTPUT);
  digitalWrite(kMegaTx2Pin, HIGH);
  pinMode(kPulsoEspPin, INPUT);
  habilitarPulsosEspEn = millis() + kIgnorarPulsosAlArrancarMs;
  Serial.println(F("PASO 1: pulsos bidireccionales iniciados."));
  Serial.println(F("MODO: GPIO14->D17 y D16->GPIO13 por pulsos."));
  diagnosticarLineasI2c(F("despues de Serial2"));

  const uint8_t pinesMotor[] = {kIzqIn1, kIzqIn2, kIzqIn3, kIzqIn4,
                                kDerIn1, kDerIn2, kDerIn3, kDerIn4};
  for (uint8_t pin : pinesMotor) pinMode(pin, OUTPUT);
  detenerMotores();
  Serial.println(F("PASO 2: motores detenidos."));
  diagnosticarLineasI2c(F("despues de motores"));

  pinMode(kTrigFrontal, OUTPUT);
  pinMode(kEchoFrontal, INPUT);
  digitalWrite(kTrigFrontal, LOW);
  pinMode(kPirPin, INPUT);
  proximaPresenciaPermitidaEn = millis() + kPirWarmupMs;
  Serial.println(F("PASO 3: sensores configurados."));
  diagnosticarLineasI2c(F("despues de sensores"));

  Serial.println(F("PASO 4: iniciando servos."));
  servoVidrio.attach(kServoVidrioPin);
  diagnosticarLineasI2c(F("despues de servo vidrio"));
  servoPlastico.attach(kServoPlasticoPin);
  diagnosticarLineasI2c(F("despues de servo plastico"));
  cerrarCompuertas();
  Serial.println(F("PASO 5: servos cerrados."));
  diagnosticarLineasI2c(F("despues de cerrar servos"));

  Serial.println(F("PASO 6: iniciando bus I2C."));
  pinMode(SDA, INPUT_PULLUP);
  pinMode(SCL, INPUT_PULLUP);
  delay(5);
  diagnosticarLineasI2c(F("antes de Wire"));
  Wire.begin();
  Wire.setWireTimeout(kI2cTimeoutUs, true);
  Wire.setClock(kI2cClockHz);
  delay(5);
  diagnosticarLineasI2c(F("despues de Wire"));
  Serial.println(F("PASO 7: buscando OLED en 0x3C."));
  if (i2cResponde(kDireccionOled)) {
    Serial.println(F("PASO 8: OLED detectada; iniciando."));
    oledDisponible = oled.begin(SSD1306_SWITCHCAPVCC, kDireccionOled);
    if (oledDisponible) {
      mostrarCara(CaraReci::Lista);
      Serial.println(F("OLED: carita RECI lista."));
    } else {
      Serial.println(F("AVISO: OLED detectada pero no pudo iniciar."));
    }
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
  leerSerial(Serial, entradaUsb);  // Pruebas por USB / Monitor Serial.
  actualizarPulsoEsp();             // ESP GPIO14 -> Mega D17, sin UART.
  actualizarRecepcionCodigoQr();    // Completa o cancela un QR incompleto.
  actualizarRuta();
  actualizarPresencia();
  actualizarCompuerta();
}
