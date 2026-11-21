"""Generate the animated demo used in the README (docs/img/demo.gif).

    python holograph.py demo            # once: sample handwriting
    python tools/demo_gif.py            # writes docs/img/demo.gif

It types the source text on top and "writes" it by hand below, word by word.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import comun as C  # noqa: E402
import escribir as E  # noqa: E402

TEXT = (r"Theorem. \lim_{x \to 2} x^2 = 4." "\n"
        r"Proof. Let ε > 0 and choose δ = min{1, \frac{ε}{5}}." "\n"
        r"X′ = \pmat{2 & 0 ; 0 & −1} X + \pmat{e^{2t} ; 2},   \sum_{n=1}^\infty \frac{1}{n^2} = \frac{π^2}{6}")
SOURCE = ["Theorem. \\lim_{x \\to 2} x^2 = 4.",
          "Proof. Let ε > 0 and choose δ = min{1, \\frac{ε}{5}}.",
          "X′ = \\pmat{2 & 0 ; 0 & −1} X + \\pmat{e^{2t} ; 2},  \\sum_{n=1}^\\infty \\frac{1}{n^2} = \\frac{π^2}{6}"]

W, SCALE = 1500, 0.6           # render width, output scale
EVERY = 1                      # keep one frame every N words


def main():
    letra_dir = Path(C.DATA_DIR) / "letra_demo"
    if not (letra_dir / "glifos.json").exists():
        sys.exit("Run `python holograph.py demo` first.")
    letra = E.Letra(letra_dir)
    snaps = []
    pages = E.render(TEXT, letra, xh=26, ancho=W, semilla=5, papel="rayado", color="azul",
                     al_escribir=lambda p, a: snaps.append(a.copy()))
    page = pages[0]
    H = page.height
    ink = Image.new("RGBA", (W, H), E.COLORS["azul"] + (255,))
    paper = E._paper(W, H, "rayado", int(26 * 2.5) + 52, 26 * 3.0, 26, int(26 * 2.5))

    # cabecera con el texto fuente
    mono = C.font_path("consola.ttf", "DejaVuSansMono.ttf", "Menlo.ttc", "cour.ttf")
    font = ImageFont.truetype(mono, 19) if mono else ImageFont.load_default()
    head_h = 150

    def frame(alpha, typed_lines):
        img = Image.new("RGB", (W, head_h + H), (250, 250, 248))
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, head_h], fill=(30, 33, 40))
        d.text((24, 14), "$ holograph write notes.txt -o notes.pdf", fill=(120, 220, 140), font=font)
        for i, ln in enumerate(typed_lines):
            d.text((24, 48 + i * 30), ln, fill=(220, 224, 230), font=font)
        pg = paper.copy()
        layer = ink.copy()
        layer.putalpha(alpha)
        pg.alpha_composite(layer)
        img.paste(pg.convert("RGB"), (0, head_h))
        return img.resize((int(W * SCALE), int((head_h + H) * SCALE)), Image.LANCZOS)

    frames, durations = [], []
    empty = Image.new("L", (W, H), 0)
    # 1) se "teclea" el texto fuente
    for li, ln in enumerate(SOURCE):
        for k in range(8, len(ln) + 8, 8):
            frames.append(frame(empty, SOURCE[:li] + [ln[:k]]))
            durations.append(40)
    frames.append(frame(empty, SOURCE)); durations.append(500)
    # 2) se escribe a mano palabra a palabra
    for i, a in enumerate(snaps[::EVERY]):
        frames.append(frame(a, SOURCE)); durations.append(110)
    frames.append(frame(snaps[-1], SOURCE)); durations.append(3500)

    out = ROOT / "docs" / "img" / "demo.gif"
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=64) for f in frames]
    pal[0].save(out, save_all=True, append_images=pal[1:], duration=durations, loop=0, optimize=True)
    print(f"{out}  ({len(frames)} frames, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
