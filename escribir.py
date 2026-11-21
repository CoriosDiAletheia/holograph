"""Convierte texto en una imagen/PDF escrita con tu letra.

Uso:
    python escribir.py "Hola, mundo" -o hola.png
    python escribir.py -f texto.txt -o apuntes.pdf --papel rayado --color azul
    python escribir.py "E = mc²" --modo promedio -o formula.png

Modos:
    aleatorio  (por defecto) cada vez que se repite una letra se elige una de
               tus muestras al azar, evitando repetir la misma seguida.
    promedio   usa una versión "media" de cada carácter (más uniforme, algo
               más borrosa; se ve menos natural).
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

import comun as C

COLORS = {
    "negro": (25, 25, 30), "azul": (20, 45, 140), "boli": (35, 55, 120),
    "rojo": (170, 25, 30), "verde": (20, 100, 50), "grafito": (70, 70, 75),
}
PAPERS = ("blanco", "rayado", "cuadriculado", "transparente")

# Caracteres que se fabrican a partir de otros que sí escribiste:
# carácter -> (base, escala, desplazamiento vertical en unidades de x)
DERIVED = {}
for _d, _sub, _sup in zip("0123456789+-=()n", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₙ", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿ"):
    DERIVED[_sub] = (_d, 0.6, -0.45)
    DERIVED[_sup] = (_d, 0.6, 0.95)
for _c, _sub in zip("aeoxijrv", "ₐₑₒₓᵢⱼᵣᵥ"):
    DERIVED[_sub] = (_c, 0.6, -0.45)


@dataclass
class Glyph:
    img: Image.Image      # L, 255 = tinta
    unit_px: float        # altura de la x en píxeles de `img`
    top_u: float          # altura sobre la línea base (en unidades de x)
    w_u: float


class Letra:
    """Carga los glifos extraídos de una carpeta (mi_letra/)."""

    def __init__(self, folder, acentos=True, signos=True):
        """acentos: dibujar tilde aguda en á é í ó ú; signos: centrar y escalar + − = …"""
        self.folder = Path(folder)
        data = json.loads((self.folder / "glifos.json").read_text(encoding="utf-8"))
        self.glyphs: dict[str, list[Glyph]] = {}
        for g in data["glyphs"]:
            p = self.folder / "glifos" / g["file"]
            if not p.exists():          # borrado a mano en la revisión
                continue
            img = Image.open(p).convert("L")
            img.load()
            self.glyphs.setdefault(g["char"], []).append(
                Glyph(img, g["unit_px"], g["top_u"], g["w_u"]))
        if not self.glyphs:
            raise SystemExit(f"No hay glifos en {self.folder}")
        import ajustes
        if signos:
            ajustes.fix_signs(self.glyphs)
            ajustes.fix_primes(self.glyphs)
        ajustes.add_checkmarks(self.glyphs)
        if acentos:
            ajustes.fix_accents(self.glyphs)
        self._avg: dict[str, Glyph] = {}
        # medidas de referencia para espacios
        lows = [g.w_u for c in "nmoeau" for g in self.glyphs.get(c, [])]
        self.space_u = 0.75 * (float(np.median(lows)) if lows else 1.0)
        self._fallback_fonts = C.font_paths(C.HAND_FONTS + C.LABEL_FONTS)

    @property
    def chars(self):
        return "".join(sorted(self.glyphs))

    # -------------------------------------------------------------- variantes
    def has(self, ch):
        ch = C.ALIAS.get(ch, ch)
        return ch in self.glyphs or (ch in DERIVED and DERIVED[ch][0] in self.glyphs)

    def variant(self, ch, rnd, bags, mode):
        """Elige una muestra del carácter.

        Usa una "bolsa barajada" por carácter: se van sacando todas tus muestras
        en orden aleatorio antes de repetir ninguna, y al rebarajar se evita que
        la primera nueva sea igual a la última usada. Así, en un texto largo,
        todas tus variantes aparecen con la misma frecuencia y nunca seguidas.
        """
        ch = C.ALIAS.get(ch, ch)
        opts = self.glyphs.get(ch)
        if not opts and ch in DERIVED and DERIVED[ch][0] in self.glyphs:
            base, scale, shift = DERIVED[ch]
            g = self.variant(base, rnd, bags, mode)
            # misma imagen, más pequeña y desplazada (sub/superíndice)
            return Glyph(g.img, g.unit_px / scale, g.top_u * scale + shift, g.w_u * scale)
        if not opts:
            return self._fallback(ch)
        if mode == "promedio":
            return self.average(ch)
        if len(opts) == 1:
            return opts[0]
        bag, prev = bags.get(ch, ([], None))
        if not bag:
            bag = list(opts)
            rnd.shuffle(bag)
            if bag[-1] is prev:                 # no repetir en la costura
                bag[0], bag[-1] = bag[-1], bag[0]
        g = bag.pop()
        bags[ch] = (bag, g)
        return g

    def average(self, ch):
        """Superpone todas las muestras alineadas por línea base y centro, y re-afila."""
        if ch in self._avg:
            return self._avg[ch]
        opts = self.glyphs[ch]
        U = 60.0
        tops = [g.top_u for g in opts]
        heights = [g.img.height / g.unit_px for g in opts]
        widths = [g.img.width / g.unit_px for g in opts]
        top = float(np.median(tops))
        H = int(U * (top - min(t - h for t, h in zip(tops, heights)))) + 4
        W = int(U * max(widths)) + 4
        acc = np.zeros((H, W), np.float32)
        for g in opts:
            s = U / g.unit_px
            im = g.img.resize((max(1, round(g.img.width * s)), max(1, round(g.img.height * s))), Image.LANCZOS)
            canvas = Image.new("L", (W, H))
            canvas.paste(im, ((W - im.width) // 2, int(U * (top - g.top_u)) + 2))
            acc += np.asarray(canvas, np.float32)
        acc /= len(opts) * 255.0
        # re-afilar: lo que aparece en la mayoría de muestras se vuelve trazo
        sharp = np.clip((acc - 0.28) / 0.25, 0, 1)
        ys, xs = np.nonzero(sharp > 0.05)
        if len(xs) == 0:
            self._avg[ch] = opts[0]
            return opts[0]
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        img = Image.fromarray((sharp[y0:y1, x0:x1] * 255).astype(np.uint8), "L")
        g = Glyph(img, U, top - (y0 - 2) / U, img.width / U)
        self._avg[ch] = g
        return g

    def _fallback(self, ch):
        """Carácter que no escribiste: se dibuja con una fuente 'manuscrita' de Windows."""
        key = "\0" + ch
        if key in self._avg:
            return self._avg[key]
        U = 60
        import pymupdf
        path = next((p for p in self._fallback_fonts
                     if pymupdf.Font(fontfile=p).has_glyph(ord(ch))), self._fallback_fonts[0])
        font = ImageFont.truetype(path, int(U * 2))
        x0, y0, x1, y1 = font.getbbox(ch, anchor="ls")
        img = Image.new("L", (max(1, x1 - x0) + 4, max(1, y1 - y0) + 4))
        ImageDraw.Draw(img).text((2 - x0, 2 - y0), ch, fill=255, font=font, anchor="ls")
        g = Glyph(img, U, (-y0 + 2) / U, img.width / U)
        self._avg[key] = g
        return g


# ------------------------------------------------------------------ maquetación
def render(text, letra: Letra, *, xh=28, ancho=1700, alto=None, margen=None,
           interlineado=3.0, color="azul", papel="rayado", modo="aleatorio",
           semilla=None, inclinacion=0.0, desorden=1.0, espaciado=0.12, formato=True, avisos=None,
           espacio_palabras=1.0):
    """Devuelve una lista de páginas (PIL RGBA). `xh` = altura de la x en px.

    alto=None -> una sola imagen tan alta como haga falta.
    desorden  -> multiplica todas las variaciones aleatorias (0 = rígido).
    formato   -> interpretar ^ _ \\frac \\pmat \\bmat \\vmat (ver formulas.py).
    """
    import ajustes
    import formulas as F
    rnd = random.Random(semilla)
    ink = COLORS.get(color, color) if isinstance(color, str) else color
    margen = int(margen if margen is not None else xh * 2.5)
    lh = xh * interlineado
    bags = {}
    lay = F.Layout(letra, rnd, bags, modo, espaciado, 0.04 * desorden, ajustes.math_axis(letra.glyphs),
                   word_space=espacio_palabras)
    space = letra.space_u * xh * espacio_palabras
    max_w = ancho - 2 * margen

    # 1) partir en líneas (respetando saltos de línea y ajustando palabras)
    lines = []          # [(palabras [(x_px, Box)], asc, desc)]
    for para in F.split_top(F.parse(text, formato), "\n"):
        cur, cur_w = [], 0.0
        for word in F.split_top(para, " "):
            if not word:
                cur_w += letra.space_u * xh
                continue
            box = lay.seq(word)
            w = box.w * xh
            if w > max_w and avisos is not None:
                txt = "".join(getattr(nd, "ch", "▢") for nd in word)[:40]
                avisos.append(f"Elemento más ancho que la página ({w / max_w:.0%} del ancho): «{txt}». "
                              "Pártelo en varias líneas o reduce --tamano.")
            gap = space * (1 + rnd.gauss(0, 0.15 * desorden)) if cur else 0
            if cur and cur_w + gap + w > max_w:
                lines.append(cur)
                cur, cur_w, gap = [], 0.0, 0
            cur.append((cur_w + gap, box))
            cur_w += gap + w
        lines.append(cur)

    # 2) colocar cada línea en un renglón del papel (las altas ocupan varios) y paginar
    first_base = margen + xh * 2
    H_page = alto
    pages_lines, page, prev_b, prev_bottom, prev_tall = [], [], None, None, False
    for line in lines:
        asc = max([b.asc for _, b in line] + [1.0]) * xh
        desc = min([b.desc for _, b in line] + [-0.3]) * xh
        if prev_b is None:
            b = first_base
            while b - asc < margen * 0.5:
                b += lh
        else:
            b = prev_b + lh
            # en renglones normales se tolera que colas e índices se rocen; si hay algo alto
            # (matrices, fracciones grandes) se deja aire de verdad
            line_tall = any(bx.tall for _, bx in line)
            tol = 0.25 * xh if (line_tall or prev_tall) else -0.45 * xh
            while b - asc < prev_bottom + tol:
                b += lh
        if H_page and page and b - desc > H_page - margen * 0.6:
            pages_lines.append(page)
            page = []
            b = first_base
            while b - asc < margen * 0.5:
                b += lh
        page.append((b, line))
        prev_b, prev_bottom, prev_tall = b, b - desc, any(bx.tall for _, bx in line)
    pages_lines.append(page)

    pages = []
    for page in pages_lines:
        last = max([b - min([bx.desc for _, bx in ln] + [0]) * xh for b, ln in page] + [first_base])
        H = H_page or int(last + xh * 1.5 + margen)
        alpha = Image.new("L", (ancho, H), 0)
        for b, line in page:
            base = b + rnd.gauss(0, 0.06 * xh * desorden)
            slope = rnd.gauss(0, 0.004 * desorden)          # líneas ligeramente torcidas
            drift_x = margen + rnd.gauss(0, 0.15 * xh * desorden)
            for wx, box in line:
                for gx, dy, g, sc in box.items:
                    x = drift_x + wx + gx * xh
                    y = base - dy * xh + slope * (x - margen) + rnd.gauss(0, 0.035 * xh * desorden * sc)
                    _stamp(alpha, g, x, y, xh * sc, rnd, inclinacion, desorden)
        paper = _paper(ancho, H, papel, first_base, lh, xh, margen)
        inkl = Image.new("RGBA", (ancho, H), ink + (255,))
        inkl.putalpha(alpha)
        paper.alpha_composite(inkl)
        pages.append(paper)
    return pages


def _stamp(alpha, g: Glyph, x, base_y, xh, rnd, inclinacion, desorden):
    s = xh / g.unit_px
    stretch = 1 + rnd.gauss(0, 0.035 * desorden)          # algo más ancha / estrecha
    w, h = max(1, round(g.img.width * s * stretch)), max(1, round(g.img.height * s))
    im = g.img.resize((w, h), Image.LANCZOS)
    top = base_y - g.top_u * xh
    cy = g.top_u * xh                                      # fila de la línea base
    # inclinación (cizalla alrededor de la línea base): positiva = hacia la derecha
    t = math.tan(math.radians(inclinacion + rnd.gauss(0, 2.5 * desorden)))
    if abs(t) > 0.004:
        pad = max(0.0, -min(t * cy, t * (cy - h)))
        W2 = int(math.ceil(w + abs(t) * h)) + 1
        im = im.transform((W2, h), Image.AFFINE, (1, t, -(pad + t * cy), 0, 1, 0), resample=Image.BICUBIC)
        x -= pad
        w = W2
    ang = rnd.gauss(0, 1.2 * desorden)                     # pequeño giro aleatorio
    if abs(ang) > 0.2:
        # rotar alrededor del punto (centro, línea base) para no mover la letra
        cx = w / 2
        im = im.rotate(ang, resample=Image.BICUBIC, expand=True, center=(cx, cy))
        dx, dy = (im.width - w) / 2, (im.height - h) / 2
        x, top = x - dx, top - dy
    # ligera variación de presión
    if desorden > 0:
        im = im.point(lambda v, k=rnd.uniform(0.85, 1.0): int(v * k))
    # combinar solo en la región de la letra (máximo = trazos que se cruzan no se oscurecen de más)
    x0, y0 = int(round(x)), int(round(top))
    cx0, cy0 = max(0, x0), max(0, y0)
    cx1, cy1 = min(alpha.width, x0 + im.width), min(alpha.height, y0 + im.height)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    im = im.crop((cx0 - x0, cy0 - y0, cx1 - x0, cy1 - y0))
    box = (cx0, cy0, cx1, cy1)
    alpha.paste(ImageChops.lighter(alpha.crop(box), im), box)


def _paper(W, H, papel, first_base, lh, xh, margen):
    if papel == "transparente":
        return Image.new("RGBA", (W, H), (0, 0, 0, 0))
    page = Image.new("RGBA", (W, H), (255, 255, 253, 255))
    d = ImageDraw.Draw(page)
    if papel == "rayado":
        y = first_base
        while y < H - xh:
            d.line([(0, y), (W, y)], fill=(170, 195, 230, 255), width=max(1, int(xh / 22)))
            y += lh
        d.line([(margen * 0.7, 0), (margen * 0.7, H)], fill=(230, 150, 150, 255), width=max(1, int(xh / 18)))
    elif papel == "cuadriculado":
        step = lh / 2
        k = 0.0
        while k < max(W, H):
            d.line([(k, 0), (k, H)], fill=(205, 220, 235, 255))
            d.line([(0, first_base % step + k), (W, first_base % step + k)], fill=(205, 220, 235, 255))
            k += step
    return page


def save(pages, out, dpi=200):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".pdf":
        import pymupdf
        doc = pymupdf.open()
        for im in pages:
            pw, ph = im.width * 72 / dpi, im.height * 72 / dpi
            pg = doc.new_page(width=pw, height=ph)
            import io
            buf = io.BytesIO()
            im.save(buf, "PNG")
            pg.insert_image(pg.rect, stream=buf.getvalue())
        doc.save(out, deflate=True)
        return [out]
    if len(pages) == 1:
        pages[0].save(out)
        return [out]
    outs = []
    for i, im in enumerate(pages, 1):
        o = out.with_name(f"{out.stem}_{i:02d}{out.suffix}")
        im.save(o)
        outs.append(o)
    return outs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("texto", nargs="?")
    ap.add_argument("-f", "--archivo", help="leer el texto de un .txt")
    ap.add_argument("-l", "--letra", default=C.LETRA_DIR, help="carpeta generada por extraer.py")
    ap.add_argument("-o", "--out", default="salida.png", help=".png o .pdf")
    ap.add_argument("--tamano", type=int, default=28, help="altura de la x en píxeles")
    ap.add_argument("--ancho", type=int, default=1700)
    ap.add_argument("--hoja", action="store_true", help="paginar en hojas tamaño carta (1700x2200 px)")
    ap.add_argument("--color", default="azul", help=", ".join(COLORS))
    ap.add_argument("--papel", default="rayado", choices=PAPERS)
    ap.add_argument("--modo", default="aleatorio", choices=("aleatorio", "promedio"))
    ap.add_argument("--desorden", type=float, default=1.0)
    ap.add_argument("--inclinacion", type=float, default=0.0, help="grados extra de inclinación")
    ap.add_argument("--semilla", type=int)
    ap.add_argument("--literal", action="store_true", help="no interpretar ^ y _ como super/subíndices")
    ap.add_argument("--acentos-originales", action="store_true", help="no sustituir tus acentos por tilde")
    ap.add_argument("--signos-originales", action="store_true", help="no centrar ni escalar + − = …")
    a = ap.parse_args()
    text = Path(a.archivo).read_text(encoding="utf-8") if a.archivo else a.texto
    if not text:
        ap.error("falta el texto (o -f archivo.txt)")
    letra = Letra(a.letra, acentos=not a.acentos_originales, signos=not a.signos_originales)
    missing = sorted({c for c in text if not c.isspace() and not letra.has(c)})
    if missing:
        print("Aviso: sin muestras para", " ".join(missing), "-> se usa una fuente de respaldo")
    pages = render(text, letra, xh=a.tamano, ancho=1700 if a.hoja else a.ancho,
                   alto=2200 if a.hoja else None, color=a.color, papel=a.papel, modo=a.modo,
                   semilla=a.semilla, inclinacion=a.inclinacion, desorden=a.desorden,
                   formato=not a.literal)
    for o in save(pages, a.out):
        print("OK:", o)


if __name__ == "__main__":
    main()
