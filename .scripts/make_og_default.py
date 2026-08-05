#!/usr/bin/env python3
"""Render images/og-default.jpg — the branded 1200x630 share card used by the
home, list and topic pages.

This is a STABLE asset. It is already committed and does not need re-rendering;
running this only makes sense if the brand itself changes. Re-rendering churns
a new binary for no gain, so it refuses unless you pass --force.

    python3 .scripts/make_og_default.py --force
"""
import os
import sys

from PIL import Image, ImageDraw

import brand
import hpp
from brand import ACCENT, GREEN_LIGHT, MONO_B, MUTED, SANS_B, SANS_R, WHITE

OUT = "images/og-default.jpg"


def main() -> None:
    hpp.require_root()
    if os.path.exists(OUT) and "--force" not in sys.argv:
        print(f"{OUT} exists; pass --force to re-render (it is a stable asset)")
        return

    img = brand.backdrop()
    d = ImageDraw.Draw(img)

    logo = brand.cover(Image.open("images/hpp.jpg").convert("RGB"), (210, 210))
    brand.glow_behind(img, (86, 210, 210, 210), 42, blur=18, pad=20)
    logo = brand.mask_round(logo, 34)
    img.paste(logo, (86, 210), logo)

    x = 340
    d.text((x, 176), "T H E   P O D C A S T", font=brand.font(MONO_B, 22), fill=ACCENT)
    d.text((x, 214), "Happy Path", font=brand.font(SANS_B, 82), fill=WHITE)
    d.text((x, 300), "Programming", font=brand.font(SANS_B, 82), fill=GREEN_LIGHT)

    tag = brand.font(SANS_R, 27)
    d.text((x, 410), "No-frills discussions between Bruce Eckel", font=tag, fill=MUTED)
    d.text((x, 446), "and James Ward about programming.", font=tag, fill=MUTED)
    d.text((x, 510), "happypathprogramming.com",
           font=brand.font(MONO_B, 24), fill=GREEN_LIGHT)

    brand.save(img, OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
