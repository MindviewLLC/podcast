#!/usr/bin/env python3
"""Add each episode's own Apple Podcasts and YouTube links to its page.

    python3 .scripts/episode_links.py

Writes two pills into the hero `.pills` row of every episode page, right after
"Play on Spotify":
- "Play on Apple Podcasts": the episode's page on Apple Podcasts, from the public
  iTunes lookup API (matched by audio URL, else by `#NNN` in the title).
- "Watch on YouTube": the episode's real video, from `youtube.real_videos`.
  The podcast audio that YouTube re-publishes from the feed (a still of the
  logo) is never linked; episodes without a real video get no YouTube pill.

The pills carry `pill--apple` / `pill--youtube`, which is how a re-run finds
and replaces its own output; everything else in the row is the page's own.
If either source can't be fetched, the run changes nothing and says so (a
warning, exit 0), so an outage never strips links from the site.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hpp  # noqa: E402
import youtube  # noqa: E402
from social import esc, icon  # noqa: E402

APPLE_ID = "1531666706"
APPLE_LIMIT = 200  # the lookup API's maximum
APPLE_LOOKUP = (f"https://itunes.apple.com/lookup?id={APPLE_ID}"
                f"&entity=podcastEpisode&limit={APPLE_LIMIT}")
RE_PILLS = re.compile(r'(<div class="pills">)(.*?)(</div>)', re.S)
RE_OWN = re.compile(r'<a class="pill pill--(?:apple|youtube)"[^>]*>.*?</a>', re.S)
RE_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def apple_episodes() -> tuple[dict[str, str], dict[int, str], bool]:
    """(audio URL -> episode URL, episode number -> episode URL, complete?).
    `complete` is False when the API's result cap may have cut off old episodes."""
    req = urllib.request.Request(APPLE_LOOKUP, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        results = json.load(r)["results"]
    by_audio: dict[str, str] = {}
    by_num: dict[int, str] = {}
    episodes = [x for x in results if x.get("wrapperType") == "podcastEpisode"]
    for x in episodes:
        url = x.get("trackViewUrl") or ""
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "podcasts.apple.com":
            continue
        # drop the `uo=4` affiliate-tracking parameter, keep the `i=` episode id
        query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k == "i"]
        if not query:
            continue
        url = urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))
        if x.get("episodeUrl"):
            by_audio[x["episodeUrl"]] = url
        m = re.match(r"\s*#(\d+)\b", x.get("trackName") or "")
        if m:
            by_num.setdefault(int(m.group(1)), url)
    return by_audio, by_num, len(episodes) < APPLE_LIMIT


def pill(kind: str, href: str, label: str) -> str:
    return (f'<a class="pill pill--{kind}" href="{esc(href)}" target="_blank" '
            f'rel="noopener">{icon(kind)}{label}</a>')


def main() -> None:
    hpp.require_root()
    try:
        by_audio, by_num, complete = apple_episodes()
        videos = {n: vid for n, (vid, _b) in youtube.real_videos(youtube.videos()).items()
                  if RE_VIDEO_ID.fullmatch(vid)}
    except Exception as e:  # noqa: BLE001 - any fetch failure leaves the pages alone
        print(f"WARNING: couldn't fetch episode links ({e}); pages left unchanged",
              file=sys.stderr)
        return
    if not complete:
        print(f"WARNING: Apple returned {APPLE_LIMIT} episodes, its maximum; older "
              "episodes keep the Apple link they already have", file=sys.stderr)

    counts = {"apple": 0, "youtube": 0}
    for num, slug in sorted(hpp.episode_slugs().items()):
        path = f"episodes/{slug}.html"
        doc = open(path, encoding="utf-8").read()
        m = RE_PILLS.search(doc)
        if not m:
            sys.exit(f"{path}: no hero <div class=\"pills\"> row")
        old = dict(re.findall(r'<a class="pill pill--(apple|youtube)" href="([^"]*)"', m.group(2)))
        rest = RE_OWN.sub("", m.group(2))

        apple = by_audio.get(hpp.episode_page(doc)["audio"]) or by_num.get(num)
        if not apple and not complete and old.get("apple"):
            apple = hpp.unesc(old["apple"])
        added = ""
        if apple:
            added += pill("apple", apple, "Play on Apple Podcasts")
            counts["apple"] += 1
        if num in videos:
            added += pill("youtube", f"https://www.youtube.com/watch?v={videos[num]}",
                          "Watch on YouTube")
            counts["youtube"] += 1

        # after the first pill ("Play on Spotify"), before Discord and the rest
        cut = rest.find("</a>") + 4 if "</a>" in rest else 0
        row = rest[:cut] + added + rest[cut:]
        new = doc[:m.start(2)] + row + doc[m.end(2):]
        if new != doc:
            open(path, "w", encoding="utf-8").write(new)
    print(f"episode links: Apple Podcasts on {counts['apple']} pages, "
          f"YouTube video on {counts['youtube']}")


if __name__ == "__main__":
    main()
