"""Reci · cámara de la compu en lugar de la ESP32-CAM.

Hace el mismo trabajo que firmware/esp32-cam/ReciEsp32Cam.ino, pero desde la
compu: toma las fotos con la webcam, las clasifica en Reci Cloud y le manda
las órdenes al Arduino Mega por el cable USB (las mismas órdenes compactas
@A, @P, @V, @Q:... que el Mega ya entiende).

La foto se toma sola cuando el Mega avisa "BOTELLA: detectada" (el
ultrasónico interno vio un objeto quieto en el hueco).

También atiende las llamadas de la app: consulta /api/robot/calls/next cada
3 s, manda P1/P2 al Mega y, cuando el Mega avisa que llegó, marca la llamada
como resuelta y saluda a la persona en la LCD. El primer reciclaje en los
2 minutos siguientes se acredita a quien llamó.

Teclas (con la ventana de la cámara activa):
  C o ESPACIO  clasificar a mano (respaldo si el sensor no detecta)
  Q o ESC      salir
"""

import csv
import glob
import os
import queue
import threading
import time
from pathlib import Path

import cv2
import requests
import serial

AQUI = Path(__file__).resolve().parent
# Cada lectura queda registrada aquí para las métricas del informe técnico.
METRICAS_CSV = AQUI / "metricas.csv"
COLUMNAS_METRICAS = ["fecha", "foto1", "foto2", "foto3", "resultado", "confianza",
                     "latencia_fotos_ms", "latencia_total_ms", "compuerta_confirmada"]

MEGA_BAUD = 9600
# Al abrir el puerto USB el Mega se reinicia; esperamos a que termine el setup().
MEGA_ARRANQUE_S = 4.0
INTERVALO_LLAMADAS_S = 3.0
FOTOS_POR_LECTURA = 3
VOTOS_PARA_DECIDIR = 2
SEPARACION_FOTOS_S = 0.35
ESPERA_COMPUERTA_S = 3.0
# Una llamada recién atendida acredita el primer reciclaje a esa persona.
CONTEXTO_LLAMADA_S = 120.0
TIMEOUT_VISION_S = 60
TIMEOUT_HTTP_S = 15

RUTAS_DEMO = {"base": "BASE", "p1": "P1", "parada 1": "P1", "p2": "P2", "parada 2": "P2"}


def cargar_env():
    """Lee camara-pc/.env sin depender de python-dotenv."""
    ruta = AQUI / ".env"
    if not ruta.exists():
        raise SystemExit("Falta camara-pc/.env: copia .env.example como .env y complétalo.")
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())


def detectar_puerto_mega():
    candidatos = sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/cu.usbserial*")
                        + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*"))
    if not candidatos:
        raise SystemExit("No encuentro el Arduino Mega. Conéctalo por USB o define RECI_PUERTO_MEGA.")
    return candidatos[0]


class Mega:
    """Cable USB con el Mega: escribe órdenes y reparte las líneas que imprime."""

    def __init__(self, puerto):
        self._serial = serial.Serial(puerto, MEGA_BAUD, timeout=0.2)
        self._lock = threading.Lock()
        self._oyentes = []
        print(f"MEGA: conectado en {puerto}; esperando que arranque...")
        time.sleep(MEGA_ARRANQUE_S)
        threading.Thread(target=self._leer, daemon=True).start()

    def enviar(self, orden):
        with self._lock:
            self._serial.write((orden + "\n").encode("ascii", errors="ignore"))
        print(f"MEGA <- {orden}")

    def escuchar(self):
        """Devuelve una cola que recibe cada línea nueva del Mega."""
        cola = queue.Queue()
        self._oyentes.append(cola)
        return cola

    def dejar_de_escuchar(self, cola):
        self._oyentes.remove(cola)

    def _leer(self):
        while True:
            linea = self._serial.readline().decode("utf-8", errors="ignore").strip()
            if not linea:
                continue
            print(f"MEGA -> {linea}")
            for cola in list(self._oyentes):
                cola.put(linea)


class ReciCloud:
    def __init__(self, base_url, api_key):
        self._base = base_url.rstrip("/")
        self._sesion = requests.Session()
        self._sesion.headers["Authorization"] = f"Bearer {api_key}"

    def clasificar(self, jpg):
        # record_event=false: las 3 fotos son un solo depósito; se registra
        # una sola vez después de la votación.
        respuesta = self._sesion.post(
            f"{self._base}/api/vision/classify",
            files={"image": ("residuo.jpg", jpg, "image/jpeg")},
            data={"record_event": "false"},
            timeout=TIMEOUT_VISION_S,
        )
        respuesta.raise_for_status()
        return respuesta.json()

    def registrar_reciclaje(self, material, confianza, contexto_llamada):
        cuerpo = {"material": material, "confidence": round(confianza, 3), **contexto_llamada}
        respuesta = self._sesion.post(f"{self._base}/api/events/recycle", json=cuerpo,
                                      timeout=TIMEOUT_HTTP_S)
        respuesta.raise_for_status()
        return respuesta.json().get("event", {}).get("claim_code") or ""

    def siguiente_llamada(self):
        respuesta = self._sesion.get(f"{self._base}/api/robot/calls/next", timeout=TIMEOUT_HTTP_S)
        respuesta.raise_for_status()
        return respuesta.json().get("call")

    def actualizar_llamada(self, call_id, estado):
        self._post_robot("/api/robot/calls/update", {"call_id": call_id, "status": estado})

    def reportar_posicion(self, cuerpo):
        self._post_robot("/api/robot/position", cuerpo)

    def _post_robot(self, ruta, cuerpo):
        try:
            respuesta = self._sesion.post(f"{self._base}{ruta}", json=cuerpo, timeout=TIMEOUT_HTTP_S)
            print(f"CLOUD: {ruta} -> {respuesta.status_code}")
        except requests.RequestException as error:
            print(f"CLOUD: {ruta} falló: {error}")


class Reci:
    def __init__(self, mega, cloud, camara):
        self.mega = mega
        self.cloud = cloud
        self.camara = camara
        self._lock_camara = threading.Lock()
        self._clasificando = threading.Lock()
        self._ultimo_cuadro = None

        self.llamada_activa = None
        self.contexto_reciclaje = {}
        self.contexto_expira_en = 0.0

    # ---------------- cámara ----------------

    def leer_cuadro(self):
        with self._lock_camara:
            ok, cuadro = self.camara.read()
        if ok:
            self._ultimo_cuadro = cuadro
        return cuadro if ok else None

    def foto_jpg(self):
        cuadro = self.leer_cuadro()
        if cuadro is None:
            return None
        ok, jpg = cv2.imencode(".jpg", cuadro, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return jpg.tobytes() if ok else None

    # ---------------- clasificación ----------------

    def clasificar_en_segundo_plano(self):
        if self._clasificando.locked():
            print("RECI: ya hay una lectura en curso.")
            return
        threading.Thread(target=self._clasificar, daemon=True).start()

    def _clasificar(self):
        with self._clasificando:
            print(f"--- CLASIFICANDO RESIDUO: {FOTOS_POR_LECTURA} fotos ---")
            inicio = time.monotonic()
            self.mega.enviar("@A")
            votos = {"plastico": [], "vidrio": []}
            por_foto = []
            latencias_ms = []
            for numero in range(1, FOTOS_POR_LECTURA + 1):
                jpg = self.foto_jpg()
                if jpg is None:
                    print(f"ERROR: no se pudo capturar la foto {numero}")
                    por_foto.append("sin_foto")
                    continue
                inicio_foto = time.monotonic()
                try:
                    resultado = self.cloud.clasificar(jpg)
                except requests.RequestException as error:
                    print(f"ERROR: foto {numero} /vision/classify: {error}")
                    por_foto.append("error")
                    continue
                latencias_ms.append((time.monotonic() - inicio_foto) * 1000)
                material = resultado.get("material", "desconocido")
                confianza = float(resultado.get("confidence") or 0.0)
                print(f"foto {numero}: {material} ({confianza:.2f})")
                por_foto.append(material)
                if material in votos:
                    votos[material].append(confianza)
                time.sleep(SEPARACION_FOTOS_S)

            material = next((m for m, v in votos.items() if len(v) >= VOTOS_PARA_DECIDIR), None)
            if material is None:
                print("Resultado final: desconocido")
                self.mega.enviar("@U")
                self._guardar_metrica(por_foto, "desconocido", 0.0, latencias_ms, inicio, False)
                return

            confianza = sum(votos[material]) / len(votos[material])
            print(f"Resultado final: {material} ({confianza:.2f})")
            confirmada = self._abrir_compuerta(material)
            self._guardar_metrica(por_foto, material, confianza, latencias_ms, inicio, confirmada)
            if not confirmada:
                print("ERROR: el Mega no confirmó la compuerta; no se registran puntos.")
                return
            self._registrar(material, confianza)

    def _guardar_metrica(self, por_foto, material, confianza, latencias_ms, inicio, confirmada):
        total_ms = (time.monotonic() - inicio) * 1000
        promedio_ms = sum(latencias_ms) / len(latencias_ms) if latencias_ms else 0
        nuevo = not METRICAS_CSV.exists()
        with METRICAS_CSV.open("a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if nuevo:
                escritor.writerow(COLUMNAS_METRICAS)
            fotos = (por_foto + ["", "", ""])[:3]
            escritor.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), *fotos, material,
                               f"{confianza:.3f}", f"{promedio_ms:.0f}", f"{total_ms:.0f}",
                               "si" if confirmada else "no"])
        print(f"METRICAS: {material} en {total_ms / 1000:.1f} s (guardado en metricas.csv)")

    def _abrir_compuerta(self, material):
        """Manda @P/@V y espera a que el Mega confirme que movió el servo."""
        cola = self.mega.escuchar()
        try:
            self.mega.enviar("@V" if material == "vidrio" else "@P")
            limite = time.monotonic() + ESPERA_COMPUERTA_S
            while time.monotonic() < limite:
                try:
                    linea = cola.get(timeout=0.2)
                except queue.Empty:
                    continue
                if f"COMPUERTA: {material}" in linea:
                    return True
                if "No abro compuerta" in linea or "ya esta abierta" in linea:
                    return False
            return False
        finally:
            self.mega.dejar_de_escuchar(cola)

    def _registrar(self, material, confianza):
        contexto = self.contexto_reciclaje if time.monotonic() < self.contexto_expira_en else {}
        try:
            codigo = self.cloud.registrar_reciclaje(material, confianza, contexto)
        except requests.RequestException as error:
            print(f"ERROR: /events/recycle: {error}")
            return
        # El contexto de la llamada se usa una sola vez.
        self.contexto_reciclaje = {}
        if codigo:
            print(f"RECYCLE: claim_code {codigo} -> QR en la OLED")
            self.mega.enviar(f"@Q:{codigo}")
        elif contexto:
            self.mega.enviar("@L")
        else:
            self.mega.enviar("@O")

    # ---------------- llamadas desde la app ----------------

    def atender_llamadas(self):
        self.cloud.reportar_posicion({"point_name": "Base", "status": "idle"})
        while True:
            time.sleep(INTERVALO_LLAMADAS_S)
            if self.llamada_activa is not None:
                continue
            try:
                llamada = self.cloud.siguiente_llamada()
            except requests.RequestException as error:
                print(f"CALLS: /next falló: {error}")
                continue
            if not llamada or llamada.get("status") != "pending":
                continue
            ruta = RUTAS_DEMO.get(str(llamada.get("point_name", "")).strip().lower())
            if ruta is None:
                print(f"CALLS: el punto {llamada.get('point_name')} no tiene ruta demo.")
                continue

            self.llamada_activa = {**llamada, "ruta": ruta}
            self.mega.enviar(ruta)
            self.cloud.actualizar_llamada(llamada["id"], "in_progress")
            self.cloud.reportar_posicion({"point_id": llamada["point_id"], "status": "moving"})
            print(f"CALLS: Reci va a {ruta}; saludará a {llamada.get('greeting_name')}")

    def vigilar_mega(self):
        cola = self.mega.escuchar()
        while True:
            linea = cola.get()
            llamada = self.llamada_activa
            if llamada and f"Llegada estimada: {llamada['ruta']}" in linea:
                self._llegada(llamada)
            elif "BOTELLA: detectada" in linea:
                self.clasificar_en_segundo_plano()

    def _llegada(self, llamada):
        self.cloud.actualizar_llamada(llamada["id"], "resolved")
        self.cloud.reportar_posicion({"point_id": llamada["point_id"], "status": "idle"})
        nombre = llamada.get("greeting_name") or "reciclador"
        self.mega.enviar(f"@G:{nombre}")
        self.contexto_reciclaje = {"call_id": llamada["id"], "robot_point_id": llamada["point_id"]}
        self.contexto_expira_en = time.monotonic() + CONTEXTO_LLAMADA_S
        self.llamada_activa = None


def main():
    cargar_env()
    base_url = os.environ.get("RECI_API_BASE_URL", "")
    api_key = os.environ.get("RECI_ROBOT_API_KEY", "")
    if not base_url or not api_key or "PEGA_AQUI" in api_key:
        raise SystemExit("Completa RECI_API_BASE_URL y RECI_ROBOT_API_KEY en camara-pc/.env.")

    camara = cv2.VideoCapture(int(os.environ.get("RECI_CAMARA", "0")))
    if not camara.isOpened():
        raise SystemExit("No se pudo abrir la cámara. Prueba RECI_CAMARA=1 en .env.")
    camara.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camara.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    mega = Mega(os.environ.get("RECI_PUERTO_MEGA") or detectar_puerto_mega())
    reci = Reci(mega, ReciCloud(base_url, api_key), camara)
    threading.Thread(target=reci.vigilar_mega, daemon=True).start()
    threading.Thread(target=reci.atender_llamadas, daemon=True).start()
    mega.enviar("@R")

    print("Listo. C o ESPACIO = clasificar · Q o ESC = salir")
    try:
        while True:
            cuadro = reci.leer_cuadro()
            if cuadro is not None:
                cv2.imshow("Reci · camara", cuadro)
            tecla = cv2.waitKey(30) & 0xFF
            if tecla in (ord("c"), ord("C"), ord(" ")):
                reci.clasificar_en_segundo_plano()
            elif tecla in (ord("q"), ord("Q"), 27):
                break
    finally:
        camara.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
