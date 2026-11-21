"""Mini-motor de fórmulas a mano: superíndices, subíndices, fracciones y matrices.

Sintaxis (parecida a LaTeX):
    x^2   e^{2t}   a_n   x_{p,1}         super/subíndices (se apilan: ∑_{n=1}^∞)
    \\frac{a}{b}                         fracción apilada
    \\pmat{a & b ; c & d}                matriz con paréntesis   ( ; = fila nueva, & = columna)
    \\bmat{...}   \\vmat{...}             con corchetes / barras de determinante
    \\pmat{1 ; 0}                         vector columna
    \\sqrt{x^2 + 1}                       raíz con raya encima
    \\^  \\_  \\{  \\}  \\&  \\$  \\\\          el carácter literal
Las llaves sueltas que no siguen a ^ _ o a un comando se escriben tal cual: mín{1, ε}.

También entiende lo más común de LaTeX (ver LATEX_SYMBOLS y preprocess):
\\alpha \\leq \\int \\infty \\cdot \\to \\Rightarrow \\mathbb{R} \\sin \\begin{pmatrix}…\\end{pmatrix},
\\dfrac, \\left( \\right), \\text{…}, \\, \\quad, y quita los $ que delimitan fórmulas.

Todo se mide en "unidades": 1 unidad = altura de la x de tu letra.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

import re

SUB_SUP_SCALE = 0.62
SHIFT = {1: 0.95, -1: -0.45}
COMMANDS = ("\\frac", "\\pmat", "\\bmat", "\\vmat", "\\sqrt")
BRACKETS = {"p": ("(", ")"), "b": ("[", "]"), "v": ("|", "|")}
# Operadores cuyos límites se escriben debajo/encima (como a mano), no al lado
BIG_OPS = set("∑∏∐⋃⋂")
LIMIT_WORDS = ("lim", "lím", "máx", "mín", "max", "min", "sup", "inf")

# Comandos de LaTeX que se convierten en un carácter (para que una IA pueda
# escribir como está acostumbrada).
LATEX_SYMBOLS = {
    # griego
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε",
    "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "pi": "π", "varpi": "ϖ", "rho": "ρ",
    "varrho": "ϱ", "sigma": "σ", "varsigma": "ς", "tau": "τ", "upsilon": "υ", "phi": "ϕ",
    "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π",
    "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ", "Omega": "Ω",
    # operadores y relaciones
    "pm": "±", "mp": "∓", "times": "×", "div": "÷", "cdot": "·", "circ": "∘", "ast": "∗",
    "star": "⋆", "oplus": "⊕", "otimes": "⊗", "odot": "⊙", "dagger": "†", "ddagger": "‡",
    "wedge": "∧", "land": "∧", "vee": "∨", "lor": "∨", "neg": "¬", "lnot": "¬", "setminus": "∖",
    "neq": "≠", "ne": "≠", "approx": "≈", "simeq": "≃", "cong": "≅", "equiv": "≡", "sim": "∼",
    "propto": "∝", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "ll": "≪", "gg": "≫",
    "prec": "≺", "succ": "≻", "perp": "⊥", "parallel": "∥", "mid": "∣", "vdash": "⊢",
    "models": "⊨", "triangleq": "≜",
    # conjuntos y lógica
    "in": "∈", "notin": "∉", "ni": "∋", "subset": "⊂", "supset": "⊃", "subseteq": "⊆",
    "supseteq": "⊇", "subsetneq": "⊊", "cup": "∪", "cap": "∩", "emptyset": "∅",
    "varnothing": "∅", "forall": "∀", "exists": "∃", "nexists": "∄", "aleph": "ℵ",
    # cálculo
    "partial": "∂", "nabla": "∇", "int": "∫", "iint": "∬", "iiint": "∭", "oint": "∮",
    "oiint": "∯", "sum": "∑", "prod": "∏", "coprod": "∐", "infty": "∞", "prime": "′",
    "hbar": "ℏ", "ell": "ℓ", "therefore": "∴", "because": "∵", "qed": "∎", "angle": "∠",
    "degree": "°",
    # flechas
    "to": "→", "rightarrow": "→", "leftarrow": "←", "gets": "←", "leftrightarrow": "↔",
    "Rightarrow": "⇒", "implies": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔", "iff": "⇔",
    "mapsto": "↦", "uparrow": "↑", "downarrow": "↓", "longrightarrow": "⟶",
    "rightleftharpoons": "⇌", "nearrow": "↗", "searrow": "↘",
    # delimitadores y puntos
    "langle": "⟨", "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉",
    "|": "‖", "Vert": "‖", "vert": "|", "ldots": "…", "dots": "…", "cdots": "…",
    "lbrace": "{", "rbrace": "}", "{": "{", "}": "}", "%": "%", "$": "$", "#": "#",
    # funciones (se escriben como texto)
    **{f: f for f in ("sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
                      "sinh", "cosh", "tanh", "log", "ln", "exp", "det", "lim", "max", "min",
                      "sup", "inf", "dim", "ker", "deg", "gcd", "arg", "Re", "Im", "tr")},
}
SPACES = {",": " ", ";": " ", ":": " ", "quad": "  ", "qquad": "    ", " ": " ", "!": ""}
BLACKBOARD = {"R": "ℝ", "N": "ℕ", "Z": "ℤ", "Q": "ℚ", "C": "ℂ", "P": "ℙ"}
_ENV = re.compile(r"\\begin\{([pbvB]?matrix|cases)\}(.*?)\\end\{\1\}", re.S)


def preprocess(text):
    """Traduce lo más común de LaTeX al formato propio."""
    def env(m):
        kind, body = m.group(1), m.group(2)
        rows = [r.strip() for r in re.split(r"\\\\", body) if r.strip()]
        inner = " ; ".join(rows)
        k = {"pmatrix": "p", "bmatrix": "b", "vmatrix": "v", "Bmatrix": "b", "matrix": "p", "cases": "b"}[kind]
        return f"\\{k}mat{{{inner}}}"
    text = _ENV.sub(env, text)
    text = re.sub(r"\\[dt]frac\{", r"\\frac{", text)
    text = re.sub(r"\\mathbb\{([A-Z])\}", lambda m: BLACKBOARD.get(m.group(1), m.group(1)), text)
    text = re.sub(r"\\(?:text|mathrm|mathbf|mathit|operatorname|textrm|mbox)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)(?=[()\[\]|.]|\\[{}|])", "", text)
    text = re.sub(r"\\(?:left|right)\.", "", text)
    text = re.sub(r"(?<!\\)\$", "", text)           # $…$ de LaTeX: se quitan (\$ = dólar)
    text = re.sub(r"\\[()\[\]]", "", text)         # \( \) \[ \] también son delimitadores
    text = text.replace("\ufeff", "")
    return text


def find_issues(text):
    """Problemas de sintaxis: [(línea, columna, mensaje)]."""
    issues = []
    for ln, line in enumerate(preprocess(text).split("\n"), 1):
        depth = 0
        for col, c in enumerate(line, 1):
            if c == "{" and (col < 2 or line[col - 2] != "\\"):
                depth += 1
            elif c == "}" and (col < 2 or line[col - 2] != "\\"):
                depth -= 1
                if depth < 0:
                    issues.append((ln, col, "llave '}' sin abrir"))
                    depth = 0
        if depth > 0:
            issues.append((ln, len(line), f"{depth} llave(s) '{{' sin cerrar"))
        for m in re.finditer(r"\\([A-Za-z]+)", line):
            name = m.group(1)
            if "\\" + name not in COMMANDS and name not in LATEX_SYMBOLS and name not in SPACES:
                issues.append((ln, m.start() + 1, f"comando desconocido \\{name} (se escribirá literal)"))
    return issues


# ------------------------------------------------------------------ árbol
@dataclass
class Ch:
    ch: str


@dataclass
class Script:
    pos: int            # 1 super, -1 sub
    body: list


@dataclass
class Frac:
    num: list
    den: list


@dataclass
class Sqrt:
    body: list


@dataclass
class Mat:
    rows: list          # [[celda(lista de nodos), ...], ...]
    kind: str = "p"


def _match(s, i):
    """s[i] == '{' -> índice de su '}' (respeta anidamiento y escapes)."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\" and j + 1 < len(s):
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def _split_top(s, sep):
    parts, depth, cur, j = [], 0, [], 0
    while j < len(s):
        c = s[j]
        if c == "\\" and j + 1 < len(s):
            cur.append(s[j:j + 2])
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if c == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
        j += 1
    parts.append("".join(cur))
    return parts


def _one(text, i):
    """Lee UN nodo que empieza en text[i]. Devuelve (nodo, índice siguiente)."""
    n = len(text)
    c = text[i]
    if c == "\\":
        cmd = next((k for k in COMMANDS if text.startswith(k + "{", i)), None)
        if cmd:
            j = _match(text, i + len(cmd))
            if j != -1:
                inner = text[i + len(cmd) + 1:j]
                if cmd == "\\frac":
                    if j + 1 < n and text[j + 1] == "{":
                        k = _match(text, j + 1)
                        if k != -1:
                            return Frac(_seq(inner), _seq(text[j + 2:k])), k + 1
                elif cmd == "\\sqrt":
                    return Sqrt(_seq(inner)), j + 1
                else:
                    rows = [[_seq(cell.strip()) for cell in _split_top(r, "&")]
                            for r in _split_top(inner, ";")]
                    return Mat(rows, cmd[1]), j + 1
        m = re.match(r"\\([A-Za-z]+)", text[i:])
        if m and m.group(1) in LATEX_SYMBOLS:
            sym = LATEX_SYMBOLS[m.group(1)]
            k = i + len(m.group(0))
            # el espacio que sigue al comando se conserva: \alpha \in A -> "α ∈ A"
            return (Ch(sym) if len(sym) == 1 else _Word(sym)), k
        if m and m.group(1) in SPACES:
            return _Word(SPACES[m.group(1)]), i + len(m.group(0))
        if i + 1 < n and text[i + 1] in SPACES:
            return _Word(SPACES[text[i + 1]]), i + 2
        if i + 1 < n and text[i + 1] == "|":
            return Ch("‖"), i + 2
        if i + 1 < n and text[i + 1] in "^_{}&\\$%#":
            return Ch(text[i + 1]), i + 2
    if c in "^_" and i + 1 < n and text[i + 1] not in " \n^_":
        pos = 1 if c == "^" else -1
        if text[i + 1] == "{":
            j = _match(text, i + 1)
            if j != -1:
                return Script(pos, _seq(text[i + 2:j])), j + 1
        body, k = _one(text, i + 1)                     # x^2, x^\frac{1}{2}, x^\alpha
        return Script(pos, body.chars if isinstance(body, _Word) else [body]), k
    return Ch(c), i + 1


class _Word:
    """Varios caracteres que salen de un solo comando (\\sin, \\quad...)."""
    def __init__(self, s):
        self.chars = [Ch(c) for c in s]


def _seq(text):
    out, i = [], 0
    while i < len(text):
        nd, i = _one(text, i)
        if isinstance(nd, _Word):
            out.extend(nd.chars)
        else:
            out.append(nd)
    return out


def parse(text, enabled=True):
    if not enabled:
        return [Ch(c) for c in text]
    return _seq(preprocess(text))


def split_top(nodes, ch):
    """Parte una lista de nodos por un carácter de primer nivel (espacio, salto)."""
    parts, cur = [], []
    for nd in nodes:
        if isinstance(nd, Ch) and nd.ch == ch:
            parts.append(cur)
            cur = []
        else:
            cur.append(nd)
    parts.append(cur)
    return parts


# ------------------------------------------------------------------ cajas
@dataclass
class Box:
    items: list = field(default_factory=list)   # (x, dy, glyph, scale) en unidades
    w: float = 0.0
    asc: float = 0.0       # lo más alto  (sobre la línea base)
    desc: float = 0.0      # lo más bajo  (negativo si baja de la línea base)
    tall: bool = False     # contiene una matriz/vector: necesita aire vertical de verdad

    def add(self, other: "Box", dx, ddy):
        self.tall = self.tall or other.tall
        for x, dy, g, s in other.items:
            self.items.append((x + dx, dy + ddy, g, s))
        if other.items:
            self.asc = max(self.asc, other.asc + ddy)
            self.desc = min(self.desc, other.desc + ddy)


def _stretch(g, fx=1.0, fy=1.0):
    """Copia del glifo estirada (fx en ancho, fy en alto). La base queda abajo."""
    from escribir import Glyph
    w = max(1, round(g.img.width * fx))
    h = max(1, round(g.img.height * fy))
    img = g.img.resize((w, h), Image.LANCZOS)
    return Glyph(img, g.unit_px, h / g.unit_px, w / g.unit_px)


class Layout:
    def __init__(self, letra, rnd, bags, mode, espaciado, var_tamano, axis, word_space=1.0):
        self.letra, self.rnd, self.bags, self.mode = letra, rnd, bags, mode
        self.gap, self.var, self.axis = espaciado, var_tamano, axis
        self.word_space = word_space

    # -------------------------------------------------------------- nodos
    def _op_len(self, nodes, i):
        """¿Empieza en i un operador cuyos límites van debajo/encima? -> nº de nodos."""
        nd = nodes[i]
        n = len(nodes)
        if isinstance(nd, Ch) and nd.ch in BIG_OPS and i + 1 < n and isinstance(nodes[i + 1], Script):
            return 1
        for word in LIMIT_WORDS:
            k = len(word)
            if (i + k < n and isinstance(nodes[i + k], Script) and nodes[i + k].pos < 0
                    and all(isinstance(nodes[i + j], Ch) and nodes[i + j].ch == word[j] for j in range(k))
                    and not (i > 0 and isinstance(nodes[i - 1], Ch) and nodes[i - 1].ch.isalpha())):
                return k
        return 0

    def _with_limits(self, nodes, i, k, s):
        """Operador (∑, ∏, lim…) con sus límites centrados debajo y encima."""
        big = k == 1
        op = self.seq(nodes[i:i + k], s * (1.3 if big else 1.0))
        j, lims = i + k, []
        while j < len(nodes) and isinstance(nodes[j], Script) and len(lims) < 2:
            lims.append((nodes[j].pos, self.seq(nodes[j].body, s * SUB_SUP_SCALE)))
            j += 1
        W = max([op.w] + [b.w for _, b in lims])
        out = Box()
        out.add(op, (W - op.w) / 2, 0)
        for pos, b in lims:
            dy = (op.desc - 0.12 * s - b.asc) if pos < 0 else (op.asc + 0.1 * s - b.desc)
            out.add(b, (W - b.w) / 2, dy)
        out.w = W
        out.tall = bool(lims)
        return out, j

    def seq(self, nodes, s=1.0) -> Box:
        box, x = Box(), 0.0
        last_gap = 0.0
        prev_script = None          # (pos, x_inicio, x_fin) para apilar sub/super
        i = 0
        while i < len(nodes):
            nd = nodes[i]
            i += 1
            if isinstance(nd, Ch) and nd.ch == " ":
                x += self.letra.space_u * s * self.word_space
                last_gap = 0.0
                prev_script = None
                continue
            k = self._op_len(nodes, i - 1)
            if k:
                b, i = self._with_limits(nodes, i - 1, k, s)
                box.add(b, x, 0)
                last_gap = self.gap * s
                x += b.w + last_gap
                prev_script = None
                continue
            b = self.node(nd, s)
            if isinstance(nd, Script) and prev_script and prev_script[0] != nd.pos and not prev_script[3]:
                xs = prev_script[1]                      # apilar sobre el anterior
                box.add(b, xs, 0)
                x = max(prev_script[2], xs + b.w) + self.gap * s
                prev_script = (nd.pos, xs, x - self.gap * s, True)
                continue
            box.add(b, x, 0)
            start = x
            last_gap = self.gap * s * (0.62 if isinstance(nd, Script) else 1) + self.rnd.gauss(0, 0.03) * s
            x += b.w + last_gap
            prev_script = (nd.pos, start, start + b.w, False) if isinstance(nd, Script) else None
        box.w = max(0.0, x - last_gap)
        return box

    def node(self, nd, s):
        if isinstance(nd, Ch):
            return self.char(nd.ch, s)
        if isinstance(nd, Script):
            b = self.seq(nd.body, s * SUB_SUP_SCALE)
            out = Box()
            out.add(b, 0, SHIFT[nd.pos] * s)
            out.w = b.w
            return out
        if isinstance(nd, Frac):
            return self.frac(nd, s)
        if isinstance(nd, Mat):
            return self.mat(nd, s)
        if isinstance(nd, Sqrt):
            return self.sqrt(nd, s)
        raise TypeError(nd)

    def sqrt(self, nd, s):
        """√ estirado a la altura del contenido + raya encima (con tus trazos)."""
        body = self.seq(nd.body, s)
        top = max(body.asc, 1.0 * s) + 0.18 * s
        bottom = min(body.desc, 0.0) - 0.08 * s
        g = self.letra.variant("√", self.rnd, self.bags, self.mode)
        gh = g.img.height / g.unit_px
        fy = (top - bottom) / (gh * s)
        root = _stretch(g, fx=min(1.4, max(0.8, fy ** 0.3)), fy=fy)
        rw = root.img.width / root.unit_px * s
        out = Box()
        out.add(Box([(0.0, bottom, root, s)], rw, top, bottom), 0, 0)
        x = rw * 0.92
        out.add(self.hbar(body.w + 0.25 * s, s * 0.8, top - 0.02 * s), x - 0.05 * s, 0)
        out.add(body, x + 0.12 * s, 0)
        out.w = x + body.w + 0.25 * s
        return out

    def char(self, ch, s):
        g = self.letra.variant(ch, self.rnd, self.bags, self.mode)
        sc = s * (1 + self.rnd.gauss(0, self.var))
        h = g.img.height / g.unit_px
        b = Box([(0.0, 0.0, g, sc)], g.img.width / g.unit_px * sc, g.top_u * sc, (g.top_u - h) * sc)
        return b

    def hbar(self, width, s, center_y):
        """Raya horizontal hecha con tu propio guion, estirado al ancho pedido."""
        g = self.letra.variant("-", self.rnd, self.bags, self.mode)
        gw = g.img.width / g.unit_px
        bar = _stretch(g, fx=max(0.2, width / (gw * s)))
        h = bar.img.height / bar.unit_px
        dy = center_y - (bar.top_u - h / 2) * s
        return Box([(0.0, dy, bar, s)], width, dy + bar.top_u * s, dy + (bar.top_u - h) * s)

    def frac(self, nd, s):
        k = 0.78 if s > 0.7 else 0.9
        num, den = self.seq(nd.num, s * k), self.seq(nd.den, s * k)
        A = self.axis * s
        W = max(num.w, den.w) + 0.35 * s
        out = Box()
        out.add(self.hbar(W, s, A), 0, 0)
        out.add(num, (W - num.w) / 2, A + 0.28 * s - num.desc)
        out.add(den, (W - den.w) / 2, A - 0.30 * s - den.asc)
        out.w = W
        return out

    def mat(self, nd, s):
        cs = s * 0.9
        cells = [[self.seq(c, cs) for c in row] for row in nd.rows]
        ncol = max(len(r) for r in cells)
        colw = [max((r[j].w for r in cells if j < len(r)), default=0) for j in range(ncol)]
        row_asc = [max([c.asc for c in r] + [1.0 * cs]) for r in cells]
        row_desc = [min([c.desc for c in r] + [0.0]) for r in cells]
        rgap, cgap = 0.5 * s, 1.0 * s
        H = sum(a - d for a, d in zip(row_asc, row_desc)) + rgap * (len(cells) - 1)
        A = self.axis * s
        top = A + H / 2
        inner = Box()
        y = top
        for r, a, d in zip(cells, row_asc, row_desc):
            base = y - a
            x = 0.0
            for j, c in enumerate(r):
                inner.add(c, x + (colw[j] - c.w) / 2, base)
                x += colw[j] + cgap
            y = base + d - rgap
        inner.w = sum(colw) + cgap * (ncol - 1)

        out = Box()
        lch, rch = BRACKETS[nd.kind]
        ext = 0.35 * s
        BH = H + 2 * ext
        x = 0.0
        for side, ch in (("l", lch), ("r", rch)):
            g = self.letra.variant(ch, self.rnd, self.bags, self.mode)
            gh = g.img.height / g.unit_px
            fy = BH / (gh * s)
            fx = min(1.7, 1 + 0.12 * (fy - 1))
            br = _stretch(g, fx=fx, fy=fy)
            bw = br.img.width / br.unit_px * s
            bbox = Box([(0.0, A - BH / 2, br, s)], bw, A + BH / 2, A - BH / 2)
            if side == "l":
                out.add(bbox, 0, 0)
                x = bw + 0.3 * s
                out.add(inner, x, 0)
                x += inner.w + 0.3 * s
            else:
                out.add(bbox, x, 0)
                x += bw
        out.w = x
        out.tall = True
        return out
