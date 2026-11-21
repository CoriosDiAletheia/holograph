# AGENTS.md — guía para asistentes de IA

Este archivo es para ti, asistente (Claude Code, Codex, Cursor, Gemini CLI…).
El usuario quiere **texto escrito con su propia letra** (incluidas fórmulas
matemáticas). Tú haces el trabajo pesado — transcribir documentos, preparar el
texto, generar y revisar — y el usuario solo escribe una vez su plantilla a mano.

Responde al usuario en su idioma. El programa y sus mensajes están en español.

## Reglas de oro

1. **Empieza siempre con `python miletra.py estado --json`.** Te dice la etapa
   (`sin_letra`, `esperando_pdf_escrito`, `lista`) y el siguiente paso exacto.
2. **Nunca subas ni compartas `datos/`.** Ahí está la letra del usuario (un dato
   biométrico), sus PDF y sus textos. Ya está en `.gitignore`; no lo quites.
3. **Transcribe fielmente.** Al pasar un documento a mano no cambies el
   contenido. Si ves un error matemático en el original, díselo al usuario en
   lugar de corregirlo en silencio.
4. **Valida antes de generar** (`miletra validar`) y **mira el resultado**
   (`--vista` genera PNG a media resolución; ábrelos y revísalos).
5. Los archivos de trabajo van en `datos/textos/` (entrada) y `datos/salidas/`
   (resultados). Créalos si no existen.

## Instalación (una vez)

```bash
python -m pip install -r requirements.txt     # pymupdf, pillow, numpy (Python ≥ 3.10)
python miletra.py estado
```
Alternativa: `pip install -e .` deja disponible la orden `miletra` en el PATH.
En Windows, `instalar.bat` hace lo mismo con doble clic.

## Flujo A — el usuario aún no tiene letra (`etapa: sin_letra`)

1. `python miletra.py plantilla --json` → crea `datos/plantilla_mi_letra.pdf`
   (≈30 páginas, 268 caracteres: latín, dígitos, acentos, puntuación, griego y
   ~110 símbolos matemáticos). Para menos trabajo:
   `--sets "latin:6,digitos:6,puntuacion:3"`; para más naturalidad: `latin:15`.
2. Explica al usuario (no lo puedes hacer tú):
   - Enviar el PDF a su tableta como PDF (Kindle Scribe: *Send to Kindle*;
     reMarkable, Boox, iPad con GoodNotes/Notability: importar el PDF).
   - Escribir **un carácter por casilla**, apoyado en la línea continua, sin
     tocar los cuadros negros ni la fila de cuadritos de abajo.
   - Exportar el documento con lo escrito como PDF y pasarlo a la computadora.
   - Sin tableta: imprimir, escribir con bolígrafo negro y escanear a PDF
     (funciona, pero es menos preciso que una tableta).
3. Mientras tanto, si quiere probar: `python miletra.py demo` crea una letra de
   ejemplo con fuentes del sistema (`--letra demo` en las demás órdenes).

## Flujo B — importar el PDF escrito (`etapa: esperando_pdf_escrito`)

```bash
python miletra.py importar RUTA/AL/ESCRITO.pdf --json
python miletra.py revisar          # genera datos/mi_letra/revision.png
```
- Basta con el PDF: cada página trae impreso un código con su plantilla y página.
- Si dice «plantilla desconocida», la plantilla se creó en otra computadora:
  copia su `datos/plantillas/<id>.json` aquí.
- Abre `revision.png` y comenta con el usuario las muestras feas o cortadas
  (naranja = toca el borde). Para descartar una: mover su PNG a
  `datos/mi_letra/glifos/_descartados/`.

## Flujo C — pasar un documento a su letra (`etapa: lista`)

Esto es lo que más se te pedirá («pasa este PDF a mi letra»).

1. **Lee la fuente.** Para un PDF:
   `python -c "import pymupdf,sys; [print(p.get_text()) for p in pymupdf.open(sys.argv[1])]" ARCHIVO.pdf`
   La extracción de PDF rompe las matrices y fracciones en líneas sueltas:
   reconstrúyelas pensando en la matemática, no copiando línea a línea. Si
   puedes ver las páginas como imagen, úsalas para confirmar la estructura.
2. **Escribe `datos/textos/<nombre>.txt`** en el formato de `docs/FORMATO.md`
   (resumen abajo). Puedes usar LaTeX común: se traduce solo.
3. `python miletra.py validar datos/textos/<nombre>.txt --json`
   → corrige `problemas` (llaves, comandos desconocidos). `sin_muestra` lista
   caracteres que saldrán con fuente de respaldo: sustitúyelos por otros que sí
   tenga (p. ej. `•` → `–`) o avisa al usuario.
4. `python miletra.py escribir -f datos/textos/<nombre>.txt -o datos/salidas/<nombre>.pdf --hoja --vista --json`
5. **Revisa las vistas** (`*_vista_NN.png`). Problemas típicos y arreglo:
   - Una ecuación partida entre dos renglones → inserta un salto de línea antes.
   - `avisos` con «más ancho que la página» → parte la fórmula o baja `--tamano`.
   - Muy apretado/suelto → `--tamano` (24 por defecto), `--interlineado`.
6. Entrega el PDF y menciona cualquier cosa que hayas tenido que adaptar.

### Formato en 30 segundos

| Escribes | Sale |
|---|---|
| `x^2`, `e^{i(kx − ωt)}`, `a_n`, `x_{p,1}` | super/subíndices (`∑_{n=1}^∞` se apilan) |
| `\frac{a}{b}` | fracción apilada |
| `\pmat{a & b ; c & d}` / `\pmat{1 ; 0}` | matriz / vector columna con paréntesis |
| `\bmat{…}`, `\vmat{…}` | corchetes / determinante |
| `\sqrt{x^2 + 1}` | raíz con raya |
| `\alpha \leq \int \infty \cdot \to \mathbb{R} \sin` | α ≤ ∫ ∞ · → ℝ sin |
| `\begin{pmatrix} a & b \\ c & d \end{pmatrix}` | igual que `\pmat` |
| `$…$` | los `$` se quitan; `\$` = dólar |
| salto de línea | salto de renglón (las líneas largas se parten solas entre palabras) |

Unicode directo también vale: `ε₀ x² ∮ ⇒ ℏ`. Lista completa: `docs/FORMATO.md`.

## Referencia de órdenes

| Orden | Para qué |
|---|---|
| `estado` | etapa actual y siguiente paso |
| `plantilla [--sets S] [-o PDF]` | PDF con casillas |
| `importar PDF` | extraer letra del PDF escrito |
| `revisar` | `revision.png` con todas las muestras |
| `caracteres` | qué hay, qué se deriva, qué falta |
| `validar ARCHIVO` | sintaxis y caracteres sin muestra |
| `escribir (TEXTO \| -f ARCHIVO \| stdin) -o SALIDA` | generar `.pdf`/`.png`; `--hoja --vista --tamano --color --papel --desorden --semilla` |
| `demo` | letra de prueba sin tableta |
| `exportar ZIP` | copia de seguridad de la letra |
| `app` | interfaz gráfica para el usuario |

Todas aceptan `--json`; con error devuelven `{"ok": false, "error": "..."}` y
código de salida 1. Las carpetas se pueden mover con la variable `MILETRA_HOME`.

## Cómo funciona (por si tienes que modificar el código)

| Módulo | Qué hace |
|---|---|
| `comun.py` | geometría de la plantilla, conjuntos de caracteres, alias, rutas, fuentes |
| `plantilla.py` | genera el PDF (marcas de registro + código binario de página/plantilla) |
| `extraer.py` | alinea con las marcas, lee el código, recorta cada casilla, guarda glifos |
| `ajustes.py` | correcciones al cargar: tilde aguda, signos al eje matemático, primas, ✓ |
| `formulas.py` | parser del formato + maquetación de fórmulas (cajas, fracciones, matrices) |
| `escribir.py` | `Letra` (carga glifos, elige variantes sin repetir) y `render` (páginas) |
| `miletra.py` | CLI · `app.py` interfaz Tk · `simular.py` relleno falso para pruebas |

Pruebas: `python -m pytest -q` (usan una letra simulada; no tocan `datos/`).
