"""miletra — escribe cualquier texto (con fórmulas) usando TU letra.

Una sola orden con subórdenes. Pensada para personas y para asistentes de IA
(Claude Code, Codex, Cursor...): todas aceptan --json y devuelven un objeto JSON.

  miletra estado                     ¿en qué paso estoy? (empieza siempre por aquí)
  miletra plantilla [--sets ...]     crea el PDF con casillas para escribir a mano
  miletra importar ESCRITO.pdf       extrae tu letra del PDF ya escrito
  miletra revisar                    hoja de contacto con todas tus muestras
  miletra caracteres                 qué caracteres tienes y cuáles faltan
  miletra validar TEXTO.txt          revisa la sintaxis antes de generar
  miletra escribir -f TEXTO.txt -o salida.pdf [--hoja] [--vista]
  miletra demo                       crea una letra de prueba (sin tableta) para ensayar
  miletra exportar letra.zip         copia de seguridad de tu letra
  miletra app                        abre la interfaz gráfica

Ejecuta  miletra <orden> -h  para ver las opciones de cada una.
Formato del texto: docs/FORMATO.md   ·   Guía para IA: AGENTS.md
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
        etapa, siguiente = "lista", ("Tu letra está lista. Escribe con: miletra escribir -f texto.txt -o salida.pdf "
                                     "(o miletra app).")
    elif templates and not any(t["importada"] for t in templates):
        etapa, siguiente = "esperando_pdf_escrito", ("Hay una plantilla generada pero no importada. Escríbela en la "
                                                     "tableta (o imprímela), expórtala como PDF y ejecuta: "
                                                     "miletra importar ESCRITO.pdf")
    else:
        etapa, siguiente = "sin_letra", ("No hay letra todavía. Ejecuta: miletra plantilla  (o miletra demo para "
                                         "probar con una letra de ejemplo).")
    out.put(version=__version__, etapa=etapa, siguiente_paso=siguiente, carpeta_datos=C.DATA_DIR,
            carpeta_letra=letra_dir, caracteres=len(chars), muestras=sum(chars.values()),
            plantillas=templates, demo_disponible=(Path(C.DATA_DIR) / "letra_demo" / "glifos.json").exists())
    out.say(f"Mi letra {__version__}\n  datos: {C.DATA_DIR}\n  letra: {letra_dir}")
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
                          "con lo escrito y ejecuta: miletra importar ESCRITO.pdf")
    out.say(f"Plantilla: {dst}  ({pages} páginas, {cells} casillas, {len(items)} caracteres)")
    out.say("Siguiente: escríbela en la tableta, expórtala como PDF y ejecuta  miletra importar ESCRITO.pdf")
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
        return fail(out, "No hay letra. Ejecuta primero: miletra importar ESCRITO.pdf (o miletra demo).")
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
        return fail(out, "Falta el texto: miletra validar archivo.txt")
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
        return fail(out, "Falta el texto: miletra escribir \"Hola\" -o hola.png   o   -f archivo.txt")
    try:
        letra = _load_letra(a)
    except (FileNotFoundError, SystemExit):
        return fail(out, f"No hay letra en {_letra_dir(a)}. Ejecuta: miletra estado")
    issues, missing = _check(text, letra)
    avisos = []
    pages = E.render(text, letra, xh=a.tamano, ancho=1700, alto=2200 if a.hoja else None,
                     color=a.color, papel=a.papel, modo=a.modo, semilla=a.semilla,
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
    out.put(carpeta_letra=str(dst), muestras=n, uso="miletra escribir --letra demo -f texto.txt -o prueba.pdf")
    out.say(f"Letra de demostración creada en {dst} ({n} muestras).")
    out.say("Pruébala:  miletra escribir --letra demo \"x^2 + \\frac{1}{2}\" -o prueba.png")
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
def build_parser():
    ap = argparse.ArgumentParser(prog="miletra", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_):
        p = sub.add_parser(name, help=help_, description=help_)
        p.add_argument("--json", action="store_true", help="salida en JSON (para IA / scripts)")
        p.set_defaults(fn=fn)
        return p

    def letra_opts(p):
        p.add_argument("--letra", help="carpeta de letra (por defecto datos/mi_letra; «demo» = letra de prueba)")
        p.add_argument("--acentos-originales", action="store_true", help="no sustituir tus acentos por tilde")
        p.add_argument("--signos-originales", action="store_true", help="no centrar ni escalar + − = …")

    p = add("estado", cmd_estado, "en qué paso estás y qué hacer después")
    p.add_argument("--letra")

    p = add("plantilla", cmd_plantilla, "crear el PDF con casillas para escribir a mano")
    p.add_argument("--sets", default=C.DEFAULT_SETS,
                   help=f"conjunto:muestras,... Conjuntos: {', '.join(C.CHARSETS)}; grupos: "
                        f"{', '.join(C.GROUPS)}; extra=CARACTERES. Por defecto: {C.DEFAULT_SETS}")
    p.add_argument("-o", "--out", help="ruta del PDF (por defecto datos/plantilla_mi_letra.pdf)")
    p.add_argument("--titulo", default="Mi letra")

    p = add("importar", cmd_importar, "extraer tu letra del PDF escrito (basta con el PDF)")
    p.add_argument("pdf")
    p.add_argument("--layout", help="solo si la plantilla se creó en otra computadora: su .json")
    p.add_argument("--letra")

    p = add("revisar", cmd_revisar, "generar la hoja de revisión (revision.png)")
    p.add_argument("--letra")

    p = add("caracteres", cmd_caracteres, "qué caracteres tienes y cuáles faltan")
    letra_opts(p)

    p = add("validar", cmd_validar, "revisar la sintaxis de un texto antes de generarlo")
    p.add_argument("archivo", nargs="?")
    p.add_argument("--texto")
    letra_opts(p)

    p = add("escribir", cmd_escribir, "generar PNG/PDF con tu letra")
    p.add_argument("texto", nargs="?", help="texto directo (o usa -f, o stdin)")
    p.add_argument("-f", "--archivo", help="archivo .txt (UTF-8) con el texto y fórmulas")
    p.add_argument("-o", "--out", required=True, help="salida .pdf o .png (varias hojas -> _01, _02…)")
    p.add_argument("--hoja", action="store_true", help="paginar en hojas carta (1700×2200 px)")
    p.add_argument("--vista", action="store_true", help="además, PNG a media resolución de cada hoja (para revisar)")
    p.add_argument("--tamano", type=int, default=24, help="altura de la x en px (por defecto 24)")
    p.add_argument("--color", default="azul", help="negro, azul, boli, rojo, verde, grafito")
    p.add_argument("--papel", default="rayado", choices=("blanco", "rayado", "cuadriculado", "transparente"))
    p.add_argument("--modo", default="aleatorio", choices=("aleatorio", "promedio"))
    p.add_argument("--desorden", type=float, default=1.0, help="0 = rígido, 1 = natural, 2 = con prisa")
    p.add_argument("--inclinacion", type=float, default=0.0, help="grados (positivo = a la derecha)")
    p.add_argument("--separacion", type=float, default=0.12, help="separación entre letras")
    p.add_argument("--interlineado", type=float, default=3.0, help="distancia entre renglones (en alturas de x)")
    p.add_argument("--semilla", type=int, help="fija el azar (mismo resultado cada vez)")
    p.add_argument("--literal", action="store_true", help="no interpretar ^ _ \\frac \\pmat …")
    letra_opts(p)

    add("demo", cmd_demo, "crear una letra de prueba con fuentes del sistema (sin tableta)")

    p = add("exportar", cmd_exportar, "guardar tu letra en un .zip")
    p.add_argument("zip")
    p.add_argument("--letra")

    add("app", cmd_app, "abrir la interfaz gráfica")
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
