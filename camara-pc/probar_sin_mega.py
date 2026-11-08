"""Reci · probar la clasificación solo con la cámara (sin Arduino Mega).

Toma 3 fotos con la webcam, las clasifica en Reci Cloud y decide con la misma
votación que reci_camara.py. No manda órdenes al Mega, no registra reciclajes
ni suma puntos: solo muestra el resultado.

Cada lectura se guarda en pruebas_sin_mega.csv y las fotos en fotos_prueba/
para revisar los fallos después.

Teclas (con la ventana de la cámara activa):
  C o ESPACIO  clasificar (3 fotos)
  Q o ESC      salir

Uso:
  source .venv/bin/activate && python probar_sin_mega.py
"""

import csv
import os
import threading
import time
from datetime import datetime

import cv2

from reci_camara import (AQUI, FOTOS_POR_LECTURA, FUENTE_LOCAL, FUENTE_PROVEEDOR,
                         SEPARACION_FOTOS_S, ReciCloud, cargar_env, decidir, votos_de_foto)

CSV_PRUEBAS = AQUI / "pruebas_sin_mega.csv"
CARPETA_FOTOS = AQUI / "fotos_prueba"
COLUMNAS = ["fecha", "esperado", "resultado", "confianza", "acierto",
            "proveedor_f1", "proveedor_f2", "proveedor_f3",
            "local_f1", "local_f2", "local_f3",
            "objeto_f1", "objeto_f2", "objeto_f3",
            "regla_f1", "regla_f2", "regla_f3", "segundos"]

# Tecla para marcar qué objeto pusiste antes de clasificar (para medir aciertos).
ESPERADOS = {ord("1"): "plastico", ord("2"): "vidrio", ord("3"): "lata",
             ord("4"): "organico", ord("0"): ""}


class Prueba:
    def __init__(self, cloud, camara):
        self.cloud = cloud
        self.camara = camara
        self.cuadro = None
        self.ocupado = False
        self.esperado = ""
        self.ultimo = "C / ESPACIO = clasificar"

    def leer_cuadro(self):
        ok, cuadro = self.camara.read()
        if ok:
            self.cuadro = cuadro
        return self.cuadro

    def clasificar_en_segundo_plano(self):
        if self.ocupado:
            print("Ya hay una clasificación en curso.")
            return
        self.ocupado = True
        threading.Thread(target=self._clasificar, daemon=True).start()

    def _clasificar(self):
        inicio = time.monotonic()
        sello = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.ultimo = "Clasificando..."
        try:
            fotos, crudos = [], []
            for i in range(FOTOS_POR_LECTURA):
                if i:
                    time.sleep(SEPARACION_FOTOS_S)
                cuadro = self.cuadro
                if cuadro is None:
                    raise RuntimeError("la cámara no entrega imagen")
                ok, jpg = cv2.imencode(".jpg", cuadro, [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ok:
                    raise RuntimeError("no se pudo codificar la foto")
                (CARPETA_FOTOS / f"{sello}_f{i + 1}.jpg").write_bytes(jpg.tobytes())
                resultado = self.cloud.clasificar(jpg.tobytes())
                crudos.append(resultado)
                fotos.append(votos_de_foto(resultado))
                prov = fotos[-1].get(FUENTE_PROVEEDOR, ("-", 0.0))
                loc = fotos[-1].get(FUENTE_LOCAL, ("-", 0.0))
                objeto = (resultado.get("atributos") or {}).get("objeto_reconocido", "-")
                print(f"  foto {i + 1}: proveedor={prov[0]} ({prov[1]:.2f}) · "
                      f"local={loc[0]} ({loc[1]:.2f}) · objeto={objeto} · "
                      f"regla={resultado.get('rule_applied', '-')}")

            material, confianza = decidir(fotos)
            material = material or "desconocido"
            segundos = time.monotonic() - inicio
            acierto = "" if not self.esperado else ("si" if material == self.esperado else "no")
            marca = {"si": "  ✅ ACIERTO", "no": f"  ❌ FALLO (esperado {self.esperado})"}.get(acierto, "")
            print(f"RESULTADO: {material.upper()} ({confianza:.0%}) en {segundos:.1f} s{marca}\n")
            self.ultimo = f"{material.upper()} {confianza:.0%}{' OK' if acierto == 'si' else ' X' if acierto == 'no' else ''}"
            self._guardar(sello, material, confianza, acierto, fotos, crudos, segundos)
        except Exception as error:  # noqa: BLE001 - mostrar cualquier fallo y seguir
            print(f"ERROR: {error}\n")
            self.ultimo = "Error (ver terminal)"
        finally:
            self.ocupado = False

    def _guardar(self, sello, material, confianza, acierto, fotos, crudos, segundos):
        def col(fuente):
            return [f"{f.get(fuente, ('-', 0))[0]}:{f.get(fuente, ('-', 0))[1]:.2f}" for f in fotos]
        nuevo = not CSV_PRUEBAS.exists()
        with CSV_PRUEBAS.open("a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if nuevo:
                escritor.writerow(COLUMNAS)
            escritor.writerow([sello, self.esperado, material, f"{confianza:.3f}", acierto,
                               *col(FUENTE_PROVEEDOR), *col(FUENTE_LOCAL),
                               *[(c.get("atributos") or {}).get("objeto_reconocido", "") for c in crudos],
                               *[c.get("rule_applied", "") for c in crudos],
                               f"{segundos:.1f}"])


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
    CARPETA_FOTOS.mkdir(exist_ok=True)

    prueba = Prueba(ReciCloud(base_url, api_key), camara)
    print("Listo (sin Mega). Marca lo que pones: 1=plástico 2=vidrio 3=lata 4=orgánico 0=nada")
    print("C o ESPACIO = clasificar · Q o ESC = salir\n")
    try:
        while True:
            cuadro = prueba.leer_cuadro()
            if cuadro is not None:
                vista = cuadro.copy()
                texto = f"Esperado: {prueba.esperado or '-'} | {prueba.ultimo}"
                cv2.putText(vista, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
                cv2.putText(vista, texto, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Reci · prueba sin Mega", vista)
            tecla = cv2.waitKey(30) & 0xFF
            if tecla in ESPERADOS:
                prueba.esperado = ESPERADOS[tecla]
                print(f"Esperado: {prueba.esperado or '(sin marcar)'}")
            elif tecla in (ord("c"), ord("C"), ord(" ")):
                prueba.clasificar_en_segundo_plano()
            elif tecla in (ord("q"), ord("Q"), 27):
                break
    finally:
        camara.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
