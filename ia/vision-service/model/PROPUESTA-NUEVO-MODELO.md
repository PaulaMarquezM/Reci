# Propuesta de nuevo modelo local: EfficientNet-B0 y MobileNetV3-Large

> **Documento histórico.** La propuesta se ejecutó el 9 de agosto de 2026.
> MobileNetV3-Large fue el ganador y está activo; consulta
> `docs/resultados-vision/2026-08-09/README.md` para la evidencia final.

**Estado:** propuesta de experimentación; todavía no reemplaza al modelo
actual.  
**Alcance:** clasificación binaria `plastico | vidrio` con imágenes QVGA de
la ESP32-CAM.  
**Fecha:** 7 de agosto de 2026.

## Resumen

Se propone comparar tres modelos mediante *transfer learning* y con el mismo
dataset:

1. **MobileNetV2 reentrenado**, como control para medir cuánto mejora solo por
   usar fotos reales de la ESP32-CAM. Reentrenar la arquitectura actual siempre
   es una opción válida: si iguala a los candidatos, se conserva y no se cambia
   nada del despliegue.
2. **EfficientNet-B0**, como candidato principal por su equilibrio entre
   capacidad, tamaño y velocidad.
3. **MobileNetV3-Large**, como candidato eficiente: es el sucesor directo de la
   arquitectura actual y añade atención de canales sin salir del presupuesto de
   cómputo de MobileNet.

La primera opción a probar es **EfficientNet-B0**. El cambio solo se aprobará
si mejora las métricas en un conjunto final de la ESP32-CAM que ninguno de los
modelos haya visto durante el entrenamiento.

## Problema actual

MobileNetV2 presenta una brecha importante entre el dataset anterior y la
cámara del robot:

| Evaluación | Resultado | Lectura |
| --- | ---: | --- |
| Validación del dataset anterior | 98,43 % | No representa la cámara del robot |
| 1.000 capturas ESP32-CAM balanceadas | 71,60 % | Línea base real más útil |
| Recall de plástico | 60,60 % | Principal debilidad |
| Recall de vidrio | 82,60 % | Mejor, pero aún inestable |
| 300 capturas con mejor iluminación | 77,33 % | La luz y el dominio influyen mucho |

El TFLite actual ocupa aproximadamente **8,49 MiB**. También se han observado
errores con confianza cercana a 1,0. Por eso se deben mejorar la exactitud, el
equilibrio entre clases y la calibración de la confianza.

## ¿Cómo son las arquitecturas?

### MobileNetV2: referencia actual

MobileNetV2 fue diseñado para equipos con recursos limitados. Usa
convoluciones separables y bloques residuales invertidos:

```text
entrada -> expansión 1x1 -> depthwise 3x3 -> proyección 1x1
                                             + conexión residual
```

Su ventaja es la velocidad. Su menor capacidad puede facilitar que aprenda
atajos como la forma o la etiqueta de la botella, en lugar de distinguir
reflejos, textura y transparencia.

### EfficientNet-B0: candidato principal

EfficientNet usa bloques **MBConv** con atención de canales
*squeeze-and-excitation*. La familia B0-B7 aumenta coordinadamente profundidad,
ancho y resolución, en vez de escalar una sola dimensión.

```text
entrada -> expansión -> depthwise -> atención de canales -> proyección
                                                        + conexión residual
```

EfficientNet-B0 ronda los 5,3 millones de parámetros antes de adaptar la cabeza
de clasificación. Puede aprender combinaciones visuales más sutiles que
MobileNetV2 manteniendo un costo moderado. Esta posible mejora es una
hipótesis: debe medirse con la ESP32-CAM.

### MobileNetV3-Large: candidato eficiente

MobileNetV3 conserva los bloques residuales invertidos de MobileNetV2 y les
agrega dos cosas: atención de canales *squeeze-and-excitation* y la activación
*hard-swish*. La estructura del bloque se definió por búsqueda de arquitectura
(NAS) optimizando latencia real, no solo número de operaciones:

```text
entrada -> expansión 1x1 -> depthwise -> squeeze-and-excitation -> proyección 1x1
                                                                + conexión residual
```

MobileNetV3-Large ronda los 5,4 millones de parámetros, muy cerca de
EfficientNet-B0, pero con menos operaciones por inferencia. Es el candidato
más barato de desplegar porque comparte familia con el modelo actual: mismo
tipo de bloques, misma facilidad de exportación a TFLite y latencia conocida.

Su interés no es tener más capacidad que EfficientNet-B0, sino comprobar si la
atención de canales —lo que MobileNetV2 no tiene— basta para separar plástico
transparente de vidrio sin subir el costo.

Nota de implementación: en Keras, `MobileNetV3Large` incluye el reescalado de
la entrada dentro del modelo (`include_preprocessing=True`). Conviene dejarlo
así, porque encaja con el requisito de empaquetar el preprocesamiento dentro
del artefacto exportado.

## Comparación esperada

| Aspecto | MobileNetV2 | EfficientNet-B0 | MobileNetV3-Large |
| --- | --- | --- | --- |
| Parámetros aproximados | 3,5 M | 5,3 M | 5,4 M |
| Atención de canales | No | Sí | Sí |
| Capacidad | Baja | Media | Media |
| Costo esperado | Bajo | Bajo/medio | Bajo |
| Uso en el experimento | Control | Candidato principal | Candidato eficiente |
| Riesgo | Quedarse corto | Más latencia que MobileNet | Mejora marginal sobre V2 |

El tamaño final se medirá sobre cada `.tflite` con la misma cuantización; no
se deducirá únicamente del número de parámetros.

## Cómo pueden ayudar a mejorar las métricas

| Métrica | Cambio propuesto | Motivo |
| --- | --- | --- |
| Recall de plástico | EfficientNet-B0 / MobileNetV3-Large + ejemplos difíciles | Atención de canales para separar plástico transparente de vidrio |
| Recall por clase | Dataset balanceado por objeto, sesión y luz | Evita depender de un fondo u objeto repetido |
| Macro-F1 | Seleccionar por macro-F1, no solo por `accuracy` | Penaliza que una clase funcione peor |
| Precisión del voto local | Calibración y abstención | Reduce errores de confianza alta |
| Generalización | Simular QVGA, JPEG, desenfoque y cambios de luz | Acerca el entrenamiento al dominio real |
| Estabilidad | Entrenar tres semillas por modelo | Evita elegir un resultado alto por azar |

EfficientNet-B0 puede ayudar por su balance entre eficiencia, capacidad y
atención de canales. MobileNetV3-Large puede ayudar por la misma atención de
canales a un costo menor. Sin embargo, ninguna arquitectura corrige por sí sola
el cambio de dominio: el dataset de la ESP32-CAM probablemente tendrá más
impacto que cambiar de nombre de modelo. Por eso el experimento incluye
reentrenar MobileNetV2: si el salto viene de los datos, se verá ahí primero.

## Diseño del experimento

### Dataset

- Balancear `plastico` y `vidrio`.
- Incluir varios objetos físicos por clase, sesiones, fondos, distancias,
  orientaciones y niveles de luz.
- Separar entrenamiento, validación y prueba **por objeto o sesión completa**.
  Fotos consecutivas de una misma ráfaga no pueden quedar en particiones
  diferentes.
- Reservar una prueba final sin usarla para elegir arquitectura, aumentos,
  épocas ni umbrales.
- Usar las 1.000 capturas ya consultadas como regresión, no como única prueba
  final, porque sus resultados ya influyeron en decisiones del proyecto.
- Crear un conjunto aparte de latas, cartón y orgánicos para medir rechazos.
  Un clasificador binario no aprende `desconocido` sin ejemplos o una política
  explícita de abstención.

### Preprocesamiento y aumentos

- Entrada RGB de `224x224` en los tres experimentos.
- Variaciones moderadas de brillo, contraste, rotación, recorte, desenfoque y
  compresión JPEG.
- No aplicar transformaciones que eliminen las pistas del material.
- Incluir el preprocesamiento específico dentro del modelo exportado. El
  cargador actual convierte BGR a RGB, pero no llama al `preprocess_input` de
  cada arquitectura.

### Transfer learning

Todos los candidatos partirán de pesos ImageNet y tendrán la misma cabeza:

```text
backbone -> GlobalAveragePooling -> Dropout -> Dense(2, softmax)
```

1. Entrenar la cabeza con el *backbone* congelado.
2. Descongelar los últimos bloques y continuar con una tasa menor.
3. Aplicar parada temprana sobre macro-F1 de validación.
4. Ejecutar al menos tres semillas y reportar media y desviación estándar.
5. Consultar la prueba final una sola vez al terminar la selección.

### Matriz mínima

| ID | Modelo | Propósito |
| --- | --- | --- |
| E0 | MobileNetV2 actual | Línea base desplegada |
| E1 | MobileNetV2 reentrenado | Separar la mejora por datos de la mejora por arquitectura |
| E2 | EfficientNet-B0 | Candidato principal |
| E3 | MobileNetV3-Large | Medir si la atención de canales basta al costo de MobileNet |

E1, E2 y E3 usarán las mismas particiones, aumentos, semillas y presupuesto de
ajuste. Primero se compararán en punto flotante. Después se exportará el
ganador a TFLite y se repetirán las métricas, ya que la cuantización puede
introducir regresiones.

## Métricas obligatorias

- matriz de confusión;
- precisión, recall y F1 por clase;
- **macro-F1** como métrica principal;
- exactitud balanceada y exactitud global;
- número de errores con confianza alta;
- Brier score o ECE para calibración;
- cobertura y exactitud cuando se permita responder `desconocido`;
- tamaño del TFLite, memoria máxima y latencia p50/p95;
- exactitud y latencia del sistema híbrido completo, separadas de las del
  modelo local.

## Criterios de aceptación

Un candidato podrá reemplazar al modelo actual solo si cumple en la prueba
final independiente:

1. **Macro-F1 de al menos 85 %**, coherente con el criterio general del
   proyecto.
2. **Recall de al menos 85 % en cada clase**, para no esconder una clase débil
   dentro de la exactitud global.
3. Mejora de al menos **5 puntos porcentuales de macro-F1** frente al
   MobileNetV2 reentrenado E1 bajo el mismo protocolo.
4. Sin regresión relevante después de la exportación a TFLite.
5. Latencia compatible con el host definitivo, medida en ese equipo.

La meta deseable es 90 % o más de recall por clase. Si EfficientNet-B0 y
MobileNetV3-Large quedan empatados dentro del margen de las tres semillas, se
prefiere **MobileNetV3-Large** por su menor latencia y por seguir en la misma
familia que el modelo desplegado. Si E1, E2 y E3 quedan cerca entre sí, se
conserva el **MobileNetV2 reentrenado (E1)** —cambiar de arquitectura sin
ganancia medible solo agrega riesgo— y se prioriza mejorar el dataset.

## Calibración y abstención

El modelo actual siempre elige plástico o vidrio. Se propone calibrar sus
probabilidades y permitir abstención cuando la probabilidad máxima o el margen
entre clases sea insuficiente. El umbral se elegirá en validación, nunca en la
prueba final, y se reportarán juntas:

- **cobertura:** porcentaje de imágenes en las que el modelo decide;
- **exactitud cubierta:** acierto dentro de las imágenes decididas.

Así se puede aumentar la seguridad del voto local a cambio de enviar más casos
a `desconocido` o al proveedor principal.

## Integración segura

1. Exportar candidatos TFLite con el preprocesamiento incluido.
2. Conservar exactamente las etiquetas `plastico` y `vidrio`.
3. Crear un manifiesto con arquitectura, datos, particiones, semillas,
   métricas, cuantización y hash.
4. Cargar el candidato mediante `LOCAL_MODEL_PATH`, sin sobrescribir primero
   `model.tflite`.
5. Ejecutar `tests/test_local_model.py` y las pruebas de votación.
6. Desplegar inicialmente en **modo sombra**: registrar su predicción sin
   permitir que cambie la decisión del robot.
7. Comparar MobileNetV2, candidato, OpenAI+sistema experto y sistema híbrido
   sobre las mismas capturas.
8. Cambiar la política de voto solo después de aprobar las métricas.

El cargador actual obtiene el tamaño de entrada desde el TFLite. El punto
crítico es mantener el mismo contrato de entrada y salida y empaquetar el
preprocesamiento dentro del artefacto.

## Riesgos y controles

| Riesgo | Control |
| --- | --- |
| Fotos casi idénticas entre particiones | Dividir por objeto y sesión |
| Mejora causada solo por los datos | Comparar contra E1 con los mismos datos |
| Candidato sin ganancia útil frente a E1 | Comparar macro-F1, latencia y tamaño; conservar MobileNetV2 reentrenado |
| Preprocesamiento incompatible | Incluirlo dentro del TFLite |
| Cuantización reduce recall | Repetir todas las métricas tras convertir |
| Confianza alta en errores | Calibrar y permitir abstención |
| Latas/cartón forzados a una clase | Evaluar un conjunto fuera de distribución |
| Regresión en la votación | Modo sombra y cambio reversible por variable |

## Referencias

- [EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks](https://proceedings.mlr.press/v97/tan19a.html)
- [Searching for MobileNetV3](https://openaccess.thecvf.com/content_ICCV_2019/html/Howard_Searching_for_MobileNetV3_ICCV_2019_paper.html)
- [MobileNetV2: Inverted Residuals and Linear Bottlenecks](https://openaccess.thecvf.com/content_cvpr_2018/papers/Sandler_MobileNetV2_Inverted_Residuals_CVPR_2018_paper.pdf)
- [TensorFlow/Keras: EfficientNet](https://www.tensorflow.org/api_docs/python/tf/keras/applications/efficientnet)
- [TensorFlow/Keras: MobileNetV3](https://www.tensorflow.org/api_docs/python/tf/keras/applications/MobileNetV3Large)
- [Métricas más recientes con la ESP32-CAM](../README.md#validación-con-la-esp32-cam)
- [Protocolo de validación del modelo local](../../../docs/VALIDACION-MODELO-LOCAL-ESP32-CAM.md)
