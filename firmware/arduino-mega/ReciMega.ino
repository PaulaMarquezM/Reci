// ============================================================
// Reci · sketch principal para Arduino Mega 2560
//
// Responsabilidades actuales:
//   - Recibir por Serial2 la clasificación ya confirmada por el ESP32-CAM.
//   - Abrir SOLO la compuerta correspondiente durante 5 segundos.
//   - Mostrar el estado del robot en la cara OLED.
//   - Seguir la cinta de navegación cuando se lo piden (ver Navigation.h) —
//     por ahora activable a mano con M/P por el Monitor Serial (USB),
//     mientras no existan los puntos fijos reales en Supabase para armar
//     el comando CMD:MOVE desde el cloud (bloqueante anotado en PLAN.md).
//
// Hardware documentado:
//   D3  -> servo de vidrio (compuerta izquierda)
//   D4  -> servo de plástico (compuerta derecha)
//   D5-D12  -> motores (dueño: Navigation.h — ver ese archivo para el detalle)
//   D16/TX2, D17/RX2 -> ESP32-CAM
//   D20/SDA, D21/SCL -> OLED SSD1306 + LCD 16x2 + MPU (bus I2C compartido)
//   D30-D34 -> sensores de línea IR (dueño: Navigation.h)
//
// Protocolo ESP32-CAM -> Mega (una orden por línea, terminada en \n):
//   CMD:CLASSIFY:vidrio
//   CMD:CLASSIFY:plastico
//   CMD:FACE:idle|moving|thinking|happy|confused|sleep
//   CMD:OLED:<mensaje corto>
//   CMD:QR:<claim_code>   -- QR de reclamo de puntos (ver docs/DECISION-QR-RECLAMO.md)
//
// Las órdenes de clasificación distintas de vidrio/plastico no mueven servos.
//
// Monitor Serial (USB, para probar navegación sin depender del cloud):
//   M -> empieza a seguir la línea
//   P -> para el robot y cancela el seguimiento
// ============================================================

#include <Servo.h>
#include <string.h>

#include "Display.h"
#include "LcdDisplay.h"
#include "Navigation.h"

namespace {

constexpr uint8_t kServoVidrioPin = 3;
constexpr uint8_t kServoPlasticoPin = 4;

constexpr uint8_t kServoCerrado = 0;
constexpr uint8_t kServoAbierto = 90;
constexpr unsigned long kCompuertaAbiertaMs = 5000UL;
constexpr unsigned long kSerialBaud = 9600UL;
constexpr size_t kCommandMaxLength = 63;

Servo servoVidrio;
Servo servoPlastico;
ReciDisplay pantalla;
ReciLcdDisplay lcd;
ReciNavigation navegacion;
bool navegando = false;

enum class CompuertaActiva : uint8_t {
  Ninguna,
  Vidrio,
  Plastico,
};

CompuertaActiva compuertaActiva = CompuertaActiva::Ninguna;
unsigned long cerrarCompuertaEn = 0;

char commandBuffer[kCommandMaxLength + 1] = {};
size_t commandLength = 0;

void cerrarCompuertas() {
  servoVidrio.write(kServoCerrado);
  servoPlastico.write(kServoCerrado);
  compuertaActiva = CompuertaActiva::Ninguna;
}

bool empiezaCon(const char* text, const char* prefix) {
  while (*prefix != '\0') {
    if (*text++ != *prefix++) return false;
  }
  return true;
}

void responder(const __FlashStringHelper* message) {
  Serial2.print(F("RECI:"));
  Serial2.println(message);
  Serial.print(F("RECI: "));
  Serial.println(message);
}

void abrirCompuerta(CompuertaActiva compuerta) {
  // Nunca se abren ambas compuertas. Mientras una está abierta, una nueva
  // clasificación se ignora para no mezclar residuos ni forzar los servos.
  if (compuertaActiva != CompuertaActiva::Ninguna) {
    responder(F("BUSY"));
    return;
  }

  if (compuerta == CompuertaActiva::Vidrio) {
    servoVidrio.write(kServoAbierto);
    responder(F("OPENED:vidrio"));
  } else if (compuerta == CompuertaActiva::Plastico) {
    servoPlastico.write(kServoAbierto);
    responder(F("OPENED:plastico"));
  } else {
    return;
  }

  compuertaActiva = compuerta;
  cerrarCompuertaEn = millis() + kCompuertaAbiertaMs;
  pantalla.setFace(FACE_HAPPY);
}

void actualizarCompuerta() {
  if (compuertaActiva == CompuertaActiva::Ninguna) return;

  if (static_cast<long>(millis() - cerrarCompuertaEn) < 0) return;

  cerrarCompuertas();
  pantalla.setFace(FACE_IDLE);
  responder(F("CLOSED"));
}

void cambiarCara(const char* state) {
  if (strcmp(state, "idle") == 0) pantalla.setFace(FACE_IDLE);
  else if (strcmp(state, "moving") == 0) pantalla.setFace(FACE_MOVING);
  else if (strcmp(state, "thinking") == 0) pantalla.setFace(FACE_THINKING);
  else if (strcmp(state, "happy") == 0) pantalla.setFace(FACE_HAPPY);
  else if (strcmp(state, "confused") == 0) pantalla.setFace(FACE_CONFUSED);
  else if (strcmp(state, "sleep") == 0) pantalla.setFace(FACE_SLEEP);
  else {
    responder(F("ERROR:unknown-face"));
    return;
  }
  responder(F("FACE:ok"));
}

void procesarComando(char* command) {
  if (strcmp(command, "CMD:CLASSIFY:vidrio") == 0) {
    abrirCompuerta(CompuertaActiva::Vidrio);
    return;
  }
  if (strcmp(command, "CMD:CLASSIFY:plastico") == 0) {
    abrirCompuerta(CompuertaActiva::Plastico);
    return;
  }
  if (empiezaCon(command, "CMD:FACE:")) {
    cambiarCara(command + strlen("CMD:FACE:"));
    return;
  }
  if (empiezaCon(command, "CMD:OLED:")) {
    pantalla.setMessage(command + strlen("CMD:OLED:"));
    responder(F("OLED:ok"));
    return;
  }
  if (empiezaCon(command, "CMD:QR:")) {
    pantalla.showClaimQR(command + strlen("CMD:QR:"));
    responder(F("QR:ok"));
    return;
  }
  if (empiezaCon(command, "CMD:LCD:")) {
    char* firstLine = command + strlen("CMD:LCD:");
    char* secondLine = strchr(firstLine, '|');
    if (secondLine == nullptr) {
      responder(F("ERROR:lcd-needs-two-lines"));
      return;
    }
    *secondLine++ = '\0';
    lcd.setLines(firstLine, secondLine);
    responder(F("LCD:ok"));
    return;
  }

  // "desconocido", baja confianza y comandos malformados no mueven servos.
  pantalla.setFace(FACE_CONFUSED);
  responder(F("ERROR:invalid-command"));
}

void leerComandosEsp32() {
  while (Serial2.available() > 0) {
    const char character = static_cast<char>(Serial2.read());

    if (character == '\r') continue;
    if (character == '\n') {
      if (commandLength > 0) {
        commandBuffer[commandLength] = '\0';
        procesarComando(commandBuffer);
        commandLength = 0;
      }
      continue;
    }

    if (commandLength >= kCommandMaxLength) {
      commandLength = 0;
      pantalla.setFace(FACE_CONFUSED);
      responder(F("ERROR:command-too-long"));
      continue;
    }

    commandBuffer[commandLength++] = character;
  }
}

// Prueba manual de navegación por el Monitor Serial (USB), sin depender
// todavía de un CMD:MOVE real desde el cloud — ver el comentario de
// cabecera. M empieza, P para y cancela (tecla de pánico si algo sale mal).
void leerComandoSerial() {
  while (Serial.available() > 0) {
    const char character = static_cast<char>(Serial.read());
    if (character == 'm' || character == 'M') {
      if (compuertaActiva != CompuertaActiva::Ninguna) {
        Serial.println(F("No navega con una compuerta abierta."));
        continue;
      }
      // begin() de nuevo por si acaso: resetea el reloj de "línea perdida",
      // así una M después de un P (o de una llegada) no arrastra la hora
      // de la sesión anterior y dispara LineaPerdida de entrada.
      navegacion.begin();
      navegando = true;
      pantalla.setFace(FACE_MOVING);
      Serial.println(F("Navegando... (P para parar)"));
    } else if (character == 'p' || character == 'P') {
      navegando = false;
      navegacion.detener();
      pantalla.setFace(FACE_IDLE);
      Serial.println(F("Detenido."));
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(kSerialBaud);   // Depuración por USB.
  Serial2.begin(kSerialBaud);  // ESP32-CAM: Mega RX2=17, TX2=16.

  navegacion.begin();

  servoVidrio.attach(kServoVidrioPin);
  servoPlastico.attach(kServoPlasticoPin);
  cerrarCompuertas();

  if (!pantalla.begin()) {
    Serial.println(F("ERROR: OLED no encontrada en 0x3C"));
  }
  pantalla.setFace(FACE_IDLE);

  lcd.begin();
  lcd.setLines("Hola, soy Reci", "Recicla y gana");
  responder(F("READY"));
  Serial.println(F("Listo. M = seguir linea, P = parar."));
}

void loop() {
  pantalla.tick();
  leerComandosEsp32();
  leerComandoSerial();
  actualizarCompuerta();

  if (navegando) {
    const ReciNavigation::Estado estado = navegacion.tick();
    if (estado == ReciNavigation::Estado::Llegada) {
      navegando = false;
      pantalla.setFace(FACE_HAPPY);
      Serial.println(F("Llegada: franja de parada detectada."));
    } else if (estado == ReciNavigation::Estado::LineaPerdida) {
      navegando = false;
      pantalla.setFace(FACE_CONFUSED);
      Serial.println(F("ERROR: linea perdida, robot detenido."));
    }
  }
}
