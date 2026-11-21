"""Pruebas de punta a punta. Usan una carpeta de datos temporal (HOLOGRAPH_HOME),
así que nunca tocan tu letra real."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(args, home, check=True):
    env = dict(os.environ, HOLOGRAPH_HOME=str(home), PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "holograph.py"), *args, "--json"],
                       capture_output=True, text=True, encoding="utf-8", env=env, cwd=ROOT)
    data = json.loads(r.stdout)
    if check:
        assert data["ok"], data
    return data


# ---------------------------------------------------------------- formato
def test_parser_estructuras():
    import formulas as F
    nodes = F.parse(r"x^2 + \frac{1}{2} \pmat{a & b ; c & d} \sqrt{y}")
    kinds = {type(n).__name__ for n in nodes}
    assert {"Script", "Frac", "Mat", "Sqrt"} <= kinds
    mat = next(n for n in nodes if isinstance(n, F.Mat))
    assert len(mat.rows) == 2 and len(mat.rows[0]) == 2


def test_latex_se_traduce():
    import formulas as F
    t = r"$\alpha \leq \int_0^\infty$ \begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix} \mathbb{R} \(x\)"
    pre = F.preprocess(t)
    assert "$" not in pre and r"\pmat{1 & 0 ; 0 & 1}" in pre and "ℝ" in pre and "\\(" not in pre
    chars = "".join(n.ch for n in F.parse(t) if isinstance(n, F.Ch))
    assert "α" in chars and "≤" in chars and "∫" in chars


def test_validar_detecta_errores():
    import formulas as F
    issues = F.find_issues(r"\frac{1}{2 y \noexiste{x}")
    msgs = " ".join(m for _, _, m in issues)
    assert "sin cerrar" in msgs and "noexiste" in msgs


def test_codigo_de_pagina_ida_y_vuelta():
    import comun as C
    for p, s in [(0, "000001"), (29, "f66f19"), (500, "abcdef")]:
        assert C.decode_code(C.encode_code(p, s)) == (p, s)


# ---------------------------------------------------------------- flujo completo
@pytest.fixture(scope="module")
def home(tmp_path_factory):
    h = tmp_path_factory.mktemp("holograph_home")
    run(["demo"], h)
    return h


def test_demo_no_altera_estado(home):
    d = run(["status"], home)
    assert d["etapa"] == "sin_letra" and d["plantillas"] == [] and d["demo_disponible"]


def test_limites_debajo_y_encima():
    import formulas as F
    lay = F.Layout.__new__(F.Layout)
    nodes = F.parse(r"\sum_{n=1}^\infty a_n + \lim_{x \to 0} f + mín{1, 2} + x_i^2")
    ops = [i for i in range(len(nodes)) if lay._op_len(nodes, i)]
    chars = [nodes[i].ch for i in ops]
    assert chars == ["∑", "l"]            # ∑ y lim; ni «mín{» (sin índice) ni x_i


def test_estado_sin_letra(tmp_path):
    d = run(["estado"], tmp_path)
    assert d["etapa"] == "sin_letra"


def test_plantilla_simular_importar(tmp_path):
    import simular as S
    d = run(["plantilla", "--sets", "minusculas:2,digitos:2", "-o", str(tmp_path / "p.pdf")], tmp_path)
    assert d["paginas"] >= 1
    assert run(["estado"], tmp_path)["etapa"] == "esperando_pdf_escrito"
    S.simulate(str(tmp_path / "p.pdf"), str(tmp_path / "e.pdf"), vacias=0.0)
    d = run(["importar", str(tmp_path / "e.pdf")], tmp_path)
    assert d["muestras_nuevas"] == d["muestras_totales"] > 50
    assert run(["estado"], tmp_path)["etapa"] == "lista"


def test_escribir_con_formulas(home, tmp_path):
    txt = tmp_path / "t.txt"
    txt.write_text("Sea X′ = \\pmat{2 & 0 ; 0 & −1} X + \\pmat{e^{2t} ; 2}\n"
                   "u = −\\frac{1}{6}e^{2t},  \\sqrt{x^2 + 1},  ∑_{n=1}^∞ 1/n^2\n", encoding="utf-8")
    v = run(["validar", str(txt), "--letra", "demo"], home)
    assert v["valido"]
    out = tmp_path / "s.pdf"
    d = run(["escribir", "-f", str(txt), "-o", str(out), "--hoja", "--vista", "--letra", "demo"], home)
    assert d["paginas"] == 1 and out.exists() and len(d["vistas"]) == 1


def test_error_en_json(tmp_path):
    d = run(["escribir", "hola", "-o", str(tmp_path / "x.png")], tmp_path, check=False)
    assert d["ok"] is False and "letra" in d["error"].lower()
