# Formato del texto

Un archivo `.txt` en UTF-8. Cada salto de línea es un renglón nuevo; las líneas
largas se parten solas entre palabras (nunca dentro de una fórmula agrupada).
Una línea vacía deja un renglón en blanco.

## Texto

Cualquier carácter Unicode. Se usa tu muestra si la tienes; si no, se deriva de
otra (ver abajo) o, como último recurso, se dibuja con una fuente de respaldo
(`miletra validar` te dice cuáles).

## Super y subíndices

| Escribes | Resultado |
|---|---|
| `x^2` | un carácter arriba |
| `e^{2t}` | todo lo de las llaves arriba |
| `a_n`, `x_{p,1}` | abajo |
| `∑_{n=1}^∞`, `∫_0^{2π}` | sub y super seguidos se **apilan** |
| `x^\alpha`, `x^\frac{1}{2}` | un comando también vale como índice |

Las llaves que **no** siguen a `^`, `_` o a un comando se escriben tal cual:
`mín{1, ε/5}`, `{X_1, X_2}`.

## Estructuras

| Escribes | Resultado |
|---|---|
| `\frac{num}{den}` | fracción apilada (anidable) |
| `\pmat{a & b ; c & d}` | matriz con paréntesis: `&` columnas, `;` filas |
| `\pmat{1 ; 0 ; −3}` | vector columna |
| `\bmat{…}` | con corchetes |
| `\vmat{…}` | determinante (barras) |
| `\sqrt{…}` | raíz con raya encima |

Todo se puede anidar: `\pmat{−\frac{t}{2} − \frac{1}{4} ; e^{2t}}`.
Los paréntesis, barras, la raíz y las rayas de fracción se hacen estirando
tus propios trazos.

## LaTeX que se entiende

- Entornos: `\begin{pmatrix} … \end{pmatrix}` (también `bmatrix`, `vmatrix`,
  `Bmatrix`, `matrix`, `cases`), con `&` y `\\`.
- `\dfrac`, `\tfrac` → `\frac`; `\left( … \right)` y `\big…` → paréntesis normales.
- `\text{…}`, `\mathrm{…}`, `\mathbf{…}`, `\operatorname{…}` → su contenido.
- `\mathbb{R}` → ℝ (también N Z Q C P).
- Espacios: `\,` `\;` `\:` `\quad` `\qquad`.
- `$…$`: los `$` se quitan. Para un signo de dólar escribe `\$`.
- Símbolos (más de 150): griego (`\alpha … \Omega`, `\varepsilon`, `\vartheta`…),
  operadores (`\pm \times \cdot \circ \oplus \otimes \wedge \vee \neg`),
  relaciones (`\leq \geq \neq \approx \equiv \sim \propto \ll \gg \perp \parallel`),
  conjuntos (`\in \notin \subset \subseteq \cup \cap \emptyset \forall \exists`),
  cálculo (`\partial \nabla \int \iint \iiint \oint \sum \prod \infty \hbar \ell`),
  flechas (`\to \Rightarrow \iff \mapsto \leftrightarrow`),
  delimitadores (`\langle \rangle \lfloor \rceil \|`), puntos (`\ldots \cdots`),
  funciones (`\sin \cos \log \ln \exp \det \lim \max \min`…).
  Lista exacta: `LATEX_SYMBOLS` en `formulas.py`.

Un comando que no esté en la lista se escribe literal y `miletra validar` lo
avisa como «comando desconocido».

## Literales

`\^` `\_` `\{` `\}` `\&` `\$` `\%` `\#` `\\` escriben el carácter tal cual.

## Caracteres derivados (no hace falta escribirlos en la plantilla)

- Subíndices/superíndices Unicode: `₀…₉ ⁰…⁹ ₊ ₋ ⁺ ⁻ ₙ ⁿ ₐ ₑ ₒ ₓ ᵢ ⱼ` → tus dígitos/letras en pequeño.
- Griego igual al latín: `Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Χ ο` → tus latinas.
- Duplicados Unicode: `∆→Δ`, `µ→μ`, `−→-`, `⋅→·`, `’→'`, `ħ→ℏ`, `⟹→⇒`…
- `✓` se dibuja con el grosor de tu trazo si no lo escribiste.

## Ejemplo

```
(a)    X′ = \pmat{2 & 0 ; 0 & −1} X + \pmat{e^{2t} ; 2}
W = \vmat{e^{2t} & 0 ; 0 & e^{−t}} = e^{t} ≠ 0 para todo t.
u_3 = −\frac{1}{6}e^{2t},   ∫_0^\infty e^{-x}\,dx = 1,   \sqrt{x^2 + 1}
```
