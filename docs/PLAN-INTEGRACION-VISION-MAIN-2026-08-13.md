# Plan de integración de visión con la rama principal

**Fecha de preparación:** 12 de agosto de 2026
**Sesión prevista:** 13 de agosto de 2026
**Fuente de visión auditada:** `integration/andrea-axel-vision` en `7c375c4`
**Rama principal auditada:** `origin/main` en `96aaa96`
**Estado:** integración en `integration/vision-main-20260813`; pendiente de
pruebas finales y revisión, sin fusión realizada desde esta rama hacia `main`

**Alcance acordado para esta fase:** el equipo de visión no modifica `web/`.
Las referencias web de este documento se conservan únicamente como contexto
histórico del contrato ya integrado; no forman parte de los cambios, pruebas ni
commits preparados el 13 de agosto después de seleccionar el modelo local.

## 1. Objetivo exacto

Integrar en el proyecto principal únicamente el subsistema de clasificación de
residuos que ya fue probado:

- cámara OV3660 en una placa compatible con AI Thinker ESP32-CAM;
- tres capturas QVGA por residuo;
- OpenAI + heurísticas OpenCV + sistema experto de 193 reglas;
- MobileNetV2 TFLite float32 como modelo local activo; MobileNetV3-Large INT8
  se conserva como respaldo auditado sin voto;
- dos diagnósticos por foto, hasta seis diagnósticos por depósito;
- una única decisión final: `plastico`, `vidrio` o `desconocido`;
- apertura de una sola compuerta únicamente después de una decisión válida.

La integración no debe reemplazar ni degradar las funciones que ya están en la
rama principal: HTTPS, llamadas desde la aplicación, navegación, reporte de
posición, puntos, QR, LCD, OLED, freno ultrasónico y control de motores.

## 2. Conclusión de la auditoría

No se debe hacer un `merge` directo de toda la rama
`integration/andrea-axel-vision` sobre `main` ni copiar completo su firmware de
ESP32-CAM. Una simulación de mezcla detectó conflictos en:

- `firmware/arduino-mega/ReciMega.ino`;
- el traslado del sketch antiguo de ESP32-CAM a su carpeta actual;
- `firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino`.

Además de esos conflictos visibles, sustituir el sketch completo eliminaría
funciones nuevas de `main` que Git no puede proteger semánticamente:

- `ReciHttpClient` y el certificado para HTTPS;
- sincronización NTP antes de usar TLS;
- `RobotCallDispatcher`;
- contexto de la llamada para asignar puntos;
- consulta de rutas y reporte de llegada/posición.

La estrategia segura es crear una rama nueva desde la última `main`, trasladar
selectivamente el servicio de visión y adaptar a mano solo la parte de
clasificación del firmware principal.

## 3. Qué existe actualmente en cada rama

| Componente | `origin/main` (`96aaa96`) | Rama de visión (`7c375c4`) | Acción |
| --- | --- | --- | --- |
| Web y API del robot | Desplegada; HTTPS y contratos de llamadas actuales | Basada en una versión anterior | Conservar `main`; añadir solo el contrato `vision_votes` |
| Servicio experto | Proveedor + sistema experto, sin modelo local activo | OpenAI + sistema experto + modelos locales candidatos | Trasladar selectivamente y validar el artefacto desplegado |
| Modelo local | No está en `main` | V2 float32 y V3 INT8 disponibles | Activar V2 por la comparación operativa; conservar V3 como respaldo |
| ESP32-CAM | HTTPS, NTP, llamadas y eventos; vota un resultado por foto | OV3660/QVGA y votación separada por fuente | Integrar funciones, no reemplazar archivo |
| Mega para demo real | `ReciRutaDemo.ino`, rutas, motores, servos y eventos | No contiene los últimos cambios | Conservar exactamente el de `main` |
| Mega modular | `ReciMega.ino`, navegación por sensores de línea | Tiene cambios antiguos de PIR | No usar como objetivo de la demo actual |
| Uno de prueba | Receptor UART con OLED/LCD | Igual; no muestra `CLASSIFY` en Serial | Mejorar solo el sketch de prueba |

La rama principal avanzó dos commits respecto al ancestro común `06d6870`; la
rama de visión tiene 51 commits propios. Esa divergencia es otra razón para no
mezclar todo automáticamente.

## 4. Hallazgos que no se pueden ignorar

### 4.1 El sketch del Mega que corresponde a la demostración completa

Para la prueba integrada se debe usar:

`firmware/arduino-mega/ReciRutaDemo/ReciRutaDemo.ino`

Ese archivo acepta `BASE`, `P1`, `P2`, emite `EVENT:ROUTE_STARTED`,
`EVENT:ARRIVED`, `EVENT:OBSTACLE` y `EVENT:PRESENCE`, controla las compuertas y
acepta `CMD:CLASSIFY:vidrio|plastico`. Es el que coincide con
`RobotCallDispatcher` del ESP32-CAM.

`firmware/arduino-mega/ReciMega.ino` no procesa actualmente las órdenes
`BASE/P1/P2` del despachador. No se deben combinar ambos sketches durante esta
integración.

### 4.2 Hay documentación contradictoria sobre los pines UART

El código principal y `firmware/esp32-cam/README.md` usan **Serial2**:

- Mega D17/RX2 recibe desde ESP32 GPIO14/TX;
- Mega D16/TX2 transmite hacia ESP32 GPIO13/RX mediante divisor de voltaje;
- GND de ambos equipos debe ser común.

Una sección antigua de `docs/CONEXIONES.md` todavía coloca el ESP32 en
Serial1/D18-D19 y el HC-05 en D16-D17. Antes de conectar el Mega hay que mirar
el cableado real y confirmar que D16/D17 están libres. Para esta integración
manda el código actual: Serial2 queda para la ESP32-CAM. Si el HC-05 ya está
físicamente conectado allí, se detiene la prueba y el equipo decide dónde
reubicarlo; no se conectan dos dispositivos al mismo UART.

### 4.3 La prueba con Uno es útil, pero no sustituye la prueba con Mega

El Uno comprueba que GPIO14 transmite líneas completas a 9600 baudios y que los
comandos llegan sin corrupción. No comprueba:

- el canal Mega → ESP32 por GPIO13;
- el divisor de nivel de 5 V a 3,3 V;
- `RobotCallDispatcher`;
- las rutas `BASE/P1/P2` y los eventos de llegada;
- los servos o bloqueos de seguridad del Mega.

### 4.4 Política vigente: votación conjunta de las dos fuentes

MobileNetV2 y OpenAI+sistema experto analizan las mismas tres fotos y
aportan seis votos individuales. La política restaurada combina ambas fuentes:

1. `desconocido` es una abstención y no suma a plástico ni a vidrio.
2. Se cuentan juntos los votos válidos de las dos fuentes.
3. Si OpenAI+sistema experto aporta tres abstenciones, el modelo local decide
   únicamente si sus tres votos son idénticos; una mayoría local 2–1 devuelve
   `desconocido`.
4. En los demás casos gana la clase con mayor cantidad total de votos.
5. Si el resultado total empata, se usa la preferencia de los votos válidos de
   OpenAI+sistema experto como desempate.
6. Si faltó una respuesta o el empate no puede resolverse con el proveedor, el
   resultado es `desconocido` y no se abre ninguna compuerta.

Ejemplos obligatorios:

| OpenAI | Modelo local | Resultado |
| --- | --- | --- |
| P, P, D | P, V, P | plástico, 4–1 |
| V, V, D | V, P, V | vidrio, 4–1 |
| P, D, D | P, P, V | plástico, 3–1 |
| V, D, D | V, V, P | vidrio, 3–1 |
| D, D, D | V, V, V | vidrio por unanimidad local, 3–0 |
| D, D, D | V, V, P | desconocido; modelo local no unánime |
| P, D, D | V, V, V | vidrio, 3–1 |
| P, P, V | V, V, P | plástico por desempate del proveedor, 3–3 |

`P` significa plástico, `V` vidrio y `D` desconocido/abstención. Como el modelo
local es binario, la batería física debe incluir objetos fuera de distribución
para observar el riesgo de que sus votos dominen cuando el proveedor se
abstiene; ese riesgo queda documentado y no se oculta.

### 4.5 Selección del modelo local activo

El 13 de agosto se compararon los dos artefactos TFLite disponibles con el
mismo pipeline de producción sobre 1.000 capturas OV3660/QVGA balanceadas:

| Artefacto | Tipo | Exactitud | Macro-F1 | Mayoría de tripletas | p50 |
| --- | --- | ---: | ---: | ---: | ---: |
| MobileNetV2 | float32 | 71,60 % | 71,25 % | 75,15 % | 14,53 ms |
| MobileNetV3-Large | INT8 | 57,10 % | 57,09 % | 59,09 % | 5,12 ms |

MobileNetV2 queda activo porque la mejora de calidad supera ampliamente la
diferencia de latencia dentro del servicio Python. El conjunto puede solaparse
con datos de desarrollo, por lo que sirve para escoger entre artefactos pero no
se presenta como prueba reservada. MobileNetV3-Large INT8 se conserva completo
en `model/backups/` y no participa en `vision_votes`.

El modelo local sigue siendo binario y no produce por sí mismo la categoría
`desconocido`. Esa salida pertenece al proveedor+sistema experto y a la
política final. Cuando el proveedor entrega tres abstenciones, se conserva la
decisión acordada por el equipo: el modelo local solo autoriza con unanimidad
3/3; una división 2–1 rechaza.

### 4.6 Desarrollo local y producción no tienen la misma red

Para la prueba local, la ESP32 llama a Next.js en la IP de la Mac y Next.js
llama a `vision-service` en la misma Mac. Una aplicación desplegada en Vercel
no puede llamar a `127.0.0.1` de la Mac. La integración de código puede quedar
completa localmente, pero producción necesita que `VISION_SERVICE_URL` apunte a
un contenedor accesible desde Vercel. No se debe declarar producción completa
sin verificar este punto.

## 5. Reglas de seguridad para toda la sesión

- Nunca trabajar directamente sobre `main`.
- Nunca subir `ReciEsp32CamSecrets.h`, `.env`, claves o contraseñas.
- No conectar Mega TX de 5 V directamente a GPIO13 del ESP32.
- No alimentar el ESP32 desde el pin 5 V del Uno.
- No alimentar servos desde el 5 V del Mega bajo carga.
- Conectar GND común antes de conectar señales UART.
- Hacer las primeras pruebas del Mega con motores sin alimentación y ruedas
  levantadas.
- Mantener los servos sin alimentación hasta aprobar el caso desconocido.
- Una prueba fallida detiene la fase; no se continúa “para ver si después
  funciona”.
- No borrar ni reemplazar funciones de navegación, HTTPS o llamadas para hacer
  pasar la clasificación.

## 6. Fase A — prueba ESP32-CAM → Arduino Uno

### 6.1 Material necesario

- ESP32-CAM con OV3660 y cable USB;
- Arduino Uno y cable USB;
- un cable Dupont para la señal;
- un cable Dupont para GND común;
- iluminación externa estable;
- computadora y hotspot Wi-Fi de 2,4 GHz;
- al menos un objeto conocido de vidrio, uno de plástico y uno ajeno a esas
  clases.

### 6.2 Cableado, con ambos equipos apagados

| Origen | Destino | Motivo |
| --- | --- | --- |
| ESP32 GPIO14/TX | Uno D10/RX | Datos a 9600 baudios |
| ESP32 GND | Uno GND | Referencia eléctrica común |
| ESP32 USB | Computadora o fuente USB estable | Alimentación propia |
| Uno USB | Computadora | Alimentación y Monitor Serial |

No conectar Uno D11 al ESP32. No conectar 5 V entre las placas. En esta fase la
comunicación es únicamente ESP32 → Uno.

### 6.3 Archivos que se abren en Arduino IDE

ESP32-CAM:

`firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino`

Arduino Uno:

`firmware/arduino-uno/ReciUnoEsp32CamTest/ReciUnoEsp32CamTest.ino`

Configuración ESP32:

- placa: `AI Thinker ESP32-CAM`;
- puerto: el USB serial que aparece al conectar la placa;
- Monitor Serial: 115200;
- librería: ArduinoJson;
- red: exclusivamente 2,4 GHz.

Configuración Uno:

- placa: `Arduino Uno`;
- puerto: el que desaparece al desconectar el Uno;
- Monitor Serial: 115200;
- enlace interno `SoftwareSerial`: 9600;
- librerías del sketch actual: U8g2 y LiquidCrystal I2C.

### 6.4 Mejora obligatoria del receptor Uno

El sketch actual recibe `CMD:CLASSIFY`, pero no lo muestra ni lo procesa. Antes
de usarlo como evidencia, el agente debe hacer dos cambios pequeños:

1. imprimir en el Monitor Serial cada línea completa recibida, antes de llamar
   a `processCommand`;
2. reconocer el prefijo `CMD:CLASSIFY:` y mostrar el material en Serial y, si
   están conectadas, en las pantallas.

No se agrega ningún servo al Uno. La prueba solo observa comandos.

Salida mínima esperada en el Monitor Serial del Uno:

```text
ESP -> UNO: CMD:FACE:thinking
ESP -> UNO: CMD:LCD:Analizando residuo|No lo retires
ESP -> UNO: CMD:CLASSIFY:vidrio
ESP -> UNO: CMD:FACE:happy
```

Para un desconocido no debe aparecer ninguna línea `CMD:CLASSIFY:`.

### 6.5 Preparación de servicios en la Mac

Terminal 1:

```bash
cd /Users/hernandezaxel/Pau/Reci/ia/vision-service
python3 -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Terminal 2:

```bash
cd /Users/hernandezaxel/Pau/Reci/web
npm run dev -- -H 0.0.0.0
```

Antes de probar:

- la Mac y el ESP32 deben estar en el mismo hotspot;
- `web/.env.local` debe apuntar `VISION_SERVICE_URL` a
  `http://127.0.0.1:8001` y usar la misma `VISION_SERVICE_API_KEY` del servicio;
- el archivo local ignorado `ReciEsp32CamSecrets.h` debe usar
  `http://IP_DE_LA_MAC:3000`, nunca `localhost` ni `127.0.0.1`;
- no se copian los valores de las claves al documento, commit o chat.

Comprobación del servicio:

```bash
curl http://127.0.0.1:8001/health
```

Debe indicar `status: ok`, modelo local disponible y el archivo
`model.tflite`. Si el modelo local no está disponible, se detiene la prueba.

### 6.6 Orden de carga y encendido

1. Con las placas todavía separadas, cargar el sketch de prueba al Uno.
2. Abrir su Monitor Serial y confirmar que inicia sin caracteres corruptos.
3. Cerrar el Monitor Serial del Uno antes de volver a seleccionar otro puerto.
4. Cargar el firmware de visión al ESP32-CAM.
5. Abrir el Monitor Serial del ESP32 a 115200.
6. Confirmar `Sensor de camara detectado: PID=0x3660`.
7. Confirmar `Camara en QVGA (optimizada)` y `Wi-Fi listo`.
8. Apagar/desconectar ambos equipos.
9. Conectar GPIO14 → D10 y GND → GND.
10. Encender primero el Uno y después el ESP32.
11. Confirmar en el Uno la recepción de `CMD:LCD` y `CMD:FACE:idle`.

Los caracteres ilegibles que aparecen únicamente durante el arranque ROM del
ESP32 no invalidan la prueba. Los comandos posteriores sí deben ser legibles.

### 6.7 Matriz mínima de prueba con Uno

Hacer al menos tres rondas por caso, sin cambiar iluminación dentro de una
ronda:

| Caso | Resultado esperado |
| --- | --- |
| Botella de vidrio conocida | exactamente un `CMD:CLASSIFY:vidrio` |
| Botella de plástico conocida | exactamente un `CMD:CLASSIFY:plastico` |
| Objeto ajeno: lata/cartón/mano | ningún `CMD:CLASSIFY` |
| Wi-Fi apagado | ningún `CMD:CLASSIFY` |
| `vision-service` detenido | ningún `CMD:CLASSIFY` |

Registrar por ronda:

| Dato | Valor |
| --- | --- |
| Objeto real | |
| Iluminación | |
| Tres votos OpenAI | |
| Tres votos MobileNetV2 | |
| Regla final | |
| Comando recibido en Uno | |
| Tiempo total aproximado | |
| Correcto | sí/no |

La fase A aprueba únicamente si el Uno recibe líneas completas y los cinco
casos cumplen la política de seguridad. Si el caso desconocido produce
`CMD:CLASSIFY`, se documenta el resultado y se implementa la regla de la
sección 4.4 antes de continuar.

## 7. Fase B — crear la rama de integración desde la principal

No ejecutar estos comandos con cambios locales sin guardar. El agente debe
mostrar primero `git status` y detenerse si hay archivos modificados que no
reconoce.

```bash
cd /Users/hernandezaxel/Pau/Reci
git fetch origin --prune
git status --short
git switch -c integration/vision-main-20260813 origin/main
git rev-parse --short HEAD
```

El 12 de agosto el punto esperado era `96aaa96`. Si mañana `origin/main` está
en otro commit, revisar primero:

```bash
git log --oneline 96aaa96..origin/main
git diff --name-status 96aaa96..origin/main -- \
  firmware/arduino-mega \
  firmware/esp32-cam \
  ia/vision-service \
  web/src/app/api/vision \
  web/src/lib/vision
```

Si aparece algún cambio en esas rutas, se pausa la copia selectiva y se ajusta
este plan a la nueva versión. No se asume que `main` permanece igual.

## 8. Fase C — trasladar el servicio de visión

### 8.1 Archivos de producción y pruebas que sí se trasladan

- `ia/vision-service/main.py`;
- `ia/vision-service/vision/`;
- `ia/vision-service/expert_system/`;
- `ia/vision-service/tests/`;
- `ia/vision-service/Dockerfile`;
- `ia/vision-service/requirements.txt`;
- `ia/vision-service/requirements-dev.txt`;
- `ia/vision-service/.gitignore`;
- `ia/vision-service/README.md`;
- `ia/vision-service/scripts/probar_fotos.py`;
- `ia/vision-service/scripts/probar_sistema_mixto.py`;
- `ia/vision-service/scripts/comparar_modelos_locales.py`;
- `ia/vision-service/scripts/entrenamiento/`, porque una prueba automatizada
  valida su manifiesto;
- modelo activo, etiquetas, README, manifiesto y validación TFLite;
- respaldo MobileNetV3-Large INT8 para auditoría o comparación en sombra.

Comando base, desde la nueva rama:

```bash
git restore --source=origin/integration/andrea-axel-vision -- \
  ia/vision-service/.gitignore \
  ia/vision-service/Dockerfile \
  ia/vision-service/README.md \
  ia/vision-service/requirements.txt \
  ia/vision-service/requirements-dev.txt \
  ia/vision-service/main.py \
  ia/vision-service/expert_system \
  ia/vision-service/vision \
  ia/vision-service/tests \
  ia/vision-service/scripts/probar_fotos.py \
  ia/vision-service/scripts/probar_sistema_mixto.py \
  ia/vision-service/scripts/comparar_modelos_locales.py \
  ia/vision-service/scripts/entrenamiento \
  ia/vision-service/model/model.tflite \
  ia/vision-service/model/labels.txt \
  ia/vision-service/model/README.md \
  ia/vision-service/model/entrenamiento_manifest.json \
  ia/vision-service/model/tflite_validacion.json \
  ia/vision-service/model/backups/mobilenetv2_run_20260721_2129 \
  ia/vision-service/model/backups/mobilenetv3large_20260809_004420_split42_seed1
```

No trasladar al runtime de `main`:

- `dataset-esp32cam/`;
- `runs/*.keras`;
- `.venv/` o `__pycache__/`;
- claves o archivos `.env`;
- los notebooks, salvo que el equipo decida publicarlos como material académico;
- modelos candidatos de EfficientNet u otras corridas no ganadoras.

### 8.2 Verificaciones inmediatas

```bash
cd /Users/hernandezaxel/Pau/Reci/ia/vision-service
python3 -m pytest -q
python3 tests/test_cases.py
shasum -a 256 model/model.tflite
```

Resultados de referencia antes de integrar:

- `pytest`: 20 pruebas aprobadas;
- sistema experto: 118/118;
- SHA-256 de MobileNetV2 activo:
  `da71c12244076c1fe8f206a444f0c7fad9af467f813976acd40e027ae62f56b1`.

La advertencia local de LibreSSL y la deprecación de
`tensorflow.lite.Interpreter` no son fallos de prueba. Sí es fallo que no cargue
el modelo, que cambie el hash o que falte una clase.

### 8.3 Aplicar la votación conjunta

Actualizar `vision/voting.py`, sus pruebas y la función equivalente del
firmware para cumplir la tabla de la sección 4.4. La prueba automatizada debe
incluir como mínimo:

- mayoría total de los seis votos;
- abstenciones del proveedor;
- mayoría local contraria a un voto aislado del proveedor;
- empate 3–3 resuelto por el proveedor;
- confusión que no pueda desempatarse;
- captura o fuente ausente.

No se usan umbrales de confianza inventados. Si el equipo desea un umbral del
modelo local, debe calibrarlo con un conjunto reservado que contenga objetos
ajenos; no se elige durante la prueba mirando resultados individuales.

## 9. Fase D — integrar el contrato en Next.js

Antes de editar `web/`, leer completo `web/AGENTS.md`. La versión principal usa
Node 24 y Next.js 16.3; no copiar `package.json`, `.nvmrc` ni
`package-lock.json` de la rama de visión.

Trasladar solamente:

```bash
git restore --source=origin/integration/andrea-axel-vision -- \
  web/src/lib/vision/service.ts \
  web/src/app/api/vision/classify/route.ts
```

Después revisar manualmente que:

- se preserva `record_event=false` en las tres fotos;
- `vision_provider_result`, `vision_local_result` y `vision_votes` atraviesan
  la ruta sin perderse;
- solo se aceptan las fuentes `openai_sistema_experto` y `modelo_local`;
- `vision_local_shadow_result` no entra en `vision_votes`;
- la caída del servicio devuelve `desconocido`;
- los comentarios nombran MobileNetV2 como activo y V3 únicamente como respaldo;
- no se modifica ninguna ruta de llamadas, eventos, autenticación o Supabase.

Pruebas web, con Node 24:

```bash
cd /Users/hernandezaxel/Pau/Reci/web
npm ci
npm run lint
npm run build
```

No continuar si `lint` o `build` fallan. No se arreglan errores eliminando
validaciones de tipos.

## 10. Fase E — adaptar el firmware principal de ESP32-CAM

Archivo destino:

`firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino`

Se edita el archivo que viene de `main`. No se restaura ni copia encima el de
la rama de visión.

### 10.1 Elementos de `main` que deben permanecer

- `#include "ReciHttpClient.h"`;
- `#include "RobotCallDispatcher.h"`;
- certificado TLS y selección HTTP/HTTPS;
- sincronización NTP de `connectWiFi`;
- `ReciRobotCallDispatcher dispatcher(mega)`;
- `dispatcher.addRecycleContext`, `clearRecycleContext` y asignación directa de
  puntos a la llamada;
- `dispatcher.begin()` en `setup`;
- `dispatcher.tick()` en `loop`;
- endpoints de llamadas, posición y eventos;
- uso de `ReciHttpClient` en todas las solicitudes.

### 10.2 Elementos de la rama de visión que se integran

- soporte explícito y registro del PID OV3660;
- QVGA fija para mantener el dominio probado;
- `WiFi.setSleep(false)` y espera de conexión ampliada;
- timeout HTTP de visión de 30 segundos;
- contador de abstenciones;
- lectura de `vision_votes` por cada foto;
- acumuladores independientes `providerVotes` y `localVotes`;
- compatibilidad temporal con una respuesta sin `vision_votes`;
- diagnóstico opcional `vision_local_shadow_result`, siempre sin voto;
- registro de los seis diagnósticos y de la regla final;
- confianza final calculada con los votos ganadores de ambas fuentes, o solo
  con el proveedor cuando este resuelve un empate;
- votación conjunta y desempate de la sección 4.4.

### 10.3 Elementos que no se copian desde la rama de visión

- `WiFiClient` plano en lugar de `ReciHttpClient`;
- la función facial `greetVisitor` y su lector PIR antiguo;
- el `recordRecycleEvent` que no conoce `RobotCallDispatcher`;
- un `setup` sin `dispatcher.begin`;
- un `loop` sin `dispatcher.tick`;
- archivos locales de credenciales.

### 10.4 Contrato de salida al Mega

La IA solo debe emitir:

```text
CMD:CLASSIFY:vidrio
```

o:

```text
CMD:CLASSIFY:plastico
```

una vez por depósito aprobado. Para `desconocido`, error, empate o falta de
respuesta no se emite ningún `CMD:CLASSIFY`; solo se permiten mensajes de LCD y
cara de rechazo.

### 10.5 Compilación

En Arduino IDE:

- placa `AI Thinker ESP32-CAM`;
- cámara OV3660 conectada como está actualmente;
- ArduinoJson instalada;
- archivo local de secretos al lado del `.ino` e ignorado por Git;
- verificar primero, cargar después;
- Monitor Serial a 115200.

La compilación exitosa no prueba la política de decisión; después hay que
repetir la matriz de la fase A con el firmware integrado.

## 11. Fase F — prueba ESP32-CAM ↔ Arduino Mega

### 11.1 Firmware del Mega

Usar el archivo de `main`:

`firmware/arduino-mega/ReciRutaDemo/ReciRutaDemo.ino`

No cambiar pines de motores, servos ni calibraciones durante la integración de
IA. Si algo físico no coincide, se documenta como problema separado.

### 11.2 Cableado bidireccional

Con todo apagado:

| ESP32-CAM | Arduino Mega | Condición |
| --- | --- | --- |
| GPIO14/TX | D17/RX2 | directo |
| GPIO13/RX | D16/TX2 | divisor 1 kΩ / 2 kΩ obligatorio |
| GND | GND | obligatorio |
| 5V | fuente USB/power bank estable | no desde el Mega |

Divisor:

```text
Mega D16/TX2 ── 1 kΩ ──┬── GPIO13/RX ESP32
                       │
                      2 kΩ
                       │
                      GND
```

Medir aproximadamente 3,3 V en el nodo antes de conectarlo al ESP32. GPIO13 y
GPIO14 se comparten con microSD en algunas placas; no habilitar microSD mientras
se use este UART.

### 11.3 Prueba escalonada

1. Desconectar alimentación de motores y servos.
2. Mantener ruedas levantadas.
3. Cargar `ReciRutaDemo.ino` al Mega.
4. Confirmar que `kEsp32CamConectada` sea `false` mientras RX2 esté físicamente
   desconectado; ponerlo en `true` únicamente después del cableado UART.
5. Conectar UART y volver a cargar el Mega con la opción correcta.
6. Encender Mega y después ESP32.
7. Confirmar en LCD/Serial los comandos de inicio.
8. Ejecutar una clasificación de vidrio y una de plástico sin servos
   alimentados; el Mega debe reconocer el comando, pero no habrá movimiento.
9. Ejecutar desconocido y caída de red; no debe aparecer una orden de apertura.
10. Alimentar únicamente los servos con fuente adecuada y GND común.
11. Repetir vidrio: solo la compuerta de vidrio abre y se cierra.
12. Repetir plástico: solo la compuerta de plástico abre y se cierra.
13. Repetir desconocido: ninguna compuerta se mueve.
14. Enviar dos clasificaciones seguidas mientras una compuerta está abierta;
    la segunda debe ser ignorada por seguridad.
15. Solo después conectar motores y probar rutas con ruedas levantadas.

### 11.4 Regresiones del proyecto principal

La integración no se aprueba hasta verificar también:

- conexión HTTPS del ESP32 con la URL de producción o HTTP local según la
  configuración elegida;
- consulta de llamadas cada tres segundos;
- orden `P1` o `P2` recibida por el Mega;
- `EVENT:ROUTE_STARTED` procesado por el ESP32;
- freno ante obstáculo;
- `EVENT:ARRIVED` y actualización de la llamada;
- saludo en LCD;
- clasificación después de llegar;
- evento de reciclaje creado una sola vez;
- puntos asignados a la llamada o QR generado cuando no hay llamada;
- navegación bloqueada mientras una compuerta está abierta;
- ningún cambio en los pines y tiempos ya calibrados del robot.

## 12. Orden recomendado de commits

No crear un único commit gigante. Usar commits reversibles:

1. `feat(vision): integrar modelos locales y votos independientes`
   - servicio, modelo, reglas y pruebas;
2. `feat(web): propagar votos del servicio de vision`
   - únicamente los dos archivos del contrato web;
3. `feat(firmware): integrar voto mixto sin perder HTTPS y llamadas`
   - ESP32-CAM y receptor Uno de prueba;
4. `docs(vision): documentar integracion segura con Mega`
   - resultados, contrato y documentación actualizada.

La promoción posterior del candidato activo se registra por separado como
`fix(vision): activar MobileNetV2 tras comparacion operativa`, incluyendo el
binario, sus manifiestos, la prueba de hash y el respaldo íntegro de V3 INT8.

Antes de cada commit:

```bash
git diff --check
git status --short
git diff --stat
```

Antes de subir:

```bash
git log --oneline origin/main..HEAD
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
```

Subir únicamente la rama de integración y abrir revisión. No hacer `push` a
`main` directamente:

```bash
git push -u origin integration/vision-main-20260813
```

## 13. Recuperación ante fallos

- Si falla una prueba física: cortar alimentación, desconectar señal y anotar
  el último paso aprobado.
- Si falla el Uno: volver a probar solo UART y GND, sin pantallas.
- Si falla el Mega pero el Uno aprobó: revisar divisor, Serial2 y conflicto con
  HC-05; no modificar la IA para ocultar un problema eléctrico.
- Si falla `pytest`: no continuar al firmware.
- Si falla web `build`: no desplegar ni probar con Vercel.
- Si falla HTTPS o llamadas después de editar el ESP32: comparar inmediatamente
  con `origin/main`; probablemente se reemplazó una función que debía conservarse.
- Si un commit rompe una fase ya aprobada, usar `git revert <commit>` en la rama
  de integración. No usar `git reset --hard` ni borrar trabajo.
- El punto de retorno de software principal auditado es `96aaa96`; la fuente de
  visión probada es `7c375c4`.

## 14. Definición de terminado

La integración está lista para revisión solo cuando todos estos puntos sean
verdaderos:

- [ ] rama creada desde la `main` más reciente;
- [ ] ningún secreto aparece en `git status` o `git diff`;
- [ ] SHA-256 del MobileNetV2 activo coincide;
- [ ] 20 pruebas automatizadas aprobadas;
- [ ] 118/118 casos formales del sistema experto aprobados;
- [ ] `npm run lint` aprobado;
- [ ] `npm run build` aprobado con Node 24;
- [ ] ESP32-CAM compila conservando HTTPS y `RobotCallDispatcher`;
- [ ] OV3660 reporta PID `0x3660` y trabaja en QVGA;
- [ ] Uno recibe comandos completos a 9600;
- [ ] vidrio y plástico conocidos se clasifican correctamente;
- [ ] objeto desconocido no genera `CMD:CLASSIFY`;
- [ ] error de Wi-Fi/servicio no abre compuertas;
- [ ] Mega abre solo la compuerta indicada y la cierra;
- [ ] una segunda orden no abre otra compuerta mientras la primera está activa;
- [ ] navegación, obstáculo, llamada, llegada, puntos y QR siguen funcionando;
- [ ] cambios separados en commits revisables;
- [ ] rama subida para revisión, sin modificar `main` directamente.

## 15. Instrucción lista para el agente de la sesión

> Trabaja desde `/Users/hernandezaxel/Pau/Reci`. Lee completo
> `docs/PLAN-INTEGRACION-VISION-MAIN-2026-08-13.md` antes de editar. Ejecuta una
> fase a la vez y muestra evidencia al usuario antes de continuar. Empieza por
> actualizar `origin/main` y comprobar que el árbol esté limpio. No mezcles la
> rama de visión completa: crea una rama desde `origin/main`, traslada el
> servicio de forma selectiva y adapta el firmware ESP32 de `main` conservando
> HTTPS, NTP, `RobotCallDispatcher` y el contexto de puntos. Para el robot usa
> `ReciRutaDemo.ino`; no sustituyas navegación ni pines. Antes de alimentar
> servos, demuestra con el Uno y con pruebas automatizadas que un objeto
> desconocido no emite `CMD:CLASSIFY`. No subas secretos y no hagas push directo
> a `main`.
