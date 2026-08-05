#!/usr/bin/env python3
"""Regenerate sitemap.xml from the pages actually on disk.

Ordering matches how the site reads: home, the three list pages, episodes
newest first, guests A-Z, then topics in the curated tag-cloud order. Each URL
carries a <lastmod> derived from episode publication dates in the feed — an
episode's own date, and for a guest, topic or list page the date of the newest
episode it covers.

    python3 .scripts/make_sitemap.py
    python3 .scripts/make_sitemap.py --refresh    # re-fetch the feed first
"""
from __future__ import annotations

import datetime
import sys

import hpp
from hpp import SITE

HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')


def episode_dates(feed: dict[int, dict]) -> dict[str, str]:
    """episode slug -> YYYY-MM-DD."""
    out: dict[str, str] = {}
    for path in hpp.pages():
        kind, _section, slug = hpp.classify(path)
        if kind != "episode":
            continue
        ep = hpp.episode_page(open(path, encoding="utf-8").read())
        date = (feed.get(ep["number"], {}) or {}).get("date_only", "")
        if not date and ep["date"]:
            try:
                date = datetime.datetime.strptime(
                    ep["date"], "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                date = ""
        if date:
            out[slug] = date
    return out


def newest(dates: dict[str, str], slugs) -> str:
    found = [dates[s] for s in slugs if s in dates]
    return max(found) if found else ""


def main() -> None:
    hpp.require_root()
    feed = hpp.episodes_from_feed(refresh="--refresh" in sys.argv)
    dates = episode_dates(feed)
    latest = max(dates.values()) if dates else ""

    rows: list[tuple[str, str]] = [
        (f"{SITE}/", latest),
        (f"{SITE}/episodes/", latest),
        (f"{SITE}/guests/", latest),
        (f"{SITE}/topics/", latest),
    ]
    for slug, _title in hpp.episode_index_items():
        rows.append((f"{SITE}/episodes/{slug}.html", dates.get(slug, "")))
    for slug, _name in hpp.guest_index_items():
        doc = open(f"guests/{slug}.html", encoding="utf-8").read()
        rows.append((f"{SITE}/guests/{slug}.html",
                     newest(dates, [s for s, _ in hpp.appearances(doc)])))
    for slug, _name in hpp.topic_index_items():
        doc = open(f"topics/{slug}.html", encoding="utf-8").read()
        rows.append((f"{SITE}/topics/{slug}.html",
                     newest(dates, [s for s, _ in hpp.appearances(doc)])))

    body = "".join(
        f"  <url><loc>{loc}</loc>"
        + (f"<lastmod>{mod}</lastmod>" if mod else "")
        + "</url>\n"
        for loc, mod in rows)
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(HEAD + body + "</urlset>\n")

    expected = len([p for p in hpp.pages()])
    print(f"sitemap.xml: {len(rows)} urls (pages on disk: {expected})")
    if len(rows) != expected:
        sys.exit("sitemap does not cover every page — check the index listings")


if __name__ == "__main__":
    main()
