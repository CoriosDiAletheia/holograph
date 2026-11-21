"""Rellena una plantilla con "letra a mano" falsa (fuentes del sistema) para probar
el flujo completo sin tener que escribir en una tableta.

    python simular.py plantilla.pdf -o escrito_simulado.pdf

Además re-escala y desplaza ligeramente cada página, como podría ocurrir
al exportar desde la tableta, para comprobar que las marcas de registro funcionan.
"""
from __future__ import annotations

import argparse
import json
import random

import pymupdf

import comun as C


def _fonts():
    out = []
    for i, p in enumerate(C.font_paths(C.HAND_FONTS + C.LABEL_FONTS)):
        try:
            out.append((f"S{i}", p, pymupdf.Font(fontfile=p)))
        except Exception:
            pass
    if not out:
        out.append(("helv", None, pymupdf.Font("helv")))
    return out


def simulate(pdf_in, pdf_out, vacias=0.05, seed=7):
    rnd = random.Random(seed)
    src = pymupdf.open(pdf_in)
    layout = json.loads(src.embfile_get("layout.json"))
    fonts = _fonts()

    for page, pl in zip(src, layout["pages"]):
        for n, p, _ in fonts:
            if p:
                page.insert_font(fontname=n, fontfile=p)
        for cell in pl["cells"]:
            if rnd.random() < vacias:
                continue
            ch = cell["char"]
            cand = [x for x in fonts if x[2].has_glyph(ord(ch))]
            if not cand:
                continue
            name, _, f = cand[0]
            unit = cell["base_y"] - cell["xh_y"]
            size = unit * 2.0 * rnd.uniform(0.9, 1.1)
            x0, _, x1, _ = cell["write"]
            w = f.text_length(ch, fontsize=size)
            x = (x0 + x1) / 2 - w / 2 + rnd.uniform(-6, 6)
            y = cell["base_y"] + rnd.uniform(-1.2, 1.2)
            m = pymupdf.Matrix(rnd.uniform(-4, 4))
            page.insert_text((x, y), ch, fontsize=size, fontname=name, color=(0, 0, 0),
                             morph=(pymupdf.Point(x, y), m))

    # simular una exportación con otra escala y un pequeño desplazamiento
    out = pymupdf.open()
    for i in range(len(src)):
        W, H = C.PAGE_W * 1.12, C.PAGE_H * 1.12
        p = out.new_page(width=W, height=H)
        p.show_pdf_page(pymupdf.Rect(4, 7, W - 3, H - 2), src, i)
    # la tableta podría no conservar los archivos incrustados: no los copiamos
    out.save(pdf_out)
    return pdf_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="escrito_simulado.pdf")
    ap.add_argument("--vacias", type=float, default=0.05, help="fracción de casillas sin escribir")
    a = ap.parse_args()
    simulate(a.pdf, a.out, a.vacias)
    print(f"OK: {a.out}")


if __name__ == "__main__":
    main()
