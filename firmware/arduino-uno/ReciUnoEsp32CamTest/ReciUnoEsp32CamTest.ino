// ============================================================
// Reci · prueba completa: Arduino Uno + OLED + LCD + ESP32-CAM
//
// El Uno muestra los comandos que manda ReciEsp32Cam.ino:
//   CMD:FACE:idle|thinking|happy|confused
//   CMD:LCD:primera linea|segunda linea
//   CMD:CLASSIFY:vidrio|plastico
//
// Librerías: U8g2, LiquidCrystal I2C (SoftwareSerial es incluida en Arduino).
// ============================================================

#include <LiquidCrystal_I2C.h>
#include <SoftwareSerial.h>
#include <U8g2lib.h>
#include <Wire.h>
#include <string.h>

namespace {

// OLED por I2C software: SCL=A3, SDA=A2. El modo por páginas evita reservar
// el búfer completo de 1 KB, que no cabe junto con LCD y SoftwareSerial en el Uno.
// LCD por I2C físico: SCL=A5, SDA=A4.
U8G2_SSD1306_128X64_NONAME_1_SW_I2C oled(U8G2_R0, A3, A2, U8X8_PIN_NONE);
LiquidCrystal_I2C lcd(0x27, 16, 2);

// SoftwareSerial(rx, tx). El TX no se conecta en esta prueba.
// ESP32 GPIO14/TX -> Uno D10/RX.
SoftwareSerial espLink(10, 11);

enum class Face : uint8_t { Idle, Thinking, Happy, Confused };
Face currentFace = Face::Idle;

char command[64] = {};
uint8_t commandLength = 0;

void lcdLine(uint8_t row, const char* text) {
  lcd.setCursor(0, row);
  lcd.print(F("                "));
  lcd.setCursor(0, row);
  lcd.print(text);
}

void showLcd(const char* firstLine, const char* secondLine) {
  lcdLine(0, firstLine);
  lcdLine(1, secondLine);
}

void drawFace() {
  oled.firstPage();
  do {
    oled.drawRFrame(3, 3, 122, 58, 12);

    if (currentFace == Face::Thinking) {
      oled.drawDisc(40, 25, 8);
      oled.drawDisc(88, 25, 8);
      oled.drawDisc(52, 46, 3);
      oled.drawDisc(64, 46, 3);
      oled.drawDisc(76, 46, 3);
    } else if (currentFace == Face::Happy) {
      // Ojos ^^ y sonrisa grande.
      oled.drawLine(28, 31, 39, 20);
      oled.drawLine(39, 20, 50, 31);
      oled.drawLine(78, 31, 89, 20);
      oled.drawLine(89, 20, 100, 31);
      oled.drawCircle(64, 38, 17);
      oled.setDrawColor(0);
      oled.drawBox(43, 18, 43, 20);
      oled.setDrawColor(1);
    } else if (currentFace == Face::Confused) {
      oled.drawDisc(40, 27, 9);
      oled.drawDisc(88, 27, 9);
      oled.drawCircle(64, 46, 6);
    } else {
      oled.drawRBox(28, 17, 22, 24, 10);
      oled.drawRBox(78, 17, 22, 24, 10);
      oled.drawCircle(64, 38, 17);
      oled.setDrawColor(0);
      oled.drawBox(43, 18, 43, 20);
      oled.setDrawColor(1);
    }
  } while (oled.nextPage());

}

void setFace(const char* state) {
  if (strcmp(state, "thinking") == 0) currentFace = Face::Thinking;
  else if (strcmp(state, "happy") == 0) currentFace = Face::Happy;
  else if (strcmp(state, "confused") == 0) currentFace = Face::Confused;
  else currentFace = Face::Idle;
  drawFace();
}

void processCommand(char* value) {
  if (strncmp(value, "CMD:FACE:", 9) == 0) {
    setFace(value + 9);
    return;
  }

  if (strncmp(value, "CMD:LCD:", 8) == 0) {
    char* firstLine = value + 8;
    char* secondLine = strchr(firstLine, '|');
    if (secondLine == nullptr) return;
    *secondLine++ = '\0';
    showLcd(firstLine, secondLine);
    return;
  }

  if (strncmp(value, "CMD:CLASSIFY:", 13) == 0) {
    const char* material = value + 13;
    if (strcmp(material, "vidrio") == 0 || strcmp(material, "plastico") == 0) {
      Serial.print(F("CLASIFICACION RECIBIDA: "));
      Serial.println(material);
      showLcd(strcmp(material, "vidrio") == 0 ? "VIDRIO" : "PLASTICO", "CMD recibido");
    } else {
      Serial.println(F("CMD:CLASSIFY invalido"));
    }
  }
}

void readEspCommands() {
  while (espLink.available() > 0) {
    const char character = static_cast<char>(espLink.read());
    if (character == '\r') continue;

    if (character == '\n') {
      if (commandLength > 0) {
        command[commandLength] = '\0';
        Serial.print(F("ESP -> UNO: "));
        Serial.println(command);
        processCommand(command);
        commandLength = 0;
      }
      continue;
    }

    if (commandLength < sizeof(command) - 1) command[commandLength++] = character;
    else commandLength = 0;
  }
}

}  // namespace

void setup() {
  Serial.begin(115200);
  espLink.begin(9600);

  lcd.init();
  lcd.backlight();
  showLcd("Hola, soy Reci", "Mira a camara");

  oled.setI2CAddress(0x3C << 1);
  oled.begin();
  drawFace();
}

void loop() {
  readEspCommands();
}
