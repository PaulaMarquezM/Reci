# ESP32-CAM de Reci

Este sketch es para el módulo **AI Thinker ESP32-CAM**. Para clasificar un
residuo toma tres fotos con flash, consulta el backend y solo manda abrir una
compuerta cuando existe una mayoría segura. No guarda fotos ni contiene
credenciales de Supabase.

## Antes de compilar

1. Instala `esp32 by Espressif Systems` desde el Gestor de tarjetas de Arduino
   IDE y `ArduinoJson` desde el Gestor de bibliotecas.
2. Copia `ReciEsp32CamSecrets.h.example` a `ReciEsp32CamSecrets.h` y rellena
   Wi-Fi, URL del backend y `ROBOT_API_KEY`. Ese archivo ya está ignorado por
   Git: nunca lo publiques ni lo pegues en un chat.
3. En la Mac, ejecuta la web con acceso de red:

   ```bash
   cd web
   npm run dev -- -H 0.0.0.0
   ```

   `RECI_API_BASE_URL` debe usar la IP de la Mac, no `127.0.0.1`. Puedes ver la
   IP Wi-Fi de la Mac con `ipconfig getifaddr en0`.

   Esta es la forma correcta de hacer la **primera prueba**, porque la Mac, la
   ESP32 y la app comparten el mismo Wi-Fi. Cuando se publique la web en Vercel,
   se sustituye por `https://tu-proyecto.vercel.app`; antes de eso hay que
   activar TLS en el sketch, no se debe intentar usar `WiFiClient` normal con
   una URL `https`.

## Cableado ESP32-CAM ↔ Mega

| ESP32-CAM AI Thinker | Arduino Mega | Nota |
| --- | --- | --- |
| GPIO14 (TX) | RX2, D17 | conexión directa: 3.3 V es leído como HIGH por Mega |
| GPIO13 (RX) | TX2, D16, mediante divisor | protege el RX de 3.3 V del ESP32 |
| GND | GND común | obligatorio |
| 5V | Power Bank 5 V estable | no alimentar desde el Mega |

El divisor para **D16 del Mega → GPIO13 del ESP32** es:

```text
Mega D16 ── 1kΩ ──┬── GPIO13 / RX ESP32
                  │
                 2kΩ
                  │
                 GND común
```

La OLED y LCD se conectan al **Mega**, no a la ESP32:

```text
Mega D20/SDA -> SDA de OLED + SDA de LCD
Mega D21/SCL -> SCL de OLED + SCL de LCD
Mega GND     -> GND de OLED + GND de LCD
Mega 5V      -> VCC de OLED* + VCC de LCD
```

\* Revisa la etiqueta de la OLED: algunos módulos requieren 3.3 V.

## Cargar la ESP32-CAM

Con el adaptador ESP32-CAM-MB por USB, selecciona **AI Thinker ESP32-CAM** y el
puerto correcto. Si no carga automáticamente: GPIO0 a GND, pulsa Upload, quita
GPIO0 de GND al terminar y pulsa Reset. Abre el monitor serial a 115200 para ver
el resultado de cada reconocimiento.

## Probar clasificación de residuos

1. Inicia la web y `ia/vision-service`; la web debe tener configuradas
   `VISION_SERVICE_URL` y `VISION_SERVICE_API_KEY`.
2. Pon un único residuo centrado frente a la cámara, con fondo mate y luz frontal.
3. En el Monitor Serial (115200) escribe **C** y envíalo.
4. La ESP32 toma tres fotos VGA (QVGA sin PSRAM). Si al menos dos dicen
   `vidrio` o `plastico`, manda `CMD:CLASSIFY:<material>` al Mega.

Las fotos de esta validación no crean eventos ni puntos: la persistencia debe
ocurrir una sola vez después del voto mayoritario.

## Probar primero la conexión con la app (sin cámara ni movimiento)

1. Con RECI físicamente en **BASE**, carga `ReciRutaDemo.ino` al Mega. Antes de
   conectar la ESP32, deja `kEsp32CamConectada = false`.
2. Carga este sketch a la ESP32-CAM y confirma en su Monitor Serial (115200)
   que muestra `Wi-Fi listo: ...`. Su primer mensaje hará aparecer en el LCD
   del Mega `Hola, soy RECI / Envia C para leer`: eso confirma el cable serie.
3. Solo entonces cambia en el Mega `kEsp32CamConectada` a `true` y vuelve a
   cargarlo. Nunca lo actives con RX2/D17 desconectado, porque un pin flotante
   se interpreta como órdenes aleatorias.
4. Reinicia ambos equipos, abre el Monitor Serial del Mega a **9600**, y envía
   `SET:BASE` una sola vez. Ese paso confirma la posición real; no se hace de
   forma automática porque RECI no tiene GPS ni sensores de línea.
5. Desde la web, usa el botón para llamar a RECI a P1 o P2. La ESP consulta la
   llamada cada tres segundos, envía la orden al Mega y, al llegar, el LCD
   muestra `Hola, <nombre> / Soy RECI`.

Para esta primera prueba, no llames desde la app hasta que las ruedas estén
levantadas o tengas el recorrido despejado. La app no sustituye el freno físico
ni el ultrasónico.
