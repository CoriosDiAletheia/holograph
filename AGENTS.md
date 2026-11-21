# AGENTS.md — guide for AI assistants

This file is for you, the assistant (Claude Code, Codex, Cursor, Gemini CLI…).
The user wants **text written in their own handwriting** (math included). You do the heavy
lifting — transcribing documents, preparing the text, rendering and checking — while the user
only ever writes their template by hand, once.

**Talk to the user in their language.** The program's messages, JSON keys and GUI are in
Spanish; every command and option also has an English name (used below).

## Golden rules

1. **Always start with `python holograph.py status --json`.** It reports the stage
   (`sin_letra` = no handwriting yet, `esperando_pdf_escrito` = template created but not
   imported, `lista` = ready) and the exact next step (`siguiente_paso`).
2. **Never upload or share `datos/`.** It holds the user's handwriting (biometric-like personal
   data), their PDFs and texts. It is git-ignored; keep it that way.
3. **Transcribe faithfully.** When turning a document into handwriting do not change the
   content. If you spot a mathematical error in the source, tell the user instead of silently
   fixing it.
4. **Validate before rendering** (`validate`) and **look at the result** (`--preview` writes
   half-size PNGs of every page — open them and check them).
5. Working files go in `datos/textos/` (input) and `datos/salidas/` (output). Create them if needed.

## Install (once)

```bash
python -c "import pymupdf, PIL, numpy"        # if this succeeds, skip the next line
python -m pip install -r requirements.txt     # pymupdf, pillow, numpy (Python ≥ 3.10)
python holograph.py status
```
Alternatively `pip install -e .` provides a `holograph` command. On Windows, `instalar.bat` does it with a double click.
Data location can be changed with the `HOLOGRAPH_HOME` environment variable.

## Flow A — no handwriting yet (`etapa: sin_letra`)

1. `python holograph.py template --json` → creates `datos/plantilla_mi_letra.pdf`
   (≈30 pages, 268 characters: Latin, digits, accents, punctuation, Greek, ~110 math symbols).
   Less work: `--sets "latin:6,digitos:6,puntuacion:3"`. More natural results: `latin:15`.
   Set names: `minusculas mayusculas digitos acentos puntuacion griego_min griego_may
   operadores relaciones conjuntos calculo flechas delimitadores otros`, groups `latin griego
   matematicas`, and `extra=CHARS`.
2. Explain to the user (you cannot do this part):
   - Send the PDF to their tablet as a PDF (Kindle Scribe: *Send to Kindle*; reMarkable, Boox,
     iPad with GoodNotes/Notability: import the PDF).
   - Write **one character per box**, sitting on the solid line, without touching the black
     corner squares or the row of small squares at the bottom.
   - Export the annotated document as PDF and bring it to the computer.
   - No tablet: print it, write with a black pen, scan to PDF (works, less precise).
3. Meanwhile, to try things out: `python holograph.py demo` builds sample handwriting from
   system fonts into `datos/letra_demo/`. Pass `--hand demo` to `write`, `validate`, `chars`
   and `review`. The demo does not change `status` (it still says `sin_letra` until the user
   imports their own handwriting). It is a font-based imitation: tell the user it will look far
   more natural with their real samples.

## Flow B — import the filled-in PDF (`etapa: esperando_pdf_escrito`)

```bash
python holograph.py import PATH/TO/WRITTEN.pdf --json
python holograph.py review          # writes datos/mi_letra/revision.png
```
- The PDF alone is enough: each page carries a printed code with its template id and page number.
- "plantilla … desconocida" (unknown template) means it was created on another computer: copy
  its `datos/plantillas/<id>.json` here.
- Open `revision.png` and go over bad or clipped samples with the user (orange = touches the
  box border). To discard one, move its PNG to `datos/mi_letra/glifos/_descartados/`.

## Flow C — turn a document into handwriting (`etapa: lista`)

This is the request you'll get most ("convert this PDF into my handwriting").

1. **Read the source.** For a PDF:
   `python -c "import pymupdf,sys; [print(p.get_text()) for p in pymupdf.open(sys.argv[1])]" FILE.pdf`
   Text extraction scatters matrices and fractions over separate lines: rebuild them from the
   mathematics, not line by line. If you can view the pages as images, use them to confirm structure.
2. **Write `datos/textos/<name>.txt`** in the format of `docs/FORMAT.md` (summary below).
   Everyday LaTeX is translated automatically. Things the format cannot express and what to do:
   - **bold / italics** (e.g. bold vectors **X**) → plain letters (handwriting has no bold);
   - **headings** → their own line, with a blank line before;
   - **centered display equations** → their own line (text is always left-aligned);
   - **boxed answers** → write the answer on its own line; optionally add `✓` or `⇒` before it;
   - **tables / figures** → describe them in text or tell the user they were left out.
   When the user names a part of a document ("part (a)"), confirm the scope if the shared
   introduction or title is ambiguous; by default include only that part.
3. `python holograph.py validate datos/textos/<name>.txt --json`
   → fix `problemas` (braces, unknown commands). `sin_muestra` lists characters that will fall
   back to a system font: replace them with ones the user has (e.g. `•` → `–`) or tell the user.
4. `python holograph.py write -f datos/textos/<name>.txt -o datos/salidas/<name>.pdf --sheet --preview --json`
   Defaults: blue ink, ruled paper, x-height 24 px. `--sheet` paginates into **US-letter**
   pages (the only page size); without it you get one tall image. So "letter-size, blue ink"
   = `--sheet` (blue is already the default).
5. **Inspect the previews** (`*_vista_NN.png`). Typical issues and fixes:
   - An equation split across two lines → insert a line break before it.
   - `avisos` saying an item is wider than the page → split the formula or lower `--size`.
   - Too cramped/loose → `--size`, `--line-height` (default 3), `--word-spacing` (default 1;
     try 1.3 if words run together).
   - Lines with tall matrices get extra room automatically; if something still touches the
     line above, add an empty line before it.
6. Deliver the PDF and mention anything you had to adapt.

### Format in 30 seconds

| You write | Result |
|---|---|
| `x^2`, `e^{i(kx − ωt)}`, `a_n`, `x_{p,1}` | super/subscripts (a sub + sup pair is stacked) |
| `\sum_{n=1}^\infty`, `\prod_…^…`, `\lim_{x \to 0}` | limits **below/above** the operator (also `min max sup inf`) |
| `\frac{a}{b}` | stacked fraction |
| `\pmat{a & b ; c & d}` / `\pmat{1 ; 0}` | matrix / column vector in parentheses |
| `\bmat{…}`, `\vmat{…}` | square brackets / determinant bars |
| `\sqrt{x^2 + 1}` | radical with bar |
| `\alpha \leq \int \infty \cdot \to \mathbb{R} \sin` | α ≤ ∫ ∞ · → ℝ sin |
| `\begin{pmatrix} a & b \\ c & d \end{pmatrix}` | same as `\pmat` |
| `$…$`, `\(…\)` | delimiters are removed; `\$` = dollar sign |
| newline | new line (long lines wrap between words automatically) |

Plain Unicode works too: `ε₀ x² ∮ ⇒ ℏ`. Full list: `docs/FORMAT.md`.

## Command reference

| Command (Spanish alias) | Purpose |
|---|---|
| `status` (`estado`) | current stage and next step |
| `template` (`plantilla`) `[--sets S] [-o PDF]` | template PDF |
| `import` (`importar`) `PDF` | extract handwriting from the written PDF |
| `review` (`revisar`) | `revision.png` with every sample |
| `chars` (`caracteres`) | available, derived and missing characters |
| `validate` (`validar`) `FILE` | markup problems and characters without samples |
| `write` (`escribir`) `(TEXT \| -f FILE \| stdin) -o OUT` | render `.pdf`/`.png`; `--sheet --preview --size --color --paper --word-spacing --line-height --messiness --slant --seed` |
| `demo` | sample handwriting without a tablet |
| `export` (`exportar`) `ZIP` | back up the handwriting |
| `app` | GUI for the user |

Every command accepts `--json`; on error it prints `{"ok": false, "error": "..."}` and exits 1.
Colors: `black blue ballpoint red green graphite`; paper: `ruled grid white transparent`.

## Architecture (if you need to change the code)

| Module | Role |
|---|---|
| `comun.py` | template geometry, character sets, aliases, paths, system fonts |
| `plantilla.py` | builds the template PDF (registration marks + binary page/template code) |
| `extraer.py` | aligns with the marks, decodes the code, crops each box, stores glyphs |
| `ajustes.py` | load-time fixes: clean acute accents, signs on the math axis, primes, ✓ |
| `formulas.py` | markup parser + formula layout (boxes, fractions, matrices, radicals, LaTeX) |
| `escribir.py` | `Letra` (loads glyphs, picks variants without repeats) and `render` (pages) |
| `holograph.py` | CLI · `app.py` Tk GUI · `simular.py` fake handwriting for tests |

Tests: `python -m pytest -q` (they use simulated handwriting in a temp dir; `datos/` is never touched).
