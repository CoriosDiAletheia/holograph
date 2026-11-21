"""Correcciones automáticas que se aplican al cargar la letra.

No modifican tus archivos de muestras: se recalculan cada vez que se carga
la letra, así que siguen funcionando aunque vuelvas a importar un PDF.

1. Signos matemáticos (+ − = × ÷ ± < > ≤ ≥ → …): se centran en el "eje
   matemático" (la altura a la que va el signo menos) y se escalan a un
   tamaño proporcionado con tus dígitos. Se conserva la variación entre
   tus muestras (unas un poco más arriba, otras más grandes…).

2. Acentos (á é í ó ú Á É Í Ó Ú): se borra la marca que escribiste encima
   de la letra y se dibuja una tilde aguda inclinada, con el grosor de tu
   propio trazo y una pequeña variación en cada muestra.
"""
from __future__ import annotations

import random
import statistics as st
from dataclasses import replace

import numpy as np
from PIL import Image, ImageDraw

from extraer import _components, _dilate

# carácter -> (dimensión a normalizar, tamaño objetivo en unidades de x) ; None = solo centrar
SIGNS = {
    "+": ("h", 1.0), "-": ("w", 0.95), "=": ("w", 1.05), "±": ("h", 1.15), "∓": ("h", 1.15),
    "×": ("h", 0.8), "÷": ("h", 1.0), "·": None, "∘": None, "∗": None, "⋆": None,
    "~": None, "∼": None, "≈": ("w", 1.05), "≃": ("w", 1.05), "≅": ("w", 1.05), "≡": ("w", 1.05),
    "≢": ("w", 1.05), "≠": ("w", 1.05), "≜": None, "≝": None, "∝": None,
    "<": ("h", 1.05), ">": ("h", 1.05), "≤": ("h", 1.3), "≥": ("h", 1.3), "≪": ("h", 1.05), "≫": ("h", 1.05),
    "≺": ("h", 1.05), "≻": ("h", 1.05),
    "→": None, "←": None, "↔": None, "⇒": None, "⇐": None, "⇔": None, "↦": None, "⟶": None, "⇌": None,
    "⊕": None, "⊗": None, "⊙": None, "∧": None, "∨": None, "¬": None,
    "–": ("w", 0.95), "—": None,
}

# Letras cuya marca no se puede separar con seguridad de la propia letra
# (tu I lleva barrita arriba): se construyen desde la letra base sin acento.
FROM_BASE = {"Í"}

ACCENTED = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
            "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U"}


# ---------------------------------------------------------------- signos
def _median_top(glyphs, chars):
    v = [g.top_u for c in chars for g in glyphs.get(c, [])]
    return st.median(v) if v else None


def math_axis(glyphs):
    """Altura del eje matemático, calculada a partir de tu propia letra."""
    xtop = _median_top(glyphs, "xaonuvzsc") or 0.85
    cap = _median_top(glyphs, "0123456789ABEHNT") or 1.8
    # en tipografía el eje está ~0.55 de la altura x y ~0.36 de la de mayúsculas;
    # se promedian porque las proporciones de la letra a mano varían mucho
    return 0.5 * (0.55 * xtop + 0.36 * cap)


def fix_signs(glyphs):
    axis = math_axis(glyphs)
    for ch, spec in SIGNS.items():
        gs = glyphs.get(ch)
        if not gs:
            continue
        hs = [g.img.height / g.unit_px for g in gs]
        ws = [g.img.width / g.unit_px for g in gs]
        centers = [g.top_u - h / 2 for g, h in zip(gs, hs)]
        c_med = st.median(centers)
        k = 1.0
        if spec:
            dim, target = spec
            cur = st.median(hs if dim == "h" else ws)
            k = max(0.6, min(2.2, target / cur)) if cur > 0 else 1.0
        out = []
        for g, h, c in zip(gs, hs, centers):
            new_h = h * k
            new_c = axis + (c - c_med) * k * 0.6       # se atenúa la variación de altura
            out.append(replace(g, unit_px=g.unit_px / k, top_u=new_c + new_h / 2, w_u=g.w_u * k))
        glyphs[ch] = out
    return axis


PRIMES = "′″‴"


def fix_primes(glyphs):
    """Las primas (X′, f″) van arriba, a la altura de las mayúsculas."""
    cap = _median_top(glyphs, "0123456789ABEHNT") or 1.8
    for ch in PRIMES:
        gs = glyphs.get(ch)
        if not gs:
            continue
        tops = [g.top_u for g in gs]
        t_med = st.median(tops)
        glyphs[ch] = [replace(g, top_u=cap * 1.02 + (g.top_u - t_med) * 0.5) for g in gs]


def _polyline(points_u, stroke_px, u, rnd, ss=4):
    """Dibuja un trazo a mano alzada por los puntos dados (en unidades, y hacia arriba)."""
    pts = [(x * u, y * u) for x, y in points_u]
    pad = stroke_px * 2
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    W = int(max(xs) - min(xs) + 2 * pad) + 2
    H = int(max(ys) - min(ys) + 2 * pad) + 2
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    X = lambda x: (x - min(xs) + pad) * ss
    Y = lambda y: (max(ys) - y + pad) * ss
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(4, int(np.hypot(x1 - x0, y1 - y0) / 1.5))
        for i in range(n + 1):
            t = i / n
            r = stroke_px * rnd.uniform(0.92, 1.05) / 2 * ss
            cx, cy = X(x0 + (x1 - x0) * t), Y(y0 + (y1 - y0) * t)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    im = im.resize((W, H), Image.LANCZOS)
    top_u = (max(ys) + pad) / u
    return im, top_u


def add_checkmarks(glyphs, n=5):
    """✓ (palomita) con el grosor de tu trazo, si no la escribiste en la plantilla."""
    if glyphs.get("✓"):
        return
    ref = (glyphs.get("v") or glyphs.get("x") or [None])[0]
    if ref is None:
        return
    from escribir import Glyph
    a = np.asarray(ref.img, np.float32) / 255.0
    stroke = _stroke_width(a > 0.3)
    u = ref.unit_px
    out = []
    for i in range(n):
        rnd = random.Random(777 + i)
        j = lambda s=0.05: rnd.gauss(0, s)
        pts = [(0.0 + j(), 0.55 + j()), (0.32 + j(), 0.0 + j(0.03)),
               (0.62 + j(), 0.6 + j()), (0.95 + j(), 1.2 + j(0.08))]
        im, top_u = _polyline(pts, stroke, u, rnd)
        out.append(Glyph(im, u, top_u, im.width / u))
    glyphs["✓"] = out


# ---------------------------------------------------------------- acentos
def _stroke_width(mask):
    area = mask.sum()
    if area == 0:
        return 3.0
    inner = ~_dilate(~mask, 1)
    perim = (mask & ~inner).sum()
    return float(np.clip(2 * area / max(perim, 1), 2.0, 14.0))


def _strip_marks(a):
    """Quita las marcas que están completamente por encima del cuerpo de la letra.

    a: array float 0..1. Devuelve (array sin marcas, máscara del cuerpo) o None.
    """
    mask = a > 0.3
    comps = _components(mask)
    if len(comps) < 2:
        return None
    sizes = [len(c) for c in comps]
    big = comps[int(np.argmax(sizes))]
    top_big = big[:, 0].min()
    marks, rest = np.zeros_like(mask), np.zeros_like(mask)
    found = False
    for c in comps:
        if c is not big and c[:, 0].max() < top_big + 2:
            marks[c[:, 0], c[:, 1]] = True
            found = True
        else:
            rest[c[:, 0], c[:, 1]] = True
    if not found:
        return None
    erase = _dilate(marks, 2) & ~_dilate(rest, 1)
    b = a.copy()
    b[erase] = 0
    return b, rest


def _draw_acute(stroke, length, rnd, ss=4):
    """Tilde aguda: trazo recto inclinado (abajo-izquierda → arriba-derecha), algo
    más grueso arriba, como cuando el lápiz baja."""
    ang = np.radians(rnd.gauss(52, 6))                 # respecto a la horizontal
    L = length * rnd.uniform(0.9, 1.1)
    dx, dy = L * np.cos(ang), L * np.sin(ang)
    pad = stroke * 2
    W, H = int(dx + 2 * pad) + 2, int(dy + 2 * pad) + 2
    im = Image.new("L", (W * ss, H * ss), 0)
    d = ImageDraw.Draw(im)
    x0, y0 = pad, pad + dy            # abajo-izquierda
    x1, y1 = pad + dx, pad            # arriba-derecha
    n = 12
    for i in range(n + 1):            # trazo con grosor variable
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        r = stroke * (0.75 + 0.35 * t) / 2
        d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=255)
    im = im.resize((W, H), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0, (x0, y0)


def _rebuild(g, base_char, seed):
    """Devuelve un Glyph nuevo con tilde aguda, o None si no se puede."""
    a = np.asarray(g.img, np.float32) / 255.0
    res = _strip_marks(a)
    if res is None:
        return None
    body, body_mask = res
    ys, xs = np.nonzero(body > 0.15)
    if len(ys) == 0:
        return None
    u = g.unit_px
    rnd = random.Random(seed)
    stroke = _stroke_width(body_mask)
    top_row = ys.min()
    body_top_u = g.top_u - top_row / u
    # cuerpo de la letra: para la i se usa la columna del palo
    cx = float(np.median(xs[ys < top_row + 0.25 * u])) if base_char in "iI" else (xs.min() + xs.max()) / 2
    acute, (ax0, ay0) = _draw_acute(stroke, length=0.42 * u, rnd=rnd)
    gap = (0.16 if base_char.islower() else 0.14) * u * rnd.uniform(0.85, 1.15)
    # lienzo con la línea base en la fila B
    B = int(g.top_u * u + acute.shape[0] + gap) + 4
    W = a.shape[1] + acute.shape[1] * 2
    can = np.zeros((B + a.shape[0], W), np.float32)
    left = acute.shape[1]
    oy = int(round(B - g.top_u * u))
    can[oy:oy + a.shape[0], left:left + a.shape[1]] = body
    # el pie de la tilde queda centrado sobre la letra, un poco a la derecha
    shift = 0.12 if base_char in "iI" else -0.08     # en la i, sobre el palo y algo a la derecha
    foot_x = left + cx + shift * u + rnd.gauss(0, 0.03 * u)
    foot_y = B - body_top_u * u - gap
    px, py = int(round(foot_x - ax0)), int(round(foot_y - ay0))
    h, w = acute.shape
    region = can[py:py + h, px:px + w]
    can[py:py + h, px:px + w] = np.maximum(region, acute[:region.shape[0], :region.shape[1]])
    ys, xs = np.nonzero(can > 0.05)
    t, b, l, r = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = can[t:b, l:r]
    if base_char == "i":   # aire a la izquierda: que la tilde no se una a la letra anterior (l+í ≠ k)
        crop = np.hstack([np.zeros((crop.shape[0], int(0.18 * u)), np.float32), crop])
    img = Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8), "L")
    return replace(g, img=img, top_u=(B - t) / u, w_u=img.width / u)


def fix_accents(glyphs):
    """Sustituye la marca de acento de tus muestras por una tilde aguda."""
    changed = 0
    for ch, base in ACCENTED.items():
        out = []
        for i, g in enumerate(glyphs.get(ch, [])):
            if ch in FROM_BASE and glyphs.get(base):
                bases = glyphs[base]
                ng = _rebuild_from_base(bases[i % len(bases)], base, i)
                out.append(ng or g)
                continue
            ng = _rebuild(g, base, seed=ord(ch) * 100 + i)
            if ng is None:       # no se encontró la marca: probar con la letra base
                bases = glyphs.get(base)
                if bases:
                    ng = _rebuild_from_base(bases[i % len(bases)], base, i)
            out.append(ng or g)
            changed += ng is not None
        if out:
            glyphs[ch] = out
    return changed


def _rebuild_from_base(g, base_char, i):
    """Para letras sin marca separable: se añade la tilde a la letra base
    (en la i se quita antes el punto)."""
    if base_char == "i":
        return _rebuild(g, base_char, seed=1000 + i)
    a = np.asarray(g.img, np.float32) / 255.0
    fake = np.zeros((a.shape[0] + 2, a.shape[1]), np.float32)
    fake[2:] = a
    fake[0, 0] = 1.0                       # "marca" diminuta para reutilizar _rebuild
    g2 = replace(g, img=Image.fromarray((fake * 255).astype(np.uint8), "L"), top_u=g.top_u + 2 / g.unit_px)
    return _rebuild(g2, base_char, seed=2000 + i)
