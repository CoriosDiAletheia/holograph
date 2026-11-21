"""Genera el PDF-plantilla para escribir en la Kindle Scribe.

Uso:
    python plantilla.py                       # conjunto por defecto (completo)
    python plantilla.py --sets latin:50       # 50 muestras de cada letra latina
    python plantilla.py --sets "digitos:20,extra=€£¥:10" -o numeros.pdf

Conjuntos: los de comun.CHARSETS, los grupos latin / griego / matematicas,
o extra=CARACTERES. Formato: nombre:muestras,nombre:muestras,...

La plantilla queda registrada en la carpeta plantillas/, así que después
basta con el PDF escrito para extraer la letra.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
from pathlib import Path

import pymupdf

import comun as C

GUIDE_GRAY = (0.80, 0.80, 0.80)
BORDER_GRAY = (0.70, 0.70, 0.70)
LABEL_GRAY = (0.35, 0.35, 0.35)


def _fonts():
    """Fuentes para etiquetas: se elige la primera que tenga el glifo."""
    out = []
    for i, p in enumerate(C.font_paths(C.LABEL_FONTS)):
        try:
            out.append((f"F{i}", p, pymupdf.Font(fontfile=p)))
        except Exception:      # fuente ilegible: se ignora
            pass
    return out


def _font_for(ch, fonts):
    for name, path, f in fonts:
        if f.has_glyph(ord(ch)):
            return name, path
    return "helv", None


def save_layout(layout, out_pdf: Path | None = None):
    """Guarda la disposición en el registro (y junto al PDF si se indica)."""
    js = json.dumps(layout, ensure_ascii=False, indent=1)
    os.makedirs(C.REGISTRY_DIR, exist_ok=True)
    reg = Path(C.REGISTRY_DIR) / f"{layout['session']}.json"
    reg.write_text(js, encoding="utf-8")
    return reg


def build(items, out_pdf: Path, title="Mi letra", spec=""):
    session = secrets.token_hex(3)          # 24 bits
    slots = [(ch, i) for ch, n in items for i in range(n)]
    n_pages = (len(slots) + C.CELLS_PER_PAGE - 1) // C.CELLS_PER_PAGE
    if n_pages >= 2 ** C.PAGE_BITS - 1:
        raise SystemExit("Demasiadas páginas para el código de página.")

    fonts = _fonts()
    doc = pymupdf.open()
    layout = {"version": 2, "session": session, "spec": spec, "title": title,
              "page_size": [C.PAGE_W, C.PAGE_H], "pages": []}

    for p in range(n_pages):
        page = doc.new_page(width=C.PAGE_W, height=C.PAGE_H)
        registered = set()

        def text(pt, s, size, color, ch_for_font=None):
            name, path = _font_for(ch_for_font or s[0], fonts)
            if path and name not in registered:
                page.insert_font(fontname=name, fontfile=path)
                registered.add(name)
            page.insert_text(pt, s, fontsize=size, fontname=name, color=color)

        # Marcas de registro
        for cx, cy in C.FID_CENTERS:
            h = C.FID_SIZE / 2
            page.draw_rect(pymupdf.Rect(cx - h, cy - h, cx + h, cy + h), color=None, fill=(0, 0, 0))

        # Código de página + id de plantilla + paridad
        for (cx, cy), bit in zip(C.code_centers(), C.encode_code(p, session)):
            h = C.CODE_SIZE / 2
            r = pymupdf.Rect(cx - h, cy - h, cx + h, cy + h)
            if bit:
                page.draw_rect(r, color=None, fill=(0, 0, 0))
            else:
                page.draw_rect(r, color=GUIDE_GRAY, width=0.4)

        # Encabezado
        text((C.MARGIN + C.FID_SIZE + 8, C.MARGIN + 10),
             f"{title} · plantilla {session} · página {p + 1}/{n_pages}", 8, LABEL_GRAY, "a")
        text((C.MARGIN + C.FID_SIZE + 8, C.MARGIN + 21),
             "Un carácter por casilla, apoyado en la línea continua. No escribas sobre los cuadros negros.",
             6.3, LABEL_GRAY, "a")

        cells = []
        for slot, (ch, idx) in enumerate(slots[p * C.CELLS_PER_PAGE:(p + 1) * C.CELLS_PER_PAGE]):
            g = C.cell_geometry(slot)
            x0, y0, x1, y1 = g["cell"]
            page.draw_rect(pymupdf.Rect(x0, y0, x1, y1), color=BORDER_GRAY, width=0.6)
            page.draw_line((x0, y0 + C.LABEL_H), (x1, y0 + C.LABEL_H), color=GUIDE_GRAY, width=0.4)
            page.draw_line((x0 + 3, g["asc_y"]), (x1 - 3, g["asc_y"]), color=GUIDE_GRAY, width=0.4, dashes="[0.6 2] 0")
            page.draw_line((x0 + 3, g["xh_y"]), (x1 - 3, g["xh_y"]), color=GUIDE_GRAY, width=0.5, dashes="[3 2] 0")
            page.draw_line((x0 + 3, g["base_y"]), (x1 - 3, g["base_y"]), color=GUIDE_GRAY, width=0.8)
            text((x0 + 3, y0 + 9.5), ch, 9.5, LABEL_GRAY, ch)
            text((x1 - 14, y0 + 8.5), f"{idx + 1}", 5, GUIDE_GRAY, "1")
            cells.append({"slot": slot, "char": ch, "idx": idx, **g})
        layout["pages"].append({"index": p, "cells": cells})

    layout_json = json.dumps(layout, ensure_ascii=False)
    doc.embfile_add("layout.json", layout_json.encode("utf-8"), filename="layout.json")
    doc.set_metadata({"title": f"{title} ({session})", "subject": "plantilla mi-letra"})
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out_pdf, garbage=3, deflate=True)
    reg = save_layout(layout)
    return n_pages, len(slots), reg


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sets", default=C.DEFAULT_SETS)
    ap.add_argument("-o", "--out", default="plantilla.pdf")
    ap.add_argument("--titulo", default="Mi letra")
    a = ap.parse_args()
    items = C.parse_sets(a.sets)
    pages, cells, reg = build(items, Path(a.out), a.titulo, a.sets)
    print(f"OK: {a.out} -> {pages} páginas, {cells} casillas, {len(items)} caracteres distintos")
    print(f"    registrada en {reg}")


if __name__ == "__main__":
    main()
