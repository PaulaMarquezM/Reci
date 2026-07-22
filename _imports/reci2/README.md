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
├── docs/        # Acta de constitución y documentación del proyecto
├── web/         # Reci App (PWA) + Reci Cloud (Next.js API routes + Supabase) + Dashboard admin
├── firmware/    # Código ESP32 (motores, servos, sensores, LEDs, audio) — PlatformIO
└── ia/          # Servicio de visión en la nube (Claude/Gemini + sistema experto) — ver ia/vision-service/
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

- [`docs/PLAN.md`](docs/PLAN.md) — **plan maestro vivo**: estado actual, decisiones técnicas, roadmap de las 8 fases y backlog por subsistema. **Leer primero.**
- [`docs/ACTA.md`](docs/ACTA.md) — acta de constitución (alcance, criterios de aceptación, riesgos, BOM).
- [`docs/Acta-de-constitucion.pdf`](docs/Acta-de-constitucion.pdf) — versión PDF original firmada.
