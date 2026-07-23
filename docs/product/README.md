# Reci

Robot físico de reciclaje inteligente para el campus de la PUCE Sede Manabí.

Plataforma móvil de dos compartimentos (vidrio / plástico) que se desplaza entre puntos fijos del campus, clasifica residuos con visión artificial + sistema experto, y se acompaña de una app móvil con gamificación y recompensas.

## Subsistemas

- **Reci físico** — plataforma rodante con Arduino Mega 2560 + ESP32-CAM, servos, OLED, LEDs, audio.
- **Reci cloud** — backend en Supabase + Next.js API routes (PostgreSQL, Auth, Realtime, Storage).
- **Reci app** — PWA en Next.js + Tailwind: mapa del campus, llamar al robot, historial, cupones.

## Equipo

| Integrante | Rol principal |
| --- | --- |
| Paula Márquez | Project Manager + Lead Developer (App & Cloud) |
| Axel Hernández | Lead IA + Sistema Experto |
| Leonela Sornoza | Hardware + Testing |
| Andrea Campaña | Hardware + Testing |

## Estructura del repo

```
Reci/
├── docs/product/     # Acta, plan, decisiones y guías conservadas de RECI2
├── web/              # PWA, API routes y migraciones Supabase
├── firmware/         # ESP32-CAM, Arduino Mega y pruebas Arduino Uno
├── services/vision/  # Adaptador cloud sobre la IA compartida
├── services/face/    # Servicio de embeddings faciales
├── expert_system/    # Fuente única de reglas y razonamiento
└── vision/           # Prompt, heurísticas, TFLite y desarrollo local
```

Cada subcarpeta tiene su propio `README.md` con stack y responsables.

## Cómo correr la web en local

```bash
cd web
npm install   # solo la primera vez
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000).

## Contexto académico

- Universidad: PUCE Sede Manabí — Ingeniería de Software, 5to semestre
- Periodo: PAO 2026-01
- Duración: 16 semanas
- Materias integradoras: Análisis y Circuitos Eléctricos, Sistemas Expertos, Gestión de Proyectos, Tecnologías de Plataforma

## Documentación

- [`PLAN.md`](PLAN.md) — **plan maestro vivo**: estado actual, decisiones técnicas, roadmap de las 8 fases y backlog por subsistema. **Leer primero.**
- [`ACTA.md`](ACTA.md) — acta de constitución (alcance, criterios de aceptación, riesgos, BOM).
- [`Acta-de-constitucion.pdf`](Acta-de-constitucion.pdf) — versión PDF original firmada.
