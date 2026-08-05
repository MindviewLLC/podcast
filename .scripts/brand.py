"""Shared brand palette, fonts and drawing primitives for the share cards.

Every generated image is 1200x630 (the OpenGraph / summary_large_image size)
and shares one backdrop so the cards read as a set.
"""
from __future__ import annotations

import colorsys
import os
import re

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1200, 630

# Matches the CSS custom properties in styles.css.
INK = (20, 22, 31)           # --ink
GREEN = (15, 157, 88)        # --green
GREEN_LIGHT = (52, 211, 153)
MINT = (159, 231, 194)       # the .back link green
ACCENT = (250, 204, 21)      # --accent
MUTED = (154, 163, 178)
WHITE = (255, 255, 255)

PAD_X = 72                   # left text column origin
COL_W = 620                  # left text column width
ART_X = 736                  # right artwork column origin

# Font families in preference order. Liberation is metrically Arial-like and
# closest to the site's Inter; DejaVu is the fallback that ships nearly
# everywhere; the macOS paths keep this runnable off Linux. Cards are rendered
# once and never redrawn, so a different machine only affects NEW cards.
_SANS_BOLD = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]
_SANS_REG = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]
_MONO_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "/System/Library/Fonts/Menlo.ttc",
]


def _resolve(candidates: list[str]) -> str:
    for path in candidates:
        if os.path.exists(path):
            return path
    raise SystemExit(
        "No usable font found. Tried:\n  " + "\n  ".join(candidates) +
        "\nInstall the fonts (Debian/Ubuntu: apt-get install "
        "fonts-liberation fonts-dejavu-core).")


SANS_B = _resolve(_SANS_BOLD)
SANS_R = _resolve(_SANS_REG)
MONO_B = _resolve(_MONO_BOLD)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


# ---------------------------------------------------------------- backdrop
def _radial(center, radius, color, strength):
    """A soft radial glow, drawn small and upscaled so it stays smooth."""
    layer = Image.new("RGB", (W // 6, H // 6), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy, r = center[0] / 6, center[1] / 6, radius / 6
    steps = 48
    for i in range(steps, 0, -1):
        f = i / steps
        rr = r * f
        a = (1 - f) ** 2 * strength
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  fill=tuple(int(c * a) for c in color))
    return layer.resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(24))


def backdrop() -> Image.Image:
    """Ink background, green glow bottom-left, the brand rule, the happy path."""
    img = Image.new("RGB", (W, H), INK)
    img = ImageChops.add(img, _radial((150, 640), 880, GREEN, 0.8))
    img = ImageChops.add(img, _radial((1140, 20), 660, ACCENT, 0.18))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 8], fill=GREEN)
    d.rectangle([0, 0, 300, 8], fill=ACCENT)
    for off, alpha in [(0, 0.30), (18, 0.13)]:
        d.line([(-40, 626 + off), (400, 590 + off), (820, 604 + off),
                (1240, 546 + off)],
               fill=tuple(int(c * alpha + INK[j] * (1 - alpha))
                          for j, c in enumerate(GREEN_LIGHT)),
               width=3, joint="curve")
    return img


def footer(d: ImageDraw.ImageDraw, y: int = 540) -> None:
    d.text((PAD_X, y), "happypathprogramming.com",
           font=font(MONO_B, 22), fill=GREEN_LIGHT)


# ------------------------------------------------------------------ shapes
def mask_round(img: Image.Image, radius: int | None) -> Image.Image:
    """Round an image's corners (radius=None -> circle), antialiased."""
    s = 4
    big = Image.new("L", (img.width * s, img.height * s), 0)
    dd = ImageDraw.Draw(big)
    box = [0, 0, img.width * s - 1, img.height * s - 1]
    if radius is None:
        dd.ellipse(box, fill=255)
    else:
        dd.rounded_rectangle(box, radius=radius * s, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), big.resize(img.size, Image.LANCZOS))
    return out


def glow_behind(base, box, radius, color=(15, 157, 88, 120), blur=20, pad=26):
    """Green halo behind artwork, so it lifts off the dark backdrop."""
    x, y, w, h = box
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    dd = ImageDraw.Draw(layer)
    if radius is None:
        dd.ellipse([pad, pad, pad + w, pad + h], fill=color)
    else:
        dd.rounded_rectangle([pad, pad, pad + w, pad + h], radius=radius, fill=color)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.paste(layer, (x - pad, y - pad), layer)


def cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Resize + centre-crop to exactly `size` (CSS object-fit: cover)."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    nw, nh = max(tw, round(img.width * scale)), max(th, round(img.height * scale))
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return img.crop((left, top, left + tw, top + th))


def initials_avatar(name: str, size: int) -> Image.Image:
    """The site's deterministic gradient-initials avatar, as an image."""
    parts = [p for p in re.split(r"\s+", name) if p]
    letters = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
    hue = (sum(ord(c) for c in name) % 360) / 360.0
    c1 = tuple(int(v * 255) for v in colorsys.hls_to_rgb(hue, 0.42, 0.55))
    c2 = tuple(int(v * 255) for v in colorsys.hls_to_rgb((hue + 0.09) % 1.0, 0.60, 0.60))
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for i in range(size):
        f = i / max(size - 1, 1)
        d.line([(0, i), (size, i)],
               fill=tuple(round(c1[j] + (c2[j] - c1[j]) * f) for j in range(3)))
    f = font(SANS_B, int(size * 0.38))
    box = d.textbbox((0, 0), letters, font=f)
    d.text(((size - (box[2] - box[0])) / 2 - box[0],
            (size - (box[3] - box[1])) / 2 - box[1]), letters, font=f, fill=WHITE)
    return img


# --------------------------------------------------------------- typesetting
def wrap(draw, text: str, fnt, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if not cur or draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text: str, max_w: int, max_lines: int, sizes: list[int],
        path: str = SANS_B):
    """Largest size from `sizes` whose wrap fits in `max_lines`; else ellipsis."""
    for size in sizes:
        fnt = font(path, size)
        lines = wrap(draw, text, fnt, max_w)
        if len(lines) <= max_lines and all(
                draw.textlength(l, font=fnt) <= max_w for l in lines):
            return fnt, lines
    fnt = font(path, sizes[-1])
    lines = wrap(draw, text, fnt, max_w)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" ,;:-") + "…"
    return fnt, lines


def draw_lines(d, xy, lines, fnt, fill, leading) -> int:
    """Draw wrapped lines; return the y just past the block."""
    x, y = xy
    for line in lines:
        d.text((x, y), line, font=fnt, fill=fill)
        y += leading
    return y


def save(img: Image.Image, out: str) -> None:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, "JPEG", quality=84, optimize=True, progressive=True,
             subsampling=2)
