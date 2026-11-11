#!/usr/bin/env python3
"""List the show's YouTube videos and find episode thumbnails the site lacks.

    python3 .scripts/youtube.py            # list videos by episode, report missing thumbnails
    python3 .scripts/youtube.py --apply    # also save them to images/episodes/<slug>.jpg

The channel listing is the page's ytInitialData plus `youtubei/v1/browse`
continuations (AGENTS.md "Images"). The channel holds two kinds of upload: real
videos, and the podcast's audio re-published from the RSS feed with the show
logo as a still image. `real_videos` tells them apart by comparing each
thumbnail with images/hpp.jpg (the logo uploads score under 5, real videos over
60), so a re-publish never supplies a thumbnail or a "Watch on YouTube" link.
Video only started at CUTOFF. Saving a thumbnail deletes that episode's
audio-only share card so `make_cards.py` redraws it with the photo.
"""
from __future__ import annotations

import io
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


LOGO_DIFF = 30  # mean grey-level difference below which a thumbnail is the logo


def is_logo(image: bytes) -> bool:
    """True when a thumbnail is the show logo (letterboxed or not), i.e. the
    upload is the podcast audio re-published from the feed, not a real video."""
    from PIL import Image, ImageChops, ImageStat
    logo = Image.open(os.path.join(hpp.ROOT, "images", "hpp.jpg")).convert("L").resize((64, 64))
    im = Image.open(io.BytesIO(image)).convert("L")
    w, h = im.size
    side = min(w, h)
    left, top = (w - side) // 2, (h - side) // 2
    square = im.crop((left, top, left + side, top + side)).resize((64, 64))
    return ImageStat.Stat(ImageChops.difference(square, logo)).mean[0] < LOGO_DIFF


def real_videos(vids: dict[str, str]) -> dict[int, tuple[str, bytes]]:
    """Episode number -> (video id, thumbnail) of its real video, for every
    episode that has one; podcast re-publishes (logo thumbnails) are skipped."""
    out: dict[int, tuple[str, bytes]] = {}
    for num, ids in sorted(by_episode(vids).items()):
        for vid in ids:
            b = thumbnail(vid)
            if b and not is_logo(b):
                out[num] = (vid, b)
                break
    return out


def missing_thumbnails(real: dict[int, tuple[str, bytes]]) -> dict[int, tuple[str, bytes]]:
    """The entries of `real_videos` for episodes >= CUTOFF that have a page but
    no images/episodes/<slug>.jpg yet."""
    slugs = hpp.episode_slugs()
    return {num: v for num, v in real.items()
            if num >= CUTOFF and num in slugs
            and not os.path.exists(f"images/episodes/{slugs[num]}.jpg")}


def main() -> None:
    hpp.require_root()
    vids = videos()
    eps = by_episode(vids)
    print(f"videos: {len(vids)}  episodes with video: {len(eps)}  newest: #{max(eps) if eps else '-'}")
    slugs = hpp.episode_slugs()
    no_page = sorted(n for n in eps if n not in slugs)
    if no_page:
        print("on YouTube but no episode page yet: " + ", ".join(f"#{n}" for n in no_page))
    real = real_videos(vids)
    print(f"episodes with a real video (not a podcast re-publish): {len(real)}")
    missing = missing_thumbnails(real)
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
