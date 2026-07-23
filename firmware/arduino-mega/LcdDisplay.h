// ============================================================
// Reci · LCD 16x2 para información de la comunidad
// ============================================================

#ifndef RECI_LCD_DISPLAY_H
#define RECI_LCD_DISPLAY_H

#include <Arduino.h>
#include <LiquidCrystal_I2C.h>

class ReciLcdDisplay {
 public:
  // LCD I2C 16x2 habitual. Si el módulo usa otra dirección, ajusta 0x27.
  void begin();
  void setLines(const char* firstLine, const char* secondLine);

 private:
  static constexpr uint8_t kColumns = 16;
  LiquidCrystal_I2C _lcd{0x27, kColumns, 2};

  void writeLine(uint8_t row, const char* text);
};

#endif  // RECI_LCD_DISPLAY_H
