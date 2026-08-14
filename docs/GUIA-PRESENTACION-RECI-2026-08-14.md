# Guía operativa RECI para la presentación del 14 de agosto de 2026

- **Lugar de trabajo inicial:** Portoviejo
- **Presentación:** 14:00 en Manta
- **Inicio recomendado:** 09:00
- **Hora recomendada para dejar de modificar y empezar a empacar:** 11:20
**Rama:** `integration/vision-main-20260813`

Esta guía está pensada para ejecutar la prueba final con poco tiempo. No se
entrena ningún modelo, no se capturan nuevas imágenes y no se cambia `web/`.
Si algo falla, se vuelve al último punto aprobado; no se improvisan pines,
voltajes, reglas de votación ni credenciales.

## 1. Los dos archivos que se deben abrir

### ESP32-CAM

Abrir en Arduino IDE:

```text
firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino
```

Configuración:

- placa: **AI Thinker ESP32-CAM**;
- puerto: el USB de la ESP32-CAM-MB, normalmente `/dev/cu.usbserial-...`;
- Monitor Serial: **115200 baudios**;
- sensor esperado: **OV3660**, PID `0x3660`;
- resolución: **QVGA**;
- firmware esperado: `seis-votos-v2-local-unanime`.

El archivo `ReciEsp32CamSecrets.h` debe estar en la misma carpeta, pero está
ignorado por Git. Nunca mostrarlo en la presentación, tomarle captura, pegarlo
en un chat ni agregarlo a un commit.

### Arduino Mega 2560

Abrir en otra ventana de Arduino IDE:

```text
firmware/arduino-mega/ReciRutaDemo/ReciRutaDemo.ino
```

Configuración:

- placa: **Arduino Mega or Mega 2560**;
- puerto: el USB del Mega, normalmente `/dev/cu.usbmodem...`;
- Monitor Serial: **9600 baudios**;
- `kEsp32CamConectada = true`;
- `kEsp32CamBidireccional = true`.

Este es el sketch del robot completo. No abrir ni cargar `ReciMega.ino`, los
sketches del Uno ni los diagnósticos UART para la presentación normal.

## 2. Regla eléctrica que no se puede saltar

El ESP32 trabaja a 3,3 V y el TX2 del Mega entrega 5 V.

**Nunca conectar Mega D16/TX2 directamente a ESP32 GPIO13/RX.**

El enlace correcto, con ambos equipos apagados, es:

| Origen | Destino | Conexión |
| --- | --- | --- |
| ESP32 GPIO14/TX | Mega D17/RX2 | Directa |
| Mega D16/TX2 | ESP32 GPIO13/RX | Mediante divisor 1 kΩ / 2 kΩ |
| ESP32 GND | Mega GND | Directa y obligatoria |

Divisor obligatorio:

```text
Mega D16/TX2 ── 1 kΩ ──┬── ESP32 GPIO13/RX
                       │
                      2 kΩ
                       │
                      GND común
```

Antes de conectar el nodo a GPIO13, medir aproximadamente 3,3 V. Si no hay
multímetro o resistencias, dejar D16 y GPIO13 totalmente desconectados. La
clasificación ESP32 → Mega funcionará, pero llamadas, llegada y obstáculos no
se reportarán de vuelta al ESP32.

## 3. Cronograma recomendado

| Hora | Objetivo | Límite |
| --- | --- | --- |
| 09:00–09:10 | Inventario, rama correcta y alimentación desconectada | No reparar mecánica todavía |
| 09:10–09:25 | Hotspot, IP de la Mac y servicios 8001/3000 | No cargar firmware sin confirmar la IP |
| 09:25–09:45 | Compilar y cargar Mega y ESP32 | No conectar motores ni servos |
| 09:45–10:05 | Pantallas, UART bidireccional y arranque | Detenerse si aparecen caracteres corruptos |
| 10:05–10:25 | Desconocido, error de servicio, plástico y vidrio sin actuadores | Debe no existir `CMD:CLASSIFY` en rechazo |
| 10:25–10:50 | Servos, cierre y segunda orden bloqueada | Motores siguen desconectados |
| 10:50–11:15 | Ruta, obstáculo, llamada, llegada, puntos y QR | Ruedas levantadas primero |
| 11:15–11:20 | Guardar evidencia y apagar | No comenzar cambios grandes |
| 11:20 en adelante | Empacar y salir con margen hacia Manta | Ajustar al transporte del equipo |

Si a las 11:00 la ruta completa todavía falla, priorizar la demostración segura
de cámara, desconocido, plástico, vidrio y compuertas. No sacrificar el margen
de traslado por una modificación de último minuto.

## 4. Inventario antes de encender

- Mac cargada y cargador.
- Arduino IDE 2 instalado.
- Dos cables USB de datos: Mega y ESP32-CAM-MB.
- Hotspot Android cargado, 2,4 GHz y con datos móviles.
- Fuente o power bank estable de 5 V para la ESP32-CAM.
- Fuente separada adecuada para servos y motores.
- Resistencias de 1 kΩ y 2 kΩ para el divisor.
- Multímetro.
- Jumpers de repuesto, cinta y destornilladores.
- Una muestra conocida de plástico.
- Una muestra conocida de vidrio.
- Un objeto claramente ajeno para `desconocido`.
- Luz frontal externa; el flash integrado está desactivado para evitar reinicios.
- Presentación y este documento disponibles sin Internet.

No alimentar servos o motores desde el pin 5V del Mega. Usar su fuente adecuada
y unir solamente los GND necesarios; evitar devolver 5 V de una fuente externa
al pin 5V del Mega.

## 5. Actualizar el repositorio a las 09:00

En Terminal:

```bash
cd /Users/hernandezaxel/Pau/Reci
git switch integration/vision-main-20260813
git pull --ff-only origin integration/vision-main-20260813
git status -sb
```

Resultado esperado:

```text
## integration/vision-main-20260813...origin/integration/vision-main-20260813
```

No debe aparecer ningún archivo modificado. `ReciEsp32CamSecrets.h` no debe
aparecer porque está ignorado. No ejecutar `git reset`, no cambiar a `main` y no
hacer un merge antes de la presentación.

## 6. Preparar red y credenciales sin publicarlas

1. Encender el hotspot Android en **2,4 GHz / WPA2 Personal**.
2. Conectar la Mac al hotspot.
3. Obtener la IP actual de la Mac:

   ```bash
   ipconfig getifaddr en0
   ```

4. Abrir localmente `ReciEsp32CamSecrets.h` y verificar, sin compartir valores:

   ```text
   WIFI_SSID
   WIFI_PASSWORD
   RECI_API_BASE_URL = http://<IP_ACTUAL_DE_LA_MAC>:3000
   RECI_ROBOT_API_KEY
   ```

5. Confirmar que la configuración local de la web apunta a:

   ```text
   VISION_SERVICE_URL=http://127.0.0.1:8001
   ```

6. `VISION_SERVICE_API_KEY` debe ser igual en la web y el servicio de visión.

Si se reinicia el hotspot, repetir `ipconfig getifaddr en0`: la IP puede cambiar.
Si cambia, actualizar `RECI_API_BASE_URL` y volver a cargar la ESP32-CAM.

Nunca ejecutar `git add` sobre secretos, `.env` o `.env.local`.

## 7. Levantar servicios en el orden correcto

### Terminal 1: servicio de visión, puerto 8001

```bash
cd /Users/hernandezaxel/Pau/Reci/ia/vision-service
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Debe terminar mostrando:

```text
Application startup complete.
modelo local listo
```

Las advertencias de LibreSSL o deprecación de `tf.lite.Interpreter` no impiden
la prueba. Si aparece `address already in use`, no iniciar otra copia. Verificar:

```bash
curl http://127.0.0.1:8001/health
lsof -nP -iTCP:8001 -sTCP:LISTEN
```

Si `/health` responde, el servicio ya estaba correctamente levantado.

### Terminal 2: backend web, puerto 3000 accesible en la red

```bash
cd /Users/hernandezaxel/Pau/Reci/web
npm run dev -- -H 0.0.0.0
```

Comprobar desde otra terminal:

```bash
curl -I http://127.0.0.1:3000
```

Para la presentación solo se levanta la web existente. No editar `web/`, no
actualizar dependencias y no intentar corregir su build esa mañana.

## 8. Compilar y cargar primero el Mega

Mantener desconectadas las fuentes de motores, servos y ESP32.

1. Abrir `ReciRutaDemo.ino`.
2. Seleccionar **Arduino Mega or Mega 2560**.
3. Seleccionar el puerto `/dev/cu.usbmodem...` correspondiente.
4. Pulsar **Verificar**.
5. Si compila, pulsar **Subir**.
6. Abrir Monitor Serial a **9600**.
7. Pulsar RST una vez.

Salida esperada:

```text
OLED: carita RECI lista.
LCD: lista en 0x27.
RECI Ruta Demo lista. El robot esta detenido.
VERSION: OLED + LCD + AUTO-REANUDAR v2
```

Enviar:

```text
STATUS
```

Después, solo si el robot está físicamente en BASE, enviar:

```text
SET:BASE
```

No usar `SET:BASE` para ocultar que el robot está en otro lugar.

Si la LCD u OLED no aparecen, revisar alimentación e I2C. La cámara no causa
que una pantalla I2C deje de ser detectada.

## 9. Compilar y cargar después la ESP32-CAM

1. Cerrar su Monitor Serial antes de subir.
2. Abrir `ReciEsp32Cam.ino`.
3. Seleccionar **AI Thinker ESP32-CAM**.
4. Seleccionar su puerto `/dev/cu.usbserial-...`.
5. Pulsar **Verificar**.
6. Pulsar **Subir**.
7. `Hash of data verified` y `Hard resetting via RTS pin...` significan que la
   carga terminó; no hay que esperar más.
8. Abrir Monitor Serial a **115200**.
9. Pulsar RST una vez.

Salida esperada:

```text
Firmware de votacion: seis-votos-v2-local-unanime
Sensor de camara detectado: PID=0x3660
Camara en QVGA (optimizada)
Wi-Fi listo: <IP_DE_LA_ESP32>
Listo. Envia C por el Monitor Serial para clasificar un residuo.
```

Si se queda en `Conectando al Wi-Fi`, apagar y encender el hotspot, confirmar
SSID/clave, esperar que la Mac reconecte y pulsar RST. No cambiar la IP del
backend hasta comprobar la nueva IP de la Mac.

## 10. Conectar ESP32 y Mega, siempre apagados

1. Apagar/desconectar Mega y ESP32.
2. Confirmar que motores y servos siguen sin alimentación.
3. Conectar ESP32 GPIO14/TX → Mega D17/RX2.
4. Conectar GND de ESP32 → GND del Mega.
5. Construir y medir el divisor 1 kΩ/2 kΩ.
6. Solo después conectar Mega D16/TX2 → divisor → ESP32 GPIO13/RX.
7. Alimentar Mega por USB.
8. Alimentar ESP32 con su USB/power bank estable.

No conectar el pin 5V del Mega al 5V de la ESP32 si cada placa ya está
alimentada por su propio USB.

## 11. Prueba escalonada sin motores ni servos

### 11.1 Arranque y pantallas

1. Reiniciar primero el Mega.
2. Reiniciar después la ESP32.
3. Confirmar en el Mega líneas `RX <- CMD:LCD:...` y `RX <- CMD:FACE:idle`.
4. Confirmar que no aparecen símbolos corruptos.

Si aparecen `�` o comandos demasiado largos:

- ambos UART deben estar a 9600;
- GPIO14 debe llegar a Mega D17, no D16;
- debe existir GND común;
- no continuar a servos hasta corregirlo.

### 11.2 Desconocido, primero

1. Colocar un objeto que no sea plástico ni vidrio.
2. En el Monitor Serial del ESP32, enviar `C`.
3. Esperar las tres fotos.

Resultado obligatorio:

```text
Resultado: DESCONOCIDO (...)
MEGA <- CMD:FACE:confused
MEGA <- CMD:LCD:No estoy seguro|Intenta de nuevo
```

No puede aparecer ninguna línea `CMD:CLASSIFY`.

### 11.3 Error del servicio

1. Dejar la web en 3000 activa.
2. Detener temporalmente `vision-service` en Terminal 1 con Ctrl+C.
3. Enviar `C` una vez desde la ESP32.
4. Confirmar error/rechazo y ausencia de `CMD:CLASSIFY`.
5. Volver a levantar `vision-service` en 8001 y comprobar `/health`.

### 11.4 Plástico y vidrio sin actuadores

1. Colocar plástico conocido, enviar `C` y confirmar
   `MEGA <- CMD:CLASSIFY:plastico`.
2. Colocar vidrio conocido, enviar `C` y confirmar
   `MEGA <- CMD:CLASSIFY:vidrio`.
3. Confirmar en el Mega `RX <- CMD:CLASSIFY:<material>`.

Si el resultado real no es correcto, repetir una sola vez con fondo limpio,
objeto centrado y luz frontal. No modificar reglas o el modelo esa mañana.

## 12. Probar las compuertas con motores desconectados

Apagar todo antes de conectar la fuente de servos. Mantener los motores sin
alimentación. Unir GND de la fuente de servos con GND del Mega sin devolver su
5 V al pin 5V del Mega.

Señales actuales:

| Compuerta | Pin de señal Mega | Cerrada | Abierta |
| --- | ---: | ---: | ---: |
| Vidrio | D3 | 45 | 166 |
| Plástico | D4 | 30 | 180 |

Primero probar desde el Monitor Serial del Mega:

```text
VIDRIO
```

Debe abrir únicamente vidrio y cerrar aproximadamente dos segundos después.
Luego:

```text
PLASTICO
```

Debe abrir únicamente plástico y cerrar aproximadamente dos segundos después.

Para probar el bloqueo, enviar `VIDRIO` y, antes de dos segundos, `PLASTICO`.
Debe aparecer:

```text
RECI: Una compuerta ya esta abierta.
```

La segunda compuerta no puede moverse.

Después repetir plástico, vidrio y desconocido desde la cámara. Desconocido no
debe mover ninguna compuerta.

## 13. Probar ruta y regresiones al final

Solo después de aprobar cámara y compuertas:

1. Apagar y conectar la alimentación de motores.
2. Levantar las ruedas del piso.
3. Encender y enviar `SET:BASE` solo si la posición física corresponde.
4. Enviar `P1`.
5. Confirmar movimiento, parada y `EVENT:ROUTE_STARTED` / `EVENT:ARRIVED`.
6. Durante una ruta, acercar un obstáculo al HC-SR04 sin tocar ruedas.
7. Confirmar freno, `EVENT:OBSTACLE` y reanudación segura al despejar.
8. Probar una llamada desde la app a P1 o P2.
9. Confirmar saludo en LCD al llegar.
10. Clasificar un residuo después de la llegada.
11. Confirmar puntos asociados a la llamada o QR si no hay llamada.
12. Confirmar que una ruta no comienza mientras una compuerta está abierta.

Pines que no se modifican durante esta prueba:

- motores izquierdos: D5, D6, D7, D8;
- motores derechos: D9, D10, D11, D13;
- HC-SR04: TRIG D22, ECHO D23;
- PIR: D28;
- OLED/LCD I2C: SDA D20, SCL D21;
- servos: vidrio D3, plástico D4;
- UART2: RX2 D17, TX2 D16.

La ruta usa actualmente 8 segundos BASE→P1 y 8 segundos P1→P2. El regreso a
BASE es manual por seguridad.

## 14. Secuencia corta para presentar a las 14:00

Treinta minutos antes:

1. Encender hotspot y conectar la Mac.
2. Confirmar que la IP de la Mac no cambió.
3. Levantar `vision-service` y web.
4. Comprobar `/health`.
5. Encender Mega y después ESP32.
6. Colocar físicamente el robot en BASE y enviar `SET:BASE`.

Demostración recomendada:

1. Mostrar que RECI está listo en LCD/OLED.
2. Probar primero un desconocido y explicar que no abre ninguna compuerta.
3. Probar plástico.
4. Probar vidrio.
5. Mostrar el cierre automático y el bloqueo de segunda orden.
6. Si hay espacio seguro, ejecutar llamada/ruta y mostrar puntos o QR.

No ocultar un fallo. Si OpenAI o Internet caen, explicar la protección y mostrar
que el resultado incompleto no genera `CMD:CLASSIFY`.

## 15. Recuperación rápida

| Síntoma | Acción inmediata |
| --- | --- |
| Puerto 8001 ocupado | Probar `/health`; si responde, usar el proceso existente |
| Puerto 3000 no responde | Levantar `npm run dev -- -H 0.0.0.0` |
| ESP no ve el hotspot | Alternar hotspot, reconectar Mac y pulsar RST |
| IP de la Mac cambió | Actualizar `RECI_API_BASE_URL` y recargar ESP32 |
| `CALLS: /next respondio -1` | Backend 3000 no accesible desde la ESP32 |
| Caracteres `�` en Mega | Revisar 9600, GPIO14→D17 y GND común |
| LCD no encontrada | Revisar SDA20/SCL21, GND, VCC y dirección 0x27 |
| OLED no encontrada | Revisar SDA20/SCL21, voltaje del módulo y dirección 0x3C |
| Cámara PID distinto | No continuar; verificar módulo/cable de cámara |
| Reinicios del ESP32 | Fuente 5 V inestable; mantener flash integrado apagado |
| Desconocido genera `CMD:CLASSIFY` | Apagar servos y detener la presentación técnica |
| Dos compuertas se mueven | Cortar alimentación de servos; no corregir con software improvisado |
| Motores arrancan al encender | Cortar alimentación de motores inmediatamente |

## 16. Plan B honesto si falta tiempo

Prioridad mínima segura:

1. Servicios funcionando.
2. Cámara OV3660/QVGA detectada.
3. UART sin corrupción.
4. Desconocido sin `CMD:CLASSIFY`.
5. Plástico y vidrio con comando correcto.
6. Cada compuerta abre sola y cierra.

Si navegación o llamadas fallan, no tocar la política de visión. Presentar la
clasificación y compuertas, y mostrar como evidencia las 49 pruebas, 118/118
casos expertos y 216 combinaciones Python–firmware ya publicadas.

## 17. Checklist antes de salir de Portoviejo

- [ ] Rama correcta y árbol Git limpio.
- [ ] Servicio 8001 responde `/health`.
- [ ] Web 3000 accesible desde la red.
- [ ] IP del backend coincide con la IP actual de la Mac.
- [ ] Mega cargado con `ReciRutaDemo.ino`.
- [ ] ESP32 cargada con `ReciEsp32Cam.ino`.
- [ ] PID `0x3660` y QVGA confirmados.
- [ ] Desconocido sin `CMD:CLASSIFY`.
- [ ] Plástico correcto.
- [ ] Vidrio correcto.
- [ ] Compuerta de vidrio abre sola y cierra.
- [ ] Compuerta de plástico abre sola y cierra.
- [ ] Segunda orden bloqueada.
- [ ] Ruta/obstáculo comprobados o anotados como pendientes.
- [ ] Llamada, llegada, puntos y QR comprobados o anotados.
- [ ] Laptop, celular y power bank cargados.
- [ ] Cables, resistencias, muestras y herramientas empacados.
- [ ] Servicios cerrados y hardware apagado antes del traslado.

No fusionar con `main` antes de la revisión de la compañera.
