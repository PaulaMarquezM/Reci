"""Métricas de evaluación. La principal es macro-F1.

La exactitud global esconde una clase débil: en este proyecto el recall de
plástico fue 60,60 % mientras la exactitud parecía aceptable. Por eso la
selección de modelo y la parada temprana usan macro-F1, no `accuracy`.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from constantes import CLASES


def matriz_confusion(real: np.ndarray, predicho: np.ndarray) -> np.ndarray:
    matriz = np.zeros((len(CLASES), len(CLASES)), dtype=int)
    for r, p in zip(real, predicho):
        matriz[r][p] += 1
    return matriz


def por_clase(matriz: np.ndarray) -> tuple[dict, list[float], list[float]]:
    """Precisión, recall y F1 por clase a partir de la matriz de confusión."""
    resultado, f1s, recalls = {}, [], []
    for i, clase in enumerate(CLASES):
        vp = int(matriz[i][i])
        fp = int(matriz[:, i].sum() - vp)
        fn = int(matriz[i].sum() - vp)
        precision = vp / (vp + fp) if vp + fp else 0.0
        recall = vp / (vp + fn) if vp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        resultado[clase] = {"precision": precision, "recall": recall, "f1": f1,
                            "soporte": int(matriz[i].sum())}
        f1s.append(f1)
        recalls.append(recall)
    return resultado, f1s, recalls


def callback_macro_f1(keras, ds, muestras):
    """Publica `val_macro_f1` en los logs para que lo lean los demás callbacks.

    Keras ejecuta los callbacks en orden, así que este debe ir primero en la
    lista: EarlyStopping y ModelCheckpoint leen la métrica que deja aquí.
    """
    real = np.array([e for _, e in muestras])

    class MacroF1(keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs=None):
            if logs is None:
                return
            predicho = self.model.predict(ds, verbose=0).argmax(axis=1)
            _, f1s, _ = por_clase(matriz_confusion(real, predicho))
            logs["val_macro_f1"] = float(np.mean(f1s))
            print(f"    val_macro_f1: {logs['val_macro_f1']:.4f}")

    return MacroF1()


def evaluar(modelo, ds, muestras) -> dict:
    """Matriz de confusión y métricas por clase; macro-F1 como principal."""
    if not muestras:
        return {}

    probabilidades = modelo.predict(ds, verbose=0)
    predicho = probabilidades.argmax(axis=1)
    real = np.array([e for _, e in muestras])

    matriz = matriz_confusion(real, predicho)
    metricas, f1s, recalls = por_clase(matriz)

    confianzas = probabilidades.max(axis=1)
    errores_confiados = int(((predicho != real) & (confianzas >= 0.9)).sum())

    return {
        "matriz_confusion": matriz.tolist(),
        "metricas_por_clase": metricas,
        "macro_f1": float(np.mean(f1s)),
        "exactitud_balanceada": float(np.mean(recalls)),
        "exactitud": float((predicho == real).mean()),
        "errores_confianza_alta": errores_confiados,
        "total": len(muestras),
    }


def imprimir(titulo: str, m: dict) -> None:
    if not m:
        print(f"\n  {titulo}: sin datos (partición vacía)")
        return
    print(f"\n  {titulo} — {m['total']} imágenes")
    print(f"    macro-F1              {m['macro_f1']:.4f}   <- métrica principal")
    print(f"    exactitud balanceada  {m['exactitud_balanceada']:.4f}")
    print(f"    exactitud global      {m['exactitud']:.4f}")
    print(f"    errores con confianza >= 0.9: {m['errores_confianza_alta']}")
    for clase, v in m["metricas_por_clase"].items():
        print(f"    {clase:10s} precision {v['precision']:.4f}  "
              f"recall {v['recall']:.4f}  f1 {v['f1']:.4f}  (n={v['soporte']})")
    print(f"    matriz de confusión (filas=real {CLASES}): {m['matriz_confusion']}")
def guardar_reporte(salida: Path, prefijo: str, metricas: dict) -> None:
    """Guarda el reporte tabular y la figura de la matriz de confusión."""
    with (salida / f"{prefijo}_reporte.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["clase", "precision", "recall", "f1", "soporte"])
        for clase, valores in metricas.get("metricas_por_clase", {}).items():
            escritor.writerow([clase, valores["precision"], valores["recall"], valores["f1"], valores["soporte"]])
        escritor.writerow(["macro", "", "", metricas.get("macro_f1"), metricas.get("total")])
    import matplotlib.pyplot as plt
    matriz = np.asarray(metricas["matriz_confusion"])
    fig, eje = plt.subplots(figsize=(4.5, 4))
    imagen = eje.imshow(matriz, cmap="Blues")
    fig.colorbar(imagen, ax=eje)
    eje.set(xticks=range(len(CLASES)), yticks=range(len(CLASES)), xticklabels=CLASES,
            yticklabels=CLASES, xlabel="Predicha", ylabel="Real", title=f"Matriz - {prefijo}")
    for fila in range(len(CLASES)):
        for columna in range(len(CLASES)):
            eje.text(columna, fila, int(matriz[fila, columna]), ha="center", va="center")
    fig.tight_layout()
    fig.savefig(salida / f"{prefijo}_matriz_confusion.png", dpi=160)
    fig.savefig(salida / f"{prefijo}_matriz_confusion.pdf")
    plt.close(fig)
