# Prueba Uno + pantallas + ESP32-CAM

Esta prueba no usa Mega, motores ni servos. La ESP32-CAM captura la foto y
consulta la API; el Uno muestra la cara y el nombre recibido.

## Cableado de pantallas al Uno

| Pantalla | Arduino Uno |
| --- | --- |
| OLED VCC / GND | 5V* / GND |
| OLED SDA / SCL | A2 / A3 |
| LCD VCC / GND | 5V / GND |
| LCD SDA / SCL | A4 / A5 |

\* Revisa si tu OLED exige 3.3 V.

## Cableado ESP32-CAM al Uno

| ESP32-CAM AI Thinker | Arduino Uno | Nota |
| --- | --- | --- |
| GPIO14 (TX) | D10 (RX) | directo |
| GND | GND | obligatorio |
| 5V | Power Bank 5 V estable | no desde el Uno |

No conectes D11 del Uno al ESP32 para esta prueba: el Uno no necesita mandarle
datos y así evitamos aplicar 5 V al pin RX de 3.3 V de la ESP32.

La ESP32-CAM debe llevar el sketch `firmware/esp32-cam/ReciEsp32Cam.ino`.
Instala U8g2 y LiquidCrystal I2C para el Uno, y ArduinoJson para la ESP32.
