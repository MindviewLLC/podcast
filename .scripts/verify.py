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

    python3 .scripts/verify.py
"""
from __future__ import annotations

import json
import os
import re
import struct
import sys
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

        base = os.path.dirname(path)
        for m in re.finditer(r'(?:href|src)="([^"]+)"', doc):
            url = m.group(1)
            if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
                if url.startswith(SITE):
                    before = doc[max(0, m.start() - 60):m.start()]
                    if 'rel="canonical"' not in before:
                        problems.append(f"{path}: absolute internal link {url}")
                continue
            target = os.path.normpath(os.path.join(base, url.split("#")[0]))
            if not os.path.exists(target):
                problems.append(f"{path}: missing link target {url}")

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
