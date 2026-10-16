"""
Straighten a tilted tally photo so each row runs level across the page.

Why: Gemma reads rows straight across. On a tilted photo the numbers on the
right sit lower than their item name, so values slip into the next row.
Rotating the page level first fixes that.

How: try small rotations and keep the one where dark pixels (ink and ruled
lines) line up best into horizontal stripes, i.e. where the row-by-row
darkness varies the most. Plain numpy, no extra model.
"""

import io

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def find_tilt(img: Image.Image) -> float:
    small = ImageOps.grayscale(img)
    small.thumbnail((800, 800))
    gray = np.asarray(small, dtype=float)
    # Remove smooth shading (shadows, table colour): keep only fine marks
    # that are darker than their surroundings, i.e. ink and ruled lines.
    blurred = np.asarray(small.filter(ImageFilter.GaussianBlur(12)), dtype=float)
    marks = ((blurred - gray) > 12).astype("uint8") * 255
    h, w = marks.shape
    marks = marks[h // 6: -h // 6, w // 6: -w // 6]   # centre only: skip page edges
    best_angle, best_score = 0.0, -1.0
    for angle in np.arange(-15, 15.01, 0.5):
        rotated = Image.fromarray(marks).rotate(angle, resample=Image.NEAREST)
        rows = np.asarray(rotated, dtype=float).sum(axis=1)
        score = np.var(rows)                           # sharp stripes = level page
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def straighten(image_path: str) -> tuple[bytes, float]:
    """Return the levelled image as JPEG bytes, plus the angle corrected."""
    img = ImageOps.exif_transpose(Image.open(image_path)).convert("RGB")
    angle = find_tilt(img)
    level = img.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    buf = io.BytesIO()
    level.save(buf, format="JPEG", quality=92)
    return buf.getvalue(), angle
