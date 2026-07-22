// ============================================================
// Reci · Display.h — la cara de Reci en el OLED
// ============================================================
// Pantalla: OLED 0.96" SSD1306, I2C 0x3C, 128x64, monocromo.
// Bus: SDA pin 20, SCL pin 21 del Mega (compartido con el MPU).
//
// Librerías (Library Manager del Arduino IDE):
//   - Adafruit SSD1306
//   - Adafruit GFX Library
//   - QRCode (de Richard Moore / ricmoo) — para showClaimQR()
//
// Uso:
//   ReciDisplay pantalla;
//   void setup() { pantalla.begin(); }
//   void loop()  { pantalla.tick(); }   // <- en cada vuelta, siempre
//   ... pantalla.setFace(FACE_HAPPY);
//   ... pantalla.showClaimQR("A1B2C3D4");  // CMD:QR:<code> — reclamo de puntos
//
// ⚠️ tick() TIENE que llamarse en cada loop(): ahí viven el parpadeo y las
// animaciones. Es barato — solo habla por I2C cuando algo cambió de verdad.
// ============================================================

#ifndef RECI_DISPLAY_H
#define RECI_DISPLAY_H

#include <Arduino.h>
#include <Adafruit_SSD1306.h>
#include <qrcode.h>

// Los estados de ánimo de Reci, mapeados a lo que hace el robot.
enum Face : uint8_t {
  FACE_IDLE,      // esperando — ojos redondos + sonrisa, parpadea solo
  FACE_MOVING,    // yendo a un punto — ojos decididos
  FACE_THINKING,  // esperando la clasificación del cloud — puntitos
  FACE_HAPPY,     // llegó / clasificó bien — ojos ^^ y sonrisota
  FACE_CONFUSED,  // material desconocido — ojos redondos + boca "o"
  FACE_SLEEP,     // cargando — ojos cerrados + zZz
};

class ReciDisplay {
 public:
  // Devuelve false si el OLED no contesta en 0x3C (revisa SDA/SCL y el 5V).
  bool begin();

  // Cambia la cara. No dibuja: eso lo hace tick().
  void setFace(Face face);
  Face face() const { return _face; }

  // Muestra texto en vez de la cara (esto es CMD:OLED:<texto>).
  // Para volver a la cara, llama setFace() otra vez.
  void setMessage(const char* msg);

  // Muestra el QR de reclamo de puntos (esto es CMD:QR:<code>).
  // code: el claim_code de recycle_events, hasta 15 caracteres.
  // Para volver a la cara, llama setFace() otra vez.
  void showClaimQR(const char* code);

  // Llamar en cada loop(). Solo redibuja si hace falta.
  void tick();

 private:
  Adafruit_SSD1306 _oled{128, 64, &Wire, -1};

  Face _face = FACE_IDLE;
  bool _showingMessage = false;
  char _message[42] = {0};
  bool _showingQR = false;
  char _qrText[16] = {0};

  bool _dirty = true;         // hay algo nuevo que mandar al OLED
  bool _blinking = false;
  uint32_t _nextBlinkAt = 0;  // millis() del próximo parpadeo
  uint32_t _blinkEndsAt = 0;
  uint8_t _dots = 0;          // frame de la animación de FACE_THINKING
  uint32_t _nextDotAt = 0;

  void render();
  void drawEyes();
  void drawMouth();
  void drawQRCode();
  void drawArc(int16_t cx, int16_t cy, int16_t r, uint8_t quadrants, uint8_t thickness);
  void scheduleBlink();
};

#endif  // RECI_DISPLAY_H
