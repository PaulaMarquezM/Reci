// ============================================================
// Reci · prueba de OLED + LCD para Arduino Uno
//
// No conecta servos, motores, ESP32 ni base de datos.
// Solo verifica que las dos pantallas I2C funcionen en el mismo bus.
//
// Cableado Arduino Uno:
//   OLED SSD1306: VCC -> 5V*, GND -> GND, SDA -> A2, SCL -> A3
//                  (I2C por software: A2/A3 no son I2C físico del Uno)
//   LCD I2C 16x2: VCC -> 5V,  GND -> GND, SDA -> A4/SDA, SCL -> A5/SCL
//
// * Revisa la etiqueta de la OLED: algunos módulos requieren 3.3V.
//
// Librerías necesarias desde el gestor de bibliotecas de Arduino IDE:
//   - U8g2
//   - LiquidCrystal I2C
// ============================================================

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <U8g2lib.h>

namespace {

constexpr uint8_t kOledAddress = 0x3C;
constexpr uint8_t kLcdAddress = 0x27;
constexpr unsigned long kBlinkEveryMs = 3000UL;
constexpr unsigned long kBlinkDurationMs = 140UL;
constexpr unsigned long kLcdPageEveryMs = 3500UL;

// Orden del constructor U8g2: clock (SCL), data (SDA), reset.
// Así la OLED funciona por software con SCL=A3 y SDA=A2.
U8G2_SSD1306_128X64_NONAME_F_SW_I2C oled(U8G2_R0, A3, A2, U8X8_PIN_NONE);
LiquidCrystal_I2C lcd(kLcdAddress, 16, 2);

const char* const kLcdTopLines[] = {
  "Hola, soy Reci",
  "Top recicladores",
  "Top recicladores",
  "Top recicladores",
};

const char* const kLcdBottomLines[] = {
  "Recicla y gana",
  "1. Paula 1200",
  "2. Andrea 900",
  "3. Leonela 750",
};

constexpr uint8_t kLcdPageCount = sizeof(kLcdTopLines) / sizeof(kLcdTopLines[0]);

bool oledAvailable = false;
bool blinking = false;
unsigned long nextBlinkAt = 0;
unsigned long blinkEndsAt = 0;
unsigned long nextLcdPageAt = 0;
uint8_t lcdPage = 0;

void printLcdLine(uint8_t row, const char* text) {
  lcd.setCursor(0, row);
  lcd.print(F("                "));
  lcd.setCursor(0, row);
  lcd.print(text);
}

void showLcdPage() {
  printLcdLine(0, kLcdTopLines[lcdPage]);
  printLcdLine(1, kLcdBottomLines[lcdPage]);
}

void drawFace() {
  oled.clearBuffer();

  // Marco de la pantalla/cara.
  oled.drawRFrame(3, 3, 122, 58, 12);

  // Sonrisa: se dibuja el círculo y se borra su mitad superior.
  oled.drawCircle(64, 38, 17);
  oled.drawCircle(64, 39, 16);
  oled.drawCircle(64, 40, 15);
  oled.setDrawColor(0);
  oled.drawBox(43, 18, 43, 20);
  oled.setDrawColor(1);

  if (blinking) {
    oled.drawRBox(25, 27, 28, 4, 2);
    oled.drawRBox(75, 27, 28, 4, 2);
  } else {
    oled.drawRBox(28, 17, 22, 24, 10);
    oled.drawRBox(78, 17, 22, 24, 10);
  }

  oled.sendBuffer();
}

void updateFace() {
  const unsigned long now = millis();

  if (!blinking && now - nextBlinkAt >= kBlinkEveryMs) {
    blinking = true;
    blinkEndsAt = now + kBlinkDurationMs;
    drawFace();
  } else if (blinking && static_cast<long>(now - blinkEndsAt) >= 0) {
    blinking = false;
    nextBlinkAt = now;
    drawFace();
  }
}

void updateLcd() {
  const unsigned long now = millis();
  if (static_cast<long>(now - nextLcdPageAt) < 0) return;

  lcdPage = (lcdPage + 1) % kLcdPageCount;
  showLcdPage();
  nextLcdPageAt = now + kLcdPageEveryMs;
}

}  // namespace

void setup() {
  Wire.begin();
  Serial.begin(9600);

  lcd.init();
  lcd.backlight();
  lcd.clear();
  showLcdPage();
  nextLcdPageAt = millis() + kLcdPageEveryMs;

  // U8g2 recibe la dirección I2C desplazada un bit hacia la izquierda.
  oled.setI2CAddress(kOledAddress << 1);
  oled.begin();
  oledAvailable = true;
  drawFace();
  Serial.println(F("OLED iniciada en 0x3C"));
}

void loop() {
  if (oledAvailable) updateFace();
  updateLcd();
}
