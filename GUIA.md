# Guía de uso — Mi letra

Todo funciona en tu computadora, sin internet y sin depender de nadie.

---

## 0. Instalar (solo la primera vez)

1. Necesitas **Python 3.10 o superior** (ya lo tienes instalado). Si alguna vez cambias de
   computadora, instálalo desde python.org marcando *"Add python.exe to PATH"*.
2. Doble clic en **`instalar.bat`**. Instala las 3 librerías que usa el programa
   (PyMuPDF, Pillow y NumPy).

## Abrir el programa

Doble clic en **`iniciar.bat`**. Se abre una ventana con 4 pestañas.
(Si no se abre nada, abre una terminal en esta carpeta y ejecuta `python miletra.py app` para ver el error.)

---

## 1 · Plantilla — crear el PDF para escribir

La plantilla completa por defecto (`python miletra.py plantilla`, o el botón de esta pestaña) es
(30 páginas, 268 caracteres: latinas mayúsculas y minúsculas, dígitos, acentos, puntuación,
griego en mayúscula y minúscula y unos 110 símbolos matemáticos).

Si quieres otra plantilla (por ejemplo, más muestras de cada letra para que haya más variedad):
- marca o desmarca los grupos y cambia el número de **muestras** de cada uno;
- en *Caracteres extra* puedes escribir cualquier carácter que falte (p. ej. `ℜℑ⊛`);
- abajo se ve cuántas páginas saldrán; luego pulsa **Crear PDF de la plantilla…**.

> Las mayúsculas griegas que son iguales a las latinas (Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Χ) no se
> piden: se usan tus latinas automáticamente.

**Más muestras = más naturalidad.** Con 8 muestras por letra ya no se nota la repetición;
con 15–20 es casi imposible de notar. Puedes empezar con la plantilla completa y más adelante
hacer otra solo de minúsculas con 15 muestras: se **suman** a tu letra.

## 2 · Escribir en la Kindle Scribe

1. Envía el PDF a tu Kindle con **Send to Kindle** (la app de escritorio, la web de
   Send to Kindle o el correo de tu Kindle). Debe llegar como PDF (no convertido) para poder
   escribir encima.
2. Escribe con el lápiz, en negro, **un carácter por casilla**:
   - la **línea continua** es la línea base (donde se apoyan las letras);
   - la **discontinua** marca la altura de las minúsculas (a, c, e…);
   - la **punteada** de arriba, la altura de mayúsculas y letras altas (b, d, l…);
   - g, p, q, y, j bajan por debajo de la línea continua, como en un cuaderno.
   - La puntuación también se escribe en su altura real: el punto en la línea, el apóstrofo arriba.
3. **No escribas sobre los cuadros negros** de las esquinas ni sobre la fila de cuadritos de
   abajo: así el programa alinea y reconoce cada página.
4. Las casillas que dejes vacías simplemente se ignoran (no pasa nada).
5. Exporta el documento con tus anotaciones como PDF (en la Kindle: menú del documento →
   compartir/exportar → se envía por correo) y descárgalo a la computadora.
   El nombre del menú puede variar según la versión del software de la Kindle.

## 3 · Importar (pestaña 2)

Pulsa **Elegir PDF escrito…** y selecciona el PDF exportado. **No hace falta nada más**:
cada página lleva impreso un código con el número de página y el id de la plantilla, así que
da igual si las páginas vienen desordenadas o si falta alguna.

- Si importas otra vez la misma plantilla (por ejemplo, porque corregiste letras), sus
  muestras se **reemplazan**.
- Si importas otra plantilla distinta, se **suman**.
- Si el PDF viene de una plantilla creada en *otra* computadora, copia antes su archivo
  `datos/plantillas/xxxxxx.json` a la carpeta `datos/plantillas/` de esta.

## 4 · Revisar (pestaña 3)

Ves todas tus muestras agrupadas por carácter, apoyadas en su línea base.
- **Clic** en una muestra fea → queda descartada (gris). Otro clic la recupera.
- Las **naranjas** tocan el borde de la casilla: puede que se hayan cortado; revísalas.
- Arriba se listan los caracteres que todavía no tienen ninguna muestra.
- *Filtrar*: escribe uno o varios caracteres para ver solo esos.

## 5 · Escribir (pestaña 4)

Escribe o pega texto a la izquierda; a la derecha aparece con tu letra al instante.

- **📋 Copiar** (o Ctrl+Shift+C): copia la imagen; pégala con Ctrl+V en Word, OneNote,
  Paint, WhatsApp, etc.
- **PNG… / PDF…**: guarda el resultado. Con *Paginar en hojas tamaño carta* el PDF tiene
  varias páginas.
- **🎲 Otra variante**: vuelve a barajar qué muestra se usa para cada letra.
- **Tamaño, desorden, inclinación, separación, interlineado**: ajústalo a tu gusto.
  *Desorden 0* = rígido; 1 = natural; 2 = escrito con prisa.
- **Papel**: rayado, cuadriculado, blanco o transparente (PNG sin fondo para poner
  encima de otra imagen).
- **Tinta**: negro, azul, rojo, verde, grafito o cualquier color con «…».
- Se recuerdan tus ajustes y tu último texto al cerrar.
- **Acentos con tilde normal**: activado, borra la marca que escribiste sobre á é í ó ú
  y dibuja una tilde inclinada con el grosor de tu trazo. (La Í se arma con tu I.)
- **Centrar y ajustar signos**: activado, pone + − = × ÷ ± < > ≤ ≥ → … a media altura
  (el «eje matemático» de tu letra) y con un tamaño acorde con tus dígitos.
  Desactiva cualquiera de las dos casillas para ver tus trazos originales.
  En consola: `--acentos-originales` y `--signos-originales`.

### Fórmulas: superíndices y subíndices

Con la casilla *^ y _* activada, se usa una sintaxis parecida a LaTeX:

| Escribes                | Sale                                 |
|-------------------------|--------------------------------------|
| `x^2`                   | x con un 2 arriba                    |
| `a_n`                   | a con n abajo                        |
| `e^{i(kx − ωt)}`        | todo lo de las llaves arriba         |
| `∑_{n=1}^∞`             | n=1 abajo e ∞ arriba, **apilados**   |
| `∫_0^{2π}`              | límites de la integral apilados      |
| `a\_b`, `2\^3`          | guion bajo / acento circunflejo literal |
| `\frac{1}{2}`           | fracción apilada con raya            |
| `\pmat{2 & 0 ; 0 & −1}` | matriz con paréntesis (`&` separa columnas, `;` filas) |
| `\pmat{1 ; 0}`          | vector columna                       |
| `\bmat{…}`, `\vmat{…}`  | con corchetes / determinante con barras |

Se pueden anidar: `\pmat{−\frac{t}{2} ; e^{2t}}`. Los paréntesis y barras se estiran a partir
de tus propios trazos. Las líneas con matrices ocupan los renglones que necesiten.
Ejemplos: `ejemplos/epsilon_delta.txt` y `ejemplos/ejemplo_fisica.txt`. Sintaxis completa (incluido LaTeX): `docs/FORMATO.md`.

También puedes usar directamente caracteres Unicode como `ε₀`, `x²`, `ħ`.

### ¿Cómo evita que se vea repetido?

- Para cada carácter, el programa usa una **bolsa barajada** de tus muestras: va sacando
  todas tus versiones en orden aleatorio antes de repetir ninguna, y nunca pone la misma
  dos veces seguidas. Si escribiste 8 «a», en un texto largo verás las 8 por igual.
- Además, cada letra recibe una variación leve de tamaño, ancho, inclinación, giro, altura
  sobre la línea, presión de la tinta y separación; y cada renglón se tuerce un poco.
- Modo **promedio**: en vez de elegir muestras, usa una «media» de todas. Es más uniforme
  pero se ve menos natural; el modo **aleatorio** es el recomendado.

### Caracteres sin muestra

Si escribes un carácter que no tienes (la app los lista abajo), se dibuja con una fuente
manuscrita de Windows como respaldo. Para tenerlo con tu letra, añádelo en *Caracteres extra*
de una plantilla nueva, escríbela e impórtala.

---

## Menú «Letra»

- **Exportar mi letra (.zip)**: copia de seguridad, o para llevarla a otra computadora.
- **Importar letra (.zip)**: la carga en la carpeta que elijas.
- **Abrir carpeta de la letra**: tus muestras son PNG normales en `datos/mi_letra/glifos/`.
- **Usar otra carpeta de letra**: puedes tener varias letras (p. ej. «apuntes» y «firma»).

## Uso por línea de órdenes (opcional)

```
python miletra.py estado                       # en qué paso estás
python miletra.py plantilla --sets "latin:15,digitos:10" -o mas_letras.pdf
python miletra.py importar escrito.pdf
python miletra.py escribir "∑_{n=1}^∞ \frac{1}{n^2} = \frac{π^2}{6}" -o formula.png --color negro --papel blanco
python miletra.py escribir -f apuntes.txt -o apuntes.pdf --hoja --vista
python miletra.py validar apuntes.txt          # revisa la sintaxis antes
```

## Archivos

| Archivo / carpeta     | Qué es                                                         |
|-----------------------|----------------------------------------------------------------|
| `app.py`              | El programa con ventana                                        |
| `plantilla.py`        | Genera plantillas PDF                                          |
| `extraer.py`          | Saca tus letras del PDF escrito                                |
| `escribir.py`         | Convierte texto en imagen/PDF con tu letra                     |
| `comun.py`            | Medidas de la plantilla y lista de caracteres (puedes editarla)|
| `miletra.py`          | La orden principal (todas las funciones, con `--json`)         |
| `simular.py`          | Rellena una plantilla con letra falsa (`miletra demo`)         |
| `datos/`              | **Todo lo personal** (nunca se sube a git):                    |
| `datos/plantillas/`   | Registro de plantillas generadas (**no lo borres**)            |
| `datos/mi_letra/`     | Tu letra: `glifos.json` + `glifos/*.png`                       |
| `datos/config.json`   | Tus ajustes de la pestaña Escribir                             |

## Problemas frecuentes

- **«pág N: no reconocida»** → probablemente se tapó o tachó la fila de cuadritos de abajo
  o un cuadro negro. Esa página se omite; el resto se importa normal.
- **«plantilla xxxxxx desconocida en este equipo»** → la plantilla se creó en otra
  computadora o borraste `datos/plantillas/`. Copia ese `.json` a `datos/plantillas/`.
- **Letras cortadas (naranjas)** → escribiste tocando el borde; descártalas o reescríbelas.
- **Trazos grises o de color** → si la Kindle guarda la tinta como anotaciones se detecta en
  cualquier color; si la «aplana» en la página, usa lápiz negro.
