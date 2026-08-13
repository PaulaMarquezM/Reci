# Estado de IA y Sistema Experto — Axel Hernández

**Fecha de actualización:** 23 de julio de 2026

> **Documento histórico.** Describe el estado anterior al experimento de tres
> modelos de agosto de 2026. El modelo local activo ahora es MobileNetV3-Large;
> consulta `ia/vision-service/model/README.md` y
> `docs/resultados-vision/2026-08-09/README.md` para el estado actual.

**Responsable:** Axel Hernández — Lead IA + Sistema Experto
**Rama de trabajo:** `axel/ia-sistema-experto`

## Objetivo del módulo

Clasificar residuos de **vidrio** y **plástico** a partir de fotos de la
ESP32-CAM, de forma conservadora: si la evidencia no es suficiente, Reci no
abre una compuerta.

El flujo actual es:

```text
ESP32-CAM → API web de Reci → servicio de visión →
OpenAI+sistema experto y MobileNetV2 como votos independientes →
mayoría de hasta seis votos en ESP32-CAM →
vidrio | plastico | desconocido → Arduino Mega
```

## Trabajo completado

### Sistema experto y regresiones de RECI2

- Se revisaron RECI2 (prototipo previo) y Reci (proyecto activo).
- Se portaron al proyecto activo correcciones para Gatorade, enjuague bucal,
  atomizadores y vasos de espuma/plástico.
- Se agregaron pruebas de regresión para evitar que esas correcciones se
  pierdan con cambios posteriores.
- Resultado actual: **118/118 pruebas formales aprobadas (100 %)**. Estas
  pruebas cubren vidrio, plástico, casos ambiguos, casos extremos, objetos
  del campus, orgánicos y latas.

Commits relacionados:

- `0afe372` — correcciones de ambigüedad para Gatorade.
- `8f4e44a` — correcciones para envases y vasos plásticos.

### Servicio de visión

- El servicio privado FastAPI está integrado con la API web de Reci y se
  ejecutó localmente en la Mac para desarrollo.
- La clasificación actual usa un proveedor de visión para extraer atributos
  visuales, heurísticas OpenCV y el sistema experto de 193 reglas.
- Se configuró OpenAI como proveedor principal local para las pruebas; Claude
  y Gemini quedan disponibles como alternativas, sin eliminarse.
- OpenAI responde mediante Responses API y la respuesta se exige en JSON
  estructurado antes de pasar al sistema experto.
- Se portó el MobileNetV2/TFLite de RECI2 (`run_20260721_2129`) al servicio.
  Cada una de las tres fotos ahora se analiza con OpenAI y con el modelo
  propio, produciendo seis predicciones sobre tres capturas.
- La decisión conserva los seis votos, pero prioriza la mayoría interna de
  OpenAI+sistema experto porque la matriz actual muestra mejor rendimiento.
  Si OpenAI no tiene mayoría, se consulta la mayoría del modelo local; un
  empate global 3–3 se resuelve con OpenAI cuando tiene mayoría interna. Si
  ninguna señal tiene mayoría estricta, se devuelve `desconocido`.
- La matriz física ampliada registró **24/31 selecciones correctas (77.4 %)**
  con casos difíciles de plástico y vidrio. Esto confirmó que el modelo local
  aún debe ser respaldo; las próximas pruebas anotarán también la regla que
  tomó la decisión, no solo el resultado final.
- Si el modelo local no carga, se conserva el flujo anterior de OpenAI,
  heurísticas y sistema experto.
- La prueba de portabilidad del TFLite acertó **13/15** imágenes reales
  etiquetadas de RECI2. Los dos errores fueron el par ambiguo Gatorade
  vidrio/plástico; se mantiene la validación con objetos reales antes de
  entrenar una versión nueva del modelo.
- Resultado técnico después de la integración: **16/16 pruebas del servicio
  de visión** y **118/118 pruebas del sistema experto** aprobadas.
- La integración de OpenAI tiene pruebas unitarias sin red y una prueba real
  completada contra el endpoint local.

Commit relacionado:

- `ad11ee7` — proveedor OpenAI opcional para visión.

### Validación inicial con ESP32-CAM

- Se configuró y cargó el firmware de Reci en una AI Thinker ESP32-CAM.
- La cámara se conectó a Wi-Fi, alcanzó el servicio local y tomó tres fotos
  por clasificación con voto mayoritario.
- Se confirmaron clasificaciones correctas de botellas de plástico y de
  vidrio en pruebas controladas.
- Con la política más reciente se verificó una clasificación física de vidrio
  con **6/6 diagnósticos coincidentes** y la regla `mayoria
  OpenAI/sistema experto` visible en el Monitor Serial.
- Una captura de vidrio tuvo un fallo de comunicación en la tercera foto,
  pero las dos primeras coincidieron y el voto mayoritario clasificó
  correctamente. Se debe observar este comportamiento en la siguiente
  batería de pruebas, sin cambiar reglas todavía.
- La vista previa de la cámara se verificó desde Safari y la cámara entregó
  imágenes correctamente. La IP de la ESP32-CAM es dinámica y puede cambiar
  al reconectarla; por eso no se fija como configuración del proyecto.
- La siguiente validación física debe registrar por foto los dos votos, el
  conteo final de plástico, vidrio y abstenciones, además de la regla que
  decidió el resultado.
- Se localizaron y evaluaron 201 capturas reales QVGA etiquetadas como
  vidrio. El modelo acertó **141/201 (70.15 %)**: 77/100 en una ronda y
  63/100 en otra, además de una captura inicial correcta. No hay todavía
  capturas ESP32-CAM guardadas de plástico.
- La evidencia, limitaciones y protocolo de continuación están consolidados
  en
  [`VALIDACION-MODELO-LOCAL-ESP32-CAM.md`](VALIDACION-MODELO-LOCAL-ESP32-CAM.md).

## Qué no se ha hecho deliberadamente

- No se ha reentrenado todavía el MobileNet/TFLite con fotos de la
  ESP32-CAM; primero se portó el modelo existente para medir la brecha real.
- No se han modificado motores, servos, pantallas, navegación ni la app.
- No se han subido claves, credenciales, redes Wi-Fi ni secretos al
  repositorio.

El modelo de RECI2 está integrado, pero sus métricas anteriores no se toman
como garantía para la ESP32-CAM. Si no conserva precisión con esa cámara, se
ajustará mediante fine-tuning con el dataset propio.

## Pendiente de Axel

1. Capturar y etiquetar un dataset propio de la ESP32-CAM (meta inicial:
   mínimo 500 fotos por clase, con variedad de objetos, luz, ángulos y
   fondos). Ya existen 201 capturas locales de vidrio; deben reservarse por
   sesión y no mezclarse todas dentro del entrenamiento.
2. Crear el flujo de captura con vista en vivo para supervisar cada ronda de
   fotos mientras se guardan por clase.
3. Evaluar el modelo integrado frente al dataset de la ESP32-CAM y construir
   una matriz de confusión separada para OpenAI, MobileNetV2 y la política
   primaria + respaldo.
4. Hacer transfer learning/reentrenamiento de MobileNetV2 si la evaluación
   muestra que el modelo previo no se adapta bien a la cámara real.
5. Ajustar la prioridad o el respaldo local únicamente con resultados reales
   revisados con Paula.
6. Validar OpenAI con fotos reales (precisión, latencia y costo); usar Claude
   o Gemini solo como comparación cuando aparezca un caso ambiguo.

### Alcance de las pruebas

- La botella de chocolatada Toni de formato marrón/estrecho se considera un
  caso atípico y queda fuera del conjunto de aceptación actual. No se añadió
  una regla especial para ella, para evitar alterar el comportamiento de los
  envases plásticos generales.
- Las pruebas de aceptación se concentrarán en botellas y recipientes de
  plástico y vidrio representativos del sistema.

## Coordinación requerida con Paula

- Realizar la batería de pruebas de clasificación con objetos reales y
  registrar aciertos, errores, condiciones de luz y tiempo de respuesta.
- Ajustar los umbrales de confianza con datos reales si las pruebas lo
  requieren.
- Desplegar `ia/vision-service` en un host persistente y configurar, en el
  entorno de la app, `VISION_SERVICE_URL` y `VISION_SERVICE_API_KEY`.

Mientras se desarrolla localmente, el servicio corre en la Mac. Desplegarlo
significa que la app alojada pueda consultarlo sin depender de que esa Mac
esté encendida.

## Próxima sesión propuesta (cuando vuelva a estar disponible la cámara)

### Orden de trabajo

1. **Arranque y conexión.** Conectar la ESP32-CAM, confirmar que obtiene una
   IP y abrir la vista previa desde Safari. Anotar la IP de esa sesión, sin
   convertirla en una configuración fija.
2. **Prueba de salud.** Ejecutar una clasificación de plástico y otra de
   vidrio con la cámara final. Confirmar en el monitor serial las tres
   capturas, la respuesta del servicio y el voto mayoritario.
3. **Validación controlada.** Probar objetos representativos con cámara fija,
   iluminación estable y fondo sencillo. Registrar objeto, material real,
   resultado de cada foto, resultado final, latencia y cualquier error HTTP.
4. **Dataset supervisado.** Ejecutar el capturador separado de
   `CamaraWebServer`: usar `P` para plástico y `V` para vidrio, comprobar la
   vista en vivo y guardar las fotos en las carpetas de clase. Revisar que no
   haya imágenes negras, duplicadas o desenfocadas antes de continuar.
5. **Evaluación.** Separar las imágenes en entrenamiento, validación y
   prueba; comparar el modelo de RECI2 con el proveedor OpenAI usando fotos
   tomadas por la ESP32-CAM.
6. **Decisión de modelo.** Solo si el modelo previo no se adapta a la cámara,
   preparar reentrenamiento/transfer learning. Mantener el sistema experto
   como decisión final conservadora.
7. **Revisión con Paula.** Entregar la tabla de resultados, ejemplos de
   aciertos/errores y métricas de precisión por clase para acordar umbrales y
   siguientes cambios.
8. **Despliegue posterior.** Cuando la validación sea aprobada, desplegar el
   servicio de visión en un host persistente y configurar
   `VISION_SERVICE_URL` y `VISION_SERVICE_API_KEY` en el entorno de la app.

### Preparación que puede hacerse sin la cámara

- Verificar que el capturador y sus carpetas de salida estén listos, sin
  iniciar rondas de captura.
- Mantener una tabla de validación vacía con las columnas del documento CSV.
- Tener levantado el servicio de visión únicamente cuando se vaya a probar;
  no es necesario dejarlo ejecutándose si la ESP32-CAM no está conectada.
- No cambiar reglas por un solo objeto atípico: cualquier ajuste debe estar
  respaldado por una prueba reproducible y revisarse con Paula.
