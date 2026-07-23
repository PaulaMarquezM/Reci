#!/usr/bin/env python3
"""Genera docs/diagramas/arquitectura_reci.png — diagrama de arquitectura RECI."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "diagramas" / "arquitectura_reci.png"

W, H = 1200, 2100
MARGIN = 60

COLORS = {
    "bg": "#FAFBFC",
    "title": "#0D47A1",
    "subtitle": "#546E7A",
    "box_default": ("#FFFFFF", "#37474F", "#263238"),
    "box_camera": ("#E3F2FD", "#1565C0", "#0D47A1"),
    "box_model": ("#FFF3E0", "#EF6C00", "#E65100"),
    "box_api": ("#F3E5F5", "#7B1FA2", "#4A148C"),
    "box_fallback": ("#FFF8E1", "#F9A825", "#F57F17"),
    "box_se": ("#E8F5E9", "#2E7D32", "#1B5E20"),
    "box_vidrio": ("#E3F2FD", "#1565C0", "#0D47A1"),
    "box_plastico": ("#E8F5E9", "#2E7D32", "#1B5E20"),
    "box_rechazo": ("#FFEBEE", "#C62828", "#B71C1C"),
    "arrow": "#78909C",
    "decision": ("#ECEFF1", "#455A64", "#263238"),
}


def load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def text_size(draw, text, font):
    bbox = draw.multiline_textbbox((0, 0), text, font=font, align="center")
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def rounded_box(draw, xy, text, font, style="box_default", radius=16):
    x1, y1, x2, y2 = xy
    fill, border, text_color = COLORS[style]
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=border, width=2)
    tw, th = text_size(draw, text, font)
    tx = x1 + (x2 - x1 - tw) / 2
    ty = y1 + (y2 - y1 - th) / 2
    draw.multiline_text((tx, ty), text, fill=text_color, font=font, align="center")


def diamond(draw, cx, cy, w, h, text, font):
    fill, border, text_color = COLORS["decision"]
    points = [(cx, cy - h // 2), (cx + w // 2, cy), (cx, cy + h // 2), (cx - w // 2, cy)]
    draw.polygon(points, fill=fill, outline=border)
    tw, th = text_size(draw, text, font)
    draw.multiline_text((cx - tw / 2, cy - th / 2), text, fill=text_color, font=font, align="center")


def arrow_down(draw, x, y1, y2, label=None, font=None):
    draw.line([(x, y1), (x, y2)], fill=COLORS["arrow"], width=2)
    draw.polygon([(x, y2), (x - 7, y2 - 12), (x + 7, y2 - 12)], fill=COLORS["arrow"])
    if label and font:
        draw.text((x + 12, (y1 + y2) / 2 - 8), label, fill=COLORS["subtitle"], font=font)


def arrow_branch(draw, x_from, y_from, x_to, y_to, label=None, font=None):
    draw.line([(x_from, y_from), (x_to, y_to)], fill=COLORS["arrow"], width=2)
    if y_to > y_from:
        draw.polygon([(x_to, y_to), (x_to - 7, y_to - 12), (x_to + 7, y_to - 12)], fill=COLORS["arrow"])
    else:
        draw.polygon([(x_to, y_to), (x_to - 7, y_to + 12), (x_to + 7, y_to + 12)], fill=COLORS["arrow"])
    if label and font:
        lx = (x_from + x_to) / 2 + 8
        ly = (y_from + y_to) / 2 - 8
        draw.text((lx, ly), label, fill=COLORS["subtitle"], font=font)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (W, H), COLORS["bg"])
    draw = ImageDraw.Draw(img)

    title_font = load_font(34, bold=True)
    subtitle_font = load_font(18)
    box_font = load_font(20)
    small_font = load_font(16)
    label_font = load_font(15)

    draw.text((W / 2, 36), "RECI — Arquitectura del Sistema de IA", fill=COLORS["title"], font=title_font, anchor="ma")
    draw.text((W / 2, 78), "Flujo completo: captura → clasificación → decisión → hardware", fill=COLORS["subtitle"], font=subtitle_font, anchor="ma")

    cx = W // 2
    bw = 520
    bh = 72
    x1 = cx - bw // 2
    y = 120

    steps = [
        ("Usuario deposita objeto frente a RECI", "box_default", 56),
        ("CÁMARA\nCaptura JPG 1280×720 px", "box_camera", 72),
        ("PREPROCESAMIENTO\nRedimensionar 224×224 · Normalizar RGB", "box_default", 72),
        ("MODELO IA — MobileNetV2 (.tflite)\nClasificación binaria: plástico | vidrio · ~0.1 s", "box_model", 88),
    ]

    boxes = []
    for text, style, height in steps:
        box = (x1, y, x1 + bw, y + height)
        rounded_box(draw, box, text, box_font, style=style)
        boxes.append(box)
        y += height + 36

    last_bottom = boxes[-1][3]
    arrow_down(draw, cx, last_bottom, last_bottom + 28)

    # Decision diamond: API available?
    d_y = last_bottom + 28 + 70
    diamond(draw, cx, d_y, 300, 110, "¿API de visión\ndisponible?", box_font)

    # Left branch: API
    api_box = (cx - 280, d_y + 120, cx - 20, d_y + 120 + 88)
    rounded_box(draw, api_box, "API DE VISIÓN\nClaude Haiku / Gemini\n9 atributos visuales · ~2 s", box_font, style="box_api")

    # Right branch: Fallback
    fb_box = (cx + 20, d_y + 120, cx + 280, d_y + 120 + 88)
    rounded_box(draw, fb_box, "FALLBACK\nTM + Heurísticas OpenCV\nSin conexión / cuota agotada", box_font, style="box_fallback")

    arrow_branch(draw, cx - 70, d_y + 55, cx - 150, d_y + 120, "Sí", label_font)
    arrow_branch(draw, cx + 70, d_y + 55, cx + 150, d_y + 120, "No", label_font)

    merge_y = d_y + 120 + 88 + 40
    refine_box = (x1, merge_y, x1 + bw, merge_y + 72)
    rounded_box(draw, refine_box, "REFINAMIENTO OpenCV\nCorrige latas, metal y vidrio mal etiquetados", box_font, style="box_default")

    arrow_branch(draw, (api_box[0] + api_box[2]) // 2, api_box[3], cx, merge_y, font=label_font)
    arrow_branch(draw, (fb_box[0] + fb_box[2]) // 2, fb_box[3], cx, merge_y, font=label_font)

    y = merge_y + 72 + 36
    se_box = (x1, y, x1 + bw, y + 88)
    rounded_box(draw, se_box, "SISTEMA EXPERTO\n193 reglas IF-THEN · 18 meta-reglas · CF MYCIN", box_font, style="box_se")

    arrow_down(draw, cx, se_box[3], se_box[3] + 28)

    dec2_y = se_box[3] + 28 + 70
    diamond(draw, cx, dec2_y, 260, 100, "Decisión\nfinal", box_font)

    row_y = dec2_y + 120
    col_w = 300
    gap = 40
    total_w = col_w * 3 + gap * 2
    start_x = cx - total_w // 2

    outcomes = [
        ("VIDRIO\nCompuerta izquierda\nServo 45° · LED azul\n→ Contenedor vidrio", "box_vidrio"),
        ("PLÁSTICO\nCompuerta derecha\nServo 135° · LED verde\n→ Contenedor plástico", "box_plastico"),
        ("RECHAZO\nCompuerta cerrada\nServo 0° · LED rojo\nMaterial no permitido", "box_rechazo"),
    ]

    outcome_boxes = []
    for i, (text, style) in enumerate(outcomes):
        ox1 = start_x + i * (col_w + gap)
        ob = (ox1, row_y, ox1 + col_w, row_y + 130)
        rounded_box(draw, ob, text, small_font, style=style)
        outcome_boxes.append(ob)
        arrow_branch(draw, cx, dec2_y + 50, ox1 + col_w // 2, row_y, font=label_font)

    legend_y = row_y + 170
    draw.rounded_rectangle((MARGIN, legend_y, W - MARGIN, legend_y + 110), radius=12, fill="#FFFFFF", outline="#CFD8DC", width=1)
    draw.text((MARGIN + 20, legend_y + 16), "Notas:", fill=COLORS["title"], font=load_font(18, bold=True))
    notes = (
        "• El modelo MobileNetV2 corre siempre primero (~0.1 s) y aporta contexto al flujo híbrido.\n"
        "• Si la API falla (404, 429, 503, timeout), el fallback mantiene la operación sin interrupciones.\n"
        "• Solo PLÁSTICO y VIDRIO abren compuerta; lata, orgánico y desconocido se rechazan."
    )
    draw.multiline_text((MARGIN + 20, legend_y + 44), notes, fill=COLORS["subtitle"], font=small_font, spacing=6)

    draw.text((W / 2, H - 28), "Proyecto RECI · PUCE Sede Manabí · 2026", fill="#90A4AE", font=small_font, anchor="ma")

    img.save(OUT, "PNG", optimize=True)
    print(f"Diagrama guardado en: {OUT}")


if __name__ == "__main__":
    main()
