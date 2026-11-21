# Text format

A UTF-8 `.txt` file. Every newline starts a new line on the page; long lines wrap
automatically between words (never inside a grouped formula). An empty line leaves a blank line.
(Spanish version: [FORMATO.md](FORMATO.md).)

## Text

Any Unicode character. Your own sample is used when you have one; otherwise it is derived
from another character (see below) or, as a last resort, drawn with a fallback system font
(`holograph validate` tells you which).

## Superscripts and subscripts

| You type | Result |
|---|---|
| `x^2` | one character up |
| `e^{2t}` | everything in braces up |
| `a_n`, `x_{p,1}` | down |
| `∑_{n=1}^∞`, `∫_0^{2π}` | a sub followed by a sup (or vice versa) is **stacked** |
| `x^\alpha`, `x^\frac{1}{2}` | a command also works as an index |

Braces that do **not** follow `^`, `_` or a command are written literally:
`min{1, ε/5}`, `{X_1, X_2}`.

## Structures

| You type | Result |
|---|---|
| `\frac{num}{den}` | stacked fraction (nestable) |
| `\pmat{a & b ; c & d}` | matrix in parentheses: `&` separates columns, `;` rows |
| `\pmat{1 ; 0 ; −3}` | column vector |
| `\bmat{…}` | square brackets |
| `\vmat{…}` | determinant (vertical bars) |
| `\sqrt{…}` | radical with an overbar |

Everything nests: `\pmat{−\frac{t}{2} − \frac{1}{4} ; e^{2t}}`.
Brackets, bars, the radical sign and fraction bars are stretched versions of your own strokes.

## LaTeX that is understood

- Environments: `\begin{pmatrix} … \end{pmatrix}` (also `bmatrix`, `vmatrix`, `Bmatrix`,
  `matrix`, `cases`) with `&` and `\\`.
- `\dfrac`, `\tfrac` → `\frac`; `\left( … \right)` and `\big…` → plain delimiters.
- `\text{…}`, `\mathrm{…}`, `\mathbf{…}`, `\operatorname{…}` → their content.
- `\mathbb{R}` → ℝ (also N Z Q C P).
- Spacing: `\,` `\;` `\:` `\quad` `\qquad`.
- `$…$`, `\(…\)`, `\[…\]`: the delimiters are removed. For a literal dollar sign write `\$`.
- 150+ symbol names: Greek (`\alpha … \Omega`, `\varepsilon`, `\vartheta`…), operators
  (`\pm \times \cdot \circ \oplus \otimes \wedge \vee \neg`), relations (`\leq \geq \neq \approx
  \equiv \sim \propto \ll \gg \perp \parallel`), sets (`\in \notin \subset \subseteq \cup \cap
  \emptyset \forall \exists`), calculus (`\partial \nabla \int \iint \iiint \oint \sum \prod
  \infty \hbar \ell`), arrows (`\to \Rightarrow \iff \mapsto \leftrightarrow`), delimiters
  (`\langle \rangle \lfloor \rceil \|`), dots (`\ldots \cdots`), function names (`\sin \cos
  \log \ln \exp \det \lim \max \min`…). Exact list: `LATEX_SYMBOLS` in `formulas.py`.

A command that is not on the list is written literally, and `holograph validate` reports it
as *comando desconocido* (unknown command).

## Literals

`\^` `\_` `\{` `\}` `\&` `\$` `\%` `\#` `\\` write the character itself.

## Derived characters (no need to write them in the template)

- Unicode sub/superscripts `₀…₉ ⁰…⁹ ₊ ₋ ⁺ ⁻ ₙ ⁿ ₐ ₑ ₒ ₓ ᵢ ⱼ` → your digits/letters, scaled down.
- Greek capitals identical to Latin ones `Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Χ ο` → your Latin letters.
- Unicode duplicates: `∆→Δ`, `µ→μ`, `−→-`, `⋅→·`, `’→'`, `ħ→ℏ`, `⟹→⇒`…
- `✓` is drawn with your stroke width if you didn't write one.

## Example

```
(a)    X′ = \pmat{2 & 0 ; 0 & −1} X + \pmat{e^{2t} ; 2}
W = \vmat{e^{2t} & 0 ; 0 & e^{−t}} = e^{t} ≠ 0 for all t.
u_3 = −\frac{1}{6}e^{2t},   \int_0^\infty e^{-x}\,dx = 1,   \sqrt{x^2 + 1}
```
