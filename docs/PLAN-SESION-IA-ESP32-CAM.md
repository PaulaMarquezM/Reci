# Plan de sesión — IA, ESP32-CAM y dataset

**Responsable principal:** Axel Hernández

> **Documento histórico.** Este plan se completó antes del experimento de
> agosto de 2026. Mantiene el contexto de captura, pero no es el plan operativo
> actual ni define el modelo desplegado.

**Apoyo esperado:** Paula Márquez para validación e integración web
**Meta de la sesión:** validar el flujo actual con objetos reales e iniciar un
dataset limpio de ESP32-CAM para evaluar/reentrenar el modelo.

Este documento no modifica el firmware de producción, la app, Supabase, los
motores ni las conexiones del robot. La recolección del dataset usa
temporalmente el ejemplo `CameraWebServer` de Arduino; al terminar se vuelve
a cargar el firmware de Reci.

## Resultado mínimo esperado al finalizar

- Una tabla con resultados de pruebas de plástico y vidrio.
- Al menos una ronda etiquetada y revisada por cada clase.
- Las fotos ordenadas localmente en `dataset-esp32cam/plastico/` y
  `dataset-esp32cam/vidrio/`.
- Validación registrada de OpenAI, ya seleccionado como proveedor principal
  local, sin cambiar el despliegue de producción durante la sesión.

## Antes de empezar — 15 minutos

1. Confirmar que Mac y ESP32-CAM están en la misma red Wi-Fi de 2.4 GHz.
2. Tener disponibles varios objetos de plástico y vidrio; incluir envases de
   formas, colores y transparencias distintos.
3. Preparar una mesa con fondo simple y luz estable. Evitar que una lámpara
   apunte directamente al lente o se refleje de frente en el envase.
4. Abrir la plantilla
   [`PLANTILLA-VALIDACION-ESP32-CAM.csv`](PLANTILLA-VALIDACION-ESP32-CAM.csv)
   en Excel, Numbers o Google Sheets. Si se prefiere crear una hoja aparte,
   usar estas mismas columnas:

   | ID | Material real | Objeto | Luz/fondo | Resultado | Confianza | Tiempo | Observación |
   | --- | --- | --- | --- | --- | --- | --- | --- |

5. No subir claves, fotos ni credenciales al repositorio.

## Bloque A — Validar el flujo actual de Reci con Paula — 45 a 60 minutos

### A.1 Levantar los servicios locales

En una terminal, iniciar la app de Reci:

```bash
cd /Users/hernandezaxel/Pau/Reci/web
npm run dev
```

En otra, iniciar el servicio de visión con el `.env` local ya configurado:

```bash
cd /Users/hernandezaxel/Pau/Reci/ia/vision-service
python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### A.2 Cargar y probar el firmware de Reci

1. Abrir el sketch de Reci para la ESP32-CAM en Arduino IDE.
2. Verificar que la URL del servidor corresponde a la IP actual de la Mac.
3. Cargar el sketch y abrir el Monitor Serial a 115200.
4. Esperar el mensaje de Wi-Fi listo.
5. Por cada objeto, dejarlo fijo en el encuadre y enviar `C`.
6. Registrar los tres votos, el resultado final, la confianza, el QR si se
   generó y cualquier error HTTP.
7. Probar al menos 10 objetos: 5 de plástico y 5 de vidrio, con dos intentos
   por objeto cuando haya tiempo.

### Criterio para avanzar

No cambiar reglas durante este bloque. Si hay un fallo, registrar primero si
la causa parece encuadre, luz, red, tiempo de respuesta o clasificación.

## Bloque B — Capturar dataset supervisado — 60 a 90 minutos

### B.1 Cambiar temporalmente a CameraWebServer

1. En Arduino IDE, abrir **File → Examples → ESP32 → Camera →
   CameraWebServer**.
2. Seleccionar la placa **AI Thinker ESP32-CAM** y configurar la misma red
   Wi-Fi.
3. Cargar el ejemplo y abrir el Monitor Serial a 115200.
4. Copiar la IP que muestra la cámara.
5. En el navegador abrir `http://IP_DE_LA_CAMARA` y pulsar **Start Stream**.
   Mantener esa pestaña visible durante todas las rondas.

### B.2 Ejecutar el capturador

En otra terminal:

```bash
cd /Users/hernandezaxel/Pau/Reci/ia/vision-service
python3 scripts/capturar_dataset_esp32cam.py \
  --camera http://IP_DE_LA_CAMARA \
  --count 100 \
  --interval 2
```

El script usa el endpoint `/capture` del ejemplo CameraWebServer y guarda
archivos locales. No detiene ni modifica la vista en vivo.

| Tecla | Acción |
| --- | --- |
| `P` | Inicia una ronda de 100 fotos para `dataset-esp32cam/plastico/` |
| `V` | Inicia una ronda de 100 fotos para `dataset-esp32cam/vidrio/` |
| `Q` | Cierra el capturador |

### B.3 Método de captura eficiente

1. Empezar con una ronda de plástico (`P`) y observar la vista en vivo.
2. Durante los 200 segundos de la ronda, variar lentamente giro, inclinación,
   distancia y posición del objeto; no moverlo de forma brusca.
3. Cambiar a otro objeto plástico y repetir solo si aporta variedad real.
4. Repetir el procedimiento con vidrio (`V`).
5. Revisar rápidamente 10 fotos al azar de cada carpeta: deben mostrar el
   objeto, no estar completamente oscuras y tener la etiqueta correcta.
6. Anotar para cada ronda objeto, condiciones de luz, fondo y cantidad real
   de fotos guardadas.

La variedad vale más que 1,000 imágenes casi idénticas. Meta inicial sugerida:
500 o más imágenes útiles por clase, distribuidas entre varios objetos y
condiciones.

## Bloque C — Cierre técnico — 20 minutos

1. Presionar `Q` en el capturador y confirmar que las fotos quedaron en las
   carpetas correctas.
2. Volver a cargar el firmware de Reci en la ESP32-CAM; CameraWebServer es
   solo para recolección de dataset.
3. Guardar la tabla de validación y el conteo de fotos por clase.
4. No añadir el dataset a Git: `dataset-esp32cam/` está ignorado a propósito.
5. Compartir con Paula el resultado: aciertos/total, fallos observados,
   condiciones de prueba y siguiente decisión.

## Después de la sesión

1. Ejecutar el modelo de RECI2 sobre las fotos recolectadas y calcular una
   matriz de confusión.
2. Medir OpenAI sobre un subconjunto fijo de fotos, registrando precisión,
   latencia y costo estimado. Consultar Claude solo para contrastar casos
   ambiguos o fallos repetibles.
3. Ajustar reglas o heurísticas únicamente cuando exista evidencia repetible
   en las fotos y en la tabla de validación.
4. Si el modelo previo no se adapta a ESP32-CAM, preparar el
   reentrenamiento/transfer learning de MobileNetV2 con el dataset propio.
