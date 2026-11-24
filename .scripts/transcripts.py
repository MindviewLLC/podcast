#!/usr/bin/env python3
"""Save each episode's Spotify transcript and show it on the episode page.

    python3 .scripts/transcripts.py

Spotify publishes its auto-generated transcripts in the podcast feed as
Podcasting 2.0 `<podcast:transcript type="application/x-subrip">` tags (Spotify
for Creators: Settings → Transcripts → "Distribute transcripts across other
platforms via RSS"). For every episode page whose feed item has one, this

- saves the SRT as `transcripts/<slug>.srt` (served by the site, and linked
  from `feed.xml` by `make_feed.py`), rewriting it only when Spotify's copy
  changed, so an edited transcript in Spotify for Creators flows through;
- writes a "Transcript" panel at the end of the page's `.ep-main` column: the
  cues merged into timestamped paragraphs inside a `<details>`, plus a small
  inline script that seeks the page's audio player when a timestamp is
  clicked (without JavaScript the timestamp is just a `#t-<seconds>` anchor).

The panel sits between `<!-- transcript -->` and `<!-- /transcript -->`, which
is how a re-run finds and replaces its own output. A transcript that can't be
fetched keeps the copy already saved, and a saved transcript is never deleted
because the feed stopped listing it, so an outage or a toggled setting never
strips transcripts from the site.
"""
from __future__ import annotations

import html
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hpp  # noqa: E402

DIR = "transcripts"
START, END = "<!-- transcript -->", "<!-- /transcript -->"
RE_OWN = re.compile(r"\n*[ \t]*" + re.escape(START) + r".*?" + re.escape(END), re.S)
RE_MAIN_END = re.compile(r'\n([ \t]*)</div>\s*<aside class="ep-aside">')
RE_TIME = re.compile(r"(\d+):(\d\d):(\d\d)[,.](\d{3})\s*-->\s*(\d+):(\d\d):(\d\d)[,.](\d{3})")
PARAGRAPH_SECONDS = 45   # start a new paragraph after this long, at a sentence end
PAUSE_SECONDS = 2.5      # ...or at a pause this long
# Spotify's speech-to-text reliably mishears the host's name; fixed on the page
# only (the saved .srt stays exactly as Spotify published it)
CORRECTIONS = {"Bruce Eckle": "Bruce Eckel"}

# Seeks the page's player from a timestamp; opens the transcript for a #t- link.
SCRIPT = """<script>
(function(){var t=document.getElementById('transcript');if(!t)return;
var a=document.querySelector('audio.player'),dt=t.querySelector('details');
function go(){if(/^#t-\\d+$/.test(location.hash)){dt.open=true;
var e=document.getElementById(location.hash.slice(1));if(e)e.scrollIntoView();}}
go();window.addEventListener('hashchange',go);
t.addEventListener('click',function(e){var l=e.target.closest('a.ts');if(!l||!a)return;
a.currentTime=+l.dataset.t;a.play().catch(function(){});});
})();
</script>"""


def cues(srt: str) -> list[tuple[float, float, str]]:
    """(start, end, text) of every SRT cue."""
    out = []
    for block in re.split(r"\r?\n\s*\r?\n", srt.strip()):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines[:2]):
            m = RE_TIME.search(line)
            if m:
                g = [int(x) for x in m.groups()]
                start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
                end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
                text = " ".join(x.strip() for x in lines[i + 1:] if x.strip())
                if text:
                    out.append((start, end, text))
                break
    return out


def paragraphs(cs: list[tuple[float, float, str]]) -> list[tuple[int, str]]:
    """Cues merged into (start second, text) paragraphs."""
    out: list[tuple[int, str]] = []
    start, words, last_end = None, [], 0.0
    for s, e, text in cs:
        if start is not None:
            sentence_end = re.search(r'[.?!]["\')]?$', words[-1])
            if (s - last_end >= PAUSE_SECONDS
                    or (s - start >= PARAGRAPH_SECONDS and sentence_end)):
                out.append((int(start), " ".join(words)))
                start, words = None, []
        if start is None:
            start = s
        text = re.sub(r"\s+", " ", text).strip()
        for wrong, right in CORRECTIONS.items():
            text = text.replace(wrong, right)
        words.append(text)
        last_end = e
    if start is not None:
        out.append((int(start), " ".join(words)))
    return out


def clock(secs: int) -> str:
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def panel(slug: str, srt: str, indent: str) -> str:
    seen: set[int] = set()
    body = []
    for t, text in paragraphs(cues(srt)):
        while t in seen:  # ids stay unique even if two paragraphs share a second
            t += 1
        seen.add(t)
        body.append(f'<p id="t-{t}"><a class="ts" href="#t-{t}" data-t="{t}">'
                    f'{clock(t)}</a> {html.escape(text, quote=False)}</p>')
    i = indent
    return "\n".join([
        f"{i}{START}",
        f'{i}<section class="panel transcript" id="transcript">',
        f"{i}  <h2>Transcript</h2>",
        f'{i}  <p class="transcript-note">Generated automatically by Spotify, so expect the '
        f"odd misheard word. Select a timestamp to play from there. "
        f'<a href="../{DIR}/{slug}.srt" download>Download (.srt)</a></p>',
        f"{i}  <details>",
        f"{i}    <summary>Read the transcript</summary>",
        f'{i}    <div class="transcript-body">',
        *(f"{i}      {p}" for p in body),
        f"{i}    </div>",
        f"{i}  </details>",
        f"{i}</section>",
        SCRIPT,
        f"{i}{END}",
    ])


def fetch(url: str) -> str | None:
    """The transcript at `url` as text, or None (with a warning) if unusable."""
    if not url.startswith("https://"):
        print(f"WARNING: skipping non-HTTPS transcript {url}", file=sys.stderr)
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8-sig")
    except Exception as e:  # noqa: BLE001 - keep the saved copy on any failure
        print(f"WARNING: couldn't fetch {url} ({e}); keeping any saved copy",
              file=sys.stderr)
        return None
    if not cues(text):
        print(f"WARNING: {url} has no SRT cues; keeping any saved copy", file=sys.stderr)
        return None
    return text.replace("\r\n", "\n")


def main() -> None:
    hpp.require_root()
    os.makedirs(DIR, exist_ok=True)
    feed = hpp.episodes_from_feed()
    saved = shown = 0
    for num, slug in sorted(hpp.episode_slugs().items()):
        path, srt_path = f"episodes/{slug}.html", f"{DIR}/{slug}.srt"
        url = feed.get(num, {}).get("transcript")
        if url and (text := fetch(url)) is not None:
            old = open(srt_path, encoding="utf-8").read() if os.path.exists(srt_path) else None
            if text != old:
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                saved += 1

        doc = open(path, encoding="utf-8").read()
        new = RE_OWN.sub("", doc)
        if os.path.exists(srt_path):
            m = RE_MAIN_END.search(new)
            if not m:
                sys.exit(f"{path}: no end of <div class=\"ep-main\"> before the aside")
            block = panel(slug, open(srt_path, encoding="utf-8").read(), m.group(1) + "  ")
            new = new[:m.start()] + "\n" + block + new[m.start():]
            shown += 1
        if new != doc:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)
    print(f"transcripts: {shown} episode pages have one ({saved} saved or updated this run)")


if __name__ == "__main__":
    main()
