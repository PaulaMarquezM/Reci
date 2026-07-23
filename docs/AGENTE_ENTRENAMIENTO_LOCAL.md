# RECI — Guía completa: entrenamiento local en Windows (usuario + agente)

> **Para quién es este documento:** Axel (usuario) y el **Cursor Agent** en la PC de escritorio **Windows**.  
> **Objetivo:** Entrenar MobileNetV2 (plástico / vidrio) **100% local**, sin Colab ni Drive en tiempo de ejecución.  
> **Idea del plan:** Descargar `RECI_dataset_propio` de Google Drive una vez → dejar entrenando de largo en Windows → evitar desconexiones de Colab y enlaces de Drive que caducan.

---

## Cómo usar este documento (flujo usuario + agente)

```
┌─────────────────────────────────────────────────────────────────┐
│  PASO 0 — AXEL (antes del agente)                               │
│  · Descargar RECI_dataset_propio de Drive al disco Windows      │
│  · git clone / git pull del repo RECI                           │
│  · Rellenar la sección 2 de este archivo (rutas y decisiones)   │
│  · Pegar el mensaje de la sección 3 en un chat nuevo (Agent)     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASO 1 — AGENTE (Windows + VS Code)                            │
│  · Leer este archivo completo                                   │
│  · Usar las rutas de la sección 2 (no inventar rutas)           │
│  · Seguir checklist sección 4 en orden                          │
│  · Marcar [x] al completar cada ítem                            │
│  · Reportar resultados (sección 8)                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASO 2 — AXEL + AGENTE (al terminar)                           │
│  · Revisar manifest y tests juntos                              │
│  · Si 16/16 OK → usar model.tflite en demo / Mac               │
│  · Continuar roadmap A1–A8 en README si aplica                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Resumen del plan (contexto)

| Qué | Detalle |
|-----|---------|
| **Problema con Colab** | Sesión se desconectó en Fase 1 (~época 7/15). Quedó `mejor_modelo.keras` (~91.6% val en época 3). |
| **Solución** | `scripts/entrenar_modelo.py` en Windows con dataset **ya en disco**. |
| **Tiempo** | CPU: 12–24+ h (completo) o ~2–6 h (solo Fase 2). GPU NVIDIA: más rápido. |
| **No hacer** | Colab, montar Drive durante entrenamiento, commitear `model/` ni `.env`. |

**Repo:** https://github.com/AxelJhostin/RECI · branch `main`

---

## 2. Configuración local — **RELLENAR ANTES DE ABRIR EL AGENTE**

> Axel: completa los campos de abajo en este archivo (o díselos al agente en el primer mensaje).  
> El agente **debe usar exactamente estas rutas** en todos los comandos.

### 2.1 Rutas en Windows

| Campo | Valor (rellenar) | Ejemplo |
|-------|------------------|---------|
| **Usuario Windows** | `________________` | `Axel` |
| **RECI_REPO** (proyecto clonado) | `________________` | `C:\Users\Axel\RECI` |
| **RECI_DATASET** (carpeta descargada de Drive) | `________________` | `C:\Users\Axel\RECI_dataset_propio` |
| **¿Dónde dejaste el dataset?** (nota libre) | `________________` | `En Descargas, movido a C:\Users\Axel\...` |

### 2.2 Checkpoint de Colab (si lo descargaste)

| Campo | Valor (rellenar) |
|-------|------------------|
| **¿Existe carpeta `runs/` dentro del dataset?** | Sí / No |
| **Nombre del run de Colab** | `________________` | ej. `run_20260715_1437` |
| **Ruta completa al checkpoint Fase 1** | `________________` | ej. `C:\Users\Axel\RECI_dataset_propio\runs\run_20260715_1437\mejor_modelo.keras` |
| **¿El archivo `mejor_modelo.keras` existe?** | Sí / No |

### 2.3 Decisión de entrenamiento (marcar UNA)

- [ ] **Opción A** — Continuar desde Colab (**solo Fase 2**) — si existe `mejor_modelo.keras` *(recomendado en tu caso)*
- [ ] **Opción B** — Entrenamiento **completo** desde cero (Fase 1 + 2 + export)
- [ ] **Opción C** — Reanudar **Fase 1** en local (`--resume`)

### 2.4 Entorno

| Campo | Valor (rellenar) |
|-------|------------------|
| **Python instalado** (`python --version`) | `________________` |
| **¿Tiene GPU NVIDIA?** | Sí / No / No sé |
| **Editor** | VS Code + terminal integrada |

### 2.5 Verificación rápida que Axel puede hacer antes del agente

En PowerShell (sustituir `RECI_DATASET`):

```powershell
$DATA = "PEGAR_RUTA_RECI_DATASET_AQUI"
Test-Path "$DATA\dataset_organizado\train\plastico"
Test-Path "$DATA\dataset_organizado\train\vidrio"
Test-Path "$DATA\dataset_organizado\val\plastico"
Test-Path "$DATA\dataset_organizado\val\vidrio"
(Get-ChildItem "$DATA\dataset_organizado\train\plastico").Count
(Get-ChildItem "$DATA\dataset_organizado\train\vidrio").Count
```

Referencia (~21k fotos totales): train plástico ~11k, train vidrio ~6.5k, val ~3k. Si todo es **0** → descarga incompleta.

---

## 3. Mensaje para pegar al agente (chat nuevo en Windows)

> **Axel:**  
> 1. Rellena la sección 2 arriba.  
> 2. Copia el bloque de abajo **sustituyendo** los valores entre `<<< >>>`.  
> 3. Abre Cursor en la PC Windows → **Agent mode** → pega el mensaje.

```
Proyecto RECI — entrenamiento 100% local en Windows.

INSTRUCCIÓN PRINCIPAL:
Lee y ejecuta EN ORDEN el archivo:
  docs/AGENTE_ENTRENAMIENTO_LOCAL.md
Marca el checklist (sección 4) con [x] al completar cada paso.
No uses Colab. No uses Google Drive en runtime.

─── RUTAS (configuradas por el usuario) ───
RECI_REPO:     <<< C:\Users\Axel\RECI >>>
RECI_DATASET:  <<< C:\Users\Axel\RECI_dataset_propio >>>
Usuario Windows: <<< Axel >>>

─── DATASET ───
Carpeta descargada de Drive y dejada en disco local: SÍ
Nota del usuario sobre ubicación: <<< ej. en C:\Users\Axel\RECI_dataset_propio >>>

─── CHECKPOINT COLAB (si aplica) ───
Existe mejor_modelo.keras: <<< Sí / No >>>
Ruta checkpoint: <<< C:\Users\Axel\RECI_dataset_propio\runs\run_20260715_1437\mejor_modelo.keras >>>
Nombre del run: <<< run_20260715_1437 >>>

─── OPCIÓN ELEGIDA ───
<<< A: solo Fase 2 desde checkpoint | B: entrenamiento completo | C: reanudar Fase 1 >>>

─── OBJETIVO ───
1. git pull en RECI_REPO
2. venv + pip install -r requirements.txt
3. Verificar estructura dataset (sección 2.5 del doc)
4. Ejecutar scripts\entrenar_modelo.py según opción elegida
5. Dejar corriendo de largo — desactivar suspensión del PC
6. Al terminar: leer entrenamiento_manifest.json
7. Copiar model.tflite y labels.txt a RECI_REPO\model\
8. python tests\test_imagenes_completo.py (meta 16/16)
9. Reportar: accuracy, recall vidrio/plástico, ruta del run, tiempo

─── RESTRICCIONES ───
- No commitear model/ ni .env
- Si RAM baja: --batch-size 16
- Si el usuario corrige una ruta, actualizar todos los comandos

Empieza por el checklist paso 0 y confirma las rutas antes de entrenar.
```

---

## 4. Checklist del agente (marcar `[x]` al avanzar)

### Fase preparación

- [ ] **0** — Leer sección 2 (rutas del usuario). Si faltan, **preguntar antes de continuar**.
- [ ] **1** — `cd RECI_REPO` → `git pull`
- [ ] **2** — Crear venv: `python -m venv .venv` → activar `.\.venv\Scripts\Activate.ps1`
- [ ] **3** — `pip install --upgrade pip` → `pip install -r requirements.txt`
- [ ] **4** — Verificar carpetas `dataset_organizado/train` y `val` (conteos > 0)
- [ ] **5** — Verificar TensorFlow: `python -c "import tensorflow as tf; print(tf.__version__); print(tf.config.list_physical_devices('GPU'))"`
- [ ] **6** — Confirmar opción A / B / C con el usuario si no está clara

### Fase entrenamiento

- [ ] **7** — Pedir al usuario desactivar **suspensión** del PC (Configuración → Energía)
- [ ] **8** — Ejecutar comando de entrenamiento (sección 5 — según opción)
- [ ] **9** — Monitorear que avanza (épocas, sin error OOM). Si OOM → reiniciar con `--batch-size 16`

### Fase cierre

- [ ] **10** — Abrir `entrenamiento_manifest.json` del run y validar métricas (sección 7)
- [ ] **11** — Copiar `model.tflite` + `labels.txt` → `RECI_REPO\model\`
- [ ] **12** — `python tests\test_imagenes_completo.py` (meta **16/16**)
- [ ] **13** — `python tests\test_cases.py` (meta **117/117**)
- [ ] **14** — Completar reporte final (sección 8) para el usuario

---

## 5. Comandos de entrenamiento (sustituir rutas de sección 2)

Variables para copiar/pegar en PowerShell:

```powershell
# ── Definir rutas (usar valores de sección 2) ──
$REPO    = "PEGAR_RECI_REPO"
$DATA    = "PEGAR_RECI_DATASET"
$RUN     = "PEGAR_NOMBRE_RUN"          # ej. run_20260715_1437
$CKPT    = "$DATA\runs\$RUN\mejor_modelo.keras"

cd $REPO
.\.venv\Scripts\Activate.ps1
```

### Opción A — Solo Fase 2 (continuar desde Colab) ★ recomendado si hay checkpoint

```powershell
python scripts\entrenar_modelo.py `
  --solo-fase 2 `
  --dataset-base $DATA `
  --checkpoint $CKPT
```

### Opción B — Entrenamiento completo

```powershell
python scripts\entrenar_modelo.py `
  --sync-fotos-repo `
  --dataset-base $DATA
```

### Opción C — Reanudar Fase 1

```powershell
python scripts\entrenar_modelo.py `
  --solo-fase 1 `
  --resume `
  --output-dir "$DATA\runs\$RUN" `
  --dataset-base $DATA
```

### Si falla por memoria

```powershell
python scripts\entrenar_modelo.py --solo-fase 2 --dataset-base $DATA --checkpoint $CKPT --batch-size 16
```

### Ayuda

```powershell
python scripts\entrenar_modelo.py --help
```

---

## 6. Estructura esperada del dataset local

```
RECI_DATASET/                          ← RECI_DATASET de sección 2
├── plastico/                          ← fotos en bruto
├── vidrio/
├── dataset_organizado/                ← OBLIGATORIO
│   ├── train/
│   │   ├── plastico/
│   │   └── vidrio/
│   └── val/
│       ├── plastico/
│       └── vidrio/
└── runs/
    └── run_20260715_1437/             ← run Colab (opcional)
        ├── mejor_modelo.keras         ← Fase 1 (checkpoint)
        ├── mejor_modelo_ft.keras      ← Fase 2 (tras entrenar)
        ├── model.tflite               ← salida final
        ├── labels.txt
        ├── entrenamiento_manifest.json
        ├── training_state.json
        ├── fase1_history.csv
        └── fase2_history.csv
```

---

## 7. Durante el entrenamiento (dejar de largo)

### Usuario (Axel)

1. **No suspender** el PC ni cerrar la tapa si es laptop (o configurar “nunca” en energía).
2. Mantener VS Code abierto (puede minimizar).
3. Si hay corte de luz → al volver, avisar al agente para `--resume`.

### Agente

1. Confirmar que el proceso sigue vivo (nuevas líneas `Epoch X/Y` en terminal).
2. Si se interrumpe: ver sección 9 (errores) y reanudar con `--resume`.
3. **No** iniciar Colab ni depender de Drive.

### Qué verás en terminal (normal)

```
======================================================================
 PASO 4/6 — Fase 1: entrenar capas nuevas ...
======================================================================
Epoch 1/15
...
```

O en Opción A:

```
 PASO 5/6 — Fase 2: fine-tuning ...
```

---

## 8. Al terminar — validar e instalar

### 8.1 Criterios en `entrenamiento_manifest.json`

| Métrica | Umbral |
|---------|--------|
| `accuracy` | ≥ 0.90 |
| `metricas_por_clase.vidrio.recall` | ≥ 0.85 |
| `metricas_por_clase.plastico.recall` | ≥ 0.85 |

### 8.2 Copiar modelo a RECI

```powershell
$RUN_PATH = "$DATA\runs\$RUN"   # o el run nuevo que creó el script
New-Item -ItemType Directory -Force -Path "$REPO\model"
Copy-Item "$RUN_PATH\model.tflite" "$REPO\model\model.tflite"
Copy-Item "$RUN_PATH\labels.txt"   "$REPO\model\labels.txt"
```

### 8.3 Tests

```powershell
cd $REPO
python tests\test_imagenes_completo.py
python tests\test_cases.py
```

---

## 9. Reporte final (plantilla para el agente)

Copiar y completar al terminar:

```
═══════════════════════════════════════
 RECI — Reporte entrenamiento local
═══════════════════════════════════════
Fecha:
PC:
Opción usada: A / B / C

Rutas:
  REPO:    ...
  DATASET: ...
  RUN:     ...

Resultados (entrenamiento_manifest.json):
  accuracy:        ...
  loss:            ...
  recall vidrio:   ...
  recall plastico: ...

Archivos generados:
  model.tflite:  Sí / No  (ruta)
  labels.txt:    Sí / No

Tests:
  test_imagenes_completo: __/16
  test_cases:             __/110

Modelo instalado en model/: Sí / No

Tiempo total aproximado:
Problemas encontrados:
Próximo paso sugerido:
═══════════════════════════════════════
```

---

## 10. Errores frecuentes

| Error | Causa | Solución |
|-------|-------|----------|
| `No existe ...\plastico` | `RECI_DATASET` mal escrita | Corregir ruta en sección 2 |
| `Dataset vacío` | Falta `dataset_organizado` | Re-descargar carpeta completa de Drive |
| `checkpoint no encontrado` | No se copió `runs/` de Colab | Opción B (completo) o pedir al usuario el archivo |
| `No module named tensorflow` | venv no activado | `.\.venv\Scripts\Activate.ps1` |
| OOM / memoria | batch muy grande | `--batch-size 16` o `8` |
| Muy lento | CPU sin GPU | Normal; dejar de largo |
| `Activate.ps1` bloqueado | Política PowerShell | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

---

## 11. División de responsabilidades

| Tarea | Quién |
|-------|-------|
| Descargar `RECI_dataset_propio` de Drive | **Axel** |
| Rellenar sección 2 y pegar mensaje sección 3 | **Axel** |
| `git pull`, venv, pip, comandos entrenamiento | **Agente** |
| Desactivar suspensión del PC | **Axel** |
| Vigilar que no se cierre VS Code / terminal | **Axel** |
| Reanudar con `--resume` si hay fallo | **Agente** |
| Revisar manifest y decidir si reemplaza producción | **Axel + Agente** |
| Copiar `model.tflite` al Mac / demo | **Axel** (después) |
| Roadmap A1–A8 (cámara, Claude) | **Otro chat / Mac** — ver README |

---

## 12. Archivos de referencia en el repo

| Archivo | Uso |
|---------|-----|
| **`docs/AGENTE_ENTRENAMIENTO_LOCAL.md`** | **Este archivo** — guía usuario + agente |
| `scripts/entrenar_modelo.py` | Script de entrenamiento |
| `docs/ENTRENAMIENTO_MODELO.md` | Guía técnica adicional |
| `README.md` | Arquitectura + roadmap demo A1–C3 |
| `RECI_entrenar_automatico.ipynb` | Legacy Colab — no usar |

---

## 13. Después del entrenamiento (qué sigue en el proyecto)

1. Llevar `model/model.tflite` a la Mac de desarrollo si entrenaste en Windows.
2. Probar `python3 vision/camera.py` con Claude en `.env`.
3. Continuar **Roadmap demo funcional** en README (ítems A1–A8).

---

*Última actualización: Julio 2026 · Entrenamiento local Windows · Colaboración usuario + agente*
