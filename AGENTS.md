# Regenerating this site (for AI runs)

Generate/update the website from @SPEC.md, following @DESIGN.md. This repo holds
**only static assets** served from the root — no build system, no committed
scripts (per SPEC "Architecture"). Regeneration is done by an AI (you): fetch the
sources below and (re)write the HTML/CSS/images. Keep any generator you write
**outside** the repo.

## Output layout (all at repo root; links are RELATIVE so IntelliJ preview at
`/happypathprogramming/…` and prod at `/` both work)
- `index.html` (hero + recent episodes + hosts section `#hosts`), `styles.css`
- `episodes/index.html` + `episodes/<slug>.html` (one per episode, unique URL)
- `guests/index.html` + `guests/<slug>.html`
- `topics/index.html` (tag cloud) + `topics/<slug>.html` (episodes per topic)
- `images/`, `sitemap.xml`, `robots.txt`, `CNAME`
- No `hosts.html` (hosts live on index). Nav = Episodes / Guests / Topics (the logo links home).

## Data sources
- **Episodes (canonical):** RSS `https://anchor.fm/s/2ed56aa0/podcast/rss`
  (120+ items). Per item: title (`#NNN …`), description(HTML), `<link>` (Spotify),
  pubDate, `enclosure` mp3, `itunes:duration`, `itunes:episode`. Discord link +
  resource links are parsed out of the description.
- **Guests:** derived from the `"… with <Name>"` pattern in episode titles
  (use the LAST " with "; split on `&`/`,`/` and `; a name inside parens like
  "Kyo (Flavio Brasil)" → the person). Reject non-names (digits/`;`/stopwords).
  Manual overrides for titles without "with": #117 Bill Venners & Dianne Marsh,
  #105 Nathan Sobo.
- **Host bios:** mindviewllc.com/about (Bruce), jamesward.com (James).
- **Social accounts (fixed, keep on every regen):**
  - Show Bluesky: `https://bsky.app/profile/happypathprogramming.com` → footer
    "Community" column. The show has NO X/Twitter account — don't invent one.
  - Bruce: `https://bsky.app/profile/bruceeckel.bsky.social`, `https://x.com/BruceEckel`
  - James: `https://bsky.app/profile/jamesward.com`, `https://x.com/JamesWard`
  - Both hosts' handles go on their home-page host cards as chips.
- **Topics:** tag each episode by matching a curated keyword→topic map against
  its title+description; each topic gets a page listing its episodes.

## Images (store in `images/`)
- **Logo:** `images/hpp.jpg` (also the fallback everywhere).
- **Hosts:** real photos `images/bruce-eckel.jpg`, `images/james-ward.jpg`
  (mindviewllc.com/publicity/BruceEckel.jpg; jamesward.com about-page photo).
- **Guests → `images/guests/<slug>.jpg`:** only from the guest's OWN
  name-linked profile in the description (anchor text == guest name — do NOT grab
  resource/repo links or you get wrong faces/org logos). Resolve via
  `github.com/<user>.png` or `unavatar.io/{twitter|linkedin}/<user>` or
  `unavatar.io/<domain>`. No photo → deterministic gradient initials avatar.
- **Episodes → `images/episodes/<slug>.jpg`:** from the YouTube channel
  (`UCJXWVm6uAKh_Nd1mqkKLW5A`). Spotify has NO per-episode art (show cover only).
  YouTube uses `lockupViewModel` (contentId+title); paginate via
  `youtubei/v1/browse` with the continuation token + `INNERTUBE_API_KEY`. Match
  video→episode by `#NNN`. Use `maxresdefault`/`mqdefault` (NOT sd/hqdefault —
  those return a gray placeholder). **Only keep an image that is byte-unique**
  across the channel: audio-only episodes reuse the logo as their thumbnail, and
  video only started ~episode #109, so early "unique" logo-letterbox variants
  must be dropped (cutoff `#109`). Result: ~12 real thumbnails; the rest use the
  logo.

## Verify before finishing
- Every page parses; **0 absolute-internal links** (must be relative); 0 broken
  links; images referenced exist. Serve the parent dir and confirm assets 200
  under `/happypathprogramming/…`.
