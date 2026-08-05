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
  - Show Bluesky: `https://bsky.app/profile/happypathprogramming.com` and show
    X/Twitter: `https://x.com/happypathprog` → footer "Community" column.
    `@happypathprog` is also the `twitter:site` meta tag on every page.
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
- **Share cards (`images/og/…`) — WRITE ONCE, NEVER RE-RENDER.** Every episode
  and guest page has its own 1200×630 OpenGraph card so a shared link shows that
  page's own title/name, not generic show branding:
  - `images/og-default.jpg` — the branded fallback (ink background + green glow,
    logo, wordmark, tagline, domain) used by the home, list and topic pages.
  - `images/og/episodes/<slug>.jpg` — `EPISODE #NNN` kicker in accent yellow,
    the short display title (the `.ep-card-title` form, guest stripped) auto-fit
    to at most 4 lines, a `with <guests>` line in mint, `date · duration` in
    mono, and the domain. Right side: the episode's YouTube thumbnail in a
    rounded panel, else the logo.
  - `images/og/guests/<slug>.jpg` — `PODCAST GUEST` kicker, the name auto-fit to
    at most 3 lines, the line "on the Happy Path Programming podcast", the
    domain, and a circular crop of the guest photo (or the same deterministic
    gradient-initials avatar the site uses when there is no photo).
  - All inputs are **immutable facts** — episode number, title, guests, air date,
    duration, guest name — so a card never goes stale. Deliberately keep counts
    and other changing values OFF the images; they live in `twitter:label/data`,
    which is rewritten on every regen for free. On a regen, render a card only
    when the file is MISSING (i.e. for a new episode or guest) and leave every
    existing file byte-for-byte alone. The one time to delete a card and let it
    re-render is when an episode's YouTube thumbnail first appears after the
    audio-only card was made.
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

## Social sharing (every page — regenerate all of this)
Head, in this order, ending with `theme-color` (rewriters key off that):
`<link rel="canonical">`, `<link rel="alternate" type="application/rss+xml">`
to the feed, then `og:type` / `og:site_name` / `og:locale` / `og:title` /
`og:description` / `og:url` / `og:image` (+ `:type` `:width` `:height` `:alt`),
then `twitter:card` / `:site` / `:creator` (`@happypathprog`) / `:title` /
`:description` / `:image` / `:image:alt`, then `author` and `theme-color`.
- **Image + card type.** Always `summary_large_image` at 1200×630: episode pages
  point at `images/og/episodes/<slug>.jpg`, guest pages at
  `images/og/guests/<slug>.jpg`, and the home/list/topic pages at
  `images/og-default.jpg`. Never point a `summary_large_image` at the square
  logo or at a raw guest photo.
- **Episode pages** additionally: `og:type=article`, `article:published_time`
  (ISO-8601 from the RSS `pubDate`), `article:section=Technology`, one
  `article:tag` per topic, one `article:author` per host, `og:audio` +
  `og:audio:type` from the RSS `enclosure` (note early episodes are `.m4a`), and
  `twitter:label1/data1` = Duration, `label2/data2` = Guest(s) (else Published).
- **Guest pages:** `og:type=profile` + `profile:first_name` / `:last_name`,
  `twitter:label1/data1` = Episodes count. **Topic/list pages:** the same
  Episodes count pair.
- **JSON-LD** — one `<script type="application/ld+json">` per page, a
  `{"@context","@graph":[…]}`, placed at the end of `<head>`: home →
  `PodcastSeries` (`webFeed`, hosts as `author`, `sameAs` the show's socials) +
  `WebSite`; episode → `PodcastEpisode` (`episodeNumber`, `datePublished`,
  `timeRequired`, `associatedMedia` AudioObject, guests as `actor`, topics as
  `keywords`, `partOfSeries`); guest → `ProfilePage` + `Person` (`performerIn`);
  topic and index pages → `CollectionPage` + `ItemList`. Every page except home
  also gets a `BreadcrumbList`.
- **On-page share row.** `.share-row` of `.share-btn`s: Bluesky
  (`bsky.app/intent/compose`), X (`x.com/intent/post…&via=happypathprog`),
  LinkedIn (`sharing/share-offsite`), Hacker News (`submitlink`), Reddit
  (`submit`), a `.js-copy` clipboard button, and a `.js-native` button that a
  small inline script before `</body>` un-hides only when `navigator.share`
  exists. Share URLs are the absolute prod URLs. Episode pages put the row in a
  `.panel.share-panel` ("Share this episode") at the end of `.ep-aside`; every
  other page gets a `<section class="wrap share-section">` with a `.share-card`
  band just before `</main>`.

## Verify before finishing
- Every page parses; **0 absolute-internal links** (must be relative — the
  absolute prod URLs in `canonical`/`og:`/JSON-LD/share links are intentional);
  0 broken links; images referenced exist. Serve the parent dir and confirm
  assets 200 under `/happypathprogramming/…`.
- Every page has a valid JSON-LD block, a share row, and the full
  `og:`/`twitter:` set; `og:image`/`twitter:image` resolve to files that exist.
