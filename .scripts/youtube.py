#!/usr/bin/env python3
"""List the show's YouTube videos and find episode thumbnails the site lacks.

    python3 .scripts/youtube.py            # list videos by episode, report missing thumbnails
    python3 .scripts/youtube.py --apply    # also save them to images/episodes/<slug>.jpg

The channel listing is the page's ytInitialData plus `youtubei/v1/browse`
continuations (AGENTS.md "Images"). A thumbnail is only used when its bytes are
unique across the channel: audio-only episodes reuse the logo, and video only
started at CUTOFF. Saving a thumbnail deletes that episode's audio-only share
card so `make_cards.py` redraws it with the photo.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hpp  # noqa: E402

CHANNEL = "UCJXWVm6uAKh_Nd1mqkKLW5A"
CUTOFF = 109
UA = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en"}


def _get(url: str, data: bytes | None = None, headers: dict | None = None) -> bytes:
    """YouTube answers bursts of requests with an occasional HTTP 403/429, so
    retry those (and 5xx) with backoff; a 404 is final."""
    import time
    for delay in (5, 15, 30, None):
        req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if delay is None or not (e.code in (403, 429) or e.code >= 500):
                raise
            time.sleep(delay)
    raise AssertionError("unreachable")


def _walk(o, vids: dict, tokens: list) -> None:
    if isinstance(o, dict):
        lv = o.get("lockupViewModel")
        if isinstance(lv, dict) and lv.get("contentId"):
            title = (lv.get("metadata", {}).get("lockupMetadataViewModel", {})
                     .get("title", {}).get("content", ""))
            vids.setdefault(lv["contentId"], title)
        # Follow only the grid's own "load more" token. The sort chips
        # (Latest/Popular/Oldest) carry continuation tokens too, and following
        # those re-lists the channel and ends in HTTP 403.
        cir = o.get("continuationItemRenderer")
        if isinstance(cir, dict):
            tok = (cir.get("continuationEndpoint", {}).get("continuationCommand", {})
                   .get("token"))
            if tok:
                tokens.append(tok)
        for v in o.values():
            _walk(v, vids, tokens)
    elif isinstance(o, list):
        for v in o:
            _walk(v, vids, tokens)


def videos() -> dict[str, str]:
    """videoId -> title, for every video on the channel (newest first)."""
    page = _get(f"https://www.youtube.com/channel/{CHANNEL}/videos").decode("utf-8", "replace")
    key = re.search(r'"INNERTUBE_API_KEY":"([^"]+)"', page).group(1)
    ver = re.search(r'"clientVersion":"([^"]+)"', page).group(1)
    data = json.loads(re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S).group(1))
    vids: dict[str, str] = {}
    tokens: list[str] = []
    _walk(data, vids, tokens)
    seen = set()
    while tokens:
        tok = tokens.pop()
        if tok in seen:
            continue
        seen.add(tok)
        body = json.dumps({"context": {"client": {"clientName": "WEB", "clientVersion": ver}},
                           "continuation": tok}).encode()
        more = json.loads(_get(f"https://www.youtube.com/youtubei/v1/browse?key={key}", body,
                               {"Content-Type": "application/json"}))
        _walk(more, vids, tokens)
    return vids


def by_episode(vids: dict[str, str]) -> dict[int, list[str]]:
    """Episode number -> its video ids, matched by the `#NNN` in the title."""
    out: dict[int, list[str]] = {}
    for vid, title in vids.items():
        m = re.match(r"\s*#(\d+)\b", title)
        if m:
            out.setdefault(int(m.group(1)), []).append(vid)
    return out


def newest_episode(vids: dict[str, str] | None = None) -> int:
    eps = by_episode(videos() if vids is None else vids)
    return max(eps) if eps else 0


def thumbnail(vid: str) -> bytes | None:
    """maxresdefault, else mqdefault (sd/hqdefault return a gray placeholder)."""
    for name in ("maxresdefault", "mqdefault"):
        try:
            return _get(f"https://i.ytimg.com/vi/{vid}/{name}.jpg")
        except urllib.error.HTTPError:
            continue
    return None


def missing_thumbnails(vids: dict[str, str]) -> dict[int, tuple[str, bytes]]:
    """Episode number -> (video id, image) for episodes >= CUTOFF that have a
    byte-unique thumbnail on YouTube but no images/episodes/<slug>.jpg."""
    thumbs = {vid: thumbnail(vid) for vid in vids}
    counts: dict[str, int] = {}
    for b in thumbs.values():
        if b:
            h = hashlib.md5(b).hexdigest()
            counts[h] = counts.get(h, 0) + 1
    slugs = hpp.episode_slugs()
    out: dict[int, tuple[str, bytes]] = {}
    for num, ids in sorted(by_episode(vids).items()):
        if num < CUTOFF or num not in slugs:
            continue
        if os.path.exists(f"images/episodes/{slugs[num]}.jpg"):
            continue
        for vid in ids:
            b = thumbs.get(vid)
            if b and counts[hashlib.md5(b).hexdigest()] == 1:
                out[num] = (vid, b)
                break
    return out


def main() -> None:
    hpp.require_root()
    vids = videos()
    eps = by_episode(vids)
    print(f"videos: {len(vids)}  episodes with video: {len(eps)}  newest: #{max(eps) if eps else '-'}")
    slugs = hpp.episode_slugs()
    no_page = sorted(n for n in eps if n not in slugs)
    if no_page:
        print("on YouTube but no episode page yet: " + ", ".join(f"#{n}" for n in no_page))
    missing = missing_thumbnails(vids)
    if not missing:
        print("thumbnails: none missing")
        return
    for num, (vid, b) in missing.items():
        slug = slugs[num]
        if "--apply" in sys.argv[1:]:
            with open(f"images/episodes/{slug}.jpg", "wb") as f:
                f.write(b)
            card = f"images/og/episodes/{slug}.jpg"
            if os.path.exists(card):
                os.remove(card)
            print(f"saved images/episodes/{slug}.jpg from {vid} (share card will redraw)")
        else:
            print(f"missing thumbnail: #{num} {slug} <- {vid} (run with --apply)")


if __name__ == "__main__":
    main()
