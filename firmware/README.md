# Reci · Firmware

Código de los dos microcontroladores del robot:

## Arduino Mega 2560 — cerebro de control

Gestiona toda la lógica de bajo nivel:

- **Movimiento**: 4 motorreductores TT via 2 drivers L298N.
- **Compuertas**: 2 servomotores SG5010 (una por compartimento vidrio/plástico).
- **Obstáculos**: sensores ultrasónicos HC-SR04 — parada automática a ≤ 20 cm.
- **Interfaz**: pantalla OLED 0.96" I2C con animaciones de estado.
- **Comunicación**: Serial/UART con el ESP32-CAM para recibir la decisión de clasificación.

## ESP32-CAM + OV2640 — sistema de visión

- Captura la imagen del residuo con la cámara OV2640.
- Envía la imagen vía WiFi al endpoint `POST /api/vision/classify` del cloud.
- Recibe la respuesta `{material, confidence}` del servidor.
- Reenvía la decisión al Arduino Mega por Serial/UART.
- También publica la posición y eventos al cloud directamente.

## Stack

- **Arduino Mega**: C++ con framework Arduino (Arduino IDE o PlatformIO).
- **ESP32-CAM**: C++ con framework Arduino + `HTTPClient` + `ArduinoJson`.
- Comunicación interna: UART entre ESP32-CAM (TX/RX) y Arduino Mega (Serial2).
- Comunicación externa: HTTPS desde ESP32-CAM → Reci Cloud.

## Protocolo UART interno (ESP32-CAM → Arduino Mega)

```
CMD:<accion>:<parametro>\n
```

Ejemplos:
- `CMD:CLASSIFY:vidrio\n` — clasificación confirmada: abrir compuerta de vidrio
- `CMD:CLASSIFY:plastico\n` — clasificación confirmada: abrir compuerta de plástico
- `CMD:OLED:Clasificando...\n` — mostrar mensaje de texto en pantalla
- `CMD:FACE:happy\n` — cambiar la cara de Reci
- `CMD:LCD:Hola, soy Reci|Recicla y gana\n` — actualizar las dos líneas de la LCD
- `CMD:STOP\n` — detener motores

### La cara de Reci (`CMD:FACE:<estado>`)

Implementada en [`arduino-mega/Display.h`](arduino-mega/Display.h) + `Display.cpp`.
Es la misma cara que la mascota de la app (`web/src/components/reci-mascot.tsx`),
rediseñada para 1 bit: el OLED es monocromo, no hay glow ni degradados.

| estado | cuándo | cara |
| --- | --- | --- |
| `idle` | esperando | ojos redondos + sonrisa, parpadea solo |
| `moving` | yendo a un punto | ojos entrecerrados, concentrado |
| `thinking` | esperando al cloud | mirando arriba + puntitos animados |
| `happy` | llegó / clasificó bien | ojos `^^` + sonrisota |
| `confused` | material desconocido | ojos redondos + boca `o` |
| `sleep` | cargando | ojos cerrados + zZz |

La cara está dibujada con primitivas de Adafruit_GFX, no con un bitmap: así
parpadea, se anima y ocupa flash en vez de 1KB de RAM.

**Dos cosas que no se pueden ignorar:**

1. `pantalla.tick()` va en **cada** vuelta del `loop()`. Ahí viven el parpadeo y
   las animaciones. Es barato: solo habla por I2C cuando algo cambió.
2. El bus I2C va a **400kHz** (`Wire.setClock(400000)`, ya está en `begin()`).
   A los 100kHz por defecto, cada refresco del OLED bloquea el bus ~90ms — con
   eso el robot deja de leer los ultrasonidos a tiempo y se lleva por delante el
   criterio de aceptación #9 (frenar a ≤20cm).

```cpp
#include "Display.h"

ReciDisplay pantalla;

void setup() {
  Serial2.begin(9600);           // ESP32-CAM
  if (!pantalla.begin()) {
    // el OLED no contesta en 0x3C — revisa SDA/SCL y el 5V
  }
  pantalla.setFace(FACE_IDLE);
}

void loop() {
  pantalla.tick();               // siempre, en cada vuelta
  leerUltrasonidos();
  moverMotores();
  // ... y al parsear CMD:FACE:happy → pantalla.setFace(FACE_HAPPY);
}
```

## Sketch principal actual

[`arduino-mega/ReciMega.ino`](arduino-mega/ReciMega.ino) integra las compuertas
y la OLED. Recibe las órdenes del ESP32-CAM por **Serial2** (Mega: RX2 = pin 17,
TX2 = pin 16), no por Serial1: Serial1 queda reservado para el HC-05 según el
mapa de conexiones actualizado.

Una compuerta solo se abre ante una clasificación válida del sistema experto:

```
CMD:CLASSIFY:vidrio
CMD:CLASSIFY:plastico
```

`vidrio` activa el servo de la compuerta izquierda (D3) y `plastico` el de la
derecha (D4), durante 5 s. Cualquier otro valor, incluida una clasificación
desconocida, no mueve ningún servo. Los motores quedan inicializados y detenidos
hasta implementar la navegación.

## Ruta demo + OLED

[`arduino-mega/ReciRutaDemo/ReciRutaDemo.ino`](arduino-mega/ReciRutaDemo/ReciRutaDemo.ino)
es la versión de demostración ya calibrada para la ruta recta: BASE → P1 → P2,
con 8 s por tramo. Conserva el freno ultrasónico y muestra la carita de RECI en
la OLED SSD1306: tranquila al esperar, concentrada en movimiento, feliz al
llegar y en alerta ante un obstáculo. Requiere instalar **Adafruit SSD1306**,
**Adafruit GFX Library** y **QRCode** desde el gestor de librerías de Arduino.
El QR se dibuja realmente en la OLED, con margen blanco para que lo lea la PWA. La pantalla
está conectada al Mega por SDA=20 y SCL=21, normalmente en la dirección `0x3C`.
Si la OLED no responde, el robot sigue deteniéndose y funcionando; solo informa
el aviso por el Monitor Serial.

La misma ruta demo también integra las compuertas ya calibradas: `VIDRIO` o
`PLASTICO` desde el Monitor Serial abren solo una tapa durante 2 s y la cierran
automáticamente. Las órdenes futuras `CMD:CLASSIFY:vidrio` y
`CMD:CLASSIFY:plastico` usan el mismo comportamiento al llegar desde la
ESP32-CAM. Por seguridad, no abre una tapa mientras RECI está en movimiento.
Además, ningún movimiento manual o automático puede comenzar con una tapa
abierta; una ruta solicitada en ese momento espera y arranca al cerrarse.

Al terminar una llamada, la ESP32-CAM conserva por 2 minutos su `call_id` y el
punto de llegada. El primer reciclaje válido se acredita directamente al usuario
de esa llamada (10 puntos). Si no existe ese contexto, el backend devuelve un
código y el Mega mantiene su QR visible para reclamar los puntos desde la PWA.

La LCD I2C 16x2 se usa para información conectada con la app: saludo inicial,
saludo personalizado y ranking. Usa la dirección `0x27` por defecto y comparte
SDA/SCL con la OLED y el MPU. Instala también la librería **LiquidCrystal I2C**
desde el gestor de librerías de Arduino. Si el escáner I2C reporta otra dirección
para la LCD, cambia `kDireccionLcd` en `arduino-mega/ReciRutaDemo/ReciRutaDemo.ino`.
La ruta demo muestra ya `Hola, soy RECI`, el punto actual, los destinos y las
alertas de obstáculo en esa LCD.

## Energía

- **Power Bank 10,000 mAh** → 5V constantes para Arduino Mega, ESP32-CAM y OLED.
- **Batería LiPo** → potencia para motores DC via L298N.
- **Módulo LM2596** → regula LiPo a 5V para proteger la lógica.

## Responsables

Leonela Sornoza, Andrea Campaña (apoyo: Axel Hernández).

## Estado

Fase 2 pendiente (semanas 3–4), con un adelanto:

- ✅ `arduino-mega/Display.h` + `Display.cpp` — la cara de Reci en el OLED.
  Escrita y con chequeo sintáctico, pero **sin probar en hardware**: el OLED
  todavía está en el carrito. Hay que verificarla contra la pantalla real.
- ⏳ El resto (`Motors.h`, `Servos.h`, `Ultrasonic.h`, sketch principal) arranca
  con el ensamble físico, siguiendo [`docs/CONEXIONES.md`](../docs/CONEXIONES.md).
