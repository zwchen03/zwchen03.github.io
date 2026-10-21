"""Turn a picture into a pixel-art avatar for the site.

Usage: python scripts/pixelate_avatar.py <source image> [grid=48] [colors=12] [eye=1x1]
Writes assets/avatar-pixel.png (grid x grid pixels, upscaled 8x with hard edges).

Each grid cell takes the most common palette colour in its block, except that
dark outline colours win whenever they cover a noticeable share of the block,
so thin lines survive the downscale instead of blurring into grey. Small dark
dots sitting on a light surface (eyes) are re-drawn afterwards (default 1x1 pixel),
since they are usually smaller than a cell and would otherwise vanish.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

src = Path(sys.argv[1])
grid = int(sys.argv[2]) if len(sys.argv) > 2 else 48
colors = int(sys.argv[3]) if len(sys.argv) > 3 else 12
eye_w, eye_h = map(int, (sys.argv[4] if len(sys.argv) > 4 else "1x1").split("x"))
out = Path(__file__).resolve().parent.parent / "assets" / "avatar-pixel.png"
DARK_SHARE = 0.22  # min share of a block an outline colour needs to claim the cell

im = Image.open(src).convert("RGB")
side = min(im.size)
left, top = (im.width - side) // 2, (im.height - side) // 2
im = im.crop((left, top, left + side, top + side))
im = im.resize((grid * 16, grid * 16), Image.Resampling.LANCZOS).filter(ImageFilter.MedianFilter(5))

# flatten to a small palette first, so every block votes among a few clean colours
q = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
pal = q.getpalette()[: colors * 3]
rgb = [tuple(pal[i:i + 3]) for i in range(0, len(pal), 3)]
dark = {i for i, (r, g, b) in enumerate(rgb) if 0.299 * r + 0.587 * g + 0.114 * b < 70}

px = q.load()
cell = q.width // grid
small = Image.new("RGB", (grid, grid))
for gy in range(grid):
    for gx in range(grid):
        votes = Counter(px[x, y] for y in range(gy * cell, (gy + 1) * cell)
                        for x in range(gx * cell, (gx + 1) * cell))
        total = cell * cell
        dark_votes = [(n, c) for c, n in votes.items() if c in dark]
        if dark_votes and max(dark_votes)[0] / total >= DARK_SHARE:
            pick = max(dark_votes)[1]
        else:
            pick = votes.most_common(1)[0][0]
        small.putpixel((gx, gy), rgb[pick])

# re-draw small dark dots on light surroundings (eyes) as eye_w x eye_h pixels
lum = np.asarray(im).astype(float) @ [0.299, 0.587, 0.114]
labels, _ = ndimage.label(lum < 70)
darkest = min((rgb[i] for i in dark), key=sum, default=(20, 20, 20))
for i, sl in enumerate(ndimage.find_objects(labels), 1):
    area = (labels[sl] == i).sum()
    if not (cell * cell * 0.1 < area < cell * cell * 4):
        continue
    y0, x0 = max(sl[0].start - 6, 0), max(sl[1].start - 6, 0)
    box = labels[y0:sl[0].stop + 6, x0:sl[1].stop + 6]
    if lum[y0:sl[0].stop + 6, x0:sl[1].stop + 6][box != i].mean() < 200:
        continue  # not on a light surface
    cy, cx = ndimage.center_of_mass(labels == i)
    gx, gy = int(cx / cell - eye_w / 2 + 0.5), int(cy / cell - eye_h / 2 + 0.5)
    for dx in range(eye_w):
        for dy in range(eye_h):
            small.putpixel((min(gx + dx, grid - 1), min(gy + dy, grid - 1)), darkest)

small.resize((grid * 8, grid * 8), Image.Resampling.NEAREST).save(out)
print(f"wrote {out} ({grid}x{grid}, {colors} colors)")
