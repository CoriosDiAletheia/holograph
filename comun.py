"""Geometría compartida de la plantilla y conjuntos de caracteres.

Todas las medidas están en puntos PDF (1 pt = 1/72 in).
La página tiene proporción 3:4, igual que la pantalla de la Kindle Scribe,
para que se vea a pantalla completa sin márgenes extra.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------- página
PAGE_W, PAGE_H = 450.0, 600.0
MARGIN = 18.0

# Marcas de registro (cuadros negros en las esquinas) para corregir
# escalado/desplazamiento al leer la página exportada.
FID_SIZE = 12.0
FID_CENTERS = [
    (MARGIN + FID_SIZE / 2, MARGIN + FID_SIZE / 2),                    # sup-izq
    (PAGE_W - MARGIN - FID_SIZE / 2, MARGIN + FID_SIZE / 2),           # sup-der
    (MARGIN + FID_SIZE / 2, PAGE_H - MARGIN - FID_SIZE / 2),           # inf-izq
    (PAGE_W - MARGIN - FID_SIZE / 2, PAGE_H - MARGIN - FID_SIZE / 2),  # inf-der
]

# Código binario impreso abajo, entre las marcas inferiores:
#   10 bits número de página (+1) | 24 bits id de plantilla | 2 bits de paridad
# Con él, el PDF escrito se identifica solo, aunque la Kindle borre los metadatos.
PAGE_BITS = 10
SESSION_BITS = 24
CODE_BITS = PAGE_BITS + SESSION_BITS
CODE_SIZE = 6.0
CODE_STEP = 9.5
CODE_X0 = 56.0
CODE_Y = FID_CENTERS[2][1]


def code_centers():
    return [(CODE_X0 + i * CODE_STEP, CODE_Y) for i in range(CODE_BITS + 2)]


def encode_code(page_index: int, session_hex: str):
    data = [((page_index + 1) >> b) & 1 for b in range(PAGE_BITS)]
    s = int(session_hex, 16)
    data += [(s >> b) & 1 for b in range(SESSION_BITS)]
    return data + [sum(data[0::2]) % 2, sum(data[1::2]) % 2]


def decode_code(bits):
    """-> (page_index, session_hex) o None si la paridad no cuadra."""
    data, p = bits[:CODE_BITS], bits[CODE_BITS:]
    if [sum(data[0::2]) % 2, sum(data[1::2]) % 2] != p:
        return None
    page = sum(b << i for i, b in enumerate(data[:PAGE_BITS]))
    sess = sum(b << i for i, b in enumerate(data[PAGE_BITS:]))
    if page == 0:
        return None
    return page - 1, f"{sess:06x}"


# Carpetas. El código vive en APP_DIR; TODO lo personal (tu letra, tus PDF
# escritos, el registro de plantillas, tus ajustes y salidas) vive en DATA_DIR,
# que nunca se sube a git. Se puede cambiar con la variable HOLOGRAPH_HOME.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.abspath(os.environ.get("HOLOGRAPH_HOME") or os.environ.get("MILETRA_HOME")
                           or os.path.join(APP_DIR, "datos"))
REGISTRY_DIR = os.path.join(DATA_DIR, "plantillas")
LETRA_DIR = os.path.join(DATA_DIR, "mi_letra")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


# ---------------------------------------------------------------- rejilla
GRID_X0, GRID_X1 = MARGIN, PAGE_W - MARGIN
GRID_Y0, GRID_Y1 = 52.0, 562.0
COLS, ROWS = 6, 8
CELL_W = (GRID_X1 - GRID_X0) / COLS
CELL_H = (GRID_Y1 - GRID_Y0) / ROWS
LABEL_H = 12.0          # franja superior con la etiqueta del carácter
CROP_INSET = 1.5        # margen interior al recortar la zona de escritura

# Guías dentro de la zona de escritura (fracción de su altura, desde arriba)
GUIDE_ASC = 0.12        # línea de ascendentes / mayúsculas (punteada)
GUIDE_XH = 0.40         # altura de la x (discontinua)
GUIDE_BASE = 0.68       # línea base (continua)

CELLS_PER_PAGE = COLS * ROWS


def cell_geometry(slot: int):
    """Devuelve la geometría de la celda `slot` (0..CELLS_PER_PAGE-1)."""
    r, c = divmod(slot, COLS)
    x0 = GRID_X0 + c * CELL_W
    y0 = GRID_Y0 + r * CELL_H
    x1, y1 = x0 + CELL_W, y0 + CELL_H
    wy0 = y0 + LABEL_H          # inicio zona de escritura
    wh = y1 - wy0
    return {
        "cell": [x0, y0, x1, y1],
        "write": [x0, wy0, x1, y1],
        "asc_y": wy0 + GUIDE_ASC * wh,
        "xh_y": wy0 + GUIDE_XH * wh,
        "base_y": wy0 + GUIDE_BASE * wh,
    }


# ---------------------------------------------------------------- caracteres
CHARSETS = {
    # ---- latín
    "minusculas": "abcdefghijklmnñopqrstuvwxyz",
    "mayusculas": "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ",
    "digitos": "0123456789",
    "acentos": "áéíóúüÁÉÍÓÚÜ",
    "puntuacion": ".,;:¿?¡!\"'“”()[]{}-–—_/\\@#$%&*+=<>|~^°…«»€",
    # ---- griego (las mayúsculas idénticas a las latinas, como Α Β Ε, se
    #      toman automáticamente de tus latinas: ver ALIAS más abajo)
    "griego_min": "αβγδεζηθικλμνξπρστυφχψωςϵϑϕϖϱ",
    "griego_may": "ΓΔΘΛΞΠΣΥΦΨΩ",
    # ---- matemáticas
    "operadores": "±∓×÷·∘∗⋆⊕⊗⊙†‡∧∨¬⊻",
    "relaciones": "≠≈≃≅≡≢∼≜≝∝≤≥≪≫≺≻⊥∥∣⊢⊨",
    "conjuntos": "∈∉∋⊂⊃⊆⊇⊊⊄∪∩∖∅ℕℤℚℝℂℙℵ∀∃∄",
    "calculo": "∂∇∫∬∭∮∯∑∏∐√∛∞′″ℏℓℒℋℱ∴∵∎∠",
    "flechas": "→←↔⇒⇐⇔↦↑↓⟶⇌↗↘",
    "delimitadores": "⟨⟩‖⌊⌋⌈⌉",
    "otros": "½⅓¼¾‰",
}
# Grupos para escribir menos en la línea de órdenes
GROUPS = {
    "latin": ["minusculas", "mayusculas"],
    "griego": ["griego_min", "griego_may"],
    "matematicas": ["operadores", "relaciones", "conjuntos", "calculo", "flechas", "delimitadores", "otros"],
}
DEFAULT_SETS = ("minusculas:8,mayusculas:8,digitos:8,acentos:4,puntuacion:4,"
                "griego_min:6,griego_may:6,matematicas:4")

# Caracteres que NO hace falta escribir porque se ven igual que otro.
# carácter -> carácter de origen
ALIAS = {
    # griego que coincide con el latín
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Χ": "X", "ο": "o",
    # símbolos duplicados en Unicode
    "∆": "Δ", "µ": "μ", "Ω": "Ω", "−": "-", "⋅": "·", "∶": ":", "‐": "-", "’": "'", "‘": "'",
    "ħ": "ℏ", "ϐ": "β", "⟹": "⇒", "⟸": "⇐", "⟺": "⇔", "⟼": "↦", "ϰ": "κ",
}


def parse_sets(spec: str, default_n: int = 10):
    """'minusculas:20,digitos:10,extra=xyz:3' -> [(char, n), ...] sin repetidos."""
    out, seen = [], set()
    parts = []
    for part in filter(None, (p.strip() for p in spec.split(","))):
        name, sep, n = part.partition(":")
        for sub in GROUPS.get(name, [name]):
            parts.append(sub + sep + n)
    for part in parts:
        name, _, n = part.partition(":")
        n = int(n) if n else default_n
        if n <= 0:
            continue
        if name.startswith("extra="):
            chars = name[len("extra="):]
        elif name in CHARSETS:
            chars = CHARSETS[name]
        else:
            raise SystemExit(f"Conjunto desconocido: {name!r}. Opciones: {', '.join(CHARSETS)} o extra=CARACTERES")
        for ch in chars:
            if ch not in seen and not ch.isspace():
                seen.add(ch)
                out.append((ch, n))
    return out


def glyph_filename(ch: str, i: int) -> str:
    return f"U{ord(ch):05X}_{i:03d}.png"


# ---------------------------------------------------------------- fuentes del sistema
# Solo se usan para las etiquetas de la plantilla y como respaldo de caracteres
# que no escribiste. Se buscan en Windows, macOS y Linux.
FONT_DIRS = [
    os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
    os.path.expanduser(r"~\AppData\Local\Microsoft\Windows\Fonts"),
    "/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts"),
    os.path.expanduser("~/.local/share/fonts"),
]
_FONT_INDEX = None


def _font_index():
    global _FONT_INDEX
    if _FONT_INDEX is None:
        _FONT_INDEX = {}
        for d in FONT_DIRS:
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith((".ttf", ".otf", ".ttc")):
                        _FONT_INDEX.setdefault(f.lower(), os.path.join(root, f))
    return _FONT_INDEX


def font_path(*names):
    """Primera fuente encontrada de la lista (sin distinguir mayúsculas)."""
    idx = _font_index()
    for n in names:
        p = idx.get(n.lower())
        if p:
            return p
    return None


# Equivalentes en macOS / Linux de las fuentes de Windows usadas
LABEL_FONTS = ["arial.ttf", "segoeui.ttf", "seguisym.ttf", "cambria.ttc", "times.ttf",
               "DejaVuSans.ttf", "NotoSans-Regular.ttf", "NotoSansMath-Regular.ttf",
               "NotoSansSymbols-Regular.ttf", "Arial Unicode.ttf", "STIXGeneral.otf",
               "STIXTwoMath-Regular.otf", "LiberationSans-Regular.ttf", "FreeSerif.ttf"]
HAND_FONTS = ["Inkfree.ttf", "segoesc.ttf", "Chalkboard.ttc", "Noteworthy.ttc", "MarkerFelt.ttc",
              "ComicNeue-Regular.ttf", "Caveat-Regular.ttf", "PatrickHand-Regular.ttf"]


def font_paths(names):
    return [p for p in (font_path(n) for n in names) if p]
