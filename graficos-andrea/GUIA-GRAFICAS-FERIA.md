# Guía de gráficas para la feria

Qué figuras preparar para exponer el **sistema experto** y el **modelo de IA** de
Reci, y en qué orden contarlas.

En un póster caben unas 10–12 gráficas. Sobrar es peor que faltar: cada figura
que no se entiende sola le quita atención a las que sí. Por eso esta guía separa
un **núcleo de 8** del catálogo completo por bloque.

Convenciones: ⭐ = imprescindible · ⭐⭐ = es la historia que hay que contar.

---

## El núcleo — si solo haces 8

| # | Gráfica | Por qué gana su espacio |
| --- | --- | --- |
| 1 | Diagrama del sistema completo | Es el gancho: residuo → 3 fotos → 2 señales → 6 votos → compuerta |
| 2 | Anatomía de una regla del sistema experto | Muestra que hay conocimiento escrito, no solo una caja negra |
| 3 | Ejemplos de aumentos de datos | La misma foto con brillo, QVGA y JPEG. Se entiende sin explicar nada |
| 4 | Curvas de aprendizaje | Loss y accuracy, entrenamiento vs. validación, con las dos fases marcadas |
| 5 | Matriz de confusión | Todo el mundo la reconoce |
| 6 | Precision / recall / F1 por clase | Barras agrupadas |
| 7 | Las 9 corridas con media ± DE | La evidencia de rigor |
| 8 | Los tres dominios (98,43 / 71,60 / 63,2 %) | El hallazgo honesto; es lo que más pesa ante un jurado |

---

## Bloque 1 · Sistema experto

| Gráfica | Qué muestra |
| --- | --- |
| **Anatomía de una regla** ⭐ | Una regla real anotada: condiciones → conclusión → CF. Sirve `R167`, que reconoce vidrio por propiedades físicas aunque el proveedor se equivoque de objeto |
| **193 reglas → 5 conclusiones** ⭐ | Barras horizontales: PLASTICO 115, VIDRIO 50, ORGANICO 21, LATA 6, DESCONOCIDO 1. Corrige de entrada la confusión de que 193 reglas = 193 respuestas posibles |
| **Especificidad de las reglas** | Histograma: 62 reglas exigen 2 atributos y 6 exigen 6. Hay reglas generales y reglas quirúrgicas |
| **Diagrama del motor de inferencia** ⭐ | Hechos → meta-reglas → forward chaining → CF por categoría → backward chaining → política conservadora |
| **Combinación de CF estilo MYCIN** | Por qué dos reglas de 0,90 dan 0,99 y no 1,80. Solo si el público es técnico |
| **La política conservadora A2** | El umbral de 0,75 y los tres caminos al rechazo. Explica por qué el sistema prefiere no abrir ninguna compuerta |
| **Espacio de entradas** | 6.386.688 combinaciones posibles de los 9 atributos, cubiertas por 193 reglas |

Datos de apoyo: `ia/vision-service/expert_system/knowledge_base.py` y
`inference_engine.py` (constantes `UMBRAL_APERTURA_CF`, `UMBRAL_BACKWARD`,
`CF_FORWARD_SEGURO`).

---

## Bloque 2 · Arquitectura del modelo

| Gráfica | Qué muestra |
| --- | --- |
| **Diagrama de la arquitectura** ⭐ | `224×224×3 → backbone → GlobalAveragePooling → Dropout → Dense(2) → softmax` |
| **Convolución normal vs. separable** ⭐ | El truco de MobileNet en dos pasos (*depthwise* + *pointwise*). Justifica la elección de arquitectura |
| **Cómo funciona una convolución** | El filtro 3×3 deslizándose y el mapa que produce. Con público general vale más que el diagrama de arquitectura |
| **Comparativa de las 3 arquitecturas** | Tabla: parámetros, capas, tamaño, latencia y activación (ReLU6 vs. hard-swish) |
| **Reparto de parámetros** | 99,89 % de backbone heredado de ImageNet frente a 0,11 % de cabeza propia. Explica *transfer learning* de un vistazo |

---

## Bloque 3 · Datos e hiperparámetros

| Gráfica | Qué muestra |
| --- | --- |
| **Composición del dataset** ⭐ | Barras: 17.630 de entrenamiento, 199 de validación, 200 de prueba, desglosado por clase |
| **Partición por sesión** ⭐ | Las 8 sesiones asignadas cada una a un solo conjunto. **Evidencia de ausencia de fuga**: un jurado técnico la busca |
| **Ejemplos de aumentos** ⭐ | Una foto original y cuatro versiones aumentadas. La gráfica más rentable de la lista |
| **Tabla de hiperparámetros** ⭐ | Lote 32 · dropout 0,3 · épocas 15 + 25 · paciencia 6 · lr 1e-3 → 1e-5 · semillas 42 y 1/2/3 |
| **Las dos fases del transfer learning** | Backbone congelado → 70 % congelado, con las dos tasas de aprendizaje |

---

## Bloque 4 · Curvas de aprendizaje

| Gráfica | Qué muestra |
| --- | --- |
| **Loss y accuracy por época** ⭐ | Entrenamiento vs. validación, con línea vertical en el cambio de fase y marca en la mejor época |
| **macro-F1 de validación por época** | La métrica que decidió qué pesos se conservaron |
| **La brecha entrenamiento/validación** | 99,65 % frente a 84,4 % al final. Muestra el sobreajuste y por qué la parada temprana salvó el resultado |

---

## Bloque 5 · Evidencia de proceso controlado

Este bloque es el que separa un proyecto de feria de uno de verdad.

| Gráfica | Qué muestra |
| --- | --- |
| **Las 9 corridas con media ± DE** ⭐ | 3 arquitecturas × 3 semillas, con barra de error |
| **Por qué tres semillas** ⭐⭐ | Con la semilla 1 la diferencia era **+5,02 pp** → se cambiaba de arquitectura. Con las tres semillas es **+3,35 pp** → no se cambia. Por 0,02 puntos se estuvo a punto de tomar la decisión equivocada |
| **Criterios de aceptación** ⭐ | Los 5 criterios fijados **antes** de ver resultados, con ✓/✗ por candidato |
| **Prueba reservada intacta** | 200 imágenes sin abrir. Demuestra que se entiende por qué no se miran |

---

## Bloque 6 · Métricas

| Gráfica | Qué muestra |
| --- | --- |
| **Matriz de confusión** ⭐ | Heatmap con conteos y porcentajes |
| **Precision / recall / F1 por clase** ⭐ | Barras agrupadas |
| **Por qué macro-F1 y no accuracy** ⭐ | El contraejemplo: un clasificador que siempre responde «plástico» saca 95 % de exactitud siendo inútil. Justifica la métrica elegida |
| **Errores con confianza alta** | 17 de 25 errores llegaron con confianza ≥ 0,90. Explica por qué no basta un umbral |

---

## Bloque 7 · El hallazgo honesto

Contraintuitivo pero cierto: **enseñar lo que falló impresiona más que enseñar
solo lo que funcionó.** Un jurado distingue enseguida entre quien midió y quien
solo reportó el número bonito.

| Gráfica | Qué muestra |
| --- | --- |
| **Los tres dominios** ⭐⭐ | 98,43 % → 71,60 % → 63,2 %, con la analogía del examen sorpresa |
| **La inversión del recall** ⭐ | La clase débil cambia según la cámara: prueba que el modelo aprendió el contexto y no el material |
| **Regresión por cuantización** ⭐ | Acuerdo float32 ↔ int8: MobileNetV2 conserva el 98,5 %, MobileNetV3-Large baja al 47 %. La causa es la activación: ReLU6 acotada frente a hard-swish sin cota |
| **Capacidad de rechazo** | 0/23 el modelo local frente a 20/23 el sistema experto. **Justifica por qué el proyecto necesita las dos IA** |

---

## Cómo montarlo

Orden narrativo que funciona explicando de pie:

```
1. El problema  →  2. Las dos IA  →  3. Cómo decide cada una
      →  4. Cómo se entrenó  →  5. Qué tan bien funciona
      →  6. Qué descubrimos que no esperábamos
```

Tres reglas prácticas:

- **Una figura, una idea.** Si necesitas dos frases para explicar qué se ve,
  sobra.
- **Rotula los valores sobre las barras.** El jurado mira de lejos y no va a
  leer el eje.
- **Guarda las gráficas profundas en el portátil**, no en el póster. La
  combinación de CF, la especificidad de las reglas y la brecha
  entrenamiento/validación son excelentes cuando alguien pregunta en serio.

Si hubiera que elegir **una sola** figura para el centro del póster: el diagrama
del sistema con los 6 votos. Es lo único que muestra que hay dos inteligencias
distintas colaborando, que es lo que hace particular a Reci.

---

## Material ya disponible

Antes de generar nada, revisar lo que existe:

| Fuente | Contiene |
| --- | --- |
| [`resultados-vision/2026-08-09/graficas/`](resultados-vision/2026-08-09/graficas/) | Curvas de entrenamiento y matrices de confusión de las 9 corridas, en PNG y PDF |
| [`resultados-vision/2026-08-09/metricas/`](resultados-vision/2026-08-09/metricas/) | Precision/recall/F1 por clase y la inspección de cada TFLite, en JSON y CSV |
| [`resultados-vision/2026-08-09/historiales/`](resultados-vision/2026-08-09/historiales/) | Métricas por época y fase, para regenerar curvas con otro estilo |
| [`resultados-vision/2026-08-09/resumen_comparacion.csv`](resultados-vision/2026-08-09/resumen_comparacion.csv) | Una fila por corrida: base para la gráfica de las 9 corridas |
| `ia/vision-service/model/analisis-mobilenetv2.ipynb` | Figuras del modelo desplegado: tres dominios, inversión de recall, capacidad de rechazo, correlaciones |
| `ia/vision-service/model/analisis-modelos-entrenados.ipynb` | Figuras del experimento comparativo, incluida la verificación de cuantización |
| [`conceptos/`](conceptos/) | Serie explicativa: convolución, transfer learning, cambio de dominio, votación |

Las gráficas de los cuadernos se exportan con clic derecho sobre la figura, o
reejecutando la celda con `plt.savefig(..., dpi=300)` para calidad de impresión.

---

## Documentos relacionados

- [`resultados-vision/2026-08-09/README.md`](resultados-vision/2026-08-09/README.md) — informe del experimento
- [`../ia/vision-service/model/README.md`](../ia/vision-service/model/README.md) — estado del modelo activo
- [`../ia/vision-service/model/PROPUESTA-NUEVO-MODELO.md`](../ia/vision-service/model/PROPUESTA-NUEVO-MODELO.md) — criterios de aceptación
- [`PLAN.md`](PLAN.md) — estado general del proyecto
