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
- **Share card:** `images/og-default.jpg` — a fixed 1200×630 branded card (ink
  background + green glow, logo, wordmark, tagline, domain). It is the
  OpenGraph/Twitter image for every page that has no real artwork of its own.
  Treat it as a **stable asset**: keep the existing file rather than
  re-rendering it, so daily regens don't churn a new binary.
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
- **Image + card type.** Real 16:9 episode thumbnail → that image (1280×720) with
  `summary_large_image`. Guest with a real photo → the square photo with
  `summary` (a face reads better small than a letterboxed banner). Everything
  else → `images/og-default.jpg` (1200×630) with `summary_large_image`. Never
  point a `summary_large_image` at the square logo.
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
