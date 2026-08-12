# Prueba aislada de cámara y clasificación

Este sketch prueba toda la cadena de visión sin tocar el robot:

`ESP32-CAM -> Wi-Fi -> web local -> servicio de visión -> resultado`

No necesita cables hacia el Mega. No mueve ruedas, no abre compuertas y no
registra eventos/puntos.

1. Copia `ReciCamaraClasificacionSecrets.h.example` como
   `ReciCamaraClasificacionSecrets.h` y completa los mismos datos que ya usas
   en `ReciEsp32CamSecrets.h`.
2. En la Mac deja la web encendida:
   `cd /Users/pau/Downloads/Reci/web && npm run dev -- -H 0.0.0.0`
3. Carga `ReciCamaraClasificacionTest.ino` a una ESP32-CAM AI Thinker.
4. Abre el Monitor Serial a 115200, coloca un solo residuo con buena luz y
   manda `C`.
5. El resultado es válido cuando al menos dos de las tres fotos concuerdan.

Cuando pase esta prueba, se vuelve a cargar `../ReciEsp32Cam/ReciEsp32Cam.ino`
para la operación integrada: ahí sí el resultado se envía al Mega y abre la
compuerta correspondiente.
