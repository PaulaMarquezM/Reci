# Reci: guía para continuar la prueba ESP32-CAM + Arduino Uno

Esta guía retoma la prueba desde el punto en que quedó. No hace falta volver a configurar Wi-Fi ni volver a registrar el rostro en la app.

## Estado actual

Ya funciona lo siguiente:

- La ESP32-CAM se conecta a la red Wi-Fi de 2.4 GHz.
- La ESP32-CAM alcanza la app de Reci en la Mac.
- La app envía la foto al servicio facial.
- El servicio facial detectó un rostro al menos una vez: `POST /api/face/recognize 200`.

Los mensajes `422` anteriores significan que en esa foto no se detectó un rostro válido; no indican un problema de red.

## Antes de encender la ESP32-CAM

Abre **dos terminales** en la Mac y déjalas abiertas durante la prueba.

### Terminal 1: aplicación web de Reci

```bash
cd /Users/pau/Documents/devStudent/Reci/web
npm run dev -- -H 0.0.0.0
```

Debe aparecer que Next está listo en el puerto `3000`.

### Terminal 2: servicio facial

```bash
cd /Users/pau/Documents/devStudent/Reci/ia/face-service
source .venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 8000
```

Debe aparecer `Uvicorn running on http://127.0.0.1:8000`.

## Conexiones que ya quedan en el Arduino Uno

| Componente | Pin del Arduino Uno |
| --- | --- |
| OLED SDA | A2 |
| OLED SCL | A3 |
| OLED VCC / GND | 5V* / GND |
| LCD SDA | A4 |
| LCD SCL | A5 |
| LCD VCC / GND | 5V / GND |

\* Si el módulo OLED indica que usa solo 3.3 V, usa 3.3 V en vez de 5 V.

## Conectar la ESP32-CAM al Uno

La ESP32-CAM permanece puesta en su adaptador USB y alimentada por su propio USB. El Uno también usa su propio USB.

La comunicación requiere únicamente dos conexiones:

| ESP32-CAM | Arduino Uno | Uso |
| --- | --- | --- |
| `IO14` | D10 | Datos desde la ESP hacia el Uno |
| `GND` | GND | Tierra común, obligatoria |

No conectes el pin D11 del Uno a la ESP. No conectes 5 V del Uno a la ESP32-CAM.

### Importante sobre los cables

La cámara entra en un adaptador USB y sus pines no quedan disponibles para conectar Dupont al mismo tiempo. Para esta conexión permanente hay que soldar dos cables finos a los contactos rotulados **IO14** y **GND** de la placa ESP32-CAM, no al adaptador USB.

Hazlo con el USB desconectado y la cámara retirada del adaptador. Luego se vuelve a colocar la cámara en el adaptador USB. Si no hay cautín, no fuerces cables dentro de los huecos: espera a tener ayuda para soldar o un adaptador de pines apilable.

## Cargar el sketch al Arduino Uno

1. Abre Arduino IDE.
2. Ve a **File → Open…**.
3. Abre este archivo:

   ```text
   /Users/pau/Documents/devStudent/Reci/firmware/arduino-uno/ReciUnoEsp32CamTest/ReciUnoEsp32CamTest.ino
   ```

4. Selecciona placa **Arduino Uno** y el puerto del Uno. No selecciones el puerto `usbserial-1130`, que corresponde a la ESP32-CAM.
5. Pulsa **Upload**.

El sketch requiere las librerías `U8g2` y `LiquidCrystal I2C`. Ya estaban instaladas si la prueba previa de las dos pantallas funcionó.

## Prueba final

1. Enciende el Uno y la ESP32-CAM.
2. La LCD del Uno debe mostrar `Hola, soy Reci` y `Mira a camara`.
3. El OLED debe mostrar la carita.
4. Pulsa el botón **RST** de la ESP32-CAM.
5. Ponte frente a la cámara, a 40–70 cm, mirando al lente y con luz frontal.

Durante el intento, el OLED cambia a cara pensativa. Si coincide con el rostro registrado en la app, la LCD muestra el saludo con el nombre. Si no hay coincidencia, mostrará que no pudo reconocerte o te pedirá intentar de nuevo.

## Si algo falla

| Mensaje | Qué significa | Qué hacer |
| --- | --- | --- |
| `ERROR: no se pudo conectar al Wi-Fi` | La ESP no pudo entrar a la red. | Confirma que la red es 2.4 GHz y revisa SSID/clave del archivo de secretos. |
| `ERROR: /recognize respondió -1` | La ESP no logra comunicarse con la app web. | Confirma que Next sigue abierto con `-H 0.0.0.0` y que la IP de la Mac no cambió. |
| `POST /api/face/recognize 422` | La foto no tenía un rostro válido. | Mejora la luz, mira al lente y no estés demasiado cerca. |
| `POST /api/face/recognize 200` | La toma llegó y se procesó correctamente. | Revisa el Monitor Serial y las pantallas para ver si hubo coincidencia. |
| Símbolos raros al inicio del Monitor Serial | La ESP se reinició con el monitor abierto. | Es normal; espera a que se reconecte a Wi-Fi. |

## Seguridad al finalizar la prueba

Las claves de Wi-Fi y de API no deben compartirse ni subirse a Git. Como fueron visibles durante la configuración, conviene rotar `ROBOT_API_KEY`, `FACE_SERVICE_API_KEY` y las claves de Supabase antes de una demostración pública o de publicar el repositorio.
