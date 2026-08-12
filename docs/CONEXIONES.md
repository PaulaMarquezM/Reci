# RECI — Guía de Conexiones de Hardware

> **Imprime esto.** Úsalo como referencia física mientras ensamblas.
> Versión: 1.0 · Junio 2026

---

## ORDEN DE ENSAMBLE (empieza aquí)

Sigue este orden para no dañar componentes:

```
ETAPA 1 → Energía y tierra común
ETAPA 2 → Arduino Mega solo (sin nada conectado, prueba LED)
ETAPA 3 → Motores + L298N
ETAPA 4 → Servomotores
ETAPA 5 → Sensores (ultrasonidos + PIR)
ETAPA 6 → Pantalla OLED + MPU (I2C)
ETAPA 7 → ESP32-CAM
ETAPA 8 → Prueba integrada completa
```

---

## ETAPA 1 — Sistema de Energía

### ¿Qué tienes?
- LiPo 7.4V → potencia motores y Arduino
- Power Bank 10,000mAh → potencia electrónica sensible (ESP32, sensores)
- LM2596 → convierte 7.4V a 5V estables para ESP32-CAM

### Diagrama de distribución de energía

```
┌─────────────────────────────────────────────────────────────────┐
│                    FUENTES DE ENERGÍA                           │
└─────────────────────────────────────────────────────────────────┘

  ┌──────────────┐                    ┌────────────────────┐
  │  LiPo 7.4V   │                    │  Power Bank 10Ah   │
  │  [+]   [-]   │                    │   Puerto USB        │
  └──┬───────┬───┘                    └────────┬───────────┘
     │       │                                 │
     │       └──────────────────┐              │
     │  (+ rojo)                │ (- negro)    │ (cable USB)
     │                          │              │
     ├──→ VIN Arduino Mega      │              └──→ Puerto USB Arduino Mega
     │     (7-12V, OK)          │                   (alternativa más estable)
     │                          │
     ├──→ +12V L298N #1  ←──── GND L298N #1
     │
     ├──→ +12V L298N #2  ←──── GND L298N #2
     │
     └──→ LM2596 IN(+)   ←──── GND Arduino
              │
              ↓
         LM2596 OUT(+) = 5.0V exactos ← ajusta el potenciómetro
              │
              └──→ 5V ESP32-CAM


  ⚠️  REGLA DE ORO: TODOS los GND van conectados entre sí
  ┌────────────────────────────────────────────────────────┐
  │  GND LiPo ── GND Mega ── GND L298N#1 ── GND L298N#2  │
  │             ── GND ESP32 ── GND Sensores               │
  └────────────────────────────────────────────────────────┘
```

### Cómo ajustar el LM2596

```
1. Conecta LM2596 IN(+) a LiPo+ y IN(-) a GND
2. Enciende la LiPo
3. Mide con multímetro en OUT(+) y OUT(-)
4. Gira el potenciómetro hasta leer exactamente 5.00V
5. Apaga. YA puedes conectar el ESP32
```

---

## ETAPA 2 — Arduino Mega (mapa de pines)

```
                    ┌─────────────────────────────┐
                    │       ARDUINO MEGA 2560      │
                    │                              │
    Motores ───     │  2  ← L298N#1 IN1            │
    L298N #1  ───   │  3  ← L298N#1 IN2            │
              ───   │  4  ← L298N#1 IN3            │
              ───   │  5  ← L298N#1 IN4            │
              ───   │  6  ← L298N#1 ENA (PWM)      │
              ───   │  7  ← L298N#1 ENB (PWM)      │
                    │                              │
    Motores ───     │  8  ← L298N#2 IN1            │
    L298N #2  ───   │  9  ← L298N#2 IN2            │
              ───   │ 10  ← L298N#2 IN3            │
              ───   │ 11  ← L298N#2 IN4            │
              ───   │ 12  ← L298N#2 ENA (PWM)      │
              ───   │ 13  ← L298N#2 ENB (PWM)      │
                    │                              │
    HC-05    ───    │ 16  TX2 → HC-05 RXD          │
    Bluetooth ───   │ 17  RX2 ← HC-05 TXD          │
                    │                              │
    ESP32-CAM ───   │ 18  TX1 → ESP32 RX ⚠️dividor │
              ───   │ 19  RX1 ← ESP32 TX           │
                    │                              │
    I2C Bus  ───    │ 20  SDA ← OLED + MPU         │
             ───    │ 21  SCL ← OLED + MPU         │
                    │                              │
    Ultrason. ───   │ 22  → Sensor frontal TRIG    │
              ───   │ 23  ← Sensor frontal ECHO    │
              ───   │ 24  → Sensor izq. TRIG       │
              ───   │ 25  ← Sensor izq. ECHO       │
              ───   │ 26  → Sensor der. TRIG       │
              ───   │ 27  ← Sensor der. ECHO       │
                    │                              │
    PIR      ───    │ 28  ← PIR OUT                │
                    │                              │
    Servos   ───    │ 44  → Servo #1 (plástico)    │
             ───    │ 45  → Servo #2 (vidrio)      │
                    │                              │
                    │ 5V  → sensores, servos, OLED │
                    │ 3V3 → MPU HW-123 VCC         │
                    │ GND → GND común              │
                    │ VIN ← LiPo 7.4V             │
                    └─────────────────────────────┘
```

---

> ⚠️ **Desactualizado — verificar antes de energizar.** El código real de
> `firmware/arduino-mega/ReciMega.ino` (jul 2026) usa D3/D4 para los servos
> de las compuertas y D5-D12 para los motores como 8 pines digitales
> simples, sin ENA/ENB conectados al Mega (sin PWM). El diagrama de abajo
> documenta D2/D3 para IN1/IN2 y D6/D7 para ENA/ENB — no coincide, y D3 no
> puede ser servo y motor a la vez. Antes de conectar nada, confirma con
> multímetro/continuidad cuál mapping es el que realmente está soldado en
> el robot, y actualiza esta sección para que quede como fuente de verdad
> real. Ver `firmware/arduino-mega/Navigation.h` para el detalle.

## ETAPA 3 — Motores con L298N

### Cómo identificar tus 4 motores TT

```
Vista desde arriba del robot:

        FRENTE
   ┌────────────┐
   │  M1    M2  │   M1 = izq. delantero  → L298N #1 motor A
   │            │   M2 = der. delantero  → L298N #2 motor A
   │  M3    M4  │   M3 = izq. trasero   → L298N #1 motor B
   └────────────┘   M4 = der. trasero   → L298N #2 motor B
        ATRÁS
```

### L298N #1 — Ruedas IZQUIERDAS

```
  ┌─────────────────────────────────────┐
  │           L298N #1                  │
  │                                     │
  │  +12V ←── LiPo 7.4V (+)           │
  │  GND  ←── GND común               │
  │  5V   ──→ (puedes usarlo p/ servos)│
  │                                     │
  │  IN1  ←── Arduino Pin 2            │
  │  IN2  ←── Arduino Pin 3            │
  │  ENA  ←── Arduino Pin 6 (PWM)      │
  │                                     │
  │  IN3  ←── Arduino Pin 4            │
  │  IN4  ←── Arduino Pin 5            │
  │  ENB  ←── Arduino Pin 7 (PWM)      │
  │                                     │
  │  OUT1 ──→ Motor M1 (cable A)       │
  │  OUT2 ──→ Motor M1 (cable B)       │
  │                                     │
  │  OUT3 ──→ Motor M3 (cable A)       │
  │  OUT4 ──→ Motor M3 (cable B)       │
  └─────────────────────────────────────┘

  💡 Si el motor gira al revés → intercambia OUT1 y OUT2 entre sí
```

### L298N #2 — Ruedas DERECHAS

```
  ┌─────────────────────────────────────┐
  │           L298N #2                  │
  │                                     │
  │  +12V ←── LiPo 7.4V (+)           │
  │  GND  ←── GND común               │
  │                                     │
  │  IN1  ←── Arduino Pin 8            │
  │  IN2  ←── Arduino Pin 9            │
  │  ENA  ←── Arduino Pin 12 (PWM)     │
  │                                     │
  │  IN3  ←── Arduino Pin 10           │
  │  IN4  ←── Arduino Pin 11           │
  │  ENB  ←── Arduino Pin 13 (PWM)     │
  │                                     │
  │  OUT1 ──→ Motor M2 (cable A)       │
  │  OUT2 ──→ Motor M2 (cable B)       │
  │                                     │
  │  OUT3 ──→ Motor M4 (cable A)       │
  │  OUT4 ──→ Motor M4 (cable B)       │
  └─────────────────────────────────────┘
```

---

## ETAPA 4 — Servomotores (tapas)

```
  SERVO #1 — Tapa PLÁSTICO              SERVO #2 — Tapa VIDRIO
  ──────────────────────────            ──────────────────────────
  Cable NARANJA (señal) ──→ Pin 44      Cable NARANJA (señal) ──→ Pin 45
  Cable ROJO    (VCC)   ──→ 5V*         Cable ROJO    (VCC)   ──→ 5V*
  Cable MARRÓN  (GND)   ──→ GND         Cable MARRÓN  (GND)   ──→ GND

  * Usa el pin 5V del L298N, NO el pin 5V del Arduino Mega
    (el Mega no da suficiente corriente para servos bajo carga)

  Ángulos de apertura sugeridos:
  ┌─────────────┬──────────────┬─────────────────┐
  │  Estado     │  Ángulo      │  Función        │
  ├─────────────┼──────────────┼─────────────────┤
  │  Cerrado    │  0°          │  Reposo         │
  │  Abierto    │  90°         │  Depositar      │
  └─────────────┴──────────────┴─────────────────┘
```

---

## ETAPA 5 — Sensores Ultrasónicos + PIR

### 3× HC-SR04 (ultrasonidos)

```
  ┌──────────────────────────────────────────────────────────────┐
  │                                                              │
  │   FRONTAL              IZQUIERDO            DERECHO         │
  │   ┌────────┐           ┌────────┐           ┌────────┐      │
  │   │ HC-SR04│           │ HC-SR04│           │ HC-SR04│      │
  │   │VCC TRIG│           │VCC TRIG│           │VCC TRIG│      │
  │   │GND ECHO│           │GND ECHO│           │GND ECHO│      │
  │   └──┬──┬──┘           └──┬──┬──┘           └──┬──┬──┘      │
  │      │  │                 │  │                 │  │         │
  │     5V Pin22             5V Pin24             5V Pin26      │
  │     GND Pin23            GND Pin25            GND Pin27     │
  │                                                              │
  └──────────────────────────────────────────────────────────────┘

  Posición física recomendada:
  ┌───────────────────────────────┐
  │        ↑ FRONTAL (22/23)      │   A 30cm del suelo aprox.
  │  ←IZQ  ┌──────────┐  DER→   │
  │ (24/25) │   RECI   │ (26/27) │   Apuntando 45° hacia afuera
  │         └──────────┘         │
  └───────────────────────────────┘
```

### PIR (detector de presencia)

```
  ┌──────────────┐
  │  Módulo PIR  │
  │              │
  │  VCC ──────→ 5V Arduino
  │  GND ──────→ GND común
  │  OUT ──────→ Pin 28 Arduino
  └──────────────┘

  Montaje: frontal del robot, apuntando hacia el usuario
  Distancia de detección: ~1-3 metros (ajustable con potenciómetro)
```

---

## ETAPA 6 — OLED + MPU HW-123 (Bus I2C)

```
  Los dos comparten los mismos cables SDA y SCL — eso es normal.
  El bus I2C identifica cada módulo por su dirección única.

  ┌─────────────────────────────────────────────────────────┐
  │                   BUS I2C                               │
  │                                                         │
  │  Arduino Pin 20 (SDA) ─────┬──────────────┐            │
  │  Arduino Pin 21 (SCL) ──┬──┼──────────┐   │            │
  │                          │  │          │   │            │
  │                     ┌────┴──┴──┐  ┌───┴───┴──┐        │
  │                     │  OLED    │  │ MPU HW-123│        │
  │                     │ 0.96"    │  │  (0x68)   │        │
  │                     │ (0x3C)   │  │           │        │
  │                     │ VCC→5V   │  │ VCC→3.3V  │        │
  │                     │ GND→GND  │  │ GND→GND   │        │
  │                     └──────────┘  └───────────┘        │
  └─────────────────────────────────────────────────────────┘

  Direcciones I2C:
  ┌──────────────┬───────────────┬──────────────────────────┐
  │  Módulo      │  Dirección    │  Nota                    │
  ├──────────────┼───────────────┼──────────────────────────┤
  │  OLED 0.96"  │  0x3C         │  Fija                    │
  │  MPU HW-123  │  0x68 / 0x69  │  Pin AD0: LOW=68, HI=69  │
  └──────────────┴───────────────┴──────────────────────────┘
```

---

## ETAPA 7 — ESP32-CAM

### ⚠️ IMPORTANTE: Divisor de voltaje obligatorio

```
  El ESP32-CAM trabaja en 3.3V. Si conectas directamente
  el TX del Arduino (5V) al RX del ESP32 → lo quemas.

  DIVISOR DE VOLTAJE (R1=1kΩ, R2=2kΩ):

  Arduino TX1 (5V)
       │
      [R1 = 1kΩ]
       │
       ├──────────→  ESP32-CAM U0RXD (3.3V)
       │
      [R2 = 2kΩ]
       │
      GND

  Voltaje resultante: 5V × (2kΩ / 3kΩ) = 3.33V ✓
```

### Conexión completa ESP32-CAM

```
  ┌─────────────────────────────────────────────────────────┐
  │                    ESP32-CAM                            │
  │                                                         │
  │  5V   ←────── LM2596 OUT (5V regulados)                │
  │  GND  ←────── GND común                                │
  │                                                         │
  │  U0TXD ──────────────────────→ RX1 Arduino (Pin 19)    │
  │                                                         │
  │  U0RXD ←── [divisor voltaje] ── TX1 Arduino (Pin 18)   │
  │                                                         │
  │  IO0  → GND solo para PROGRAMAR (quita después)        │
  └─────────────────────────────────────────────────────────┘

  Para programar el ESP32-CAM:
  ┌────────────────────────────────────────────────────────┐
  │  1. Conecta el ESP32-CAM-MB (programador USB)          │
  │  2. IO0 → GND (modo flash)                             │
  │  3. Conecta USB a la PC                                │
  │  4. Carga el código desde Arduino IDE                  │
  │  5. Desconecta IO0 de GND                              │
  │  6. Presiona RESET en el módulo                        │
  └────────────────────────────────────────────────────────┘
```

---

## ETAPA 8 — Vista completa del sistema

```
                         ╔══════════════════╗
                         ║   CLOUD (Vercel)  ║
                         ║   Next.js + API   ║
                         ║   Modelo IA       ║
                         ╚════════╤═════════╝
                                  │ WiFi / Internet
                         ╔════════╧═════════╗
                         ║    ESP32-CAM      ║
                         ║  Cámara OV2640    ║
                         ║  Envía foto al    ║
                         ║  servidor IA      ║
                         ╚════════╤═════════╝
                                  │ Serial (TX/RX)
                    ╔═════════════╧══════════════════╗
                    ║         ARDUINO MEGA 2560       ║
                    ║         Controlador central     ║
          ┌─────────╣                                 ╠────────────┐
          │         ║                                 ║            │
    ┌─────┴──────┐  ╚════════════════════════════════╝  ┌─────────┴──────┐
    │  L298N #1  │         │          │         │        │    L298N #2    │
    │ Ruedas izq.│      Servos     Ultrason.   PIR       │  Ruedas der.  │
    └────────────┘      (x2)       (x3)                 └────────────────┘
    Motor M1 M3       Tap. plas.  Frontal                 Motor M2 M4
                      Tap. vidrio Izq. Der.
```

---

## Tabla de materiales — orden de uso

```
┌─────┬───────────────────────────────┬──────────┬──────────────────────────┐
│ Ord │ Componente                    │ Estado   │ Necesitas esto para...   │
├─────┼───────────────────────────────┼──────────┼──────────────────────────┤
│  1  │ LM2596 Buck Converter         │ Carrito  │ Proteger el ESP32        │
│  1  │ Cables Dupont M-M (40 pcs)    │ Carrito  │ Todo                     │
│  2  │ Arduino Mega 2560             │ Ya tienes│ Cerebro central          │
│  2  │ LiPo 7.4V                     │ Ya tienes│ Alimentar motores        │
│  3  │ 2× L298N                      │ Carrito  │ Controlar 4 motores      │
│  3  │ 4× Motores TT + 4× Llantas   │ Carrito  │ Movimiento               │
│  4  │ 2× Servo Futaba S3003         │ Carrito  │ Tapas de depósito        │
│  5  │ 3× Sensor ultrasónico HC-SR04│ Ya tienes│ Evitar obstáculos        │
│  5  │ Módulo PIR                    │ Ya tienes│ Detectar persona         │
│  6  │ OLED 0.96" I2C               │ Carrito  │ Mostrar info al usuario  │
│  6  │ MPU HW-123                    │ Ya tienes│ Detectar inclinación     │
│  7  │ ESP32-CAM + programador MB    │ Carrito  │ Cámara + WiFi            │
│  7  │ Resistencias 1kΩ y 2kΩ       │ COMPRA   │ Divisor de voltaje       │
│  8  │ Power Bank 10,000mAh          │ Ya tienes│ Electrónica estable      │
└─────┴───────────────────────────────┴──────────┴──────────────────────────┘

⚠️  NO está en la lista pero necesitas:
    - 2× Resistencias 1kΩ (puedes conseguirlas en cualquier tienda electrónica)
    - 1× Resistencia 2kΩ
    - Multímetro (para calibrar el LM2596)
    - Estaño + cautín (para soldar el divisor de voltaje)
```

---

## Checklist de prueba por etapa

```
ETAPA 1 — Energía
  [ ] LM2596 ajustado a 5.00V (medir con multímetro antes de conectar)
  [ ] LiPo conectada → Mega enciende (luz LED verde)
  [ ] Todos los GND unidos

ETAPA 2 — Arduino solo
  [ ] Subir sketch "Blink" → LED pin 13 parpadea

ETAPA 3 — Motores
  [ ] Los 4 motores giran en la dirección correcta
  [ ] Avanzar: M1+M3 adelante, M2+M4 adelante
  [ ] Girar: M1+M3 adelante, M2+M4 atrás (o viceversa)

ETAPA 4 — Servos
  [ ] Servo #1 abre y cierra a 0° y 90°
  [ ] Servo #2 abre y cierra a 0° y 90°

ETAPA 5 — Sensores
  [ ] Serial Monitor muestra distancias de los 3 ultrasónicos
  [ ] PIR detecta movimiento (Serial Monitor cambia de 0 a 1)

ETAPA 6 — I2C
  [ ] I2C Scanner encuentra OLED en 0x3C
  [ ] I2C Scanner encuentra MPU en 0x68
  [ ] OLED muestra texto de prueba

ETAPA 7 — ESP32-CAM
  [ ] ESP32-CAM conecta al WiFi (ver IP en Serial Monitor)
  [ ] Captura foto y la envía al servidor
  [ ] Arduino recibe respuesta del servidor ("plastico" o "vidrio")

ETAPA 8 — Integración
  [ ] Robot recibe llamada desde la app → se mueve
  [ ] Usuario deposita residuo → ESP32 captura → IA clasifica → servo correcto abre
  [ ] Posición del robot se actualiza en el mapa de la app
```

---

## Notas rápidas de seguridad

```
🔴 NUNCA conectes el ESP32-CAM con el Arduino a 3.3V desde TX sin el divisor
🔴 NUNCA alimentes los servos directamente del pin 5V del Arduino Mega
🔴 NUNCA conectes la LiPo sin verificar la polaridad primero (rojo=+, negro=-)
🟡 Siempre ajusta el LM2596 ANTES de conectar el ESP32
🟡 Si algo huele raro o se calienta → desconecta de inmediato
🟢 Usa el Power Bank para la electrónica (más estable que la LiPo)
🟢 Conecta el GND común primero, siempre
```

---

*Documento generado para el proyecto RECI · PUCE Sede Manabí · PAO 2026-01*
