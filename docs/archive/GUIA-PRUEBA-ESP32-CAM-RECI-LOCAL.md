# Guía de prueba de la ESP32-CAM

Esta guía documenta la prueba de la ESP32-CAM usada por Reci: la cámara toma
tres fotos de un residuo, el backend decide `plastico` o `vidrio` y el
controlador abre la compuerta correspondiente.

> Esta guía corresponde a la integración ESP32-CAM del repositorio `Reci` de
> plataforma. El sistema experto de este repositorio sigue siendo la referencia
> para validar objetos, reglas y calidad de las capturas.

## Resultado esperado

```text
foto 1: plastico (0.92)
foto 2: plastico (0.89)
foto 3: plastico (0.94)
Resultado final: plastico
CMD:CLASSIFY:plastico
```

La compuerta solo debe abrir si dos de las tres fotos coinciden. Sin mayoría,
el resultado correcto es `DESCONOCIDO`: no se abre ninguna compuerta.

## 1. Preparar la zona de lectura

- Conecta la ESP32-CAM AI Thinker al adaptador USB ESP32-CAM-MB.
- Usa la misma red Wi-Fi de 2.4 GHz para Mac y ESP32-CAM.
- Fija la cámara inclinada hacia el objeto; evita una vista totalmente cenital.
- Usa un fondo mate uniforme y luz frontal externa.
- Centra un único residuo en el encuadre y no lo muevas durante la lectura.

No uses el flash interno durante las primeras pruebas: en algunas placas causa
un reinicio por falta de corriente cuando se combina con cámara VGA y Wi-Fi.

## 2. Configurar la red sin publicar secretos

El sketch local de la ESP32-CAM necesita cuatro datos privados:

```cpp
#define WIFI_SSID "NOMBRE_DE_TU_WIFI"
#define WIFI_PASSWORD "CONTRASENA_DE_TU_WIFI"
#define RECI_API_BASE_URL "http://IP_DE_TU_MAC:3000"
#define RECI_ROBOT_API_KEY "MISMA_LLAVE_DEL_BACKEND"
```

Obtén la IP de la Mac con:

```bash
ipconfig getifaddr en0
```

No uses `127.0.0.1`, `localhost` ni la IP mostrada por la ESP32: el servidor
está en la Mac. Nunca subas el archivo de secretos ni compartas capturas con
claves o contraseñas. Rota cualquier secreto que se haya mostrado por error.

## 3. Iniciar los servicios de desarrollo

En la Mac se necesitan dos procesos activos:

```bash
# Servicio de visión
cd /Users/pau/Documents/devStudent/Reci/ia/vision-service
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8001
```

```bash
# Aplicación web
cd /Users/pau/Documents/devStudent/Reci/web
npm run dev -- -H 0.0.0.0
```

El backend web debe apuntar al servicio de visión local:

```env
VISION_SERVICE_URL=http://127.0.0.1:8001
VISION_SERVICE_API_KEY=LA_MISMA_LLAVE_DEL_SERVICIO
```

El servicio de visión también necesita esa llave y una configuración de Claude
o Gemini. Mantén ambas terminales abiertas durante la prueba.

## 4. Cargar el sketch de la ESP32-CAM

En Arduino IDE selecciona **AI Thinker ESP32-CAM**, el puerto
`/dev/cu.usbserial-...` correspondiente y velocidad de carga `115200`.

Si aparece `Failed to connect to ESP32: No serial data received`:

1. Cierra el Monitor Serial.
2. Conecta `IO0` a `GND` temporalmente.
3. Pulsa `RST`.
4. Pulsa **Upload**.
5. Al ver `Connecting...`, pulsa `RST` otra vez.
6. Espera a `Hash of data verified`.
7. Quita el cable `IO0`–`GND`.
8. Pulsa `RST` para iniciar la aplicación.

## 5. Ejecutar la lectura

Con el Monitor Serial abierto a `115200`, espera el mensaje que indica que la
cámara y Wi-Fi están listos. Luego escribe `C` y presiona Enter.

La ESP32 toma tres fotos, el sistema experto recibe tres análisis y se decide
por voto mayoritario. El resultado final se debe comparar con la batería de
20 objetos de [BATERIA_B1.md](BATERIA_B1.md).

## Diagnóstico rápido

| Mensaje | Acción |
| --- | --- |
| `Brownout detector was triggered` | Usa luz externa, cable USB corto/de datos y desconecta periféricos durante la prueba. |
| `respondio -3` | Confirma que la web está activa y que la IP de la Mac es correcta. |
| `respondio 404` | El `RECI_API_BASE_URL` apunta al servidor equivocado o la web no está activa. |
| `DESCONOCIDO` | Repite con mejor luz, fondo, ángulo y objeto centrado. |
| `no se pudo capturar foto` | Revisa cinta OV2640, cable USB y alimentación. |
