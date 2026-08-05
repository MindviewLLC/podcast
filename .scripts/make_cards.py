#!/usr/bin/env python3
"""Render the per-page 1200x630 OpenGraph share cards.

    images/og/episodes/<slug>.jpg   episode number + title + guests + facts
    images/og/guests/<slug>.jpg     guest name + photo

WRITE ONCE. Everything drawn on a card is an immutable fact about that episode
or guest, so a card never goes stale and is never re-rendered: this only draws
cards whose file is MISSING. On a normal update that means the new episode and
any new guests, and nothing else. Values that CAN change (a guest's appearance
count, say) are deliberately kept off the images — they live in the page's
twitter:label/data, which social.py rewrites every run for free.

    python3 .scripts/make_cards.py            # new episodes / guests only
    python3 .scripts/make_cards.py --force    # redraw everything (rare)

The one routine reason to redraw a single card is an episode whose YouTube
thumbnail appeared after its audio-only card was made: delete that one file.
"""
import os
import sys

from PIL import Image, ImageDraw

import brand
import hpp
from brand import ACCENT, ART_X, COL_W, MINT, MONO_B, MUTED, PAD_X, SANS_R, WHITE


def episode_card(out, *, number, title, guests, date, duration, artwork):
    img = brand.backdrop()
    d = ImageDraw.Draw(img)

    if artwork and os.path.exists(artwork):
        box = (ART_X, 202, 400, 225)                     # 16:9 video thumbnail
        art = brand.cover(Image.open(artwork).convert("RGB"), box[2:])
        brand.glow_behind(img, box, 18)
        art = brand.mask_round(art, 18)
        img.paste(art, box[:2], art)
    else:
        box = (ART_X + 80, 195, 240, 240)                # square show logo
        logo = brand.cover(Image.open("images/hpp.jpg").convert("RGB"), box[2:])
        brand.glow_behind(img, box, 40)
        logo = brand.mask_round(logo, 40)
        img.paste(logo, box[:2], logo)

    if number:
        d.text((PAD_X, 104), f"E P I S O D E   # {number}",
               font=brand.font(MONO_B, 22), fill=ACCENT)

    fnt, lines = brand.fit(d, title, COL_W, 4, [62, 56, 50, 45, 40, 36])
    leading = round(fnt.size * 1.16)
    y = max(150, 300 - len(lines) * leading // 2)
    y = brand.draw_lines(d, (PAD_X, y), lines, fnt, WHITE, leading)

    if guests:
        gf, glines = brand.fit(d, "with " + ", ".join(guests), COL_W, 2,
                               [30, 27, 24, 21])
        y = brand.draw_lines(d, (PAD_X, y + 16), glines, gf, MINT,
                             round(gf.size * 1.3))

    facts = " · ".join(x for x in (date, duration) if x)
    if facts:
        d.text((PAD_X, y + 14), facts, font=brand.font(MONO_B, 21), fill=MUTED)

    brand.footer(d)
    brand.save(img, out)


def guest_card(out, *, name, photo):
    img = brand.backdrop()
    d = ImageDraw.Draw(img)

    box = (ART_X + 40, 165, 300, 300)
    face = (brand.cover(Image.open(photo).convert("RGB"), box[2:])
            if photo and os.path.exists(photo)
            else brand.initials_avatar(name, box[2]))
    brand.glow_behind(img, box, None, blur=24, pad=30)
    face = brand.mask_round(face, None)
    img.paste(face, box[:2], face)

    d.text((PAD_X, 150), "P O D C A S T   G U E S T",
           font=brand.font(MONO_B, 22), fill=ACCENT)

    fnt, lines = brand.fit(d, name, COL_W, 3, [70, 62, 54, 48, 42])
    leading = round(fnt.size * 1.16)
    y = brand.draw_lines(d, (PAD_X, 208), lines, fnt, WHITE, leading)

    # Nothing volatile here: an appearance count would go stale the next time
    # this guest is on the show, and these cards are never re-rendered.
    d.text((PAD_X, y + 18), "on the Happy Path Programming podcast",
           font=brand.font(SANS_R, 27), fill=MUTED)

    brand.footer(d)
    brand.save(img, out)


def main() -> None:
    hpp.require_root()
    force = "--force" in sys.argv
    short = hpp.display_titles()
    made = kept = 0

    for path in hpp.pages():
        kind, _section, slug = hpp.classify(path)
        if kind not in ("episode", "guest"):
            continue
        out = f"images/og/{kind}s/{slug}.jpg"
        if os.path.exists(out) and not force:
            kept += 1
            continue
        doc = open(path, encoding="utf-8").read()
        if kind == "episode":
            ep = hpp.episode_page(doc)
            episode_card(out, number=ep["number"],
                         title=short.get(slug) or ep["title"],
                         guests=[n for n, _ in ep["guests"]],
                         date=ep["date"], duration=ep["duration"],
                         artwork=ep["artwork"])
        else:
            g = hpp.guest_page(doc)
            guest_card(out, name=g["name"], photo=g["photo"])
        made += 1
        print(f"  drew {out}")

    print(f"cards drawn: {made}, kept: {kept}")


if __name__ == "__main__":
    main()
