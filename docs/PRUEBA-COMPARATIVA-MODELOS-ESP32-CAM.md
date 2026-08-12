# Comparación física: MobileNetV2 vs MobileNetV3-Large

Esta prueba busca responder una pregunta concreta: con fotos nuevas de la
misma ESP32-CAM, ¿cuál modelo local reconoce mejor `plastico` y `vidrio`? El
Arduino Uno solo muestra los mensajes recibidos; no participa en la inferencia
ni cambia el resultado de los modelos.

## Antes de conectar

La placa fotografiada conserva el pinout compatible con **AI Thinker
ESP32-CAM**, aunque su sensor es una **OV3660**. Por ello el mapa de cámara y
el cableado UART que ya usa `firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino`
no cambian. Al iniciar, el Monitor Serial debe confirmar `PID=0x3660`.

Para la prueba Uno + ESP32-CAM, conserva este cableado:

| ESP32-CAM | Arduino Uno | Función |
| --- | --- | --- |
| GPIO14 (TX) | D10 (RX) | Mensajes de resultado |
| GND | GND | Referencia común obligatoria |
| 5 V estable externo | — | Alimentación de ESP32-CAM |

No conectes D11 del Uno al RX de la ESP32-CAM, ni alimentes la cámara desde el
Uno. El Uno trabaja a 5 V y el RX de la ESP32-CAM es de 3.3 V.

GPIO14 comparte función con el reloj de la microSD, pero el firmware no usa la
tarjeta durante esta prueba, así que puede seguir siendo el TX hacia D10. Si
en el futuro se escribe en microSD, habrá que mover ese TX a un GPIO libre y
actualizar el firmware y el cable.

## Diseño de prueba válido

1. Reserva al menos 20 objetos: 10 de plástico y 10 de vidrio. Incluye botellas
   transparentes, oscuras, con etiqueta y casos difíciles como Powerade o
   frascos. No uses estas mismas fotos para reentrenar posteriormente.
2. Por objeto toma **tres fotos** con luz, fondo, distancia y ángulo fijos. No
   muevas el objeto durante la secuencia.
3. Guarda cada JPEG antes de clasificar, con nombres como
   `T001_plastico_f1.jpg`, `T001_plastico_f2.jpg`, `T001_plastico_f3.jpg`.
4. Anota también el resultado final del firmware y la regla que lo eligió. Una
   decisión final `desconocido` no abre compuerta.
5. Nunca concluyas con una sola marca u objeto repetido: la variedad de envases
   es más importante que muchas fotos casi iguales.

La estructura de las fotos para la evaluación local debe ser:

```text
capturas-reservadas/
  plastico/
    T001_plastico_f1.jpg
    ...
  vidrio/
    T011_vidrio_f1.jpg
    ...
```

## Comparación sobre la misma foto

El servicio incorpora un modo de sombra: MobileNetV3-Large sigue siendo el
modelo activo y mantiene sus tres votos; MobileNetV2 recibe el mismo JPEG solo
como diagnóstico. El resultado sombra **no** se agrega a `vision_votes` y no
puede abrir ni bloquear una compuerta.

En `ia/vision-service/.env`, agrega temporalmente:

```env
LOCAL_SHADOW_MODEL_PATH=model/backups/mobilenetv2_run_20260721_2129/model.tflite
LOCAL_SHADOW_MODEL_LABELS=model/backups/mobilenetv2_run_20260721_2129/labels.txt
```

Reinicia el servicio de visión. Por cada foto, el Monitor Serial mostrará:

```text
foto 1: OpenAI=plastico (0.94) | modelo=plastico (0.88)
foto 1: comparacion local activo=plastico (0.88) | sombra=vidrio (0.76) [sin voto]
```

`modelo`/`activo` es MobileNetV3-Large; `sombra` es MobileNetV2. Guarda el
Monitor Serial o copia esos datos a una tabla. Al terminar, borra las dos
variables y reinicia el servicio para dejar solo el modelo activo.

## Métricas reproducibles fuera del flujo mixto

Con las capturas guardadas, ejecuta los dos TFLite sobre exactamente los mismos
archivos:

```bash
cd /Users/hernandezaxel/Pau/Reci/ia/vision-service
python3 scripts/comparar_modelos_locales.py \
  --dataset /RUTA/capturas-reservadas \
  --output-dir resultados/comparacion-esp32cam-20260812
```

El comando no usa OpenAI ni modifica el modelo activo. Genera:

- `comparacion_por_imagen.csv`: predicción, confianza, latencia y acierto de
  ambos modelos por imagen.
- `resumen.json`: exactitud, macro-F1, matriz de confusión, métricas por clase,
  latencias p50/p95 y desacuerdos.

Para elegir, prioriza macro-F1 y recall de ambas clases. La latencia solo
desempata si la diferencia de calidad no es clara. La medición física del
sistema mixto se reporta aparte, porque OpenAI+sistema experto es la señal
primaria y el modelo local es respaldo.
