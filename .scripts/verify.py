#!/usr/bin/env python3
"""Check the site before publishing. Exits non-zero with a list of problems.

Covers the "Verify before finishing" list in AGENTS.md:
  - every page parses (tags nest and close)
  - links and assets are relative and resolve to files that exist
  - the only absolute-internal URLs are the intentional ones (canonical, og:,
    JSON-LD, share links)
  - every page has the full og:/twitter: set, a valid JSON-LD block and a
    share row
  - every referenced share image exists and is the right size
  - every <img> has width/height (no layout shift as it loads), and the
    above-the-fold hero images are not lazy-loaded
  - every referenced .jpg really is a JPEG
  - feed.xml parses and has one item per episode page, each linking to it
  - llms.txt links every episode, guest and topic page, and llms-full.txt has
    a section for every episode

    python3 .scripts/verify.py
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import hpp
from hpp import SITE

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
REQUIRED_META = [
    "og:type", "og:site_name", "og:locale", "og:title", "og:description",
    "og:url", "og:image", "og:image:type", "og:image:width", "og:image:height",
    "og:image:alt", "twitter:card", "twitter:site", "twitter:creator",
    "twitter:title", "twitter:description", "twitter:image", "twitter:image:alt",
]
problems: list[str] = []


class Nesting(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path, self.stack = path, []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            problems.append(f"{self.path}: stray </{tag}>")
        elif self.stack[-1] != tag:
            problems.append(f"{self.path}: </{tag}> closes <{self.stack[-1]}>")
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
        else:
            self.stack.pop()


def jpeg_size(path: str) -> tuple[int, int] | None:
    with open(path, "rb") as f:
        d = f.read()
    if d[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(d) - 9:
        if d[i] != 0xFF:
            i += 1
            continue
        marker = d[i + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            h, w = struct.unpack(">HH", d[i + 5:i + 9])
            return w, h
        i += 2 if (marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7) else \
            2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    return None


def check_feed() -> None:
    """feed.xml lists every episode page, linked by its absolute URL."""
    try:
        root = ET.parse("feed.xml").getroot()
    except (OSError, ET.ParseError) as e:
        problems.append(f"feed.xml: {e}")
        return
    links = {(i.findtext("link") or "") for i in root.iterfind("./channel/item")}
    want = {f"{SITE}/episodes/{s}.html" for s in hpp.episode_slugs().values()}
    for url in sorted(want - links):
        problems.append(f"feed.xml: no item for {url}")
    for url in sorted(links - want):
        problems.append(f"feed.xml: item links to a missing page {url}")


def check_llms() -> None:
    """llms.txt links every page it should; llms-full.txt covers every episode."""
    try:
        index = open("llms.txt", encoding="utf-8").read()
        full = open("llms-full.txt", encoding="utf-8").read()
    except OSError as e:
        problems.append(f"llms: {e}")
        return
    linked = set(re.findall(r"\]\((" + re.escape(SITE) + r"/[^)\s]+)\)", index))
    want = {f"{SITE}/{p}" for p in hpp.pages()
            if hpp.classify(p)[0] in ("episode", "guest", "topic")}
    for url in sorted(want - linked):
        problems.append(f"llms.txt: no link to {url}")
    for url in sorted(linked):
        if not os.path.exists(url[len(SITE) + 1:]):
            problems.append(f"llms.txt: links to a missing file {url}")
    sections = set(re.findall(r"^- Page: (\S+)$", full, re.M))
    for url in sorted(u for u in want - sections if "/episodes/" in u):
        problems.append(f"llms-full.txt: no section for {url}")


def main() -> None:
    hpp.require_root()
    paths = hpp.pages()
    ld_blocks = share_rows = 0

    for path in paths:
        doc = open(path, encoding="utf-8").read()
        kind, _section, slug = hpp.classify(path)

        checker = Nesting(path)
        checker.feed(doc)
        checker.close()
        if checker.stack:
            problems.append(f"{path}: unclosed {checker.stack}")

        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', doc, re.S)
        if not blocks:
            problems.append(f"{path}: no JSON-LD block")
        for block in blocks:
            try:
                data = json.loads(block)
            except json.JSONDecodeError as e:
                problems.append(f"{path}: bad JSON-LD ({e})")
                continue
            ld_blocks += 1
            if not data.get("@graph"):
                problems.append(f"{path}: empty JSON-LD @graph")

        if 'class="share-row"' in doc:
            share_rows += 1
        else:
            problems.append(f"{path}: no share row")

        for tag in REQUIRED_META:
            if f'"{tag}"' not in doc:
                problems.append(f"{path}: missing {tag}")

        # sized images keep the layout from shifting as they load (Lighthouse unsized-images)
        for img in re.findall(r"<img\b[^>]*>", doc):
            if not re.search(r'\swidth="\d+"', img) or not re.search(r'\sheight="\d+"', img):
                problems.append(f"{path}: <img> without width/height: {img[:80]}")
            # the hero art is above the fold (the page's LCP image): never lazy-load it
            if re.search(r'class="latest-art"', img) and 'loading="lazy"' in img:
                problems.append(f"{path}: above-the-fold <img> is lazy-loaded: {img[:80]}")
        for img in re.findall(r'<div class="ep-hero-art"><img\b[^>]*>', doc):
            if 'loading="lazy"' in img:
                problems.append(f"{path}: above-the-fold <img> is lazy-loaded: {img[:80]}")

        base = os.path.dirname(path)
        for m in re.finditer(r'(?:href|src)="([^"]+)"', doc):
            url = m.group(1)
            if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
                if url.startswith(SITE):
                    tag = doc[doc.rfind("<", 0, m.start()):m.start()]
                    if not re.match(r'<link rel="(canonical|alternate)"', tag):
                        problems.append(f"{path}: absolute internal link {url}")
                continue
            target = os.path.normpath(os.path.join(base, url.split("#")[0]))
            if not os.path.exists(target):
                problems.append(f"{path}: missing link target {url}")
            elif target.endswith(".jpg") and jpeg_size(target) is None:
                problems.append(f"{path}: {url} is not a JPEG (wrong extension?)")

        # the page's own share card must exist and be exactly 1200x630
        card = re.search(r'<meta property="og:image" content="([^"]+)"', doc)
        if card:
            local = card.group(1).replace(SITE + "/", "")
            if not os.path.exists(local):
                problems.append(f"{path}: og:image missing {local}")
            elif jpeg_size(local) != (1200, 630):
                problems.append(f"{path}: og:image {local} is {jpeg_size(local)}, "
                                f"expected (1200, 630)")
            elif kind in ("episode", "guest"):
                want = f"images/og/{kind}s/{slug}.jpg"
                if local != want:
                    problems.append(f"{path}: og:image is {local}, expected {want}")

    check_feed()
    check_llms()
    print(f"pages: {len(paths)}  json-ld: {ld_blocks}  share rows: {share_rows}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems[:40]:
            print(" -", p)
        if len(problems) > 40:
            print(f" … and {len(problems) - 40} more")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
