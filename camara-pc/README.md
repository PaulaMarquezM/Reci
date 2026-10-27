# Reci · cámara de la compu

Reemplaza a la ESP32-CAM: la webcam de la compu toma las fotos, Reci Cloud las
clasifica y la compu le manda las órdenes al Arduino Mega por el **cable USB**.
También atiende las llamadas de la app (P1 / P2) igual que hacía la ESP32.

```
webcam ──> compu (reci_camara.py) ──USB──> Arduino Mega ──> servo, motores, OLED, LCD
                  │
                  └──WiFi──> Reci Cloud (clasificación, llamadas, puntos)
```

## Preparar (una sola vez)

```bash
cd camara-pc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # y completa RECI_ROBOT_API_KEY
```

En el Mega debe estar cargado `ReciRutaDemo.ino` con
`kEsp32CamConectada = false`.

## Usar

1. Conecta el Mega a la compu por USB. **Cierra el Monitor Serial del Arduino
   IDE**: el puerto solo lo puede usar un programa a la vez.
2. `source .venv/bin/activate && python reci_camara.py`
3. La primera vez la Mac pide permiso de cámara para la Terminal: acéptalo.
4. Con la ventana de la cámara activa:
   - **C** o **ESPACIO**: clasificar (3 fotos; con 2 iguales gira el servo).
   - **Q** o **ESC**: salir.

Cuando el PIR detecta a alguien, o cuando Reci llega a un punto llamado desde
la app, la captura se hace sola a los 5 segundos.
