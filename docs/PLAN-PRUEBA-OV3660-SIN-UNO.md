# Plan de prueba: OV3660 hoy, Arduino Uno mañana

La falta temporal de cables Dupont no impide validar el sistema de visión. La
ESP32-CAM puede capturar las tres fotos, enviarlas por Wi-Fi al servicio de
visión y mostrar la decisión completa en su propio Monitor Serial. El Arduino
Uno solo se incorpora después como receptor y pantalla de esa decisión.

## Hoy: prueba sin Arduino Uno

1. Conectar la ESP32-CAM OV3660 por USB-C a la Mac.
2. Cargar `firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino` desde Arduino IDE
   usando la placa `AI Thinker ESP32-CAM`.
3. Abrir el Monitor Serial a `115200` y reiniciar la placa. Debe aparecer:

   ```text
   Sensor de camara detectado: PID=0x3660
   Camara en QVGA (optimizada)
   Wi-Fi listo: ...
   ```

4. Con el servicio de visión y la aplicación local ya iniciados, enviar `C`
   por el Monitor Serial. La ESP32 toma tres fotos y debe imprimir los votos,
   la regla usada y el resultado final.
5. Repetir con una botella de plástico y una de vidrio, con luz frontal y
   fondo mate. Registrar la salida del Monitor Serial y no retirar el objeto
   durante la secuencia de tres fotos.

Un resultado `desconocido` es seguro: no abre ni ordena abrir ninguna
compuerta. Primero se corrigen iluminación, encuadre o red antes de cambiar
reglas o modelos.

## Mañana: añadir Arduino Uno

Con ambas placas desconectadas, conectar únicamente:

| ESP32-CAM OV3660 | Arduino Uno | Propósito |
| --- | --- | --- |
| GPIO14 | D10 | ESP32 transmite el resultado por serial |
| GND | GND | Referencia eléctrica común |

Cada placa mantiene su propio USB hacia la Mac:

- ESP32-CAM por USB-C: alimentación, programación, Wi-Fi y Monitor Serial.
- Arduino Uno por USB: alimentación, carga del sketch y Monitor Serial.

No conectar 5 V entre las placas. No conectar D11 del Uno al ESP32 durante
esta prueba: el Uno no necesita transmitir y su nivel lógico de 5 V no es
seguro para el RX de 3.3 V de la ESP32-CAM.

## Orden de validación mañana

1. Cargar el sketch mínimo de recepción en el Uno.
2. Confirmar que el Uno recibe un texto de prueba desde la ESP32.
3. Cargar el firmware de clasificación en la ESP32 y enviar `C`.
4. Confirmar que el Uno recibe `CMD:CLASSIFY:plastico` o
   `CMD:CLASSIFY:vidrio` cuando exista una decisión segura.
5. Solo después conectar pantallas, servos o compuertas.
