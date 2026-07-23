# Guía de prueba de la ESP32-CAM

Esta guía prueba el flujo completo de Reci con una **AI Thinker ESP32-CAM**:
la cámara toma tres fotos de un residuo, el servidor decide `plastico` o
`vidrio` y el Arduino Mega recibe la orden de abrir la compuerta correcta.

El reconocimiento facial no es necesario para esta prueba.

## Resultado esperado

Al escribir `C` en el Monitor Serial, Reci debe imprimir tres resultados y una
decisión final:

```text
foto 1: plastico (0.92)
foto 2: plastico (0.89)
foto 3: plastico (0.94)
Resultado final: plastico
MEGA <- CMD:CLASSIFY:plastico
```

Solo abre una compuerta si al menos dos de las tres fotos coinciden. Si no hay
mayoría, responde `DESCONOCIDO` y no abre nada.

## 1. Antes de comenzar

Necesitas:

- ESP32-CAM AI Thinker con adaptador USB ESP32-CAM-MB.
- Arduino IDE, la placa `esp32 by Espressif Systems` y la librería
  `ArduinoJson`.
- La Mac y la ESP32-CAM conectadas a la misma red Wi-Fi de 2.4 GHz.
- Una fuente de luz frontal externa para el objeto. El LED flash interno está
  desactivado para evitar reinicios por falta de corriente.
- Un residuo por prueba, centrado ante la cámara, con fondo uniforme.

Para separar vidrio y plástico, monta la cámara fija e inclinada hacia el
objeto. No uses una vista totalmente vertical: el sistema necesita ver cuerpo,
cuello, tapa, transparencia y reflejos del envase.

> Nunca pegues claves, contraseñas Wi-Fi ni capturas que las muestren en un
> chat, documento o repositorio. Si una clave se compartió accidentalmente,
> rótala al terminar la prueba.

## 2. Configurar la ESP32-CAM

En Arduino IDE abre:

```text
firmware/esp32-cam/ReciEsp32Cam.ino
```

Si aún no existe, copia la plantilla de secretos:

```text
firmware/esp32-cam/ReciEsp32CamSecrets.h.example
```

a un archivo llamado:

```text
firmware/esp32-cam/ReciEsp32CamSecrets.h
```

Completa solo tus valores locales:

```cpp
#define WIFI_SSID "NOMBRE_DE_TU_WIFI"
#define WIFI_PASSWORD "CONTRASENA_DE_TU_WIFI"
#define RECI_API_BASE_URL "http://IP_DE_TU_MAC:3000"
#define RECI_ROBOT_API_KEY "MISMA_LLAVE_DE_WEB_ENV_LOCAL"
```

Obtén la IP de la Mac en una terminal:

```bash
ipconfig getifaddr en0
```

Usa ese resultado en `RECI_API_BASE_URL`. No uses `127.0.0.1`, `localhost` ni
la IP que la ESP32 muestra como propia en el Monitor Serial.

## 3. Configurar e iniciar el servicio de visión

El clasificador corre en la Mac durante desarrollo. En
`services/vision/.env` configura, como mínimo:

```env
VISION_SERVICE_API_KEY=UNA_LLAVE_PRIVADA
VISION_API=claude
ANTHROPIC_API_KEY=TU_LLAVE_DE_PROVEEDOR
CLAUDE_MODEL=claude-sonnet-4-6
```

También puedes usar Gemini configurando `VISION_API=gemini` y
`GEMINI_API_KEY`.

En `web/.env.local` agrega los mismos datos de conexión entre la web y el
servicio de visión:

```env
VISION_SERVICE_URL=http://127.0.0.1:8001
VISION_SERVICE_API_KEY=LA_MISMA_LLAVE_PRIVADA
```

Abre dos terminales y déjalas funcionando durante la prueba.

**Terminal 1 — servicio de visión**

```bash
cd /Users/pau/Documents/devStudent/Reci/services/vision
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8001
```

**Terminal 2 — aplicación web**

```bash
cd /Users/pau/Documents/devStudent/Reci/web
npm run dev -- -H 0.0.0.0
```

La segunda terminal debe permanecer abierta. Si la ESP32 devuelve `404`, casi
siempre significa que esta web no está corriendo en la IP configurada o que
`RECI_API_BASE_URL` apunta a otra computadora.

## 4. Cargar el sketch

En Arduino IDE selecciona:

- **Board:** `AI Thinker ESP32-CAM`.
- **Port:** el puerto `/dev/cu.usbserial-...` que aparezca al conectar la placa.
- **Upload Speed:** `115200`.

Si la carga muestra `Failed to connect to ESP32: No serial data received`:

1. Cierra el Monitor Serial.
2. Une temporalmente `IO0` con `GND`.
3. Pulsa el botón `RST` de la ESP32-CAM.
4. Pulsa **Upload**.
5. Cuando aparezca `Connecting...`, pulsa `RST` de nuevo.
6. Espera a `Writing at ...` y a `Hash of data verified`.
7. Quita el jumper `IO0`–`GND`.
8. Pulsa `RST` una vez para ejecutar el programa.

El mensaje `Hash of data verified` confirma que el sketch quedó cargado.

## 5. Confirmar que inició

Abre el Monitor Serial a **115200 baudios**. Después de pulsar `RST` debe
aparecer algo parecido a:

```text
Camara en VGA
Conectando al Wi-Fi...
Wi-Fi listo: 192.168.x.x
Listo. Envia C por el Monitor Serial para clasificar un residuo.
```

Si permanece en modo de carga o no imprime nada, confirma que el jumper `IO0`
–`GND` fue retirado y reinicia la placa.

## 6. Clasificar un residuo

1. Coloca una sola botella o envase frente a la cámara.
2. Ilumina el objeto de frente, sin contraluz.
3. No muevas ni retires el objeto durante unos segundos.
4. En la caja **Message** del Monitor Serial escribe `C` y presiona Enter.
5. Espera las tres fotos y el voto mayoritario.

Cuando hay mayoría, la ESP32 manda `CMD:CLASSIFY:vidrio` o
`CMD:CLASSIFY:plastico` por UART al Mega. El Mega es quien abre la compuerta.

Las tres capturas preliminares no crean eventos de reciclaje. Una vez elegido
el material, el sketch registra un solo evento y, si no había usuario
identificado, puede generar un código QR para reclamar los puntos.

## 7. Errores comunes

| Mensaje | Causa probable | Qué hacer |
| --- | --- | --- |
| `Brownout detector was triggered` | Pico de consumo por cámara, Wi-Fi o LED | Usa luz externa, cable USB corto/de datos y desconecta temporalmente periféricos del Mega. |
| `ERROR: foto ... respondio -3` | No se pudo conectar al servidor | Confirma que la web sigue ejecutándose y que la IP de la Mac es correcta. |
| `ERROR: foto ... respondio 404` | La URL llega a un servidor sin esa ruta | Revisa `RECI_API_BASE_URL` y ejecuta `npm run dev -- -H 0.0.0.0` desde `web`. |
| `Resultado: DESCONOCIDO` | No hubo dos votos iguales | Mejora luz, encuadre y fondo; vuelve a enviar `C`. |
| `ERROR: no se pudo capturar foto` | Cámara, cinta o alimentación inestable | Revisa la cinta OV2640, el cable USB y prueba sin periféricos conectados. |
| `Failed to connect to ESP32` al subir | No entró al bootloader | Sigue los ocho pasos de carga de la sección 4. |

## 8. Criterio de avance

Primero prueba cinco casos simples: botella PET de agua, botella PET de
gaseosa, vaso plástico, botella de cerveza de vidrio y frasco de vidrio.
Registra los resultados antes de probar objetos difíciles. Si la mayoría de
fallos son de captura, corrige ángulo, luz y fondo antes de cambiar reglas del
sistema experto.
