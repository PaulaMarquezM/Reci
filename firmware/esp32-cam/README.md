# ESP32-CAM de Reci

Este sketch usa el mapa de pines compatible con **AI Thinker ESP32-CAM**. La
placa actual mantiene ese mapa, pero incorpora una cámara **OV3660** en lugar
de la OV2640 habitual; el driver detecta el sensor automáticamente al iniciar.
Para clasificar un residuo toma tres fotos, consulta el backend y solo manda
abrir una compuerta cuando existe una mayoría segura. No guarda fotos ni
contiene credenciales de Supabase.

## Antes de compilar

1. Instala `esp32 by Espressif Systems` desde el Gestor de tarjetas de Arduino
   IDE y `ArduinoJson` desde el Gestor de bibliotecas.
2. Copia `ReciEsp32CamSecrets.h.example` a `ReciEsp32CamSecrets.h` y rellena
   Wi-Fi, IP local de la Mac y `ROBOT_API_KEY`.
3. En la Mac, ejecuta la web con acceso de red:

   ```bash
   cd web
   npm run dev -- -H 0.0.0.0
   ```

   `RECI_API_BASE_URL` debe usar la IP de la Mac, no `127.0.0.1`. Puedes ver la
   IP Wi-Fi de la Mac con `ipconfig getifaddr en0`.

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

Con esta placa USB-C, selecciona **AI Thinker ESP32-CAM** y el puerto correcto.
En el arranque, el Monitor Serial debe indicar `PID=0x3660`. Si la carga no
entra automáticamente, usa el botón BOOT o une GPIO0 a GND durante la carga;
retíralo al terminar y pulsa Reset. Abre el monitor serial a 115200 para ver el
resultado de cada reconocimiento.

## Probar clasificación de residuos

1. Inicia la web y `ia/vision-service`; la web debe tener configuradas
   `VISION_SERVICE_URL` y `VISION_SERVICE_API_KEY`.
2. Pon un único residuo centrado frente a la cámara, con fondo mate y luz frontal.
3. En el Monitor Serial (115200) escribe **C** y envíalo.
4. La ESP32 toma tres fotos QVGA. Cada foto recibe un voto del proveedor y
   otro del MobileNetV2 local; el Monitor Serial muestra ambos. La placa
   cuenta hasta seis votos: `desconocido` es abstención y no suma a ningún
   material. Primero busca una mayoría 2/3 o 3/3 en OpenAI; solo si OpenAI no
   tiene mayoría usa la mayoría del modelo local. Si ambas señales empatan o
   no tienen mayoría, manda `desconocido` y no abre la compuerta.

Salida esperada con el servicio híbrido:

```text
foto 1: OpenAI=plastico (0.96) | modelo=plastico (0.98)
foto 2: OpenAI=plastico (0.94) | modelo=plastico (0.99)
foto 3: OpenAI=plastico (0.95) | modelo=vidrio (0.91)
Votos validos: plastico=5 | vidrio=1 | abstenciones=0
Votos OpenAI: plastico=3 | vidrio=0 | abstenciones=0
Votos modelo: plastico=2 | vidrio=1 | abstenciones=0
Regla de decision: mayoria OpenAI/sistema experto
Resultado final: plastico
```

Las fotos de esta validación no crean eventos ni puntos: la persistencia debe
ocurrir una sola vez después del voto mayoritario.
