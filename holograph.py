"""holograph — write any text (math included) in YOUR own handwriting.

One command with subcommands, for people and for AI coding agents (Claude Code,
Codex, Cursor...). Every subcommand accepts --json and prints one JSON object.
Each subcommand has an English and a Spanish name (status = estado, ...).

  holograph status                    where am I and what next? (always start here)
  holograph template [--sets ...]     PDF with boxes to fill in by hand
  holograph import WRITTEN.pdf        extract your handwriting from the filled PDF
  holograph review                    contact sheet with all your samples
  holograph chars                     which characters you have / are missing
  holograph validate TEXT.txt         check the markup before rendering
  holograph write -f TEXT.txt -o out.pdf [--sheet] [--preview]
  holograph demo                      sample handwriting (no tablet needed) to try things
  holograph export hand.zip           back up your handwriting
  holograph app                       open the graphical interface (Spanish UI)

Run  holograph <command> -h  for its options.
Text format: docs/FORMAT.md   ·   Guide for AI agents: AGENTS.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

import comun as C

__version__ = "0.1.0"


# ------------------------------------------------------------------ salida
class Out:
    def __init__(self, as_json):
        self.as_json = as_json
        self.data = {"ok": True}

    def say(self, msg):
        if not self.as_json:
            print(msg)

    def put(self, **kw):
        self.data.update(kw)

    def done(self):
        if self.as_json:
            print(json.dumps(self.data, ensure_ascii=False, indent=1, default=str))
        return 0


def fail(out, msg, code=1):
    if out.as_json:
        print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
    return code


def _letra_dir(a):
    if getattr(a, "letra", None) == "demo":
        return os.path.join(C.DATA_DIR, "letra_demo")
    return a.letra or C.LETRA_DIR


def _index(letra_dir):
    p = Path(letra_dir) / "glifos.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


# ------------------------------------------------------------------ órdenes
def cmd_estado(a, out):
    letra_dir = _letra_dir(a)
    idx = _index(letra_dir)
    reg = Path(C.REGISTRY_DIR)
    templates = []
    imported = {g.get("session") for g in idx["glyphs"]} if idx else set()
    for f in sorted(reg.glob("*.json")) if reg.exists() else []:
        try:
            lay = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        templates.append({"id": lay["session"], "paginas": len(lay["pages"]),
                          "casillas": sum(len(p["cells"]) for p in lay["pages"]),
                          "importada": lay["session"] in imported})
    chars = {}
    if idx:
        for g in idx["glyphs"]:
            if (Path(letra_dir) / "glifos" / g["file"]).exists():
                chars[g["char"]] = chars.get(g["char"], 0) + 1
    if chars:
        etapa, siguiente = "lista", ("Tu letra está lista. Escribe con: holograph write -f texto.txt -o salida.pdf "
                                     "(o holograph app).")
    elif templates and not any(t["importada"] for t in templates):
        etapa, siguiente = "esperando_pdf_escrito", ("Hay una plantilla generada pero no importada. Escríbela en la "
                                                     "tableta (o imprímela), expórtala como PDF y ejecuta: "
                                                     "holograph import ESCRITO.pdf")
    else:
        etapa, siguiente = "sin_letra", ("No hay letra todavía. Ejecuta: holograph template  (o holograph demo para "
                                         "probar con una letra de ejemplo).")
    out.put(version=__version__, etapa=etapa, siguiente_paso=siguiente, carpeta_datos=C.DATA_DIR,
            carpeta_letra=letra_dir, caracteres=len(chars), muestras=sum(chars.values()),
            plantillas=templates, demo_disponible=(Path(C.DATA_DIR) / "letra_demo" / "glifos.json").exists())
    out.say(f"Holograph {__version__}\n  datos: {C.DATA_DIR}\n  letra: {letra_dir}")
    out.say(f"  caracteres: {len(chars)}   muestras: {sum(chars.values())}   plantillas: {len(templates)}")
    out.say(f"  etapa: {etapa}\n  siguiente paso: {siguiente}")
    return out.done()


def cmd_plantilla(a, out):
    import plantilla as P
    items = C.parse_sets(a.sets)
    dst = Path(a.out or os.path.join(C.DATA_DIR, "plantilla_mi_letra.pdf"))
    pages, cells, reg = P.build(items, dst, a.titulo, a.sets)
    out.put(pdf=str(dst.resolve()), paginas=pages, casillas=cells, caracteres=len(items), registro=str(reg),
            instrucciones="Envía el PDF a la tableta (Kindle Scribe: Send to Kindle; reMarkable/Boox/iPad: "
                          "como PDF), escribe un carácter por casilla sobre la línea continua, exporta el PDF "
                          "con lo escrito y ejecuta: holograph import ESCRITO.pdf")
    out.say(f"Plantilla: {dst}  ({pages} páginas, {cells} casillas, {len(items)} caracteres)")
    out.say("Siguiente: escríbela en la tableta, expórtala como PDF y ejecuta  holograph import ESCRITO.pdf")
    return out.done()


def cmd_importar(a, out):
    import extraer as X
    log = []
    try:
        data, n = X.import_pdf(a.pdf, Path(_letra_dir(a)), a.layout, log=log.append)
    except SystemExit as e:
        return fail(out, str(e))
    chars = {g["char"] for g in data["glyphs"]}
    no_rec = [l.strip() for l in log if "no reconocida" in l or "desconocida" in l]
    out.put(muestras_nuevas=n, muestras_totales=len(data["glyphs"]), caracteres=len(chars),
            paginas_omitidas=no_rec, revision=str(Path(_letra_dir(a)) / "revision.png"))
    for l in log:
        out.say(l)
    out.say(f"Listo: {n} muestras nuevas; total {len(data['glyphs'])} de {len(chars)} caracteres.")
    out.say(f"Revisa {Path(_letra_dir(a)) / 'revision.png'}")
    return out.done()


def cmd_revisar(a, out):
    import extraer as X
    idx = _index(_letra_dir(a))
    if not idx:
        return fail(out, "No hay letra. Ejecuta primero: holograph import ESCRITO.pdf (o holograph demo).")
    p = X.contact_sheet(Path(_letra_dir(a)), idx)
    out.put(revision=str(p))
    out.say(f"Hoja de revisión: {p}\nPara descartar una muestra: mueve su PNG a glifos/_descartados/ "
            "(o usa la pestaña Revisar de la app).")
    return out.done()


def _load_letra(a):
    import escribir as E
    return E.Letra(_letra_dir(a), acentos=not a.acentos_originales, signos=not a.signos_originales)


def cmd_caracteres(a, out):
    import escribir as E
    letra = _load_letra(a)
    have = sorted(letra.glyphs)
    derived = sorted(c for c in list(C.ALIAS) + list(E.DERIVED) if c not in letra.glyphs and letra.has(c))
    wanted = [c for c, _ in C.parse_sets(C.DEFAULT_SETS)]
    missing = [c for c in wanted if not letra.has(c)]
    out.put(con_muestras="".join(have), derivados="".join(derived), faltan="".join(missing),
            muestras_por_caracter={c: len(v) for c, v in letra.glyphs.items()})
    out.say(f"Con muestras ({len(have)}): {''.join(have)}")
    out.say(f"Derivados automáticamente ({len(derived)}): {''.join(derived)}")
    out.say(f"Faltan del conjunto estándar ({len(missing)}): {''.join(missing) or '—'}")
    return out.done()


def _read_text(a):
    if getattr(a, "archivo", None):
        return Path(a.archivo).read_text(encoding="utf-8-sig")
    if getattr(a, "texto", None):
        return a.texto
    if not sys.stdin.isatty():
        data = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        return data.replace("﻿", "").rstrip("\r\n") or None
    return None


def _check(text, letra):
    import formulas as F
    issues = [{"linea": l, "columna": c, "mensaje": m} for l, c, m in F.find_issues(text)]
    missing = set()

    def walk(nodes):
        for nd in nodes:
            if isinstance(nd, F.Ch):
                if not nd.ch.isspace() and not letra.has(nd.ch):
                    missing.add(nd.ch)
            elif isinstance(nd, F.Script):
                walk(nd.body)
            elif isinstance(nd, F.Frac):
                walk(nd.num), walk(nd.den)
            elif isinstance(nd, F.Sqrt):
                walk(nd.body)
                missing.update({"√"} - set(letra.glyphs))
            elif isinstance(nd, F.Mat):
                for row in nd.rows:
                    for cell in row:
                        walk(cell)
    walk(F.parse(text))
    return issues, sorted(missing)


def cmd_validar(a, out):
    text = _read_text(a)
    if text is None:
        return fail(out, "Falta el texto: holograph validate archivo.txt")
    letra = _load_letra(a)
    issues, missing = _check(text, letra)
    out.put(problemas=issues, sin_muestra="".join(missing), valido=not issues)
    for i in issues:
        out.say(f"  línea {i['linea']}, col {i['columna']}: {i['mensaje']}")
    if missing:
        out.say(f"  Sin muestras (se usará una fuente de respaldo): {' '.join(missing)}")
    out.say("Sin problemas de sintaxis." if not issues else f"{len(issues)} problema(s).")
    return out.done()


def cmd_escribir(a, out):
    import escribir as E
    text = _read_text(a)
    if text is None:
        return fail(out, "Falta el texto: holograph write \"Hola\" -o hola.png   o   -f archivo.txt")
    try:
        letra = _load_letra(a)
    except (FileNotFoundError, SystemExit):
        return fail(out, f"No hay letra en {_letra_dir(a)}. Ejecuta: holograph status")
    issues, missing = _check(text, letra)
    avisos = []
    color = COLOR_EN.get(a.color, a.color)
    papel = PAPER_EN.get(a.papel, a.papel)
    modo = MODE_EN.get(a.modo, a.modo)
    pages = E.render(text, letra, xh=a.tamano, ancho=1700, alto=2200 if a.hoja else None,
                     color=color, papel=papel, modo=modo, semilla=a.semilla,
                     inclinacion=a.inclinacion, desorden=a.desorden, espaciado=a.separacion,
                     interlineado=a.interlineado, formato=not a.literal, avisos=avisos)
    outs = [str(p) for p in E.save(pages, a.out)]
    vistas = []
    if a.vista:
        base = Path(a.out)
        for i, pg in enumerate(pages, 1):
            v = base.with_name(f"{base.stem}_vista_{i:02d}.png")
            pg.convert("RGB").resize((pg.width // 2, pg.height // 2)).save(v)
            vistas.append(str(v))
    out.put(archivos=outs, paginas=len(pages), vistas=vistas, sin_muestra="".join(missing),
            problemas=issues, avisos=avisos)
    for o in outs:
        out.say(f"OK: {o}")
    for v in avisos + [f"línea {i['linea']}: {i['mensaje']}" for i in issues]:
        out.say(f"Aviso: {v}")
    if missing:
        out.say(f"Sin muestras (fuente de respaldo): {' '.join(missing)}")
    return out.done()


def cmd_demo(a, out):
    """Letra de ejemplo hecha con fuentes del sistema: para probar sin tableta."""
    import tempfile

    import extraer as X
    import plantilla as P
    import simular as S
    dst = Path(C.DATA_DIR) / "letra_demo"
    with tempfile.TemporaryDirectory() as td:
        tpl = Path(td) / "demo.pdf"
        written = Path(td) / "demo_escrito.pdf"
        spec = "latin:3,digitos:3,acentos:2,puntuacion:2,griego:2,matematicas:2"
        P.build(C.parse_sets(spec), tpl, "Demo", spec)
        S.simulate(str(tpl), str(written), vacias=0.0)
        data, n = X.import_pdf(str(written), dst, log=lambda s: None)
    out.put(carpeta_letra=str(dst), muestras=n, uso="holograph write --hand demo -f text.txt -o test.pdf")
    out.say(f"Letra de demostración creada en {dst} ({n} muestras).")
    out.say("Pruébala:  holograph write --hand demo \"x^2 + \\frac{1}{2}\" -o prueba.png")
    return out.done()


def cmd_exportar(a, out):
    d = Path(_letra_dir(a))
    if not (d / "glifos.json").exists():
        return fail(out, "No hay letra que exportar.")
    with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(d / "glifos.json", "glifos.json")
        for f in (d / "glifos").glob("*.png"):
            z.write(f, f"glifos/{f.name}")
    out.put(zip=str(Path(a.zip).resolve()))
    out.say(f"Letra exportada a {a.zip}")
    return out.done()


def cmd_app(a, out):
    import app
    app.App().mainloop()
    return 0


# ------------------------------------------------------------------ argumentos
# Nombres en inglés (principales) y en español (alias). Valores también en ambos.
COLOR_EN = {"black": "negro", "blue": "azul", "ballpoint": "boli", "red": "rojo",
            "green": "verde", "graphite": "grafito"}
PAPER_EN = {"white": "blanco", "ruled": "rayado", "grid": "cuadriculado", "transparent": "transparente"}
MODE_EN = {"random": "aleatorio", "average": "promedio"}


def build_parser():
    ap = argparse.ArgumentParser(prog="holograph", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    def add(name, alias, fn, help_):
        p = sub.add_parser(name, aliases=[alias] if alias else [], help=help_, description=help_)
        p.add_argument("--json", action="store_true", help="machine-readable JSON output (for AI agents / scripts)")
        p.set_defaults(fn=fn)
        return p

    def hand_opt(p):
        p.add_argument("--hand", "--letra", dest="letra",
                       help="handwriting folder (default: data/mi_letra; 'demo' = sample handwriting)")

    def fix_opts(p):
        hand_opt(p)
        p.add_argument("--original-accents", "--acentos-originales", dest="acentos_originales",
                       action="store_true", help="keep your own accent marks instead of a clean acute accent")
        p.add_argument("--original-signs", "--signos-originales", dest="signos_originales",
                       action="store_true", help="do not center/rescale + − = < > …")

    p = add("status", "estado", cmd_estado, "where you are in the setup and what to do next")
    hand_opt(p)

    p = add("template", "plantilla", cmd_plantilla, "create the PDF template to fill in by hand")
    p.add_argument("--sets", default=C.DEFAULT_SETS,
                   help=f"set:samples,... Sets: {', '.join(C.CHARSETS)}; groups: "
                        f"{', '.join(C.GROUPS)}; extra=CHARS. Default: {C.DEFAULT_SETS}")
    p.add_argument("-o", "--out", help="PDF path (default: data/plantilla_mi_letra.pdf)")
    p.add_argument("--title", "--titulo", dest="titulo", default="Holograph")

    p = add("import", "importar", cmd_importar, "extract your handwriting from the filled-in PDF")
    p.add_argument("pdf")
    p.add_argument("--layout", help="only if the template was created on another computer: its .json")
    hand_opt(p)

    p = add("review", "revisar", cmd_revisar, "build the review sheet (revision.png)")
    hand_opt(p)

    p = add("chars", "caracteres", cmd_caracteres, "which characters you have and which are missing")
    fix_opts(p)

    p = add("validate", "validar", cmd_validar, "check a text's markup before rendering it")
    p.add_argument("archivo", nargs="?", metavar="FILE")
    p.add_argument("--text", "--texto", dest="texto")
    fix_opts(p)

    p = add("write", "escribir", cmd_escribir, "render text in your handwriting to PNG/PDF")
    p.add_argument("texto", nargs="?", metavar="TEXT", help="text to write (or use -f, or stdin)")
    p.add_argument("-f", "--file", "--archivo", dest="archivo", metavar="FILE", help="UTF-8 .txt file with text and formulas")
    p.add_argument("-o", "--out", required=True, help="output .pdf or .png (several pages -> _01, _02…)")
    p.add_argument("--sheet", "--hoja", dest="hoja", action="store_true", help="paginate into US-letter pages (1700×2200 px)")
    p.add_argument("--preview", "--vista", dest="vista", action="store_true",
                   help="also save half-size PNG previews of each page (to inspect the result)")
    p.add_argument("--size", "--tamano", dest="tamano", type=int, default=24, help="x-height in px (default 24)")
    p.add_argument("--color", default="blue", help=f"{', '.join(COLOR_EN)} (or Spanish names)")
    p.add_argument("--paper", "--papel", dest="papel", default="ruled",
                   choices=list(PAPER_EN) + list(PAPER_EN.values()))
    p.add_argument("--mode", "--modo", dest="modo", default="random",
                   choices=list(MODE_EN) + list(MODE_EN.values()))
    p.add_argument("--messiness", "--desorden", dest="desorden", type=float, default=1.0,
                   help="0 = rigid, 1 = natural, 2 = hurried")
    p.add_argument("--slant", "--inclinacion", dest="inclinacion", type=float, default=0.0,
                   help="extra slant in degrees (positive = to the right)")
    p.add_argument("--spacing", "--separacion", dest="separacion", type=float, default=0.12, help="letter spacing")
    p.add_argument("--line-height", "--interlineado", dest="interlineado", type=float, default=3.0,
                   help="distance between lines, in x-heights")
    p.add_argument("--seed", "--semilla", dest="semilla", type=int, help="fix the randomness (same output every time)")
    p.add_argument("--literal", action="store_true", help="do not interpret ^ _ \\frac \\pmat …")
    fix_opts(p)

    add("demo", None, cmd_demo, "create sample handwriting from system fonts (no tablet needed)")

    p = add("export", "exportar", cmd_exportar, "back up your handwriting to a .zip")
    p.add_argument("zip")
    hand_opt(p)

    add("app", None, cmd_app, "open the graphical interface")
    return ap

def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    a = build_parser().parse_args(argv)
    out = Out(getattr(a, "json", False))
    try:
        return a.fn(a, out)
    except FileNotFoundError as e:
        return fail(out, f"No se encontró: {e.filename or e}")
    except SystemExit as e:
        if isinstance(e.code, str):
            return fail(out, e.code)
        raise


if __name__ == "__main__":
    sys.exit(main())
