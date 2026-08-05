# `.scripts/` — site maintenance tools

Small Python tools for the repetitive, error-prone parts of updating the site:
rendering share cards, keeping every page's social metadata in agreement, and
checking the result. **They are not a build step.** Nothing serves them, nothing
runs them automatically, and the site in the repo root is complete and
publishable without them ever running. The HTML/CSS is still written by the AI
from [`../SPEC.md`](../SPEC.md), following [`../AGENTS.md`](../AGENTS.md).

This directory lives in the repo that *is* the website. GitHub Pages does not
publish dot-directories, so `.scripts/` should not appear at
`happypathprogramming.com/.scripts/` — but don't lean on that. **Never put
secrets here**: no tokens, no keys, no private URLs. Everything these tools read
is already public (the podcast RSS feed and the site's own pages), and it should
stay that way.

## Setup

Python 3.9+ and Pillow:

```sh
pip install -r .scripts/requirements.txt
```

Card rendering needs the Liberation or DejaVu font families (Debian/Ubuntu:
`apt-get install fonts-liberation fonts-dejavu-core`). On macOS it falls back to
Arial/Menlo. Cards are write-once, so a different machine's fonts only affect
cards drawn from then on.

## Usage

Run from anywhere — each tool `chdir`s to the repo root itself.

```sh
python3 .scripts/update.py              # the whole pass, in order, then verify
python3 .scripts/update.py --refresh    # same, but re-fetch the RSS feed first
```

That is the normal path after new episode pages have been generated. The
individual tools, in the order `update.py` runs them:

| Tool | What it does | Safe to re-run? |
| --- | --- | --- |
| `make_cards.py` | Draws `images/og/episodes/<slug>.jpg` and `images/og/guests/<slug>.jpg` — the per-page 1200×630 OpenGraph cards. | Yes. Draws only files that are **missing**. |
| `social.py` | Rewrites each page's `canonical`…`theme-color` head block, its JSON-LD, its share row and the inline share script. | Yes, idempotent — it replaces its own output. |
| `make_sitemap.py` | Rebuilds `sitemap.xml` from the pages on disk, with `<lastmod>` from the feed. | Yes. |
| `verify.py` | Parses every page and checks metadata, JSON-LD, links, assets and card sizes. Exits non-zero on any problem. | Yes, read-only. |

Two more, run by hand only:

- `make_og_default.py --force` — redraws `images/og-default.jpg`, the branded
  fallback card for the home, list and topic pages. Only needed if the brand
  changes; it refuses without `--force`.
- `make_cards.py --force` — redraws **every** card. Rarely what you want; see
  below.

## The one rule worth remembering

**Share cards are write-once.** Everything drawn on a card is an immutable fact
about that episode or guest — number, title, guests, air date, duration, name,
photo — so a card can never go stale, and `make_cards.py` skips any file that
already exists. A daily update therefore adds one card for the new episode plus
one per new guest, and rewrites no existing binary.

Anything that *can* change is deliberately kept **off** the images. A guest's
appearance count, for instance, lives in that page's `twitter:label1/data1`,
which `social.py` rewrites on every run for free. Keep it that way: putting a
changing value on a card would force re-rendering and defeat the whole scheme.

The one routine exception is an episode whose YouTube thumbnail only appears
after its audio-only card was drawn. Delete that single file and re-run
`make_cards.py`.

## Layout

```
brand.py             palette, fonts, backdrop, masks, text fitting — shared by
                     the card renderers so every card looks like one set
hpp.py               site constants, the RSS feed (cached in .scripts/.cache/),
                     and readers that pull fields back out of the generated
                     pages, so no two tools disagree about a page's contents
make_og_default.py   the branded fallback card
make_cards.py        per-episode and per-guest cards
social.py            OpenGraph/Twitter/JSON-LD/share rows
make_sitemap.py      sitemap.xml
verify.py            pre-publish checks
update.py            runs the above in order
```

The feed is cached at `.scripts/.cache/podcast.rss` (gitignored). Pass
`--refresh` to any tool that reads it to fetch a fresh copy.

## Adding a tool

Put shared drawing in `brand.py` and shared facts or page-reading in `hpp.py`
rather than re-deriving them — the tools agreeing with each other is the whole
point of the split. Read the site's own HTML for what the site contains, and
the RSS feed for episode facts. Add the tool to `STEPS` in `update.py` if it
belongs in the routine pass, and give it a `--force`-style guard if it would
otherwise rewrite stable binaries.
