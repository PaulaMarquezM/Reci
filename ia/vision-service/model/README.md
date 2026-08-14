# Modelo local de materiales

## Modelo activo

El servicio usa actualmente **MobileNetV2 TFLite float32** de la corrida
`run_20260721_2129`. El 13 de agosto de 2026 reemplazó como modelo activo al
MobileNetV3-Large INT8 después de comparar ambos artefactos con el mismo
pipeline de producción sobre 1.000 capturas OV3660/QVGA.

- `model.tflite`: artefacto TFLite binario activo (`float32`).
- `labels.txt`: orden de salida: `plastico`, `vidrio`.
- `entrenamiento_manifest.json`: procedencia, partición, métricas y hash del
  artefacto activo.
- `tflite_validacion.json`: comprobación del TFLite exportado.

En la comparación operativa, MobileNetV2 obtuvo **716/1.000 (71,60 %)** y
macro-F1 **71,25 %**; MobileNetV3-Large INT8 obtuvo **571/1.000 (57,10 %)** y
macro-F1 **57,09 %**. Al agrupar capturas consecutivas por tripletas, la
mayoría de MobileNetV2 acertó 248/330 (**75,15 %**) frente a 195/330
(**59,09 %**) de V3. Este conjunto sirve para comparar compatibilidad con la
cámara, pero puede solaparse con datos de desarrollo y no se presenta como
prueba reservada.

El V2 conserva además una métrica histórica de validación de 98,43 %. Esa
métrica pertenece a su entrenamiento original y se mantiene separada de la
evaluación operativa para no inflar el resultado desplegado.

El hash SHA-256 esperado del artefacto activo es
`da71c12244076c1fe8f206a444f0c7fad9af467f813976acd40e027ae62f56b1`.

El modelo emite tres de los seis votos: por cada una de las tres fotos también
vota OpenAI+sistema experto. Los seis diagnósticos se cuentan juntos,
`desconocido` se abstiene y gana la clase con más votos. Un empate se resuelve
con la preferencia de los votos válidos del proveedor. El modelo local solo
distingue `plastico` y `vidrio`; una confusión sin resolver produce
`desconocido` y no abre ninguna compuerta.

## Compatibilidad TFLite

El preprocesamiento está integrado en el artefacto: recibe RGB crudo de 0 a
255. El V2 activo tiene entrada y salida `float32`. `vision/local_model.py`
conserva además soporte para escala y punto cero, por lo que un candidato
`int8` puede evaluarse en modo sombra sin alterar el flujo activo.

## Respaldos auditados

- La copia de procedencia del V2 activo permanece en
  `backups/mobilenetv2_run_20260721_2129/`.
- MobileNetV3-Large INT8 se conserva íntegro en
  `backups/mobilenetv3large_20260809_004420_split42_seed1/`, sin participar en
  `vision_votes`. Su SHA-256 es
  `b9f7ff5660c0b168776da187ee5b65d2a0682cf771ae9e61cf5c58b2b1f4f503`.

## Entrenar un candidato

La propuesta inicial está en
[`PROPUESTA-NUEVO-MODELO.md`](PROPUESTA-NUEVO-MODELO.md). Los scripts de
`scripts/entrenamiento/` implementan las tres arquitecturas:

```bash
python scripts/entrenamiento/entrenar_mobilenetv2.py      --dataset dataset-esp32cam
python scripts/entrenamiento/entrenar_efficientnetb0.py   --dataset dataset-esp32cam
python scripts/entrenamiento/entrenar_mobilenetv3large.py --dataset dataset-esp32cam
```

Requieren `tensorflow==2.20.0` y un dataset con subcarpetas `plastico/` y
`vidrio/`. Las corridas respetan particiones por sesión, transferencia en dos
fases, parada temprana, selección por macro-F1, aumentos realistas y una prueba
reservada. Los detalles están en
[`scripts/entrenamiento/README.md`](../scripts/entrenamiento/README.md).

Para probar un candidato sin reemplazar el activo:

```bash
LOCAL_MODEL_PATH=model/runs/<corrida>/model.tflite
LOCAL_MODEL_LABELS=model/runs/<corrida>/labels.txt
```
