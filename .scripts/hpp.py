"""Shared site facts, the podcast feed, and readers for the generated pages.

The HTML in the repo root is the source of truth for what the site contains —
these helpers read it back so the tools never disagree about a page's title,
guests or slug.
"""
from __future__ import annotations

import html
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime

SITE = "https://www.happypathprogramming.com"
SITE_NAME = "Happy Path Programming"
TAGLINE = ("No-frills discussions between Bruce Eckel and James Ward about "
           "programming, what it is, and what it should be.")
TWITTER = "@happypathprog"
FEED = "https://anchor.fm/s/2ed56aa0/podcast/rss"

OG_DEFAULT = f"{SITE}/images/og-default.jpg"
OG_DEFAULT_ALT = f"{SITE_NAME} — the podcast"

HOSTS = [
    {"@type": "Person", "name": "Bruce Eckel",
     "url": "https://www.mindviewllc.com/about/",
     "sameAs": ["https://bsky.app/profile/bruceeckel.bsky.social",
                "https://x.com/BruceEckel"]},
    {"@type": "Person", "name": "James Ward", "url": "https://www.jamesward.com",
     "sameAs": ["https://bsky.app/profile/jamesward.com",
                "https://x.com/JamesWard"]},
]
SERIES_SAME_AS = [
    "https://bsky.app/profile/happypathprogramming.com",
    "https://x.com/happypathprog",
    "https://www.youtube.com/@HappyPathProgramming",
    "https://open.spotify.com/show/25XAbgCB7VeHgREPSUzBYY",
    "https://podcasts.apple.com/us/podcast/happy-path-programming/id1531666706",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"


def require_root() -> None:
    """Every tool writes repo-relative paths; make that unambiguous."""
    os.chdir(ROOT)
    if not os.path.exists("index.html"):
        sys.exit(f"{ROOT} does not look like the site repo (no index.html)")


# ------------------------------------------------------------------- feed
def fetch_feed(refresh: bool = False) -> str:
    """The podcast RSS, cached under .scripts/.cache (gitignored)."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "podcast.rss")
    if refresh or not os.path.exists(path):
        with urllib.request.urlopen(FEED, timeout=60) as r:
            data = r.read()
        with open(path, "wb") as f:
            f.write(data)
    return path


def iso_duration(raw: str) -> tuple[str, int]:
    """'01:07:26' or '3620' -> ('PT1H7M26S', seconds)."""
    if not raw:
        return "", 0
    try:
        nums = [int(p) for p in raw.strip().split(":")]
    except ValueError:
        return "", 0
    if len(nums) == 1:
        secs = nums[0]
    elif len(nums) == 2:
        secs = nums[0] * 60 + nums[1]
    else:
        secs = nums[0] * 3600 + nums[1] * 60 + nums[2]
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    out = "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{s}S" if s else "")
    return (out if out != "PT" else "PT0S"), secs


def episodes_from_feed(refresh: bool = False) -> dict[int, dict]:
    """Episode number -> publication date, duration and audio enclosure."""
    root = ET.parse(fetch_feed(refresh)).getroot()
    out: dict[int, dict] = {}
    for item in root.findall(".//item"):
        num_el = item.find(ITUNES + "episode")
        title = (item.findtext("title") or "").strip()
        if num_el is not None and (num_el.text or "").strip().isdigit():
            num = int(num_el.text.strip())
        else:
            m = re.match(r"#(\d+)", title)
            if not m:
                continue
            num = int(m.group(1))
        try:
            dt = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(
                timezone.utc)
        except Exception:
            dt = None
        enc = item.find("enclosure")
        duration, seconds = iso_duration(item.findtext(ITUNES + "duration") or "")
        out[num] = {
            "published": dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt else "",
            "date_only": dt.strftime("%Y-%m-%d") if dt else "",
            "duration": duration,
            "seconds": seconds,
            "audio": enc.get("url", "") if enc is not None else "",
            "audio_type": enc.get("type", "audio/mpeg") if enc is not None else "",
        }
    return out


# ------------------------------------------------------------------ pages
def unesc(s: str) -> str:
    return html.unescape(s)


def field(doc: str, pattern: str, default: str = "") -> str:
    m = re.search(pattern, doc, re.S)
    return unesc(m.group(1)).strip() if m else default


def pages() -> list[str]:
    """Every HTML page, repo-relative, sorted."""
    out = []
    for root, _dirs, names in os.walk("."):
        if root.startswith("./.git") or root.startswith("./.scripts"):
            continue
        out += [os.path.normpath(os.path.join(root, n))
                for n in names if n.endswith(".html")]
    return sorted(out)


def classify(path: str) -> tuple[str, str, str]:
    """(kind, section, slug) where kind is home|list|episode|guest|topic."""
    parts = os.path.normpath(path).split(os.sep)
    section = parts[0] if len(parts) > 1 else ""
    slug = os.path.basename(path)[:-5]
    if not section:
        return "home", "", slug
    if slug == "index":
        return "list", section, slug
    return {"episodes": "episode", "guests": "guest",
            "topics": "topic"}[section], section, slug


def display_titles() -> dict[str, str]:
    """slug -> the short episode title used on cards site-wide (guest stripped)."""
    doc = open("episodes/index.html", encoding="utf-8").read()
    return {s: unesc(t) for s, t in re.findall(
        r'<h3 class="ep-card-title"><a href="\.\./episodes/([^"]+)\.html">'
        r'(.*?)</a></h3>', doc)}


def episode_page(doc: str) -> dict:
    """Read one episode page back into its fields."""
    sub = field(doc, r'(<div class="ep-sub">.*?</div>)')
    topics_html = field(doc, r'(<div class="ep-topics">.*?</div>)')
    number = field(doc, r'<span class="ep-badge">Episode #(\d+)</span>')
    art = field(doc, r'<div class="ep-hero-art"><img src="\.\./(.*?)"')
    return {
        "number": int(number) if number else None,
        "title": field(doc, r'<h1 class="ep-title">(.*?)</h1>'),
        "guests": [(unesc(n), s) for s, n in re.findall(
            r'<a class="chip" href="\.\./guests/([^"]+)\.html">(.*?)</a>', sub)],
        "topics": [(unesc(n), s) for s, n in re.findall(
            r'<a class="chip chip--topic" href="\.\./topics/([^"]+)\.html">'
            r'(.*?)</a>', topics_html)],
        "date": field(doc, r'<span>🗓 ([^<]*)</span>'),
        "duration": field(doc, r'<span>⏱ ([^<]*)</span>'),
        "artwork": "" if art.endswith("hpp.jpg") else art,
        "audio": field(doc, r'<audio class="player"[^>]*src="([^"]*)"'),
    }


def guest_page(doc: str) -> dict:
    return {
        "name": field(doc, r'<div class="guest-hero-row">.*?<h1>(.*?)</h1>'),
        "photo": field(doc, r'class="avatar avatar--lg avatar-img" src="\.\./(.*?)"'),
        "episodes": appearances(doc),
    }


def topic_page(doc: str) -> dict:
    return {
        "name": field(doc, r'<span class="kicker">Topic</span>\s*<h1>(.*?)</h1>'),
        "episodes": appearances(doc),
    }


def episode_index_items() -> list[tuple[str, str]]:
    """(slug, title) of every episode, newest first, as listed on the index."""
    return appearances(open("episodes/index.html", encoding="utf-8").read())


def guest_index_items() -> list[tuple[str, str]]:
    """(slug, name) of every guest, A-Z, as listed on the guests index."""
    doc = open("guests/index.html", encoding="utf-8").read()
    # anchor on the card class: a looser href match swallows the nav link and
    # silently drops the first guest
    return [(s, unesc(n)) for s, n in re.findall(
        r'<a class="guest-card" href="\.\./guests/([^"]+)\.html">.*?'
        r'<span class="guest-name">(.*?)</span>', doc, re.S)]


def topic_index_items() -> list[tuple[str, str]]:
    """(slug, name) of every topic, in the curated tag-cloud order."""
    doc = open("topics/index.html", encoding="utf-8").read()
    return [(s, unesc(n)) for s, n in re.findall(
        r'<a class="topic-tag" href="\.\./topics/([^"]+)\.html">(.*?)<span', doc)]


def appearances(doc: str) -> list[tuple[str, str]]:
    """(slug, title) of every episode card listed on the page, in page order."""
    return [(s, unesc(t)) for s, t in re.findall(
        r'<h3 class="ep-card-title"><a href="\.\./episodes/([^"]+)\.html">'
        r'(.*?)</a></h3>', doc)]
