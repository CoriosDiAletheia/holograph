"""Mi letra — programa principal.

    Doble clic en iniciar.bat   (o:  python app.py)

Pestañas:
  1 · Plantilla   elige qué caracteres y cuántas muestras, y crea el PDF.
  2 · Importar    adjunta el PDF que escribiste en la Kindle: se extrae todo.
  3 · Revisar     mira cada muestra; clic para descartar/recuperar las feas.
  4 · Escribir    teclea y obtén el texto con tu letra (copiar, PNG, PDF).
Menú Letra: exportar/importar tu letra como .zip (copia de seguridad o
para usarla en otra computadora).
"""
from __future__ import annotations

import sys

try:
    import ctypes
    import io
    import json
    import os
    import queue
    import shutil
    import threading
    import tkinter as tk
    import zipfile
    from pathlib import Path
    from tkinter import colorchooser, filedialog, messagebox, ttk

    from PIL import Image, ImageTk

    import comun as C
    import escribir as E
    import extraer as X
    import plantilla as P
except ImportError as e:  # faltan dependencias
    import tkinter.messagebox as mb
    mb.showerror("Mi letra", f"Falta una librería: {e}.\n\nEjecuta instalar.bat una vez y vuelve a abrir.")
    sys.exit(1)

APP = Path(C.APP_DIR)
DATA = Path(C.DATA_DIR)
CONFIG = Path(C.CONFIG_PATH)


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def copy_image_to_clipboard(img: Image.Image):
    """Copia una imagen PIL al portapapeles de Windows (formato DIB)."""
    if sys.platform != "win32":
        raise OSError("Copiar imagen solo está disponible en Windows; usa «PNG…» para guardarla.")
    buf = io.BytesIO()
    bg = Image.new("RGB", img.size, "white")
    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
    bg.save(buf, "BMP")
    data = buf.getvalue()[14:]
    k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    h = k32.GlobalAlloc(0x0002, len(data))
    p = k32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    k32.GlobalUnlock(h)
    u32.OpenClipboard(None)
    u32.EmptyClipboard()
    u32.SetClipboardData(8, h)
    u32.CloseClipboard()


def open_path(p):
    try:
        os.startfile(str(p))
    except OSError as e:
        if str(p).lower().endswith((".md", ".txt", ".json")):
            import subprocess
            subprocess.Popen(["notepad.exe", str(p)])
        else:
            messagebox.showerror("Mi letra", str(e))


class ScrollCanvas(ttk.Frame):
    def __init__(self, master, bg="#e4e4e4"):
        super().__init__(master)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all(
            "<MouseWheel>", lambda ev: self.canvas.yview_scroll(-ev.delta // 120 * 3, "units")))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))


# ===================================================================== app
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mi letra")
        self.geometry("1200x700")
        self.minsize(900, 560)
        try:
            self.state("zoomed")            # maximizada
        except tk.TclError:
            pass
        try:
            ttk.Style().theme_use("vista")
        except tk.TclError:
            pass
        self.cfg = load_config()
        self.letra_dir = Path(self.cfg.get("letra_dir", C.LETRA_DIR))
        self.letra = None
        self.letra_dirty = True

        self._menu()
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)
        self.tab_tpl = TemplateTab(self.nb, self)
        self.tab_imp = ImportTab(self.nb, self)
        self.tab_rev = ReviewTab(self.nb, self)
        self.tab_wri = WriteTab(self.nb, self)
        self.nb.add(self.tab_tpl, text="  1 · Plantilla  ")
        self.nb.add(self.tab_imp, text="  2 · Importar PDF escrito  ")
        self.nb.add(self.tab_rev, text="  3 · Revisar muestras  ")
        self.nb.add(self.tab_wri, text="  4 · Escribir  ")
        self.nb.bind("<<NotebookTabChanged>>", self._tab_changed)
        self.status = ttk.Label(self, anchor="w", padding=(8, 3), relief="sunken")
        self.status.pack(fill="x", side="bottom")
        self.reload_letra()
        self.nb.select(self.tab_wri if self.letra else self.tab_tpl)

    def _menu(self):
        menu = tk.Menu(self)
        m = tk.Menu(menu, tearoff=False)
        m.add_command(label="Exportar mi letra (.zip)…", command=self.export_letra)
        m.add_command(label="Importar letra (.zip)…", command=self.import_letra)
        m.add_separator()
        m.add_command(label="Abrir carpeta de la letra", command=lambda: open_path(self.letra_dir))
        m.add_command(label="Usar otra carpeta de letra…", command=self.pick_letra)
        m.add_command(label="Abrir hoja de revisión (revision.png)",
                      command=lambda: open_path(self.letra_dir / "revision.png"))
        menu.add_cascade(label="Letra", menu=m)
        h = tk.Menu(menu, tearoff=False)
        h.add_command(label="Guía de uso", command=lambda: open_path(APP / "GUIA.md"))
        menu.add_cascade(label="Ayuda", menu=h)
        self.config(menu=menu)

    def _tab_changed(self, _e=None):
        cur = self.nb.nametowidget(self.nb.select())
        if cur is self.tab_rev:
            self.tab_rev.refresh()
        elif cur is self.tab_wri:
            if self.letra_dirty:
                self.reload_letra()
            self.tab_wri.rerender()

    def set_status(self, msg):
        self.status.config(text=msg)

    # ----------------------------------------------------------- letra
    def reload_letra(self):
        self.letra_dirty = False
        try:
            self.letra = E.Letra(self.letra_dir, acentos=self.cfg.get("fix_acentos", True),
                                 signos=self.cfg.get("fix_signos", True))
            n = sum(len(v) for v in self.letra.glyphs.values())
            self.set_status(f"Letra: {self.letra_dir}  ·  {len(self.letra.glyphs)} caracteres, {n} muestras")
        except (FileNotFoundError, SystemExit, ValueError):
            self.letra = None
            self.set_status(f"Todavía no hay letra en {self.letra_dir}. Empieza en «1 · Plantilla».")
        self.title(f"Mi letra — {self.letra_dir.name}")

    def set_letra_dir(self, d):
        self.letra_dir = Path(d)
        self.cfg["letra_dir"] = str(self.letra_dir)
        save_config(self.cfg)
        self.reload_letra()
        self.tab_rev.built_for = None

    def pick_letra(self):
        d = filedialog.askdirectory(initialdir=self.letra_dir.parent, title="Carpeta de letra")
        if d:
            self.set_letra_dir(d)

    def export_letra(self):
        if not (self.letra_dir / "glifos.json").exists():
            messagebox.showinfo("Mi letra", "Aún no hay letra que exportar.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".zip", initialfile="mi_letra.zip",
                                         filetypes=[("Letra (zip)", "*.zip")])
        if not p:
            return
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(self.letra_dir / "glifos.json", "glifos.json")
            for f in (self.letra_dir / "glifos").glob("*.png"):     # sin los descartados
                z.write(f, f"glifos/{f.name}")
        self.set_status(f"Letra exportada a {p}")

    def import_letra(self):
        p = filedialog.askopenfilename(filetypes=[("Letra (zip)", "*.zip")])
        if not p:
            return
        d = filedialog.askdirectory(title="¿En qué carpeta (vacía) la pongo?", initialdir=DATA)
        if not d:
            return
        d = Path(d)
        if (d / "glifos.json").exists() and not messagebox.askyesno(
                "Mi letra", "Esa carpeta ya tiene una letra. ¿Reemplazarla?"):
            return
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n == "glifos.json" or (n.startswith("glifos/") and n.endswith(".png") and ".." not in n):
                    z.extract(n, d)
        self.set_letra_dir(d)


# ===================================================================== 1 · plantilla
class TemplateTab(ttk.Frame):
    NAMES = {
        "minusculas": "Latinas minúsculas", "mayusculas": "Latinas mayúsculas", "digitos": "Dígitos",
        "acentos": "Vocales con acento / diéresis", "puntuacion": "Puntuación y signos",
        "griego_min": "Griegas minúsculas (+ variantes ϵ ϑ ϕ ϖ ϱ ς)",
        "griego_may": "Griegas mayúsculas (las iguales a latinas se toman de tus latinas)",
        "operadores": "Operadores", "relaciones": "Relaciones", "conjuntos": "Conjuntos y lógica",
        "calculo": "Cálculo y análisis", "flechas": "Flechas", "delimitadores": "Delimitadores",
        "otros": "Fracciones y otros",
    }

    def __init__(self, master, app: App):
        super().__init__(master, padding=14)
        self.app = app
        defaults = {}
        for part in C.DEFAULT_SETS.split(","):
            name, _, n = part.partition(":")
            for sub in C.GROUPS.get(name, [name]):
                defaults[sub] = int(n)
        ttk.Label(self, text="Elige qué escribirás y cuántas veces cada carácter. Más muestras = más variedad "
                             "(y más trabajo).", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        grid = ttk.Frame(self)
        grid.pack(fill="x", pady=10)
        ttk.Label(grid, text="Incluir", foreground="#666").grid(row=0, column=0, sticky="w")
        ttk.Label(grid, text="Muestras", foreground="#666").grid(row=0, column=1)
        self.vars = {}
        for i, (key, chars) in enumerate(C.CHARSETS.items(), 1):
            on = tk.BooleanVar(value=True)
            n = tk.IntVar(value=defaults.get(key, 4))
            ttk.Checkbutton(grid, text=self.NAMES.get(key, key), variable=on,
                            command=self.update_count).grid(row=i, column=0, sticky="w", padx=(0, 10))
            sp = ttk.Spinbox(grid, from_=1, to=100, width=5, textvariable=n, command=self.update_count)
            sp.grid(row=i, column=1, padx=6)
            sp.bind("<KeyRelease>", lambda e: self.update_count())
            preview = chars if len(chars) <= 60 else chars[:60] + "…"
            ttk.Label(grid, text=preview, font=("Segoe UI Symbol", 11)).grid(row=i, column=2, sticky="w")
            self.vars[key] = (on, n)
        row = len(C.CHARSETS) + 1
        ttk.Label(grid, text="Caracteres extra (los que quieras):").grid(row=row, column=0, sticky="w", pady=(8, 0))
        self.extra = tk.StringVar()
        self.extra_n = tk.IntVar(value=4)
        ttk.Spinbox(grid, from_=1, to=100, width=5, textvariable=self.extra_n,
                    command=self.update_count).grid(row=row, column=1, pady=(8, 0))
        e = ttk.Entry(grid, textvariable=self.extra, width=40, font=("Segoe UI Symbol", 11))
        e.grid(row=row, column=2, sticky="w", pady=(8, 0))
        e.bind("<KeyRelease>", lambda ev: self.update_count())

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=8)
        b = ttk.Frame(bar)
        b.pack(side="left")
        ttk.Button(b, text="Todo a…", command=self.set_all).pack(side="left")
        self.all_n = tk.IntVar(value=10)
        ttk.Spinbox(b, from_=1, to=100, width=5, textvariable=self.all_n).pack(side="left", padx=4)
        self.count = ttk.Label(bar, font=("Segoe UI", 10))
        self.count.pack(side="left", padx=20)
        ttk.Button(bar, text="Crear PDF de la plantilla…", command=self.create).pack(side="right")

        ttk.Label(self, foreground="#555", justify="left", text=(
            "Después: envía el PDF a tu Kindle Scribe con «Send to Kindle», escribe sobre él con el lápiz "
            "(un carácter por casilla, sobre la línea continua),\nexpórtalo como PDF y ábrelo en la pestaña "
            "«2 · Importar». No hace falta nada más: cada página lleva impreso su código.")).pack(anchor="w", pady=10)
        self.update_count()

    def set_all(self):
        for on, n in self.vars.values():
            n.set(self.all_n.get())
        self.update_count()

    def spec(self):
        parts = []
        for key, (on, n) in self.vars.items():
            try:
                if on.get() and int(n.get()) > 0:
                    parts.append(f"{key}:{int(n.get())}")
            except (tk.TclError, ValueError):
                pass
        ex = self.extra.get().replace(",", "").replace(":", "").strip()
        if ex:
            parts.append(f"extra={ex}:{self.extra_n.get()}")
        return ",".join(parts)

    def update_count(self, *_):
        try:
            items = C.parse_sets(self.spec())
        except (SystemExit, ValueError, tk.TclError):
            return
        n = sum(k for _, k in items)
        pages = -(-n // C.CELLS_PER_PAGE)
        self.count.config(text=f"{len(items)} caracteres · {n} casillas · {pages} páginas")

    def create(self):
        spec = self.spec()
        items = C.parse_sets(spec)
        if not items:
            return
        p = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile="plantilla_mi_letra.pdf",
                                         initialdir=str(DATA), filetypes=[("PDF", "*.pdf")])
        if not p:
            return
        pages, cells, _ = P.build(items, Path(p), spec=spec)
        self.app.set_status(f"Plantilla creada: {p}  ({pages} páginas, {cells} casillas)")
        if messagebox.askyesno("Plantilla lista", f"{p}\n\n{pages} páginas, {cells} casillas.\n\n¿Abrir la carpeta?"):
            open_path(Path(p).parent)


# ===================================================================== 2 · importar
class ImportTab(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master, padding=14)
        self.app = app
        ttk.Label(self, text="Adjunta el PDF que escribiste en la Kindle Scribe. Con ese único archivo basta.",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=10)
        self.btn = ttk.Button(row, text="Elegir PDF escrito…", command=self.choose)
        self.btn.pack(side="left")
        self.dest = ttk.Label(row, foreground="#555")
        self.dest.pack(side="left", padx=12)
        self.pb = ttk.Progressbar(self, mode="determinate")
        self.pb.pack(fill="x")
        self.log = tk.Text(self, height=20, font=("Consolas", 9), state="disabled", bg="#fafafa")
        self.log.pack(fill="both", expand=True, pady=10)
        ttk.Label(self, foreground="#555", text=(
            "Si importas otra vez la misma plantilla, sus muestras se reemplazan. Si importas una plantilla "
            "distinta (por ejemplo, una de solo símbolos extra),\nse suma a tu letra.")).pack(anchor="w")

    def _write(self, s):
        self.log.config(state="normal")
        self.log.insert("end", s + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def choose(self):
        p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")], title="PDF escrito en la Kindle")
        if p:
            self.run(p)

    def run(self, pdf, layout=None):
        self.btn.config(state="disabled")
        out = self.app.letra_dir
        self.dest.config(text=f"→ {out}")
        self._write(f"Procesando {pdf}")

        q = queue.Queue()        # el hilo de trabajo solo escribe aquí; la interfaz lo lee

        def work():
            try:
                data, n = X.import_pdf(pdf, out, layout, log=lambda s: q.put(("log", s)),
                                       progress=lambda i, k: q.put(("prog", (i, k))))
                chars = {g["char"] for g in data["glyphs"]}
                q.put(("log", f"Listo: {n} muestras nuevas. Tu letra tiene ahora {len(data['glyphs'])} "
                              f"muestras de {len(chars)} caracteres."))
                q.put(("done", True))
            except BaseException as e:          # noqa: BLE001
                q.put(("log", f"ERROR: {e}"))
                q.put(("done", False))

        def poll():
            try:
                while True:
                    kind, val = q.get_nowait()
                    if kind == "log":
                        self._write(val)
                    elif kind == "prog":
                        self.pb.config(maximum=max(1, val[1]), value=val[0])
                    else:
                        self.done(val)
                        return
            except queue.Empty:
                pass
            self.after(80, poll)
        threading.Thread(target=work, daemon=True).start()
        poll()

    def done(self, ok):
        self.btn.config(state="normal")
        self.app.letra_dirty = True
        self.app.tab_rev.built_for = None
        if ok:
            self.app.reload_letra()
            if messagebox.askyesno("Importado", "¿Revisar ahora las muestras?"):
                self.app.nb.select(self.app.tab_rev)


# ===================================================================== 3 · revisar
class ReviewTab(ttk.Frame):
    UNIT = 20

    def __init__(self, master, app: App):
        super().__init__(master, padding=8)
        self.app = app
        self.built_for = None
        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Clic en una muestra para descartarla (se atenúa) o recuperarla. "
                            "Las naranjas tocan el borde de la casilla: quizá salieron cortadas.").pack(side="left")
        self.filter = tk.StringVar()
        ttk.Entry(top, textvariable=self.filter, width=14, font=("Segoe UI Symbol", 10)).pack(side="right")
        ttk.Label(top, text="Filtrar caracteres:").pack(side="right", padx=4)
        self.filter.trace_add("write", lambda *a: self.build())
        self.info = ttk.Label(self, foreground="#555")
        self.info.pack(fill="x", pady=4)
        self.sc = ScrollCanvas(self, bg="white")
        self.sc.pack(fill="both", expand=True)
        self.sc.canvas.bind("<Configure>", lambda e: self.build() if abs(e.width - self._last_w) > 40 else None)
        self.items = {}
        self._last_w = 0

    def refresh(self):
        if self.built_for != self.app.letra_dir:
            self.build()

    def _load(self):
        idx = self.app.letra_dir / "glifos.json"
        if not idx.exists():
            return []
        return json.loads(idx.read_text(encoding="utf-8"))["glyphs"]

    def build(self):
        cv = self.sc.canvas
        cv.delete("all")
        self._imgs, self.items = [], {}
        self._last_w = cv.winfo_width()
        self.built_for = self.app.letra_dir
        glyphs = self._load()
        f = self.filter.get().strip()
        by = {}
        for g in glyphs:
            if not f or g["char"] in f:
                by.setdefault(g["char"], []).append(g)
        gdir = self.app.letra_dir / "glifos"
        U = self.UNIT
        cw, rh, lw = int(U * 2.6), int(U * 3.4), 46
        per_row = max(4, (max(self._last_w, 600) - lw - 20) // cw)
        y = 8
        active = discarded = 0
        for ch, gl in by.items():
            for start in range(0, len(gl), per_row):
                base = y + int(U * 2.2)
                cv.create_line(lw, base, lw + per_row * cw, base, fill="#c8d7ef")
                if start == 0:
                    cv.create_text(10, base - 8, text=ch, anchor="w", font=("Segoe UI Symbol", 16), fill="#b02020")
                for i, g in enumerate(gl[start:start + per_row]):
                    path = gdir / g["file"]
                    off = not path.exists()
                    if off:
                        path = gdir / X.DISCARD / g["file"]
                        if not path.exists():
                            continue
                        discarded += 1
                    else:
                        active += 1
                    im = Image.open(path)
                    s = U / g["unit_px"]
                    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
                    color = (200, 200, 200) if off else ((210, 100, 0) if g.get("toca_borde") else (0, 0, 0))
                    rgba = Image.new("RGBA", im.size, color + (0,))
                    rgba.putalpha(im)
                    t = ImageTk.PhotoImage(rgba)
                    self._imgs.append(t)
                    x = lw + i * cw + 4
                    item = cv.create_image(x, int(base - g["top_u"] * U), image=t, anchor="nw")
                    box = cv.create_rectangle(x - 3, y + 2, x + cw - 6, y + rh - 6,
                                              outline="#f0b0b0" if off else "", width=1)
                    for it in (item, box):
                        cv.tag_bind(it, "<Button-1>", lambda e, gg=g: self.toggle(gg))
                    self.items[g["file"]] = (item, box)
                y += rh
        cv.configure(scrollregion=(0, 0, lw + per_row * cw, y + 10))
        missing = [c for c, _ in C.parse_sets(C.DEFAULT_SETS) if not any(g["char"] == c for g in glyphs)]
        msg = f"{len(by)} caracteres · {active} muestras activas · {discarded} descartadas."
        if glyphs and missing:
            msg += "  Sin ninguna muestra: " + " ".join(missing[:60]) + (" …" if len(missing) > 60 else "")
        if not glyphs:
            msg = "Todavía no hay muestras. Importa tu PDF escrito en la pestaña 2."
        self.info.config(text=msg)

    def toggle(self, g):
        gdir = self.app.letra_dir / "glifos"
        on, off = gdir / g["file"], gdir / X.DISCARD / g["file"]
        off.parent.mkdir(exist_ok=True)
        if on.exists():
            shutil.move(on, off)
        elif off.exists():
            shutil.move(off, on)
        self.app.letra_dirty = True
        y = self.sc.canvas.yview()[0]
        self.build()
        self.sc.canvas.yview_moveto(y)


# ===================================================================== 4 · escribir
class WriteTab(ttk.Frame):
    def __init__(self, master, app: App):
        super().__init__(master)
        self.app = app
        self.pages = []
        self.seed = 1
        self.ink = app.cfg.get("ink", "azul")
        self._job = None

        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        self.text = tk.Text(left, width=48, height=10, wrap="word", font=("Segoe UI Symbol", 11), undo=True)
        self.text.insert("1.0", app.cfg.get("last_text",
                         "Sea ε > 0. Existe δ > 0 tal que |x − a| < δ ⇒ |f(x) − L| < ε.\n"
                         "∮ E·dA = Q/ε_0    ∇×B = μ_0 J + μ_0 ε_0 ∂E/∂t\n"
                         "ψ(x,t) = A e^{i(kx − ωt)},   ∑_{n=1}^∞ 1/n^2 = π^2/6"))
        self.text.pack(fill="x")
        self.text.bind("<<Modified>>", self._on_modified)

        opts = ttk.Frame(left, padding=(0, 8))
        opts.pack(fill="x")
        c = app.cfg
        self.v = {
            "xh": tk.DoubleVar(value=c.get("xh", 28)),
            "desorden": tk.DoubleVar(value=c.get("desorden", 1.0)),
            "inclinacion": tk.DoubleVar(value=c.get("inclinacion", 0.0)),
            "espaciado": tk.DoubleVar(value=c.get("espaciado", 0.12)),
            "interlineado": tk.DoubleVar(value=c.get("interlineado", 3.0)),
        }
        self.v_paper = tk.StringVar(value=c.get("papel", "rayado"))
        self.v_mode = tk.StringVar(value=c.get("modo", "aleatorio"))
        self.v_sheet = tk.BooleanVar(value=c.get("hoja", False))
        sliders = [("Tamaño de letra", "xh", 12, 70), ("Desorden / naturalidad", "desorden", 0, 2.5),
                   ("Inclinación (°)", "inclinacion", -20, 20), ("Separación de letras", "espaciado", -0.15, 0.5),
                   ("Interlineado", "interlineado", 2.0, 5.0)]
        for i, (lbl, key, a, b) in enumerate(sliders):
            ttk.Label(opts, text=lbl).grid(row=i, column=0, sticky="w", pady=2)
            ttk.Scale(opts, from_=a, to=b, variable=self.v[key], command=self._changed).grid(
                row=i, column=1, sticky="ew", padx=6)
        r = len(sliders)
        for j, (lbl, var, vals) in enumerate([("Papel", self.v_paper, E.PAPERS),
                                              ("Modo", self.v_mode, ("aleatorio", "promedio"))]):
            ttk.Label(opts, text=lbl).grid(row=r + j, column=0, sticky="w", pady=2)
            cb = ttk.Combobox(opts, textvariable=var, values=vals, state="readonly", width=14)
            cb.grid(row=r + j, column=1, sticky="w", padx=6)
            cb.bind("<<ComboboxSelected>>", self._changed)
        ttk.Checkbutton(opts, text="Paginar en hojas tamaño carta", variable=self.v_sheet,
                        command=self._changed).grid(row=r + 2, column=0, columnspan=2, sticky="w", pady=2)
        self.v_fmt = tk.BooleanVar(value=c.get("formato", True))
        ttk.Checkbutton(opts, text="^ y _ = superíndice / subíndice  (x^2, a_n, e^{iπ})", variable=self.v_fmt,
                        command=self._changed).grid(row=r + 3, column=0, columnspan=2, sticky="w", pady=2)
        self.v_fix_acc = tk.BooleanVar(value=c.get("fix_acentos", True))
        self.v_fix_sig = tk.BooleanVar(value=c.get("fix_signos", True))
        ttk.Checkbutton(opts, text="Acentos con tilde normal (á é í ó ú)", variable=self.v_fix_acc,
                        command=self._fixes_changed).grid(row=r + 4, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Checkbutton(opts, text="Centrar y ajustar signos (+ − = < > …)", variable=self.v_fix_sig,
                        command=self._fixes_changed).grid(row=r + 5, column=0, columnspan=2, sticky="w", pady=2)
        opts.columnconfigure(1, weight=1)

        colors = ttk.Frame(left)
        colors.pack(fill="x", pady=4)
        ttk.Label(colors, text="Tinta:").pack(side="left")
        for name, rgb in E.COLORS.items():
            tk.Button(colors, bg="#%02x%02x%02x" % rgb, width=2, relief="flat",
                      command=lambda n=name: self._set_ink(n)).pack(side="left", padx=2)
        ttk.Button(colors, text="…", width=3, command=self._pick_color).pack(side="left", padx=2)

        btns = ttk.Frame(left, padding=(0, 8))
        btns.pack(fill="x")
        ttk.Button(btns, text="🎲 Otra variante", command=self.reroll).pack(side="left")
        ttk.Button(btns, text="📋 Copiar", command=self.copy).pack(side="left", padx=4)
        ttk.Button(btns, text="PNG…", command=lambda: self.save(".png")).pack(side="left")
        ttk.Button(btns, text="PDF…", command=lambda: self.save(".pdf")).pack(side="left", padx=4)
        btns2 = ttk.Frame(left)
        btns2.pack(fill="x")
        ttk.Button(btns2, text="Abrir .txt…", command=self.open_txt).pack(side="left")
        ttk.Button(btns2, text="Restablecer ajustes", command=self.reset).pack(side="left", padx=4)
        self.msg = ttk.Label(left, text="", wraplength=380, foreground="#555", justify="left")
        self.msg.pack(fill="x", pady=8)
        ttk.Label(left, foreground="#888", wraplength=380, justify="left", text=(
            "Atajos: Ctrl+Shift+C copia la imagen. «Otra variante» vuelve a barajar qué muestra se usa "
            "para cada letra.")).pack(fill="x")
        app.bind("<Control-Shift-C>", lambda e: self.copy())
        app.bind("<Control-Shift-c>", lambda e: self.copy())

        self.sc = ScrollCanvas(self, bg="#d6d6d6")
        self.sc.pack(side="left", fill="both", expand=True)
        self.sc.canvas.bind("<Configure>", lambda e: self._show())

    # ---------------------------------------------------------------
    def _on_modified(self, _e=None):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self._changed()

    def _changed(self, *_):
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(250, self.rerender)

    def _fixes_changed(self):
        self.app.cfg["fix_acentos"] = self.v_fix_acc.get()
        self.app.cfg["fix_signos"] = self.v_fix_sig.get()
        save_config(self.app.cfg)
        self.app.reload_letra()
        self.rerender()

    def _set_ink(self, ink):
        self.ink = ink
        self._changed()

    def _pick_color(self):
        c = colorchooser.askcolor()
        if c and c[0]:
            self._set_ink(tuple(int(v) for v in c[0]))

    def reroll(self):
        self.seed += 1
        self.rerender()

    def reset(self):
        for k, v in {"xh": 28, "desorden": 1.0, "inclinacion": 0.0, "espaciado": 0.12, "interlineado": 3.0}.items():
            self.v[k].set(v)
        self._changed()

    def open_txt(self):
        p = filedialog.askopenfilename(filetypes=[("Texto", "*.txt"), ("Todo", "*.*")])
        if p:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", Path(p).read_text(encoding="utf-8", errors="replace"))

    def params(self):
        return dict(xh=int(self.v["xh"].get()), ancho=1700, alto=2200 if self.v_sheet.get() else None,
                    color=self.ink, papel=self.v_paper.get(), modo=self.v_mode.get(), semilla=self.seed,
                    desorden=self.v["desorden"].get(), inclinacion=self.v["inclinacion"].get(),
                    espaciado=self.v["espaciado"].get(), interlineado=self.v["interlineado"].get(),
                    formato=self.v_fmt.get())

    def _remember(self):
        c = self.app.cfg
        c.update({k: v.get() for k, v in self.v.items()})
        c.update(papel=self.v_paper.get(), modo=self.v_mode.get(), hoja=self.v_sheet.get(), formato=self.v_fmt.get(),
                 ink=self.ink, last_text=self.text.get("1.0", "end-1c")[:5000])
        save_config(c)

    def rerender(self):
        self._job = None
        letra = self.app.letra
        if not letra:
            self.pages = []
            self.msg.config(text="Aún no hay letra cargada: crea la plantilla (pestaña 1) e importa tu PDF (pestaña 2).")
            self._show()
            return
        text = self.text.get("1.0", "end-1c")
        self.pages = E.render(text or " ", letra, **self.params())
        missing = sorted({ch for ch in text if not ch.isspace() and not letra.has(ch)})
        m = f"{len(self.pages)} hoja(s)." if len(self.pages) > 1 else ""
        if missing:
            m += "  Sin muestras (se usa fuente de respaldo): " + " ".join(missing)
        self.msg.config(text=m)
        self._show()
        self._remember()

    def _show(self):
        cv = self.sc.canvas
        cv.delete("all")
        if not self.pages:
            return
        cw = max(200, cv.winfo_width() - 30)
        y, self._tk = 15, []
        for pg in self.pages:
            s = cw / pg.width
            im = pg.resize((cw, max(1, int(pg.height * s))), Image.LANCZOS)
            bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
            bg.alpha_composite(im.convert("RGBA"))
            t = ImageTk.PhotoImage(bg)
            self._tk.append(t)
            cv.create_image(15, y, image=t, anchor="nw")
            y += im.height + 15
        cv.configure(scrollregion=(0, 0, cw + 30, y))

    def copy(self):
        if not self.pages:
            return
        try:
            copy_image_to_clipboard(self.pages[0])
        except OSError as e:
            self.app.set_status(str(e))
            return
        self.app.set_status("Imagen copiada: pégala con Ctrl+V donde quieras"
                            + (" (solo la 1ª hoja)" if len(self.pages) > 1 else ""))

    def save(self, ext):
        if not self.pages:
            return
        p = filedialog.asksaveasfilename(defaultextension=ext, filetypes=[(ext.upper(), "*" + ext)])
        if p:
            outs = E.save(self.pages, p)
            self.app.set_status("Guardado: " + ", ".join(str(o) for o in outs))


if __name__ == "__main__":
    App().mainloop()
