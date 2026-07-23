# RECI — Robot Inteligente de Reciclaje

> **Proyecto integrador — Pontificia Universidad Católica del Ecuador, Sede Manabí**  
> Carrera de Ingeniería de Software · Período PAO 2026-01  
> Materias: Sistemas Expertos (IS502) · Análisis y Circuitos Eléctricos · Tecnologías de Plataforma · Gestión de Proyectos  
> Repositorio: https://github.com/AxelJhostin/RECI

---

## Monorepo unificado

Este repositorio reúne el laboratorio de IA original y el producto integrado
que antes vivía en RECI2. Hay una sola fuente para el sistema experto, las
heurísticas y el prompt; la web, los servicios cloud y el firmware consumen
ese núcleo común.

| Área | Ruta | Responsabilidad |
|---|---|---|
| IA y entrenamiento | `expert_system/`, `vision/`, `scripts/`, notebooks | Dataset, entrenamiento MobileNetV2, reglas y validación |
| Servicio de visión | `services/vision/` | Adaptador FastAPI cloud sobre la IA compartida |
| Servicio facial | `services/face/` | Embeddings faciales opt-in |
| Aplicación y nube | `web/` | PWA Next.js, API routes y migraciones Supabase |
| Robot físico | `firmware/` | ESP32-CAM, Arduino Mega y pruebas Arduino Uno |
| Documentación de producto | `docs/product/` | Acta, plan maestro, decisiones, conexiones y contratos |

La fuente vigente para la arquitectura completa del producto es
[`docs/product/PLAN.md`](docs/product/PLAN.md). El contenido técnico que sigue
en este README documenta principalmente el desarrollo y entrenamiento de IA.
La organización y comandos del repositorio están en
[`docs/MONOREPO.md`](docs/MONOREPO.md).

---

## Tabla de contenidos

1. [¿Qué es RECI?](#qué-es-reci)
2. [Arquitectura completa del sistema](#arquitectura-completa-del-sistema)
3. [Estructura de archivos](#estructura-de-archivos)
4. [Instalación desde cero](#instalación-desde-cero)
5. [Ejecución](#ejecución)
6. [Sistema experto — detalle técnico completo](#sistema-experto--detalle-técnico-completo)
7. [Modelo de Machine Learning](#modelo-de-machine-learning)
8. [Flujo de visión híbrido](#flujo-de-visión-híbrido)
9. [API REST](#api-rest)
10. [Integración hardware — pendiente](#integración-hardware--pendiente)
11. [Integración nube — guía para el equipo de plataforma](#integración-nube--guía-para-el-equipo-de-plataforma)
12. [Objetos reconocidos](#objetos-reconocidos)
13. [Pruebas formales](#pruebas-formales)
14. [Troubleshooting](#troubleshooting)
15. [Alineación académica IS502](#alineación-académica-is502)
16. [División del equipo](#división-del-equipo)
17. [Estado actual](#estado-actual)
18. [Roadmap — demo funcional (semana PAO 2026)](#roadmap--demo-funcional-semana-pao-2026)
19. [Changelog — historial de cambios](#changelog--historial-de-cambios)

**Documentación adicional:** [`docs/README.md`](docs/README.md) · [`docs/ENTRENAMIENTO_MODELO.md`](docs/ENTRENAMIENTO_MODELO.md) · [`docs/AGENTE_ENTRENAMIENTO_LOCAL.md`](docs/AGENTE_ENTRENAMIENTO_LOCAL.md) (handoff agente Windows)

---

## ¿Qué es RECI?

RECI es un **robot físico de reciclaje inteligente** diseñado para operar dentro del campus de la PUCE Sede Manabí. Es una plataforma rodante con dos compartimentos (vidrio / plástico) que, mediante visión artificial y un sistema experto, identifica el tipo de residuo que se deposita y abre únicamente la compuerta correcta.

**El sistema acepta únicamente plástico y vidrio.** Cualquier otro material (lata, metal, papel, cartón, orgánico, etc.) se rechaza con el mensaje **"Material no permitido — depositar en tacho general"** (LED rojo, compuerta cerrada).

### Subsistemas

| Subsistema | Descripción |
|---|---|
| **RECI Físico** | Plataforma rodante con 2 compartimentos, servo, sensores ultrasónicos, LEDs WS2812, pantalla OLED, audio, ESP32 |
| **RECI IA** | Módulo de visión (MobileNetV2 + Claude/Gemini) + sistema experto Python corriendo en Raspberry Pi 4 |
| **RECI Cloud** | Backend FastAPI + Supabase/PostgreSQL + dashboard admin Next.js |
| **RECI App** | Aplicación móvil (Next.js PWA o Flutter) con mapa en tiempo real, llamada al robot, sistema de recompensas |

### Contexto académico y competencia

Este proyecto participa en una **competencia entre las sedes de Portoviejo y Manta** de la PUCE Manabí. El mejor proyecto obtiene la nota máxima y puede ser patentado. El código fuente del sistema experto y el modelo ML son el núcleo diferenciador del proyecto.

---

## Arquitectura completa del sistema

### Diagrama de flujo — clasificación de un objeto

```
USUARIO deposita objeto frente a RECI
            ↓
Sensor detecta objeto
            ↓
Cámara captura imagen 1280×720 px
            ↓
MobileNetV2 (.tflite) — ~0.1 seg
Detecta clase (plastico/vidrio) + confianza
Da su "voto" como contexto para la API de visión
            ↓
Claude Haiku / Gemini — ~2 seg
Analiza la imagen visualmente con el contexto del TM
Extrae los 9 atributos del objeto real
(puede identificar papel, lata, cartón, etc.)
            ↓
Refinamiento OpenCV (refinar_atributos_api)
Corrige latas, metal y vidrio mal etiquetados por la API
            ↓
  9 atributos visuales listos
          ↓
  Sistema Experto RECI
  (193 reglas · 18 meta-reglas · forward + backward chaining · CF MYCIN)
          ↓
  Conclusión: VIDRIO | PLÁSTICO | DESCONOCIDO | LATA | ORGÁNICO
          ↓
  Controlador físico ejecuta la acción:
  VIDRIO    → abre compuerta izquierda + LED azul
  PLASTICO  → abre compuerta derecha   + LED verde
  RECHAZADO → no abre nada             + LED rojo + "Material no permitido"
          ↓
  Evento enviado al backend en nube (FastAPI + Supabase)
          ↓
  App móvil recibe notificación con puntos ganados
```

### Capas del sistema

| Capa | Componente | Tecnología |
|---|---|---|
| Percepción | Cámara + MobileNetV2 | TensorFlow Lite, Python, Raspberry Pi 4 |
| IA / Experto | Motor de inferencia + 193 reglas IF-THEN | Python handcrafted (sin librerías de SE externas) |
| Control físico | Servomotores + sensores + cámara + LEDs + actuadores | Microcontrolador / placa (por definir) |
| Comunicación local | Controlador IA ↔ controlador físico | Protocolo por definir según hardware final |
| Backend / Nube | API REST + base de datos + eventos | FastAPI + Supabase (PostgreSQL) + Vercel |
| App móvil | Mapa, llamada al robot, recompensas | Next.js + Tailwind o Flutter + Dart |
| Dashboard admin | Panel de control web | Next.js + Supabase Realtime |

### Decisiones de hardware

```
Compuerta izquierda → VIDRIO   → servo 45°  → LED azul
Compuerta derecha   → PLÁSTICO → servo 135° → LED verde
Sin compuerta       → RECHAZADO→ servo 0°   → LED rojo  → "Material no permitido" + audio/OLED
```

---

## Estructura de archivos

Desde julio de 2026 este repo es un monorepo: además del laboratorio de IA
detallado abajo, incluye `web/` (PWA Next.js + Supabase), `firmware/`
(ESP32-CAM + Arduino) y `services/` (adaptadores cloud de visión y rostro).
Ver [`docs/MONOREPO.md`](docs/MONOREPO.md) para la organización completa y
qué carpeta es la fuente única de cada responsabilidad.

```
RECI/
├── web/                         # PWA Next.js — mapa, llamadas, cupones, Supabase
├── firmware/                    # ESP32-CAM (captura + voto mayoritario) y Arduino Mega/Uno
├── services/
│   ├── vision/                  # Adaptador cloud — consume expert_system/ y vision/ de la raíz
│   └── face/                    # Reconocimiento facial (FaceNet512 vía DeepFace)
├── docs/product/                # Documentación de producto (acta, decisiones, conexiones)
│
├── expert_system/
│   ├── knowledge_base.py       # 193 reglas IF-THEN en 5 niveles + atributos válidos
│   ├── inference_engine.py     # Motor principal: forward chaining, CF MYCIN, meta-reglas
│   ├── working_memory.py       # Memoria de trabajo — hechos activos por ciclo de inferencia
│   ├── backward_chaining.py    # Encadenamiento hacia atrás — verificación de hipótesis
│   ├── certainty_factor.py     # Factor de Certeza estilo MYCIN (fórmula de combinación)
│   ├── meta_rules.py           # 18 meta-reglas que ajustan el razonamiento
│   ├── validator.py            # Validador de atributos antes de inferir
│   ├── statistics.py           # Estadísticas de sesión + payload para Supabase
│   └── explanation.py          # Reporte técnico completo exportable a JSON
│
├── vision/
│   ├── tm_classifier.py        # Clasificador MobileNetV2 (.tflite) — módulo principal
│   ├── attribute_extractor.py  # Extractor Claude/Gemini + fallback TM+heurísticas
│   ├── visual_heuristics.py    # refinar_atributos() + refinar_atributos_api() (OpenCV)
│   └── camera.py               # Captura en tiempo real — modo demo (ESPACIO) + producción
│
├── docs/
│   ├── README.md                 # Índice de documentación
│   ├── FLUJO_RECONOCIMIENTO.md   # Pipeline visión, costos API, checklist demo
│   ├── ENTRENAMIENTO_MODELO.md        # Guía humana: captura + entrenar local
│   ├── AGENTE_ENTRENAMIENTO_LOCAL.md  # Handoff agente: entrenamiento largo Windows
│   └── diagramas/
│       ├── arquitectura_reci.png # Diagrama arquitectura (informes)
│       └── arquitectura_reci.mmd # Fuente Mermaid
│
├── scripts/
│   ├── entrenar_modelo.py            # ★ Entrenamiento local MobileNetV2 (reemplaza Colab)
│   ├── estimar_costo_gemini.py       # Estimador de costo por imagen (Gemini)
│   └── generar_diagrama_arquitectura.py  # Regenerar diagrama PNG
│
├── api/
│   ├── __init__.py
│   └── app.py                  # FastAPI — 8 endpoints REST, motor de inferencia compartido
│
├── tests/
│   ├── test_cases.py             # Runner principal — 117 pruebas formales
│   ├── test_imagenes_completo.py # 16 imágenes reales — flujo TM + API + SE
│   ├── test_refinar_api.py       # Pruebas unitarias de refinamiento lata/vidrio/PET
│   ├── test_backward_chaining.py # Pruebas dedicadas a los goals de backward chaining
│   └── casos/
│       ├── __init__.py
│       ├── casos_vidrio.py     # 9 casos de vidrio
│       ├── casos_plastico.py   # 18 casos de plástico
│       ├── casos_ambiguos.py   # 10 casos difíciles (PET vs vidrio)
│       ├── casos_extremos.py   # 4 casos extremos (baja confianza, desconocidos)
│       ├── casos_campus.py     # 26 casos con objetos reales del campus PUCE Manabí
│       └── casos_lata.py       # 11 casos de LATA y bordes con vidrio/plástico
│
├── model/                      # Modelo entrenado — NO está en el repo (ver instalación)
│   ├── model.tflite            # MobileNetV2 entrenado (99.7% precisión) — descargar aparte
│   ├── labels.txt              # Clases: 0 plastico / 1 vidrio
│   └── .gitkeep
│
├── images/
│   ├── capturas/               # Fotos capturadas por la cámara en tiempo real
│   ├── api_uploads/            # Fotos subidas por la API REST (gitignoreado — solo local)
│   └── prueba1-16.jpeg         # Imágenes de prueba incluidas en el repo
│
├── logs/                       # Logs de la API en producción — solo local, no en repo
│   └── reci.log                # Registro de clasificaciones, errores y eventos
├── fotos_dataset/              # Fotos tomadas con tomar_fotos.py — solo local, no en repo
├── RECI_entrenar_automatico.ipynb  # Legacy Colab (puede desconectarse — preferir script local)
├── RECI_entrenar_modelo.ipynb      # Legacy Colab manual celda por celda
├── main.py                     # Punto de entrada principal — demo completo en consola
├── tomar_fotos.py              # Recolector local de fotos → entrenar_modelo.py
├── requirements.txt            # Dependencias Python del proyecto
├── .env                        # Variables de entorno — NO subir a GitHub (gitignoreado)
├── .env.example                # Plantilla: VISION_API, Claude, Gemini
└── .gitignore
```

---

## Instalación desde cero

### Requisitos previos

- Python 3.9 o superior
- Cámara (integrada en laptop, módulo USB, o módulo Raspberry Pi Camera)
- TensorFlow ≥ 2.20 (entrenamiento local) · opcional `tensorflow-metal` en Mac Apple Silicon
- Cuenta Anthropic o Google (para Claude/Gemini API)

### 1. Clonar e instalar dependencias

```bash
git clone https://github.com/AxelJhostin/RECI.git
cd RECI
pip3 install -r requirements.txt
```

**Dependencias principales:**

| Paquete | Versión mínima | Para qué sirve |
|---|---|---|
| fastapi | ≥ 0.128.0 | API REST |
| uvicorn | ≥ 0.39.0 | Servidor ASGI |
| opencv-python | ≥ 4.13.0 | Captura de cámara y procesamiento de imagen |
| tensorflow | ≥ 2.20.0 | Cargar y ejecutar el modelo .tflite |
| httpx | ≥ 0.28.0 | Llamadas HTTP a Claude y Gemini |
| pydantic | ≥ 2.13.0 | Validación de datos en la API |
| python-dotenv | ≥ 1.2.0 | Leer variables de entorno desde .env |
| numpy | ≥ 2.0.0 | Operaciones con arrays de imagen |

> **En Raspberry Pi:** reemplazar `tensorflow` por `tflite-runtime` para menor consumo de RAM:
> ```bash
> pip3 install tflite-runtime
> ```

### 2. Configurar variables de entorno

Crear archivo `.env` en la raíz del proyecto (copiar desde `.env.example`):

```bash
cp .env.example .env
```

**Opción recomendada — Claude Sonnet (demo):**

```bash
VISION_API=claude
ANTHROPIC_API_KEY=tu_api_key_aqui
CLAUDE_MODEL=claude-sonnet-4-6
```

> **¿Por qué Sonnet y no Haiku?** Haiku (~5× más barato) confunde latas con
> botellas por la marca (lata de Coca-Cola → `botella_gaseosa` → abría la
> compuerta de plástico) y oscila con el Gatorade de vidrio. Verificado
> jul 2026: Sonnet clasificó 39/39 capturas reales de cámara sin errores,
> con Haiku como fallback automático. Costo Sonnet: ~$0.005–0.01/foto.

Obtener API key en: https://console.anthropic.com/ (mínimo de recarga ~$5)

**Alternativa — Gemini:**

```bash
VISION_API=gemini
GEMINI_API_KEY=tu_api_key_aqui
```

Obtener API key gratuita en: https://aistudio.google.com/apikey

> Si no hay API key, el sistema funciona con **TM + heurísticas OpenCV** (`refinar_atributos` + `refinar_atributos_api`). Con API configurada, Claude/Gemini **siempre** analiza la imagen visualmente (no solo como fallback) — ver [Flujo de visión híbrido](#flujo-de-visión-híbrido).

### 3. Obtener el modelo entrenado

El modelo `.tflite` no está en el repositorio por su tamaño (8.5 MB).

**Opción A — Descargar desde Google Drive del equipo:**
```bash
# El equipo comparte el modelo en Drive
# Descargar model.tflite y labels.txt → copiar a model/
cp ~/Downloads/model.tflite model/model.tflite
cp ~/Downloads/labels.txt   model/labels.txt
```

**Opción B — Entrenar el modelo desde cero (local, recomendado):**  
Copiar `RECI_dataset_propio` desde Drive a `~/RECI_dataset_propio`, luego:

```bash
python3 scripts/entrenar_modelo.py
```

Ver [Reentrenar el modelo](#reentrenar-el-modelo-con-más-fotos) y [`docs/ENTRENAMIENTO_MODELO.md`](docs/ENTRENAMIENTO_MODELO.md).

**Opción C — Sin modelo (solo API de visión):**
Si no hay `model/model.tflite`, el sistema detecta su ausencia y usa Claude/Gemini automáticamente. No se necesita hacer nada adicional.

### 4. Verificar la instalación

```bash
# Verificar sistema experto (sin hardware, sin internet)
python3 tests/test_cases.py
# Resultado esperado: 117/117 pruebas aprobadas (100%)

# Verificar refinamiento OpenCV post-API
python3 tests/test_refinar_api.py
# Resultado esperado: 5/5 pruebas aprobadas (100%)

# Verificar goals de backward chaining
python3 tests/test_backward_chaining.py
# Resultado esperado: 6/6 pruebas aprobadas (100%)

# Verificar flujo completo con 16 imágenes reales
python3 tests/test_imagenes_completo.py
# Resultado esperado: 16/16 imágenes aprobadas (100%)

# Verificar API REST
uvicorn api.app:app --reload --port 8000
# Abrir en navegador: http://localhost:8000/health
# Debe responder: {"status": "ok", "total_reglas": 174, ...}
```

---

## Ejecución

```bash
# Modo cámara en tiempo real
python3 vision/camera.py
# ESPACIO = capturar y clasificar | P = corregir a PLÁSTICO | V = corregir a VIDRIO | Q = salir
# Requisito macOS: Ajustes del Sistema → Privacidad y Seguridad → Cámara → activar Terminal

# API REST completa
uvicorn api.app:app --reload --port 8000

# Pruebas formales del sistema experto
python3 tests/test_cases.py

# Clasificar una imagen directamente
python3 vision/tm_classifier.py images/prueba7.jpeg

# Tomar fotos para el dataset
python3 tomar_fotos.py plastico   # ESPACIO = 1 foto | R = ráfaga 60 seg
python3 tomar_fotos.py vidrio

# Demo completo en consola
python3 main.py
```

---

## Sistema experto — detalle técnico completo

### ¿Qué hace el sistema experto?

Recibe un diccionario de **9 atributos visuales** (extraídos por Claude/Gemini o por TM + heurísticas OpenCV) y razona usando reglas IF-THEN para determinar si el objeto es VIDRIO, PLÁSTICO, o no permitido. Es la "inteligencia" del sistema que toma la decisión final.

### Uso básico

```python
from expert_system.inference_engine import InferenceEngine

engine = InferenceEngine()  # crear una sola vez — reutilizar para cada objeto
engine.cargar_hechos({
    "objeto_reconocido": "botella_agua",
    "confianza_ml":      "alta",
    "transparencia":     "alta",
    "color":             "transparente",
    "forma":             "cilindrica_estandar",
    "brillo":            "medio_difuso",
    "tapa":              "rosca_plastico",
    "textura":           "lisa_brillante",
    "rigidez":           "rigido"
})
conclusion, confianza, reglas = engine.ejecutar()
# conclusion = "PLASTICO", confianza = 0.998
print(engine.obtener_explicacion())  # trazabilidad completa
hardware = engine.decision_hardware()
# {"compuerta": "derecha", "led": "verde", "angulo_servo": 135, "mensaje": "..."}
```

> **Importante:** `cargar_hechos()` limpia el estado interno antes de cada clasificación.
> El motor se puede reutilizar sin reiniciarlo — de hecho así funciona la API para mayor eficiencia.

### Los 9 atributos visuales

Estos son los datos que el modelo ML extrae de la imagen y que el sistema experto recibe:

| Atributo | Valores posibles | Descripción |
|---|---|---|
| `objeto_reconocido` | Ver tabla completa abajo | Qué objeto identificó el modelo ML |
| `confianza_ml` | `alta` `media` `baja` | Qué tan seguro está el modelo ML |
| `transparencia` | `alta` `media` `baja` `ninguna` | Cuánto deja pasar la luz el objeto |
| `color` | `transparente` `ambar` `verde_oscuro` `blanco_opaco` `negro` `variado_vivo` `marron_tierra` `metalico` | Color predominante |
| `forma` | `cilindrica_delgada` `cilindrica_estandar` `cilindrica_ancha` `conica` `rectangular_plana` `irregular` | Forma geométrica |
| `brillo` | `alto_nitido` `medio_difuso` `bajo` `metalico` | Tipo de brillo en la superficie |
| `tapa` | `rosca_plastico` `corona_metalica` `twist_off_metalica` `tapa_ancha_metalica` `domo_plastico` `sin_tapa` `sellado` | Tipo de tapa o cierre |
| `textura` | `lisa_brillante` `lisa_sin_brillo` `rugosa` `fibrosa` | Textura de la superficie |
| `rigidez` | `rigido` `flexible` `indefinido` | Rigidez del material |

### Objetos reconocidos (`objeto_reconocido`)

| Valor | Categoría final | Descripción |
|---|---|---|
| `botella_agua` | PLASTICO | Tesalia, Pure Water, Güitig, Dasani, Cristal, BonAgua |
| `botella_gaseosa` | PLASTICO | Coca-Cola, Pepsi, Sprite, Fanta, 7UP, Powerade clear |
| `botella_energizante` | PLASTICO | Volt, 220V, Profit, Speed Max |
| `botella_alcoholica_plastico` | PLASTICO | Switch, Currimcho, 24-7 |
| `vaso_plastico` | PLASTICO | Vasos de cafetería, con o sin tapa domo |
| `yogur_plastico` | PLASTICO | Toni, Rey Leche, Chocolatada Toni Chiqui |
| `funda_plastico` | PLASTICO | Fundas negras o transparentes |
| `botella_fioravanti` | PLASTICO | Gaseosa ecuatoriana oscura |
| `botella_aceite_plastico` | PLASTICO | Alesol, El Cocinero, aceite en plástico |
| `botella_jugo_plastico` | PLASTICO | Pulp, Tampico, Frugos en plástico |
| `botella_enjuague_bucal` | PLASTICO | Colgate Plax, Listerine |
| `botella_cola_gallito` | PLASTICO | Cola Gallito — gaseosa ecuatoriana |
| `botella_gatorade` | PLASTICO | Gatorade — bebida deportiva boca ancha |
| `vaso_plastico_blanco` | PLASTICO | Vasos blancos opacos de cafetería (café, chocolate, té caliente) |
| `vaso_carton` | PLASTICO | Vasos de cafetería con pinta de cartón (polipapel — decisión de equipo, jul 2026, pese al matiz de material compuesto) |
| `plato_plastico` | PLASTICO | Platos desechables blancos rígidos (comedor campus) |
| `recipiente_plastico` | PLASTICO | Bowls y contenedores de comida en plástico blanco |
| `cubierto_plastico` | PLASTICO | Tenedores, cucharas y cuchillos desechables (comedor campus) |
| `snack_plastico` | PLASTICO | Bolsas de snack: Doritos, chifles, chitos, papas Lay's |
| `pitillo` | PLASTICO | Pitillos y sorbetes de cafetería |
| `botella_mocachino` | VIDRIO | Caffe Lato Toni, Don Café |
| `botella_cerveza_vidrio` | VIDRIO | Pilsener, Club |
| `botella_salsa_vidrio` | VIDRIO | Gustadina, salsas en vidrio |
| `frasco_vidrio` | VIDRIO | Snob mermelada, frascos de conserva |
| `botella_jugo_vidrio` | VIDRIO | Jugos en vidrio, Natura vidrio |
| `botella_pony_malta` | VIDRIO | Pony Malta — malta ecuatoriana en vidrio |
| `tetra_pak` | ORGANICO | Del Valle, Sunny, Natura Tetra Pak |
| `cascara_fruta` | ORGANICO | Cáscaras de fruta |
| `restos_comida` | ORGANICO | Cualquier resto de comida |
| `papel_servilleta` | ORGANICO | Papel, servilletas |
| `carton` | ORGANICO | Cajas de cartón |
| `vaso_vidrio` | VIDRIO | Vasos/tumblers de vidrio reutilizables (brillo nítido, sin cuello de botella) |
| `lata` | LATA | Red Bull, Monster lata, atún, Coca-Cola lata |
| `desconocido` | DESCONOCIDO | Objeto no identificable |

### Componentes del sistema experto

```
InferenceEngine
    ├── KnowledgeBase          → 193 reglas IF-THEN
    ├── WorkingMemory          → hechos activos del ciclo actual
    ├── AttributeValidator     → valida los 9 atributos antes de inferir
    ├── MetaRuleEngine         → 12 meta-reglas (ajustan EL CÓMO razonar)
    ├── CertaintyFactor        → combina evidencia de múltiples reglas (MYCIN)
    ├── BackwardChainingEngine → verifica la conclusión desde los hechos
    ├── RECIStatistics         → registra clasificaciones para el dashboard
    └── ExplanationReport      → reporte técnico exportable a JSON
```

### Ciclo de inferencia (orden de ejecución)

```
1. cargar_hechos()    → validar + cargar atributos en WorkingMemory
2. MetaRuleEngine     → 12 meta-reglas ajustan el contexto de razonamiento
3. Forward chaining   → evaluar las 193 reglas contra los hechos actuales
4. CF MYCIN           → combinar evidencia de las reglas disparadas por categoría
5. Ajustes meta       → aplicar exclusiones, prioridades y sesgos del contexto
6. BackwardChaining   → verificar la conclusión desde los hechos hacia atrás
7. decision_hardware()→ traducir conclusión a ángulo servo + LED + mensaje
```

### Niveles de reglas (193 reglas)

| Nivel | Cantidad | Descripción |
|---|---|---|
| **Nivel 1** | ~42 reglas | Reconocimiento directo: objeto conocido + confianza ML alta o media |
| **Nivel 2** | ~29 reglas | Razonamiento visual: ML con confianza media, se razona por atributos |
| **Nivel 3** | ~13 reglas | Desempate: transparente vs vidrio, vaso blanco vs yogur vs cartón, vidrio vs plástico |
| **Nivel 4** | ~6 reglas | Seguridad: baja confianza o desconocido → pide segunda captura |
| **Nivel 5** | ~80 reglas | Campus Manabí: productos ecuatorianos + vasos, platos, cubiertos, snacks, pitillos |

### Meta-reglas (12)

Las meta-reglas no clasifican objetos. Ajustan **cómo** razona el sistema antes de evaluar las reglas normales:

| ID | Prioridad | Cuándo activa | Qué hace |
|---|---|---|---|
| MR01 | 10 | `confianza_ml = baja` | Potencia backward chaining, ignora objeto reconocido |
| MR02 | 9 | `forma = cilindrica_delgada` + `transparencia = alta` | Sesgo hacia PLÁSTICO +5% |
| MR03 | 10 | `tapa = corona_metalica` | Prioriza VIDRIO ×1.10 |
| MR04 | 10 | `rigidez = flexible` | Excluye VIDRIO completamente |
| MR05 | 9 | `brillo = metalico` + forma cilíndrica | Prioriza LATA ×1.15 |
| MR06 | 8 | `confianza_ml = alta` + objeto conocido | Potencia reglas de Nivel 1 ×1.20 |
| MR07 | 7 | `forma = irregular` + no rígido | Sesgo hacia ORGÁNICO +5% |
| MR08 | 9 | `tapa = twist_off_metalica` | Prioriza VIDRIO ×1.08 |
| MR09 | 10 | `color = metalico` + `forma = rectangular_plana` | Excluye LATA, sesgo PLÁSTICO +8% |
| MR10 | 6 | `objeto = desconocido` + `confianza_ml = media` | Modo cauteloso, umbral CF ≥ 0.70 |
| MR11 | 8 | `color = variado_vivo` + `brillo = bajo` + `transparencia = ninguna` | Sesgo PLÁSTICO +7% (Fioravanti, jugos) |
| MR12 | 9 | `forma = rectangular_plana` + `rigidez = rigido` + `transparencia = ninguna` | Excluye VIDRIO y LATA, sesgo ORGÁNICO +8% (Tetra Pak) |
| MR13 | 8 | `color = blanco_opaco` + `textura = lisa_brillante` + `rigidez = rigido` + `tapa = sin_tapa` | Excluye VIDRIO y LATA, sesgo PLÁSTICO +10% (vasos/platos/cubiertos blancos) |
| MR14 | 9 | `rigidez = flexible` + `tapa = sellado` | Excluye VIDRIO y LATA, sesgo PLÁSTICO +6% (bolsas de snack, fundas) |
| MR15 | 8 | `forma = cilindrica_delgada` + `tapa = sin_tapa` + `rigidez = rigido` + color no metálico | Excluye VIDRIO, sesgo PLÁSTICO +5% (pitillos, sorbetes) |

### Factor de Certeza MYCIN

```
# Combinar dos CFs positivos:
CF_combinado = CF1 + CF2 × (1 - CF1)

# Bonus automático por especificidad (más condiciones = más confiable):
CF_final = CF_base + (num_condiciones - 1) × 0.01
# Regla con 5 condiciones: +0.04 de bonus sobre una regla con 1 condición

# Interpretación:
# CF ≥ 0.90 → CERTEZA MUY ALTA
# CF ≥ 0.75 → CERTEZA ALTA
# CF ≥ 0.55 → CERTEZA MEDIA
# CF ≥ 0.35 → CERTEZA BAJA
# CF < 0.10 → SIN CERTEZA
```

### Backward Chaining (verificación de hipótesis)

El backward chaining se ejecuta **después** del forward chaining como verificación. Parte de la conclusión obtenida y verifica si los hechos la sustentan desde atrás.

Cada categoría tiene un `Goal` con condiciones ponderadas:

**Condiciones eliminatorias:** algunas condiciones representan hechos "siempre/nunca" que no admiten excepción (ej. "una botella de vidrio siempre tiene tapa metálica"). Si una condición marcada `eliminatoria=True` falla, esa categoría queda **descartada por completo**, sin importar qué tan alto sea el score ponderado. Esto evita que una categoría "gane por puntaje" cuando le falta su rasgo más determinante.

**GOAL VIDRIO** (umbral: 60% de peso cumplido)

| Condición | Peso | Valores aceptados |
|---|---|---|
| rigidez | 1.00 | `rigido` |
| brillo | 0.95 | `alto_nitido` |
| tapa **[ELIMINATORIA]** | 0.90 | `corona_metalica` `twist_off_metalica` `tapa_ancha_metalica` |
| textura | 0.80 | `lisa_brillante` |
| color | 0.75 | `ambar` `verde_oscuro` `transparente` `variado_vivo` |
| forma | 0.70 | `cilindrica_estandar` `cilindrica_ancha` `cilindrica_delgada` |
| transparencia | 0.50 | `alta` `media` `baja` `ninguna` |

**GOAL PLÁSTICO** (umbral: 55%)

| Condición | Peso | Valores aceptados |
|---|---|---|
| tapa | 0.95 | `rosca_plastico` `domo_plastico` `sin_tapa` |
| brillo | 0.85 | `medio_difuso` `bajo` |
| textura | 0.75 | `lisa_brillante` `lisa_sin_brillo` |
| color | 0.70 | `transparente` `variado_vivo` `blanco_opaco` `negro` `ambar` |
| forma | 0.65 | `cilindrica_delgada` `cilindrica_estandar` `cilindrica_ancha` `conica` `irregular` |
| rigidez | 0.60 | `rigido` `flexible` |

**GOAL ORGÁNICO** (umbral: 55%)

| Condición | Peso | Valores aceptados |
|---|---|---|
| forma | 0.90 | `irregular` `rectangular_plana` |
| textura | 0.90 | `rugosa` `fibrosa` `lisa_sin_brillo` |
| brillo | 0.85 | `bajo` |
| color | 0.65 | `marron_tierra` `variado_vivo` `blanco_opaco` |
| transparencia | 0.60 | `ninguna` `baja` |

**GOAL LATA** (umbral: 70%)

| Condición | Peso | Valores aceptados |
|---|---|---|
| brillo **[ELIMINATORIA]** | 1.00 | `metalico` |
| color | 0.95 | `metalico` |
| rigidez | 0.85 | `rigido` |
| transparencia | 0.80 | `ninguna` |
| forma | 0.75 | `cilindrica_estandar` `cilindrica_delgada` |

LATA no tiene compuerta propia (va a tacho general junto con ORGÁNICO y DESCONOCIDO), pero su goal sí se evalúa: el riesgo real es que una regla de LATA le **robe** un caso a VIDRIO o PLASTICO, que sí tienen compuerta dedicada. Por eso "brillo metálico" — su rasgo más distintivo — es eliminatorio: sin él, LATA queda descartada aunque el resto del puntaje supere el umbral.

Si backward chaining contradice al forward chaining con score > 80%, el sistema genera una advertencia (no bloquea la decisión pero queda en el log). LATA está excluida de esta verificación de consistencia (junto con DESCONOCIDO), ya que no tiene compuerta propia.

---

## Modelo de Machine Learning

### Especificaciones

| Parámetro | Valor |
|---|---|
| Arquitectura | MobileNetV2 con transfer learning (ImageNet → RECI) |
| Formato | TensorFlow Lite (.tflite) — 8.5 MB |
| Resolución de entrada | 224 × 224 px, color RGB |
| Clases | `plastico`, `vidrio` |
| Precisión en validación | 98.2% |
| Tiempo de inferencia | ~0.1 segundos |
| Hardware compatible | Windows, Mac, Linux, Raspberry Pi 4 |

### Dataset de entrenamiento

Fotos tomadas en el campus PUCE Manabí con objetos reales, variando fondos, ángulos, distancias e iluminaciones:

| Clase | Total aprox. |
|---|---|
| plastico | ~13,580 fotos |
| vidrio | ~7,767 fotos |
| **Total** | **~21,347 fotos** |

Ratio de desbalance: ~**1.75:1** (plástico / vidrio). Compensado con `class_weight` en entrenamiento.

### Proceso de entrenamiento (local — recomendado)

> **Guía paso a paso:** [`docs/ENTRENAMIENTO_MODELO.md`](docs/ENTRENAMIENTO_MODELO.md)

| Herramienta | Uso |
|---|---|
| **`scripts/entrenar_modelo.py`** | **Recomendado** — organiza fotos, Fase 1+2, exporta `.tflite`, **reanudable** si se interrumpe |
| `RECI_entrenar_automatico.ipynb` | Legacy Colab — puede desconectarse a mitad de entrenamiento |
| `RECI_entrenar_modelo.ipynb` | Legacy Colab manual |

```bash
# Entrenamiento completo (dataset en ~/RECI_dataset_propio)
python3 scripts/entrenar_modelo.py --sync-fotos-repo

# Mac Apple Silicon: aceleración GPU
pip install tensorflow-metal
```

Hardware: GPU NVIDIA / Mac Metal / CPU (más lento) · Tiempo: ~2–8 h según equipo

Salida del entrenamiento automático (no sobrescribe el modelo anterior):

```
RECI_dataset_propio/runs/run_YYYYMMDD_HHMM/
├── model.tflite
├── labels.txt
└── entrenamiento_manifest.json
```

- **Fase 1** — capas nuevas, hasta 15 épocas (EarlyStopping): ~92% val
- **Fase 2** — fine-tuning últimas 30 capas, hasta 10 épocas: **98.2%** val (último run)

**Mejoras implementadas en el notebook (Junio 2026):**

| Mejora | Descripción |
|---|---|
| `RANDOM_SEED = 42` | Reproduce exactamente el mismo split en cada entrenamiento |
| `class_weight` automático | Compensa desbalance ~1.75:1 plástico/vidrio |
| Semillas en capas de augmentation | `RandomFlip`, `RandomRotation`, `RandomZoom`, `RandomBrightness` ahora tienen `seed` fijo |
| Semillas en `image_dataset_from_directory` | El shuffle del dataset es reproducible entre ejecuciones |
| Métricas detalladas por clase | Cell 19 imprime precision, recall, F1-score y soporte para cada clase, además de la matriz de confusión |
| Carga explícita antes de exportar | Cell 21 carga `mejor_modelo_ft.keras` explícitamente antes de convertir a `.tflite`, con manejo de error si el archivo no existe |
| Path corregido | La ruta del dataset apunta a `RECI_dataset_propio/dataset_organizado` (path correcto en Drive) |

### Reentrenar el modelo con más fotos

Ver guía completa: [`docs/ENTRENAMIENTO_MODELO.md`](docs/ENTRENAMIENTO_MODELO.md)

```bash
# Paso 1 — Tomar fotos del campus
python3 tomar_fotos.py plastico   # ESPACIO = 1 foto | R = ráfaga 0.2 s/foto × 60 s
python3 tomar_fotos.py vidrio
# Variar: ángulos, distancias, fondos, iluminación. Priorizar vidrio (clase minoritaria).

# Paso 2 — Dataset en local (copiar RECI_dataset_propio desde Drive si hace falta)
#   ~/RECI_dataset_propio/plastico/
#   ~/RECI_dataset_propio/vidrio/

# Paso 3 — Entrenar en tu computadora (recomendado)
python3 scripts/entrenar_modelo.py --sync-fotos-repo
# Mac M1–M4: pip install tensorflow-metal
# Resultado en: ~/RECI_dataset_propio/runs/run_YYYYMMDD_HHMM/

# Si Colab se desconectó en Fase 1, continuar Fase 2 con mejor_modelo.keras:
# python3 scripts/entrenar_modelo.py --solo-fase 2 --checkpoint ~/RECI_dataset_propio/runs/run_XXXX/mejor_modelo.keras

# Paso 4 — Verificar manifest (accuracy, recall vidrio)

# Paso 5 — Reemplazar solo si los tests pasan
cp ~/RECI_dataset_propio/runs/run_XXXX/model.tflite model/model.tflite
cp ~/RECI_dataset_propio/runs/run_XXXX/labels.txt   model/labels.txt

# Paso 6 — Verificar
python3 tests/test_imagenes_completo.py
python3 vision/tm_classifier.py images/prueba7.jpeg
```

> Los nombres de clase en el notebook deben ser exactamente `plastico` y `vidrio` (minúsculas, sin tilde). El `tm_classifier.py` los reconoce automáticamente.

---

## Flujo de visión híbrido

> **Documento completo:** [`docs/FLUJO_RECONOCIMIENTO.md`](docs/FLUJO_RECONOCIMIENTO.md) — diagrama, payload exacto a Claude/Gemini, costos y checklist de demo.  
> **Diagrama PNG:** [`docs/diagramas/arquitectura_reci.png`](docs/diagramas/arquitectura_reci.png)

```
Cámara captura imagen (1280×720 px)
        ↓
MobileNetV2 (.tflite) — ~0.1 seg         ← siempre corre primero
Clasifica entre plastico/vidrio
Solo pasa a la API: clase + % (NO los 9 atributos del MAPA)
        ↓
Claude Haiku / Gemini — ~2 seg            ← siempre se ejecuta si hay API key
Imagen JPG completa (base64) + prompt + contexto TM
Devuelve JSON con 9 atributos visuales
        ↓
refinar_atributos_api() — OpenCV         ← corrige latas, metal y vidrio mal etiquetados
        ↓ (si la API falla 404/429/503)
TM + refinar_atributos() + refinar_atributos_api()  ← fallback automático (16/16 OK)
        ↓
9 atributos → Sistema Experto (193 reglas) → Decisión final → Hardware
```

### Costo API (estimado)

| Proveedor | Por foto | 100 fotos | 500 fotos |
|-----------|----------|-----------|-----------|
| **Claude Haiku** (recomendado) | ~$0.001–0.002 | ~$0.10–0.20 | ~$0.50–1.00 |
| Gemini 2.5 Flash | ~$0.0009 | ~$0.09 | ~$0.46 |

Recalcular Gemini: `python3 scripts/estimar_costo_gemini.py`

Configuración demo: copiar `.env.example` → `.env`, definir `VISION_API=claude` y `ANTHROPIC_API_KEY`. Para Gemini, vincular billing en [AI Studio](https://aistudio.google.com/) con tope de **$5**.

**¿Por qué la API siempre actúa y no solo como fallback?**

El modelo TFLite solo conoce 2 clases: `plastico` y `vidrio`. Siempre elige una de las dos, incluso si el objeto es papel, una lata o cartón — y puede hacerlo con 100% de confianza aunque esté equivocado. Claude/Gemini ve la imagen real y puede identificar correctamente cualquier objeto, usando el voto del TM como referencia inicial pero sin estar limitado a esas dos clases.

Esto permite que el sistema experto produzca `DESCONOCIDO` o `LATA` (tacho general) para objetos que no son plástico ni vidrio, cumpliendo el alcance del proyecto.

**¿Qué envía exactamente el TM a la API?**

Solo **2 líneas de texto** insertadas en el prompt (no la imagen procesada ni el MAPA_CLASES):

| Enviado | Ejemplo |
|---------|---------|
| `clase_tm` | `"plastico"` o `"vidrio"` |
| `prob_tm` | `99%` |
| Imagen JPG | archivo completo en base64 |

**No se envía:** `objeto_reconocido`, color, tapa, brillo ni ningún atributo del MAPA_CLASES del TM.

Detalle completo y diagrama Mermaid: [`docs/FLUJO_RECONOCIMIENTO.md`](docs/FLUJO_RECONOCIMIENTO.md).

**Respuesta JSON estructurada:**

Claude y Gemini devuelven JSON con los 9 atributos. Gemini usa `responseMimeType: application/json` para respuesta JSON pura sin markdown.

**Refinamiento OpenCV post-API (`refinar_atributos_api`):**

Tras la respuesta de Claude/Gemini, OpenCV corrige errores frecuentes: latas/metal etiquetados como plástico, PET confundido con vidrio, botellas ámbar mal clasificadas. También corre en el fallback TM.

**Fallback automático si la API no está disponible:**

Si Claude/Gemini falla (404 modelo incorrecto, 429 cuota, 503 saturado, timeout), el sistema usa **TM + heurísticas OpenCV** (`refinar_atributos` + `refinar_atributos_api`) sin interrumpir la demo. Precisión medida: **16/16** imágenes de prueba sin API.

1. **Dentro de `analizar_y_clasificar_hibrido()`** — cámara, API y tests.
2. **Cache de sesión** — tras el primer fallo, no reintenta la API en cada foto (más rápido).

**Tiempo total por clasificación:**
- Flujo híbrido TM + Claude/Gemini: ~2–3 seg
- Fallback TM + heurísticas: ~0.1–0.3 seg

### Modo demo — cámara en tiempo real

La ventana de cámara tiene 4 estados secuenciales:

| Estado | Lo que ocurre |
|---|---|
| **PREVIEW** | Cámara en vivo — colocar el objeto frente a la cámara |
| **COUNTDOWN** | Cuenta regresiva de 1 segundo — mantener el objeto quieto |
| **ANALIZANDO** | Pantalla oscura con barra de progreso animada real — TM + API corren en hilo separado mientras la animación se mueve |
| **RESULTADO** | Clasificación mostrada 5 segundos con destino, confianza y barra de color |

**Controles:**
- `ESPACIO` — capturar y clasificar (funciona en PREVIEW o en RESULTADO para siguiente objeto)
- `P` — corregir manualmente a PLÁSTICO si el sistema se equivocó
- `V` — corregir manualmente a VIDRIO si el sistema se equivocó
- `Q` — salir del modo demo

**Destinos en pantalla:**
- `VIDRIO` → texto naranja, indica compuerta izquierda
- `PLASTICO` → texto verde, indica compuerta derecha
- `LATA` / `ORGANICO` / `DESCONOCIDO` → texto rojo, indica tacho general (corregible con P o V)

> En producción el sensor ultrasónico de la Raspberry Pi reemplaza el `ESPACIO`: detecta automáticamente cuando hay un objeto frente a la cámara y dispara la captura.

---

## API REST

### Iniciar el servidor

```bash
uvicorn api.app:app --reload --port 8000
```

Documentación interactiva (Swagger): `http://localhost:8000/docs`

### Endpoints

| Endpoint | Método | Descripción |
|---|---|---|
| `/` | GET | Info general + modo de visión activo (Claude, Gemini o TM) |
| `/health` | GET | Estado del sistema: reglas cargadas, modo visión, modelo TM disponible |
| `/reglas` | GET | Total y distribución de reglas por categoría |
| `/clasificar/atributos` | POST | Clasificar enviando los 9 atributos en JSON (usa el Raspberry Pi en producción) |
| `/clasificar/imagen` | POST | Clasificar desde una imagen (flujo híbrido TM + Claude/Gemini) |
| `/estadisticas` | GET | Estadísticas de la sesión para el dashboard |
| `/historial` | GET | Historial de clasificaciones (`?limite=20`) |
| `/reset` | POST | Resetear estadísticas de la sesión |

### Estructura completa del JSON de respuesta

```json
{
  "success": true,
  "timestamp": "2026-05-29T14:30:00",
  "clasificacion": "PLASTICO",
  "confianza": 0.998,
  "confianza_pct": 99.8,
  "es_reciclable": true,
  "hardware": {
    "compuerta": "derecha",
    "led": "verde",
    "angulo_servo": 135,
    "mensaje": "PLÁSTICO detectado — abriendo compartimento derecho"
  },
  "atributos": {
    "objeto_reconocido": "botella_agua",
    "confianza_ml": "alta",
    "transparencia": "alta",
    "color": "transparente",
    "forma": "cilindrica_estandar",
    "brillo": "medio_difuso",
    "tapa": "rosca_plastico",
    "textura": "lisa_brillante",
    "rigidez": "rigido"
  },
  "reglas_disparadas": 7,
  "backward_chaining": {
    "conclusion": "PLASTICO",
    "score": 1.0,
    "consistente": true
  },
  "meta_reglas_aplicadas": ["MR06"],
  "advertencias": [],
  "payload_supabase": {
    "timestamp": "2026-05-29T14:30:00",
    "clasificacion": "PLASTICO",
    "confianza": 0.998,
    "objeto_reconocido": "botella_agua",
    "reglas_disparadas": 7,
    "backward_consistente": true,
    "es_reciclable": true,
    "compuerta": "derecha",
    "sede": "PUCE Manabí"
  }
}
```

### Optimizaciones implementadas

El motor de inferencia (`InferenceEngine`) y el clasificador TM (`TeachableMachineClassifier`) se crean **una sola vez** al iniciar la API y se reutilizan en cada petición. Esto es crítico para el rendimiento en Raspberry Pi: crearlos desde cero en cada llamada tarda ~4x más que reutilizarlos.

El endpoint `/clasificar/imagen` usa el **mismo flujo híbrido TM + Claude/Gemini** que la cámara en tiempo real — no usa TM o API por separado como antes.

Las imágenes subidas en `images/api_uploads/` se limpian automáticamente: el sistema conserva solo los 50 archivos más recientes para evitar que el almacenamiento de la Raspberry Pi se llene.

### Logging persistente

Cada clasificación, error y evento de inicio queda registrado en `logs/reci.log`:

```
2026-06-22 21:45:12 | INFO | API iniciada | modo=HIBRIDO_TM_GEMINI
2026-06-22 21:45:38 | INFO | clasificar_imagen | PLASTICO 99.8% | vision=hibrido_tm_gemini | archivo=foto.jpg
2026-06-22 21:45:41 | INFO | clasificar_atributos | VIDRIO 100.0% | objeto=botella_mocachino
2026-06-22 21:46:02 | WARNING | Claude falló (ReadTimeout) — fallback a TM+heurísticas
```

Útil para diagnosticar errores en producción (Raspberry Pi) sin necesidad de conectar un monitor.

---

## Integración hardware — pendiente

> **Esta sección se completará una vez que el equipo defina los componentes físicos definitivos.**
>
> Lo que el software ya deja listo para cuando se conecte el hardware:
> - La API REST expone en cada respuesta: `hardware.angulo_servo`, `hardware.compuerta`, `hardware.led` y `hardware.mensaje` — los valores exactos que el controlador físico necesita para actuar.
> - El motor de inferencia ya toma la decisión final y la traduce a acción de hardware. El código de circuitos solo necesita leer ese resultado y ejecutarlo.
> - La lógica de clasificación es completamente independiente del hardware: el mismo sistema experto funciona con cualquier microcontrolador o placa que pueda comunicarse con Python.
>
> **Componentes que se van a usar (por confirmar):** cámara, servomotores, sensores ultrasónicos, y otros. Los detalles de conexión, pines, protocolos y código de hardware se documentarán aquí una vez que estén definidos.

---

## Integración nube — guía para el equipo de plataforma

### Consumir la API desde Next.js

```javascript
// Clasificar desde imagen (para el dashboard)
const formData = new FormData()
formData.append('file', imagenBlob, 'objeto.jpg')

const response = await fetch('http://localhost:8000/clasificar/imagen', {
  method: 'POST',
  body: formData
})
const resultado = await response.json()
// resultado.clasificacion, resultado.hardware, resultado.payload_supabase

// Estadísticas para el dashboard
const stats = await fetch('http://localhost:8000/estadisticas').then(r => r.json())
// stats.datos.total_vidrio, stats.datos.total_plastico, stats.datos.tasa_exito_pct

// Historial de clasificaciones
const historial = await fetch('http://localhost:8000/historial?limite=20').then(r => r.json())
```

### Payload para Supabase

Cada clasificación produce automáticamente un payload listo para insertar en Supabase:

```json
{
  "timestamp": "2026-05-29T14:30:00",
  "clasificacion": "PLASTICO",
  "confianza": 0.998,
  "objeto_reconocido": "botella_agua",
  "reglas_disparadas": 7,
  "backward_consistente": true,
  "es_reciclable": true,
  "compuerta": "derecha",
  "sede": "PUCE Manabí"
}
```

### Tabla sugerida en Supabase

```sql
CREATE TABLE clasificaciones (
  id              BIGSERIAL PRIMARY KEY,
  timestamp       TIMESTAMPTZ DEFAULT NOW(),
  clasificacion   TEXT NOT NULL,          -- VIDRIO / PLASTICO / DESCONOCIDO / etc.
  confianza       FLOAT,
  objeto_reconocido TEXT,
  reglas_disparadas INT,
  backward_consistente BOOLEAN,
  es_reciclable   BOOLEAN,
  compuerta       TEXT,
  sede            TEXT DEFAULT 'PUCE Manabí',
  usuario_id      UUID REFERENCES usuarios(id)  -- opcional para gamificación
);
```

---

## Objetos reconocidos

### Plástico → compuerta derecha (servo 135°, LED verde)

Botellas de agua: Tesalia, Pure Water, Güitig, Dasani, BonAgua, Cristal, pomo PUCE  
Gaseosas: Coca-Cola, Pepsi, Sprite, Fanta, 7UP, **Cola Gallito**  
Energizantes: Volt, **220V**, Profit, Speed Max, Powerade  
Deportivas: **Gatorade** (boca ancha)  
Alcohólicas en plástico: Switch, Currimcho, 24-7, **Zhumir**  
Vasos: vasos de cafetería transparentes con o sin tapa domo  
Lácteos: yogur Toni, Rey Leche, Chocolatada Toni Chiqui  
Higiene: Colgate Plax, Listerine  
Otros: fundas plásticas, Monster negro, **Fioravanti**, **Pulp**, **Tampico**, aceite de cocina en plástico

### Vidrio → compuerta izquierda (servo 45°, LED azul)

Mocachinos: Caffe Lato Toni, Don Café  
Cervezas: Pilsener, Club verde, Club negra  
Maltas: **Pony Malta**  
Salsas: Gustadina, salsa de soya  
Frascos: Snob mermelada, conservas  
Jugos en vidrio, aceite de cocina en vidrio, **Güitig vidrio**

### No permitidos → mensaje de rechazo, servo 0°, LED rojo

Latas de aluminio (Red Bull, Monster lata, Coca-Cola lata, atún), **Tetra Pak** (Del Valle, Sunny, Natura), cartón, papel, servilletas, cáscaras de fruta, restos de comida, cualquier objeto no identificado

---

## Pruebas formales

```bash
python3 tests/test_cases.py
```

**Resultado actual: 117/117 pruebas aprobadas (100%)**

| Categoría | Resultado | Objetos cubiertos |
|---|---|---|
| VIDRIO | 9/9 (100%) | Mocachino, Pilsener, Club, frasco, salsa, Güitig, salsa soya |
| PLASTICO | 18/18 (100%) | Agua, Coca-Cola, Sprite, vaso, energizante, Switch, yogur, funda, Monster, Pepsi, Fanta, 220V |
| AMBIGUO | 10/10 (100%) | PET vs vidrio transparente, vaso cartón vs plástico, funda vs cáscara |
| EXTREMO | 4/4 (100%) | Objeto desconocido baja confianza, atributos incompletos |
| CAMPUS_PLASTICO | 17/17 (100%) | Powerade, Dasani, Chocolatada, Colgate Plax, Speed Max, **Gatorade**, **Cola Gallito**, **Fioravanti** |
| CAMPUS_VIDRIO | 7/7 (100%) | Mocachino campus, Pilsener campus, **Pony Malta** |
| CAMPUS_ORGANICO | 2/2 (100%) | **Tetra Pak Del Valle**, Tetra Pak por atributos visuales |
| LATA | 11/11 (100%) | Lata de aluminio (ML y por atributos), lata aplastada, lata ancha (atún), y bordes con VIDRIO/PLASTICO ante color/brillo metálico |

Para agregar nuevos casos de prueba: editar el archivo correspondiente en `tests/casos/` sin tocar `test_cases.py`.

Además, `tests/test_backward_chaining.py` valida directamente los goals de `BackwardChainingEngine` (6/6 casos), incluyendo las condiciones eliminatorias de VIDRIO y LATA:

```bash
python3 tests/test_backward_chaining.py
```

Pruebas de imágenes reales con flujo completo (TM + API + SE + refinamiento):

```bash
python3 tests/test_imagenes_completo.py
# Resultado esperado: 16/16 imágenes aprobadas (100%)
```

Pruebas unitarias del refinamiento OpenCV post-API:

```bash
python3 tests/test_refinar_api.py
# Resultado esperado: 5/5 pruebas aprobadas (100%)
```

---

## Troubleshooting

### El modelo no carga
```
FileNotFoundError: Modelo no encontrado: model/model.tflite
```
**Solución:** El modelo no está en el repo. Ver sección [Obtener el modelo entrenado](#3-obtener-el-modelo-entrenado).

### TensorFlow no instala en Mac
```
ERROR: Could not find a version that satisfies the requirement tflite-runtime
```
**Solución:** En Mac usar TensorFlow completo:
```bash
pip3 install tensorflow
```

### Cámara sin permisos en Mac
```
OpenCV: not authorized to capture video (status 0)
```
o bien (macOS bloquea silenciosamente y el sistema lo detecta):
```
❌ La cámara se abrió pero no entrega imágenes (ret=False).
  → En macOS, ve a Ajustes del Sistema → Privacidad y Seguridad → Cámara
    y habilita el permiso para tu Terminal/IDE. Luego reinicia la Terminal.
```
**Solución:**
```
Ajustes del Sistema → Privacidad y Seguridad → Cámara → Activar Terminal (o IDE)
Cerrar y reabrir la Terminal completamente.
```
El sistema detecta automáticamente el fallo silencioso de macOS donde `isOpened()` devuelve `True` pero `read()` falla, y muestra un mensaje claro con instrucciones.

### Cámara no abre en Raspberry Pi
```
Cannot open camera index 0
```
**Solución:** Verificar el índice correcto:
```python
# Probar índices 0, 1, 2... hasta encontrar la cámara
import cv2
for i in range(3):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"Cámara encontrada en índice {i}")
        cap.release()
```
En la Raspberry Pi Camera Module usar `cv2.VideoCapture(0)` con el driver V4L2 activado.

### Claude da error 404 / 429 / timeout

| Error | Causa |
|---|---|
| `404 Not Found` | Modelo mal escrito en `.env` — verificar `CLAUDE_MODEL=claude-haiku-4-5` (sin `s` extra al final) |
| `429 Too Many Requests` | Rate limit — el sistema reintenta con pausa automática |
| `ReadTimeout` | La respuesta tardó más de 60 segundos |

**El sistema maneja estos errores automáticamente** — cae al modo TM + heurísticas OpenCV sin interrumpir la clasificación.

### Gemini da error 503 / 429 / timeout

| Error | Causa |
|---|---|
| `429 Too Many Requests` | Rate limit por minuto (esperar 60s) o cupo diario agotado (esperar 00:00 UTC) |
| `503 Service Unavailable` | Servidor de Google temporalmente caído |
| `ReadTimeout` | La respuesta tardó más de 60 segundos |

**El sistema maneja todos estos errores automáticamente** — cae al modo TM + heurísticas OpenCV sin mostrar ningún error al usuario ni interrumpir la clasificación. La cámara y la API siguen funcionando con normalidad, con menor precisión en objetos ambiguos.

La API gratuita de Gemini 2.5 Flash tiene ~250 requests/día. Si se hacen muchas pruebas seguidas (ej. 16 imágenes × varias sesiones), el cupo puede agotarse. Para uso intensivo, considerar una API key de pago (Gemini o Claude API).

### Las pruebas fallan después de cambiar reglas
```bash
python3 tests/test_cases.py
```
Si algún caso falla, el output muestra exactamente qué reglas se dispararon. Revisar `knowledge_base.py` en el nivel de regla correspondiente. El ID de cada regla indica su nivel (R01-R19: nivel 1, R20-R49: nivel 2, R60-R69: nivel 3, R70-R82: nivel 4, R90-R150: nivel 5).

### La API da error al importar
```
ModuleNotFoundError: No module named 'expert_system'
```
**Solución:** Ejecutar la API siempre desde la raíz del proyecto:
```bash
cd /ruta/a/RECI
uvicorn api.app:app --reload --port 8000
```

---

## Alineación académica IS502

| Resultado de aprendizaje | Implementado en |
|---|---|
| Fundamentos de sistemas expertos | `knowledge_base.py` + `inference_engine.py` |
| Relación SE con IA | Arquitectura híbrida MobileNetV2 + SE handcrafted + Claude/Gemini |
| Encadenamiento hacia adelante | `InferenceEngine.ejecutar()` — loop sobre 193 reglas |
| Encadenamiento hacia atrás | `BackwardChainingEngine` — verificación de hipótesis por goals ponderados |
| Factor de Certeza MYCIN | `CertaintyFactor` — fórmula de combinación + bonus por especificidad |
| Meta-conocimiento | `MetaRuleEngine` — 12 meta-reglas que controlan el razonamiento |
| Diseño e implementación de SE | Todo el módulo `expert_system/` — 9 componentes independientes |
| Evaluación ética | `ExplanationReport` — trazabilidad completa de cada decisión con reglas y CFs |
| Validación del SE | 74 pruebas formales organizadas por categoría + 6 pruebas de backward chaining, 100% de aprobación |

---

## División del equipo

| Responsable | Área principal | Secundaria |
|---|---|---|
| **Axel Hernández** | Sistema experto + modelo ML + integración IA | Diseño de circuito |
| **Paula Márquez** | App móvil + nube | Gestión del proyecto + hardware |
| **Leonela Sornoza** | App móvil + nube | Hardware + testing |
| **Andrea Campaña** | Sistema experto + IA | Hardware + testing |

**Docentes evaluadores:**
- Ing. Alex Fernando Ricaurte Segovia — Gestión de Proyectos
- Ing. Josselyn Tatiana Gómez — Sistemas Expertos
- Ing. Alexander Mackenzie — Tecnologías de Plataforma

---

## Estado actual

### Completado ✅

**Sistema experto:**
- **193 reglas**, forward + backward chaining, CF MYCIN, **18 meta-reglas**
- Productos ecuatorianos: Fioravanti, Cola Gallito, Gatorade, Pony Malta, Tetra Pak, Güitig vidrio, Zhumir, Pulp/Tampico, aceite de cocina, Colgate Plax/Listerine
- Validador de atributos, estadísticas, reporte técnico JSON
- **117/117 pruebas formales (100%)** — campus, ambiguos, extremos, LATA
- Condiciones eliminatorias en backward chaining: VIDRIO requiere tapa metálica, LATA requiere brillo metálico — ambas con 6/6 pruebas dedicadas

**Modelo ML:**
- MobileNetV2 propio (**98.2% precisión**, **21,347 fotos** del campus PUCE Manabí)
- Notebook mejorado: semillas reproducibles (`RANDOM_SEED=42`), `class_weight` automático, métricas por clase (precision/recall/F1), matriz de confusión, path de dataset corregido

**Visión e IA:**
- Flujo híbrido TM + Claude Haiku (o Gemini): TM da contexto → API analiza visualmente → `refinar_atributos_api` → SE decide
- Claude Haiku por defecto (~$0.001–0.002/foto); Gemini como alternativa
- Fallback automático a TM + `refinar_atributos` + `refinar_atributos_api` cuando la API falla (404, 429, 503, timeout)
- **16/16 imágenes reales** aprobadas en batch de prueba (con o sin API)

**Cámara:**
- Modo demo con 4 estados (PREVIEW → COUNTDOWN → ANALIZANDO → RESULTADO)
- Análisis TM+API corre en **hilo separado (threading)** — la barra de progreso animada es real, la interfaz nunca se congela
- Corrección manual con `P`/`V` disponible en cualquier momento
- Rechazo con mensaje **"Material no permitido — depositar en tacho general"**

**API REST:**
- Motor de inferencia **y** clasificador TM cargados globalmente — **4x más rápido** en Raspberry Pi
- `/clasificar/imagen` usa flujo híbrido TM + Claude/Gemini (igual que la cámara)
- Limpieza automática de `api_uploads/` — conserva solo los 50 más recientes
- **Logging persistente en `logs/reci.log`** — registro de clasificaciones, errores y eventos de producción

**Otros:**
- Prompts de Claude/Gemini con guía explícita de objetos no permitidos (papel, lata, cartón)
- Script de recolección de fotos con modo ráfaga automática
- Pruebas de imágenes reales con reporte de tiempo por imagen y promedio de sesión

### En progreso 🔄

- **Roadmap demo funcional** — ver sección [Roadmap](#roadmap--demo-funcional-semana-pao-2026) (mejoras A1–A8 en código, luego validación y setup físico)
- Verificación en vivo con cámara usando Claude Haiku (confirmar que el modelo en `.env` responde sin 404)
- Integración con hardware físico

### Pendiente ⏳

- Integración con el hardware físico (equipo hardware — esperando definir componentes y tenerlos disponibles)
- Plataforma física: cámara, servomotores, sensores ultrasónicos y demás componentes (por definir)
- Movimiento autónomo entre 2-3 puntos fijos del campus
- Dashboard Next.js + Supabase Realtime (equipo nube)
- App móvil con mapa en tiempo real y sistema de recompensas
- Reconocimiento facial opt-in (fase 2)
- Notificación automática cuando compartimento supera 80% de capacidad

### Criterios de aceptación del proyecto

| Criterio | Umbral | Estado actual |
|---|---|---|
| Precisión clasificación vidrio/plástico | ≥ 85% | **98.2%** modelo · **16/16** pruebas imagen ✅ |
| Tiempo de respuesta flujo híbrido | ≤ 3 seg | ~2–2.5 seg ✅ |
| Tiempo de respuesta app al punto más cercano | ≤ 3 seg | Pendiente |
| Sistema de recompensas registra correctamente | — | Pendiente |
| Dashboard con latencia | ≤ 5 seg | Pendiente |
| Reconocimiento facial opt-in | ≥ 70% confianza | Pendiente |
| Notificación compartimento lleno | ≤ 20 seg | Pendiente |
| Robot detecta y se detiene ante obstáculos | ≤ 20 cm | Pendiente |

---

---

## Roadmap — demo funcional (semana PAO 2026)

> **Para agentes / desarrolladores:** esta sección es la fuente de verdad del plan de mejoras.  
> Ir marcando `[x]` al completar cada ítem. **Orden estricto en Bloque A** — no saltar tareas.  
> Tras cada ítem de código: correr la [verificación diaria](#verificación-diaria) antes de continuar.

### Meta de la semana

Demo estable en laptop con cámara:

- **Plástico y vidrio** comunes del campus → compuerta correcta
- **Lata, papel, cartón, orgánico, desconocido** → rechazo con *"Material no permitido — depositar en tacho general"*
- **Si hay duda** → rechazar (no abrir compuerta equivocada)
- **Trazabilidad** cuando algo falle (logs con atributos, reglas y proveedor de visión)

**Criterio de éxito (viernes):**

| Métrica | Objetivo |
|---------|----------|
| Tests automatizados | 117/117 SE · 5/5 refinamiento · 16/16 imágenes |
| Batería manual campus | ≥ 18/20 objetos correctos |
| Claude en vivo | Activo en cámara (no fallback silencioso por 404) |

### Problemas conocidos (punto de partida)

| Problema | Impacto | Tarea relacionada |
|----------|---------|-------------------|
| Typo `CLAUDE_MODEL=claude-haiku-4-5s` → HTTP 404 | Todo cae a fallback TM sin aviso claro | A1 |
| R19_M: `botella_gatorade` → PLASTICO siempre | Gatorade vidrio clasificado mal | A3 |
| Backward chaining solo **advierte**, no corrige | Forward gana aunque backward tenga score alto | A2 |
| Botones P/V en cámara no persisten | Se pierden correcciones útiles para dataset | A7 |
| SE depende de atributos de API/OpenCV | Basura entra → basura sale | A4, A6 |
| Una sola foto por captura | Inestabilidad con movimiento / luz variable | A5 |
| Solo 16 imágenes en batch automático | Poca cobertura de casos reales | A8, B1 |

### Bloque A — Código (prioridad; orden estricto)

- [x] **A1 — Blindar configuración de visión**  
  Verificar `.env` (`VISION_API=claude`, `CLAUDE_MODEL=claude-haiku-4-5`). Al iniciar cámara/API, mostrar proveedor y modelo activos. Si API falla, mensaje visible (no fallback silencioso).  
  *Archivos:* `vision/attribute_extractor.py`, `vision/camera.py`, `api/app.py`  
  *Listo cuando:* cámara clasifica con Claude visible en consola.

- [x] **A2 — Política de decisión conservadora**  
  Umbral mínimo de CF para abrir PLASTICO/VIDRIO (`UMBRAL_APERTURA_CF = 0.75`). Si backward contradice con score > 0.80 **y** forward no es concluyente (`CF < CF_FORWARD_SEGURO = 0.90`) → `DESCONOCIDO`. Si CF final bajo umbral → rechazo. La condición de forward-CF evita rechazar casos de vidrio confiables donde el backward roza el 0.811.  
  *Archivos:* `expert_system/inference_engine.py` (constantes de clase + bloque A2 al final de `ejecutar`)  
  *Listo:* rechazo conservador verificado en ambas ramas (CF bajo y conflicto backward); tests SE 117/117, backward 6/6, refinar API 5/5.

- [x] **A3 — Reglas producto vs material**  
  Reglas de Gatorade condicionadas por atributos físicos, no solo por marca: tapa `rosca_plastico` → PLASTICO (`R19_M`/`R19_N`), tapa metálica + `brillo alto_nitido` → VIDRIO (`R19_M2`/`R19_M3`), y `brillo medio_difuso` → PLASTICO como discriminador de material (`R19_M4`).  
  *Archivos:* `expert_system/knowledge_base.py`  
  *Listo:* discriminación verificada (tapa plástica→PLASTICO, tapa metálica+nítido→VIDRIO); TC16/TC17 siguen en PLASTICO. Nota: `prueba10/prueba12` son tests de imagen y dependen también de la extracción de atributos (capa A4).

- [ ] **A4 — Consenso TM + OpenCV + SE**  
  Formalizar vetos cuando capas se contradicen (TM ≥92% plástico + brillo difuso → no flip a vidrio; metal/lata → LATA).  
  *Archivos:* `vision/visual_heuristics.py`, capa previa a SE en `attribute_extractor.py` o `tm_classifier.py`  
  *Listo cuando:* `test_refinar_api.py` 5/5 y sin regresiones en batch 16/16.

- [x] **A5 — Triple captura + voto mayoritario**  
  Tras countdown: 3 fotos reales (~0.3 s entre cada una, `Camera.capturar_rafaga`), cada una pasa por el flujo híbrido completo. Mayoría gana (se queda con el resultado de mayor confianza entre los votos ganadores); sin mayoría (ej. 3 conclusiones distintas o empate) → `DESCONOCIDO`. Aplica tanto en `modo_demo` (cámara interactiva) como en `capturar_y_clasificar` (Raspberry Pi + sensor ultrasónico).  
  *Archivos:* `vision/camera.py` (`capturar_rafaga`, `_analizar_multiple`)  
  *Listo:* `tests/test_voto_mayoritario.py` 6/6 (mayoría 2/3, unanimidad, empate, fallos parciales/totales).

- [x] **A6 — Logging completo por clasificación**  
  Guardar en `logs/clasificaciones.jsonl`: imagen, TM, atributos antes/después de `refinar_atributos_api`, conclusión, CF, reglas disparadas, backward, proveedor.  
  *Archivos:* `vision/camera.py`, `vision/attribute_extractor.py`, `api/app.py`  
  *Listo cuando:* un fallo se explica leyendo una línea del log.

- [x] **A7 — Persistir correcciones P/V**  
  Al pulsar P o V: copia cada foto de la ráfaga a `fotos_dataset/plastico/` o `vidrio/` y añade una línea a `logs/correcciones.jsonl` con conclusión original, conclusión corregida, atributos, TM y proveedor de visión usados. Con debounce (no duplica si se mantiene la tecla presionada) y nunca lanza excepción — un fallo al escribir en disco no interrumpe la demo.  
  *Archivos:* `vision/clasificacion_log.py` (`registrar_correccion_manual`), `vision/camera.py` (`_persistir_correccion`)  
  *Listo:* `tests/test_correcciones.py` 3/3; corrección manual deja archivo en disco y línea en el log.

- [ ] **A8 — Ampliar tests automatizados**  
  Tests de umbral CF (A2), Gatorade vidrio/plástico (A3), capturas nuevas en `test_imagenes_completo.py`.  
  *Archivos:* `tests/`  
  *Listo cuando:* suite completa verde sin regresiones.

### Bloque B — Validación (después de Bloque A)

- [ ] **B1 — Batería manual 20 objetos**  
  Checklist fijo campus (PET, vidrio, lata, papel, Tetra Pak, vaso blanco, etc.). Anotar causa de cada fallo: captura / API / OpenCV / SE / umbral / voto. Meta: ≥ 18/20.  
  **Herramienta lista:** `python3 scripts/bateria_b1.py` — corre la lista fija con cámara real (usa A5 internamente), pregunta acierto/causa por objeto y guarda resumen versionado en `docs/bateria_b1/`. Lista completa y razonamiento de cada objeto en [`docs/BATERIA_B1.md`](docs/BATERIA_B1.md).  
  *Pendiente:* ejecutar la sesión física con cámara y marcar `[x]` cuando el score quede registrado.

- [ ] **B2 — Ajuste fino post-batería**  
  Solo corregir lo que falló en B1. Sin features nuevas.

### Bloque C — Fuera de código (viernes o fin de semana)

- [ ] **C1 — Setup físico de captura**  
  Fondo uniforme, luz LED frontal, objeto centrado (~40–60% del frame). Repetir B1 y comparar %.

- [ ] **C2 — Dataset (solo fallos de B1)**  
  `tomar_fotos.py` → subir a Drive → `RECI_entrenar_automatico.ipynb` (Ejecutar todo). Prioridad: vidrio difícil, vasos opacos, Gatorade vidrio.

- [ ] **C3 — Hardware (si el equipo lo tiene listo)**  
  Conectar `decision_hardware()` a servo/LED. Regla: sin confianza alta → servo 0°. No bloquea demo en laptop.

### Calendario sugerido

| Día | Foco | Entregables |
|-----|------|-------------|
| Lunes | A1 + A2 | Claude OK en vivo; umbral conservador |
| Martes | A3 + A4 | Reglas material; consenso capas |
| Miércoles | A5 + A6 + A7 | Triple captura; logs; correcciones P/V |
| Jueves | A8 + B1 + B2 | Tests verdes; batería 20 objetos |
| Viernes | C1 + C2 (+ C3) | Setup físico; fotos de fallos; ensayo demo |

### Verificación diaria

```bash
python3 tests/test_cases.py
python3 tests/test_refinar_api.py
python3 tests/test_imagenes_completo.py
python3 tests/test_voto_mayoritario.py
python3 tests/test_correcciones.py
# Opcional: python3 vision/camera.py  → 3 objetos rápidos
# Batería B1 (con cámara física): python3 scripts/bateria_b1.py
```

### Cómo continuar en un chat nuevo (Cursor Agent)

1. Abrir repo `RECI`, branch `main`.
2. Leer esta sección y [`docs/FLUJO_RECONOCIMIENTO.md`](docs/FLUJO_RECONOCIMIENTO.md).
3. Buscar el **primer ítem sin marcar `[x]`** en Bloque A.
4. Decir: *"Empecemos con A1"* (o el siguiente pendiente).
5. Tras completar: marcar `[x]` en este README, correr verificación diaria, commit si el usuario lo pide.

### Fuera de alcance esta semana

- Reescribir el SE completo · modelo TM de 3 clases (`otro`) · dashboard nube · app móvil · reentrenamiento masivo del dataset

---

## Changelog — historial de cambios

### Julio 2026 — v2.9 (A5 voto mayoritario · A7 correcciones persistentes · B1 batería manual)

**`vision/camera.py` (A5)**
- `capturar_rafaga()` — 3 fotos reales separadas ~0.3 s (no recortes de la misma imagen), cada una con timestamp a microsegundos para no colisionar.
- `_analizar_multiple()` — corre el flujo híbrido completo sobre cada foto y decide por mayoría; sin mayoría (ej. 3 conclusiones distintas) → `DESCONOCIDO` en vez de arriesgar una compuerta equivocada.
- Aplica tanto en `modo_demo` (cámara interactiva) como en `capturar_y_clasificar` (Raspberry Pi + sensor ultrasónico).

**`vision/clasificacion_log.py` + `vision/camera.py` (A7)**
- `registrar_correccion_manual()` — al corregir con P/V, copia las fotos de la ráfaga a `fotos_dataset/plastico/` o `vidrio/` y añade una línea a `logs/correcciones.jsonl` con conclusión original vs. corregida, atributos y contexto de visión usados. Debounce para no duplicar si se mantiene la tecla presionada.

**`scripts/bateria_b1.py` + `docs/BATERIA_B1.md` (B1)**
- Herramienta interactiva para correr la lista fija de 20 objetos del campus con cámara real, registrar acierto/causa por objeto y guardar resumen versionado en `docs/bateria_b1/`.
- Lista elegida para presionar los puntos débiles conocidos de vidrio-vs-plástico: pares del mismo producto en ambos materiales (Gatorade PET vs. vidrio), PET de color oscuro (Fioravanti) y vidrio con condensación (apaga el brillo especular).

**Tests**
- `tests/test_voto_mayoritario.py` (6/6) — mayoría 2/3, unanimidad, empate a tres, fallos parciales/totales de la ráfaga.
- `tests/test_correcciones.py` (3/3) — copia de imagen, log JSONL, tipo inválido, sin imágenes.
- Sin regresiones: SE 110/110, refinar API 7/8 en este entorno (el caso restante requiere el modelo TM real, no probado aquí por falta de TensorFlow para Python 3.14 — no relacionado con este cambio).

### Julio 2026 — v2.8 (documentación + entrenamiento automático)

**Documentación**
- `docs/README.md` — índice de documentación del proyecto
- `docs/ENTRENAMIENTO_MODELO.md` — guía captura → Drive → Colab → despliegue
- `docs/diagramas/arquitectura_reci.png` — diagrama de arquitectura para informes

**Entrenamiento**
- `RECI_entrenar_automatico.ipynb` — pipeline Colab completo con **Ejecutar todo**; salida en `runs/run_.../` sin pisar modelo anterior

**Otros**
- `tomar_fotos.py` — rutas Drive corregidas, mensajes de ráfaga alineados (0.2 s/foto)
- README — conteos dataset actualizados (1.75:1), estructura de archivos ampliada

### Junio 2026 — v2.7 (refinamiento fallback + mensaje hardware + reglas lata/vidrio)

**`vision/visual_heuristics.py`**
- `refinar_atributos_api()` también en fallback TM (no solo post-Claude/Gemini).
- Balance lata/vidrio/PET: TM ≥92% plástico no flip a vidrio; ámbar fuerte → vidrio; detección lata mejorada.

**`vision/tm_classifier.py`**
- Integra ambos refinamientos (`refinar_atributos` + `refinar_atributos_api`) en fallback.
- Pasa `prob_vidrio` del TM al refinamiento.

**`expert_system/inference_engine.py`**
- Mensaje hardware unificado: **"Material no permitido — depositar en tacho general"**.

**`expert_system/knowledge_base.py`**
- Reglas R165–R167 para lata/vidrio en bordes ambiguos.

**`tests/test_refinar_api.py`** (nuevo) — 5/5 pruebas unitarias de refinamiento.

**Resultado:** 16/16 imágenes · 110/110 SE · 5/5 refinamiento.

---

### Junio 2026 — v2.6 (integración Claude Vision)

**`vision/attribute_extractor.py`**
- Soporte `VISION_API=claude|gemini` con Claude Haiku por defecto.
- Reintentos automáticos en 429; normalización de typo `claude-haiku-4-5s` → `claude-haiku-4-5`.
- Fallback automático a Sonnet si el modelo Haiku no existe.

**`.env.example`** / **`env.example`**
- Plantillas con `VISION_API`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`.

**`docs/FLUJO_RECONOCIMIENTO.md`**
- Documentación actualizada: Claude Haiku, costos, checklist de demo.

---

### Junio 2026 — v2.5 (fallback TM+heurísticas OpenCV + resiliencia Gemini)

**Problema resuelto:** cuando Gemini falla (cuota 429, servidor 503), el TM solo
tenía 2 clases (`plastico`/`vidrio`) y mapeaba todo a atributos genéricos incorrectos
(papel→plástico, Gatorade vidrio→plástico, vaso café→vidrio).

**`vision/visual_heuristics.py`** (nuevo)
- Análisis OpenCV de brillo, color, forma y textura sin red externa.
- Detecta papel plano blanco → `papel_servilleta` (rechazado como ORGANICO).
- Corrige TM vidrio→plástico en vasos mate de cafetería (sin brillo nítido).
- Corrige TM plástico→vidrio en botellas ámbar con brillo nítido y baja saturación.

**`vision/tm_classifier.py`**
- Integra `refinar_atributos()` después de cada inferencia TM.

**`vision/attribute_extractor.py`**
- Reintentos y fallback entre modelos Gemini (`2.5-flash`, `2.5-flash-lite`, `2.0-flash`).
- Cache de sesión: si Gemini falla una vez, las siguientes imágenes van directo a TM+heurísticas.
- Mensajes de error claros: `cuota agotada (429)`, `servidor saturado (503)`.

**`tests/test_imagenes_completo.py`**
- 16/16 imágenes reales aprobadas sin Gemini (solo TM+heurísticas).
- Papel esperado actualizado a ORGANICO (correcto — se rechaza igual que DESCONOCIDO).

---

### Junio 2026 — v2.4 (robustez de vidrio sin tapa: nuevas reglas + MR16)

**`expert_system/knowledge_base.py`**
- +4 reglas de VIDRIO (R161–R164) para cubrir botellas y frascos sin tapa visible:
  - **R161/R162**: `verde_oscuro + alto_nitido + rigido + sin_tapa` → botella Club/Güitig sin tapa.
  - **R163**: `variado_vivo + alto_nitido + cilindrica_estandar + rigido + sin_tapa` → vidrio con etiqueta colorida.
  - **R164**: `ambar + alto_nitido + rigido + sin_tapa + ninguna transparencia` → frasco de salsa/condimento.
- Total: **174 reglas**.

**`expert_system/meta_rules.py`**
- **MR16** (prioridad 10): `verde_oscuro + brillo alto_nitido` → señal exclusiva de vidrio. Prioriza VIDRIO ×1.12 y excluye PLÁSTICO/LATA/ORGÁNICO. Es la única combinación color+brillo que no puede ser plástico de consumo.
- Total: **16 meta-reglas**.

**`expert_system/inference_engine.py`**
- Añadida condición `senal_visual_vidrio_fuerte` al bloqueo conservador de baja confianza:
  cuando MR16 activa (`priorizar_categoria=VIDRIO` + `PLASTICO` excluido), el motor no fuerza
  DESCONOCIDO aunque `confianza_ml=baja`, permitiendo que los atributos visuales ganen.

**`tests/casos/casos_vidrio.py`**
- 4 nuevos casos (T54–T57): Club verde baja confianza, Güitig verde, vidrio con etiqueta, frasco ámbar.
- Total: **108/108 tests aprobados**.

---

### Junio 2026 — v2.3 (corto plazo: snacks, cubiertos, pitillos + dashboard de estadísticas)

**`expert_system/knowledge_base.py`**
- 3 nuevos `objeto_reconocido`: `cubierto_plastico`, `snack_plastico`, `pitillo`.
- +8 reglas Nivel 1 (R19_W–R19_AB): reconocimiento directo de los 3 nuevos objetos.
- +5 reglas Nivel 2 (R69_C1–R69_P): razonamiento visual por atributos (cubiertos, snacks, pitillos).
- +10 reglas Nivel 5 (R151–R160): reglas campus para comedor y cafetería PUCE Manabí.

**`expert_system/meta_rules.py`**
- **MR13**: `blanco_opaco + lisa_brillante + rigido + sin_tapa` → excluye VIDRIO/LATA, sesgo PLÁSTICO +10%. Patrón inequívoco de vasos/platos/cubiertos desechables.
- **MR14**: `flexible + sellado` → excluye VIDRIO/LATA, sesgo PLÁSTICO +6%. Cubre bolsas de snack y fundas.
- **MR15**: `cilindrica_delgada + sin_tapa + rigido + color no metálico` → excluye VIDRIO, sesgo PLÁSTICO +5%. Pitillos y sorbetes (la condición "no metálico" evita interferir con latas).

**`expert_system/statistics.py`**
- `contadores_objeto`: nuevo dict que cuenta cuántas veces apareció cada `objeto_reconocido` en la sesión.
- `confianza_por_cat`: lista de confianzas por categoría para calcular promedios reales.
- `objetos_reconocidos_frecuentes(top)`: top N objetos más frecuentes con cantidad y porcentaje.
- `confianza_promedio_por_categoria()`: confianza promedio real por VIDRIO/PLASTICO/etc.
- `payload_detalle()`: payload extendido para el nuevo endpoint de dashboard.

**`api/app.py`**
- `GET /estadisticas/detalle`: estadísticas extendidas con top 20 historial, desglose por objeto y confianza por categoría.
- `GET /estadisticas/objetos?top=N`: top N objetos más frecuentes detectados en la sesión.
- Versión actualizada a `2.2.0` en el endpoint raíz.

**`vision/attribute_extractor.py`** y **`vision/tm_classifier.py`**
- 3 nuevos objetos en el prompt de Gemini con guía de diferenciación.
- 3 nuevas entradas en `MAPA_CLASES` de TM.

**`tests/casos/casos_plastico.py`**
- +9 casos (T63–T71): cubiertos, snacks (Doritos/chifles), pitillos.
- **Resultado: 104/104 pruebas aprobadas (100%).**

### Junio 2026 — v2.2 (nuevos objetos: vasos blancos, platos y vasos de vidrio)

**`expert_system/knowledge_base.py`**
- 4 nuevos `objeto_reconocido`: `vaso_plastico_blanco`, `vaso_vidrio`, `plato_plastico`, `recipiente_plastico`.
- +8 reglas de Nivel 1 (R19_O–R19_V): reconocimiento directo de los nuevos objetos con confianza alta y media.
- +12 reglas de Nivel 2 (R37–R49): atributos visuales para cuando el ML no reconoce el objeto específico:
  - R37–R39: vaso blanco plástico (cónico, opaco, rígido, liso — diferente a cartón que es fibroso).
  - R44–R46: plato plástico (plano, blanco, rígido, brillo difuso — diferente a servilleta flexible).
  - R47–R49: vaso de vidrio (transparente, brillo nítido, ancho, sin tapa).
- +9 reglas de Nivel 3 (R67–R69_V): desempate fino para los casos críticos:
  - R67: vaso blanco cónico liso → PLASTICO (requiere `textura: lisa_brillante` para no confundir con cartón fibroso).
  - R68–R69: plato rígido → PLASTICO vs plato flexible → ORGANICO.
  - R67_V–R69_V: brillo nítido = vidrio vs brillo difuso = plástico en vasos transparentes.
- +12 reglas de Nivel 5 (R139–R150): reglas campus con contexto específico de objetos blancos del comedor y cafetería PUCE Manabí.

**`vision/attribute_extractor.py`**
- 4 nuevos valores en el prompt de Gemini con guía rápida y diferencias clave entre objetos similares:
  - `vaso_plastico_blanco` vs `yogur_plastico` (forma cónica vs cilíndrica ancha).
  - `plato_plastico` vs `papel_servilleta` (rígido y liso vs flexible y fibroso).
  - `vaso_vidrio` vs `vaso_plastico` (brillo nítido vs brillo difuso).

**`vision/tm_classifier.py`**
- 5 nuevas entradas en `MAPA_CLASES`: `vaso_plastico_blanco`, `vaso_plastico_blanco_con_tapa`, `vaso_vidrio`, `plato_plastico`, `recipiente_plastico`.

**`tests/casos/`**
- `casos_plastico.py`: +9 casos (T39–T47) — vasos blancos (café, chocolate), platos y bowls.
- `casos_vidrio.py`: +4 casos (T50–T53) — vasos tumbler y cónicos de vidrio, por objeto y por atributos.
- `casos_ambiguos.py`: +8 casos (T55–T62) — diferenciación: vaso blanco vs yogur, plato vs servilleta, vaso vidrio vs vaso plástico, vaso plástico vs cartón.
- **Resultado: 95/95 pruebas aprobadas (100%).**

### Junio 2026 — v2.1 (mejoras de producción)

**`vision/attribute_extractor.py`**
- Gemini ahora recibe `responseMimeType: application/json` y `maxOutputTokens: 256` → devuelve JSON puro, sin markdown ni texto extra. Elimina toda la lógica manual de limpieza de respuesta.
- Logging con `logger.info` en cada llamada a Gemini para trazabilidad en producción.
- Método `_parsear_json()` como fallback defensivo para parsear la respuesta de Gemini incluso si viene con texto extra (segunda línea de defensa).

**`vision/camera.py`**
- El análisis TM+Gemini ahora corre en un **hilo separado** (`threading.Thread`). Antes, la pantalla "Analizando..." se congelaba mientras se esperaba la respuesta de Gemini (2–5 seg). Ahora la barra de progreso se anima de verdad porque el hilo principal de OpenCV nunca se bloquea.
- Se usa `resultado_hilo = []` (lista compartida) para pasar el resultado del hilo de análisis al hilo de visualización de forma segura.

**`api/app.py`**
- `TeachableMachineClassifier` se carga **una sola vez al inicio** (variable `tm_global`) en lugar de en cada request. Mejora el tiempo de respuesta ~4x en Raspberry Pi.
- `/clasificar/imagen` ahora usa el flujo híbrido TM+Gemini completo, igual que la cámara. Antes usaba solo TM o Gemini por separado.
- `_limpiar_uploads()` limpia `images/api_uploads/` automáticamente conservando solo los 50 más recientes.
- Logging persistente configurado al arranque: todas las clasificaciones y errores se guardan en `logs/reci.log` con nivel INFO.

**`RECI_entrenar_modelo.ipynb`** / **`RECI_entrenar_automatico.ipynb`**
- `RANDOM_SEED = 42` aplicado globalmente → resultados reproducibles entre ejecuciones.
- `class_weight` calculado y aplicado en Fase 1 y Fase 2 → compensa desbalance ~1.75:1 plástico/vidrio.
- Métricas detalladas por clase (precision, recall, F1-score, support) y matriz de confusión en la celda de evaluación.
- Carga explícita de `mejor_modelo_ft.keras` antes de convertir a TFLite con manejo de `FileNotFoundError`.
- Path del dataset en Drive corregido: `RECI_dataset_propio/dataset_organizado`.

**`.gitignore`**
- Añadido `logs/` para que los logs de producción no se suban al repo.

### Antes — v2.0

- Sistema experto v2.0: 113 reglas, 12 meta-reglas, condiciones eliminatorias, 74/74 pruebas.
- Flujo híbrido TM+Gemini diseñado e implementado.
- Regla R51 endurecida (LATA requiere color + brillo metálico).

---

*Última actualización: Julio 2026 — v2.8 · RECI_entrenar_automatico.ipynb · docs/ · Roadmap A1–C3 · 110/110 + 16/16 + 5/5 tests*
