#include "LcdDisplay.h"

#include <string.h>

void ReciLcdDisplay::begin() {
  _lcd.init();
  _lcd.backlight();
  _lcd.clear();
}

void ReciLcdDisplay::setLines(const char* firstLine, const char* secondLine) {
  writeLine(0, firstLine);
  writeLine(1, secondLine);
}

void ReciLcdDisplay::writeLine(uint8_t row, const char* text) {
  char line[kColumns + 1] = {};
  strncpy(line, text, kColumns);

  _lcd.setCursor(0, row);
  _lcd.print(F("                "));
  _lcd.setCursor(0, row);
  _lcd.print(line);
}
