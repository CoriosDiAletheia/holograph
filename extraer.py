"""Lee el PDF ya escrito en la Kindle Scribe y extrae cada carácter.

Uso:
    python extraer.py escrito.pdf                      # basta con el PDF
    python extraer.py parte1.pdf parte2.pdf            # varias plantillas se combinan
    python extraer.py escrito.pdf --layout x.json      # solo si la plantilla se hizo en otro equipo

Cada página trae impreso (cuadritos de abajo) el id de su plantilla y su
número de página; la disposición se busca en la carpeta plantillas/.

Resultado (carpeta de salida):
    glifos.json        índice de todos los glifos y sus medidas
    glifos/*.png       un PNG en escala de grises por muestra (blanco = tinta)
    revision.png       hoja de contacto para revisar; si una muestra salió mal,
                       borra su PNG y ya no se usará.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

import comun as C

DPI = 300
INK_LIGHT, INK_DARK = 175.0, 70.0   # gris > 175 no es tinta, < 70 es tinta plena
MIN_INK_PX = 25


# ------------------------------------------------------------ utilidades de imagen
def render_gray(page, dpi, annots=True):
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False, annots=annots)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w).astype(np.float32)


def ink_alpha(page, dpi):
    """Devuelve (alpha de tinta 0..1, imagen gris completa).

    Si la Kindle guardó los trazos como anotaciones, se resta la página sin
    anotaciones (aísla la tinta perfectamente, sea del color que sea). Si los
    trazos vienen aplanados en el contenido, se usa un umbral de oscuridad.
    """
    with_ann = render_gray(page, dpi, annots=True)
    if page.first_annot is not None:
        base = render_gray(page, dpi, annots=False)
        alpha = np.clip((base - with_ann) / 120.0, 0, 1)
        if alpha.max() > 0.3:
            return alpha, with_ann
    alpha = np.clip((INK_LIGHT - with_ann) / (INK_LIGHT - INK_DARK), 0, 1)
    return alpha, with_ann


def fit_affine(src_pts, dst_pts):
    src = np.array(src_pts, float)
    dst = np.array(dst_pts, float)
    A = np.hstack([src, np.ones((len(src), 1))])
    M, *_ = np.linalg.lstsq(A, dst, rcond=None)      # 3x2
    return lambda x, y: tuple(np.array([x, y, 1.0]) @ M)


def _components(mask):
    """Etiquetado de componentes 4-conexas (BFS sencillo, la máscara es pequeña)."""
    h, w = mask.shape
    labels = np.zeros((h, w), np.int32)
    comps, cur = [], 0
    for sy, sx in zip(*np.nonzero(mask)):
        if labels[sy, sx]:
            continue
        cur += 1
        stack, pts = [(sy, sx)], []
        labels[sy, sx] = cur
        while stack:
            y, x = stack.pop()
            pts.append((y, x))
            for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not labels[ny, nx]:
                    labels[ny, nx] = cur
                    stack.append((ny, nx))
        comps.append(np.array(pts))
    return comps


def _best_blob(mask, exp_area, near, step=3):
    """Busca la mancha cuadrada de tamaño esperado más cercana a `near`."""
    small = mask[::step, ::step]
    best, best_d = None, None
    for pts in _components(small):
        area = len(pts) * step * step
        if not (0.5 * exp_area < area < 2.0 * exp_area):
            continue
        cy, cx = pts.mean(axis=0) * step
        d = (cx - near[0]) ** 2 + (cy - near[1]) ** 2
        if best_d is None or d < best_d:
            best, best_d = (cx, cy), d
    if best is None:
        return None
    # refinar el centro con la resolución completa alrededor de la mancha
    r = int(np.sqrt(exp_area))
    x0, y0 = max(0, int(best[0] - r)), max(0, int(best[1] - r))
    sub = mask[y0:int(best[1] + r), x0:int(best[0] + r)]
    ys, xs = np.nonzero(sub)
    return (x0 + xs.mean(), y0 + ys.mean()) if len(xs) else best


def find_transform(gray, page_rect):
    """Localiza las 4 marcas negras y calcula la transformación pt -> px."""
    h, w = gray.shape
    sx, sy = w / page_rect.width, h / page_rect.height
    # la plantilla es 450x600; si la página exportada tiene otro tamaño, se escala
    kx, ky = page_rect.width / C.PAGE_W, page_rect.height / C.PAGE_H
    nominal = lambda x, y: (x * kx * sx, y * ky * sy)
    found_src, found_dst = [], []
    rad = int(0.06 * max(w, h))
    exp_area = (C.FID_SIZE * kx * sx) * (C.FID_SIZE * ky * sy)
    for cx, cy in C.FID_CENTERS:
        px, py = nominal(cx, cy)
        x0, x1 = max(0, int(px - rad)), min(w, int(px + rad))
        y0, y1 = max(0, int(py - rad)), min(h, int(py + rad))
        blob = _best_blob(gray[y0:y1, x0:x1] < 90, exp_area, (px - x0, py - y0))
        if blob is not None:
            found_src.append((cx, cy))
            found_dst.append((x0 + blob[0], y0 + blob[1]))
    if len(found_src) >= 3:
        return fit_affine(found_src, found_dst), len(found_src)
    return nominal, 0


def decode_page(gray, T):
    h, w = gray.shape
    bits = []
    for cx, cy in C.code_centers():
        px, py = T(cx, cy)
        r = 3
        x, y = int(round(px)), int(round(py))
        if not (r <= x < w - r and r <= y < h - r):
            return None
        bits.append(1 if gray[y - r:y + r + 1, x - r:x + r + 1].mean() < 100 else 0)
    return C.decode_code(bits)


# ------------------------------------------------------------ extracción
LABEL_ZONE_W = 17.0     # ancho (pt) de la etiqueta impresa arriba a la izquierda
BELOW_EXTRA = 7.0       # cuánto se mira por debajo de la casilla (colas de g, p, y...)


def _dilate(m, r):
    out = m.copy()
    h, w = m.shape
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            ys0, ys1 = max(0, dy), min(h, h + dy)
            xs0, xs1 = max(0, dx), min(w, w + dx)
            out[ys0:ys1, xs0:xs1] |= m[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx]
    return out


def _keep_components(mask, core, top_edge):
    """Quita manchas que no pertenecen a esta letra.

    Se conserva toda mancha que toque la zona de escritura (core). Las que están
    solo en las zonas ampliadas se quitan si entran desde fuera (tocan el borde
    superior de la casilla o están en la casilla de abajo).
    """
    cy0, cy1, cx0, cx1 = core
    keep = np.zeros_like(mask)
    for pts in _components(mask):
        ys, xs = pts[:, 0], pts[:, 1]
        in_core = np.any((ys >= cy0) & (ys < cy1) & (xs >= cx0) & (xs < cx1))
        if in_core:
            keep[ys, xs] = True
        elif ys.max() < cy0 and ys.min() > top_edge and len(ys) >= 15:   # tilde de la Ñ, puntos altos
            keep[ys, xs] = True
    return keep


def extract_cell(alpha, T, cell):
    x0, wy0, x1, y1 = cell["write"]
    cy0_pt = cell["cell"][1]
    ins = C.CROP_INSET
    # zona ampliada: desde el borde superior de la casilla hasta un poco por debajo
    (ax, ay), (bx, by) = T(x0 + ins, cy0_pt + ins), T(x1 - ins, y1 + BELOW_EXTRA)
    ax, ay, bx, by = int(round(ax)), int(round(ay)), int(round(bx)), int(round(by))
    ay, ax = max(ay, 0), max(ax, 0)
    crop = alpha[ay:by, ax:bx].copy()
    if crop.size == 0:
        return None
    px = lambda xp, yp: (int(round(T(xp, yp)[0])) - ax, int(round(T(xp, yp)[1])) - ay)
    # borrar las etiquetas impresas (la propia y la de la casilla de abajo)
    lx, _ = px(x0 + LABEL_ZONE_W, 0)
    _, ly = px(0, wy0)
    crop[:max(0, ly), :max(0, lx)] = 0
    _, by1 = px(0, y1)
    crop[max(0, by1):, :max(0, lx)] = 0
    # zona de escritura "propia"
    cx0, cy0 = px(x0 + ins, wy0 + ins)
    cx1, cy1 = px(x1 - ins, y1 - ins)
    core = (cy0, cy1, cx0, cx1)
    if (crop[cy0:cy1, cx0:cx1] > 0.4).sum() < MIN_INK_PX:
        return None
    mask = crop > 0.15
    small_top = 3                                   # px: lo que toca el borde superior viene de arriba
    keep = _keep_components(mask, core, small_top)
    crop = crop * _dilate(keep, 2)              # conserva también el borde suave del trazo
    mask = crop > 0.15
    if not mask.any():
        return None
    rows, cols = np.nonzero(mask.any(axis=1))[0], np.nonzero(mask.any(axis=0))[0]
    top, bot = rows[0], rows[-1] + 1
    left, right = cols[0], cols[-1] + 1
    pad = 2
    top, left = max(0, top - pad), max(0, left - pad)
    bot, right = min(crop.shape[0], bot + pad), min(crop.shape[1], right + pad)
    glyph = crop[top:bot, left:right]

    base_px = T(0, cell["base_y"])[1] - ay
    unit = T(0, cell["base_y"])[1] - T(0, cell["xh_y"])[1]   # altura de la x en px
    touches = bool(top == 0 or left == 0 or bot == crop.shape[0] or right == crop.shape[1])
    meta = {
        "w_u": glyph.shape[1] / unit,
        "h_u": glyph.shape[0] / unit,
        "top_u": (base_px - top) / unit,       # cuánto sube por encima de la línea base
        "bot_u": (base_px - bot) / unit,       # negativo si baja (g, p, q, y...)
        "unit_px": unit,
        "toca_borde": touches,
    }
    return Image.fromarray((glyph * 255).astype(np.uint8), "L"), meta


DISCARD = "_descartados"


class Layouts:
    """Busca la disposición de una plantilla: registro local, PDF o archivo dado."""

    def __init__(self, doc, layout_path=None):
        self.cache = {}
        self.fallback = None
        if layout_path:
            self.fallback = json.loads(Path(layout_path).read_text(encoding="utf-8"))
        elif "layout.json" in doc.embfile_names():
            self.fallback = json.loads(doc.embfile_get("layout.json").decode("utf-8"))
        if self.fallback:
            self.cache[self.fallback["session"]] = self.fallback

    def get(self, session):
        if session not in self.cache:
            p = Path(C.REGISTRY_DIR) / f"{session}.json"
            self.cache[session] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        return self.cache[session]


def process_pdf(pdf_path, layout_path, out_dir: Path, dpi=DPI, log=print, progress=None):
    """Extrae los glifos de un PDF escrito. Devuelve {sesión: [entradas]}."""
    doc = pymupdf.open(pdf_path)
    layouts = Layouts(doc, layout_path)
    gdir = out_dir / "glifos"
    (gdir / DISCARD).mkdir(parents=True, exist_ok=True)
    results, seen, cleaned = {}, set(), set()

    for pno, page in enumerate(doc):
        if progress:
            progress(pno, len(doc))
        alpha, gray = ink_alpha(page, dpi)
        T, nfid = find_transform(gray, page.rect)
        code = decode_page(gray, T)
        layout, idx, how = None, None, "código"
        if code:
            idx, session = code
            layout = layouts.get(session)
            if layout is None:
                log(f"  pág {pno + 1}: plantilla {session} desconocida en este equipo "
                    f"(¿se generó en otra computadora? copia su .json a plantillas/)")
                continue
        elif layouts.fallback and len(doc) == len(layouts.fallback["pages"]):
            layout, idx, how = layouts.fallback, pno, "orden"
        if layout is None or idx >= len(layout["pages"]):
            log(f"  pág {pno + 1}: no reconocida (¿tapaste el código de abajo?), se omite")
            continue
        session = layout["session"]
        if (session, idx) in seen:
            log(f"  pág {pno + 1}: duplicada, se omite")
            continue
        seen.add((session, idx))
        if session not in cleaned:      # re-importar sustituye lo anterior de esa plantilla
            for f in list(gdir.glob(f"{session}_*.png")) + list((gdir / DISCARD).glob(f"{session}_*.png")):
                f.unlink()
            cleaned.add(session)
        got = 0
        for cell in layout["pages"][idx]["cells"]:
            res = extract_cell(alpha, T, cell)
            if res is None:
                continue
            img, meta = res
            fname = f"{session}_{C.glyph_filename(cell['char'], cell['idx'])}"
            img.save(gdir / fname, optimize=True)
            results.setdefault(session, []).append(
                {"char": cell["char"], "file": fname, "session": session,
                 **{k: (float(v) if not isinstance(v, bool) else v) for k, v in meta.items()}})
            got += 1
        log(f"  pág {pno + 1} -> plantilla {session} pág {idx + 1} ({how}, {nfid}/4 marcas): {got} glifos")
    if progress:
        progress(len(doc), len(doc))
    if not results:
        raise SystemExit("No se reconoció ninguna página. ¿Es el PDF de una plantilla de Holograph?")
    return results


def import_pdf(pdf_path, out_dir: Path, layout_path=None, log=print, progress=None):
    """Todo en uno: extraer, actualizar índice y hoja de revisión."""
    out_dir = Path(out_dir)
    results = process_pdf(pdf_path, layout_path, out_dir, log=log, progress=progress)
    data = None
    for session, entries in results.items():
        data = merge_index(out_dir, session, entries, DPI)
    contact_sheet(out_dir, data)
    return data, sum(len(e) for e in results.values())


def merge_index(out_dir: Path, session, entries, dpi):
    idx_path = out_dir / "glifos.json"
    old = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"glyphs": []}
    kept = [g for g in old["glyphs"] if g.get("session") != session]
    data = {"version": 1, "dpi": dpi, "glyphs": kept + entries}
    idx_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return data


def contact_sheet(out_dir: Path, data, unit=22, max_per_row=20):
    """Hoja de revisión: una fila por carácter con todas sus muestras."""
    by_char = {}
    for g in data["glyphs"]:
        if (out_dir / "glifos" / g["file"]).exists():
            by_char.setdefault(g["char"], []).append(g)
    if not by_char:
        return None
    row_h = int(unit * 3.6)
    label_w = 50
    cell_w = int(unit * 2.4)
    rows = sum((len(v) + max_per_row - 1) // max_per_row for v in by_char.values())
    W = label_w + max_per_row * cell_w + 10
    H = rows * row_h + 10
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    fp = C.font_path("seguisym.ttf", *C.LABEL_FONTS)
    font = ImageFont.truetype(fp, 20) if fp else ImageFont.load_default()
    small = ImageFont.truetype(fp, 9) if fp else ImageFont.load_default()
    y = 5
    for ch, glyphs in by_char.items():
        for start in range(0, len(glyphs), max_per_row):
            base = y + int(unit * 2.3)
            d.line([(label_w, base), (W - 5, base)], fill=(200, 215, 240))
            d.line([(label_w, base - unit), (W - 5, base - unit)], fill=(235, 235, 235))
            if start == 0:
                d.text((10, base - 22), ch, fill=(180, 30, 30), font=font)
            for i, g in enumerate(glyphs[start:start + max_per_row]):
                im = Image.open(out_dir / "glifos" / g["file"])
                s = unit / g["unit_px"]
                im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
                x = label_w + i * cell_w + 4
                ink = Image.new("RGB", im.size, (0, 0, 0))
                sheet.paste(ink, (x, int(base - g["top_u"] * unit)), im)
                tag = g["file"].split("_")[-1].split(".")[0]
                d.text((x, base + unit * 1.0), tag, fill=(150, 150, 150) if not g["toca_borde"] else (220, 80, 0), font=small)
            y += row_h
    p = out_dir / "revision.png"
    sheet.save(p)
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--layout", help="plantilla.json (si el PDF exportado perdió la disposición incrustada)")
    ap.add_argument("-o", "--out", default=C.LETRA_DIR)
    ap.add_argument("--dpi", type=int, default=DPI)
    a = ap.parse_args()
    out = Path(a.out)
    for pdf in a.pdfs:
        print(f"Procesando {pdf}")
        data, n = import_pdf(pdf, out, a.layout)
        print(f"  {n} glifos extraídos")
    chars = {g["char"] for g in data["glyphs"]}
    print(f"Total en {out}: {len(data['glyphs'])} glifos de {len(chars)} caracteres")
    print(f"Revisa {out / 'revision.png'} (en naranja: muestras que tocan el borde, quizá recortadas)")


if __name__ == "__main__":
    main()
