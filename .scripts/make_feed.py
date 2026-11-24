#!/usr/bin/env python3
"""Write feed.xml: the site's own RSS feed of episodes.

Every item links to the episode's page on happypathprogramming.com (its guid
too), carries the page's "About this episode" text and resources, the episode's
share card as its image, the audio enclosure from the podcast feed, so the
feed also plays in a podcast app, and a `<podcast:transcript>` pointing at the
site's own copy of the transcript (`transcripts/<slug>.srt`) when it has one. Only episodes go in it: guest and topic pages
are not news.

Everything is read back from the episode pages plus the cached podcast feed,
and the channel's lastBuildDate is the newest episode's air date, so re-running
with nothing new rewrites an identical file.

    python3 .scripts/make_feed.py
    python3 .scripts/make_feed.py --refresh    # re-fetch the podcast feed first
"""
from __future__ import annotations

import os
import re
import sys
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import hpp
from hpp import SITE, SITE_FEED, SITE_NAME, TAGLINE

OUT = "feed.xml"


def attr(s: str) -> str:
    return escape(s, {'"': "&quot;"})


def cdata(s: str) -> str:
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def absolutize(fragment: str) -> str:
    """Page-relative hrefs/srcs (`../guests/x.html`) -> absolute site URLs."""
    def fix(m):
        url = m.group(2)
        if url.startswith(("http://", "https://", "mailto:", "#", "data:")):
            return m.group(0)
        while url.startswith("../"):
            url = url[3:]
        return f'{m.group(1)}="{SITE}/{url}"'
    return re.sub(r'(href|src)="([^"]*)"', fix, fragment)


def body(doc: str) -> str:
    """The episode's description and resources, as HTML for the item."""
    m = re.search(r'<h2>About this episode</h2>\s*<div class="prose">(.*?)</div>\s*</section>',
                  doc, re.S)
    prose = m.group(1).strip() if m else ""
    res = re.search(r'<h2>Resources &amp; links</h2>\s*(<ul class="res-list">.*?</ul>)', doc, re.S)
    out = prose
    if res:
        out += "\n<h3>Resources &amp; links</h3>\n" + res.group(1)
    return absolutize(out)


def rfc822(iso: str) -> str:
    return format_datetime(datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
                           .replace(tzinfo=timezone.utc), usegmt=True)


def item(slug: str, feed: dict[int, dict]) -> tuple[str, str]:
    doc = open(f"episodes/{slug}.html", encoding="utf-8").read()
    ep = hpp.episode_page(doc)
    num = ep["number"]
    info = feed.get(num, {})
    url = f"{SITE}/episodes/{slug}.html"
    title = f"#{num} {ep['title']}"
    lines = [
        "    <item>",
        f"      <title>{escape(title)}</title>",
        f"      <link>{escape(url)}</link>",
        f'      <guid isPermaLink="true">{escape(url)}</guid>',
    ]
    if info.get("published"):
        lines.append(f"      <pubDate>{rfc822(info['published'])}</pubDate>")
    for name, _s in ep["topics"]:
        lines.append(f"      <category>{escape(name)}</category>")
    lines.append(f"      <description>{cdata(body(doc))}</description>")
    audio = info.get("audio") or ep["audio"]
    if audio:
        lines.append(f'      <enclosure url="{attr(audio)}" '
                     f'length="{attr(info.get("audio_length") or "0")}" '
                     f'type="{attr(info.get("audio_type") or "audio/mpeg")}"/>')
    if num:
        lines.append(f"      <itunes:episode>{num}</itunes:episode>")
    if info.get("seconds"):
        lines.append(f"      <itunes:duration>{info['seconds']}</itunes:duration>")
    lines.append(f'      <itunes:image href="{attr(SITE)}/images/og/episodes/{attr(slug)}.jpg"/>')
    if os.path.exists(f"transcripts/{slug}.srt"):
        lines.append(f'      <podcast:transcript url="{attr(SITE)}/transcripts/{attr(slug)}.srt" '
                     'type="application/x-subrip"/>')
    lines.append("    </item>")
    return "\n".join(lines), info.get("published", "")


def main() -> None:
    hpp.require_root()
    feed = hpp.episodes_from_feed(refresh="--refresh" in sys.argv)
    items, dates = [], []
    for slug, _title in hpp.episode_index_items():
        xml, published = item(slug, feed)
        items.append(xml)
        if published:
            dates.append(published)
    built = rfc822(max(dates)) if dates else ""

    head = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" '
        'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
        'xmlns:podcast="https://podcastindex.org/namespace/1.0">',
        "  <channel>",
        f"    <title>{escape(SITE_NAME)}</title>",
        f"    <link>{SITE}/</link>",
        f'    <atom:link href="{SITE_FEED}" rel="self" type="application/rss+xml"/>',
        f"    <description>{escape(TAGLINE)}</description>",
        "    <language>en-us</language>",
        "    <copyright>Bruce Eckel &amp; James Ward</copyright>",
        *([f"    <lastBuildDate>{built}</lastBuildDate>"] if built else []),
        "    <image>",
        f"      <url>{SITE}/images/hpp.jpg</url>",
        f"      <title>{escape(SITE_NAME)}</title>",
        f"      <link>{SITE}/</link>",
        "    </image>",
        "    <itunes:author>Bruce Eckel &amp; James Ward</itunes:author>",
        f'    <itunes:image href="{SITE}/images/hpp.jpg"/>',
        '    <itunes:category text="Technology"/>',
        "    <itunes:explicit>false</itunes:explicit>",
    ]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(head + items + ["  </channel>", "</rss>"]) + "\n")

    pages = len(hpp.episode_slugs())
    print(f"{OUT}: {len(items)} episodes (episode pages on disk: {pages})")
    if len(items) != pages:
        sys.exit("feed does not cover every episode page — check episodes/index.html")


if __name__ == "__main__":
    main()
