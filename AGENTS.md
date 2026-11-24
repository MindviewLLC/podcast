# Happy Path Programming site

Follow the `zen-of-websites` and `zen-of-projects` Skills (in https://github.com/jamesward/skills); the maintenance
routine is `.factory/MAINTENANCE.md` and runs weekly. Publishing: every push to `main` is deployed to
https://happypathprogramming.com (`www.` redirects to it, so every absolute URL the
tools write uses the bare domain; `SITE` in `.scripts/hpp.py`) by the `staticSite` entry for `MindviewLLC/podcast` in
`jamesward/domains` (`domains.pkl`), which syncs the repo to S3 except the globs in `.slugignore`. CI (`.github/workflows/ci.yml`) compiles `.scripts/` with Python 3.11, the routine environment's
`python3`, and runs `.scripts/verify.py`.

# Regenerating this site (for AI runs)

Generate/update the website from @SPEC.md, following @DESIGN.md. The repo root
holds **only static assets** served from `/` — no build system (per SPEC
"Architecture"). Regeneration is done by an AI (you): fetch the sources below and
(re)write the HTML/CSS/images.

## Run the tools — don't redo their work by hand
`.scripts/` holds the maintenance tooling (see @.scripts/README.md). After you
have (re)written the pages, run:

```sh
python3 .scripts/update.py --refresh
```

which first fetches the feed once and checks it isn't a stale copy (`feed.py`:
it fails when the feed has an episode without a page, or when YouTube has an
episode newer than the feed — see "Episodes (canonical)"), then adds each
episode's Apple Podcasts, YouTube video and Discord pills, draws share cards for anything new, rewrites every page's
OpenGraph/Twitter/JSON-LD and share row, regenerates `sitemap.xml` and `feed.xml`, verifies the
result, and requests every outbound link to see that it still resolves.
**You are responsible for the HTML pages; the tools own everything
in "Social sharing" below, the `pill--apple`/`pill--youtube`/`pill--discord` episode pills, the
episode pages' "Transcript" panel and `transcripts/`, plus `sitemap.xml`, `feed.xml`,
`llms.txt` and `llms-full.txt`.** Don't hand-write those — write
the pages, then run the pass. If the tools need to change, change them there
(they are committed, and shared modules `brand.py`/`hpp.py` keep them in
agreement); keep genuinely one-off scratch code outside the repo, and never put
secrets in `.scripts/`. `.slugignore` keeps it off the site, but the repo is public.

## Output layout (all at repo root; links are RELATIVE so IntelliJ preview at
`/happypathprogramming/…` and prod at `/` both work)
- `index.html` (hero + recent episodes + hosts section `#hosts`), `styles.css`
- `episodes/index.html` + `episodes/<slug>.html` (one per episode, unique URL)
- `guests/index.html` + `guests/<slug>.html`
- `topics/index.html` (tag cloud) + `topics/<slug>.html` (episodes per topic)
- `images/`, `sitemap.xml` (written by `.scripts/make_sitemap.py`), `robots.txt`, `CNAME`
- `robots.txt` allows everything and carries the owners' Content Signals choice
  (contentsignals.org): `Content-Signal: search=yes, ai-input=yes, ai-train=yes`.
  Keep it on every regen; changing it is the owners' decision.
- `llms.txt` and `llms-full.txt` (llmstxt.org; written by `.scripts/make_llms.py` from the
  pages). `llms.txt` is the index: the show, the hosts, and a link with a one-line note
  for every episode, guest and topic page. `llms-full.txt` is the full text: each
  episode's facts, listen links, description and resources in Markdown. Both use
  absolute URLs, since they are read on their own.
- `transcripts/<slug>.srt` — each episode's Spotify transcript (written by
  `.scripts/transcripts.py`; see "Transcripts" below).
- `feed.xml` — the site's own RSS feed (episodes only; written by `.scripts/make_feed.py`).
  Each item links to its page here (`<link>` and `guid`), carries the page's description and
  resources, the episode's share card and the audio enclosure. **Every RSS link on the site
  points at it, never at the anchor.fm feed:** the head `alternate` link and JSON-LD `webFeed`
  use `https://happypathprogramming.com/feed.xml`; the hero, "Listen anywhere" and footer
  RSS links use the relative `feed.xml` / `../feed.xml` (no `target="_blank"`).
- No `hosts.html` (hosts live on index). Nav = Episodes / Guests / Topics (the logo links home).
- `.scripts/`, `.claude/`, `.factory/` and `.github/` are tooling and config; `.slugignore` keeps
  them (and the Markdown docs) off the site. Add any new non-site file to `.slugignore`.

## Data sources
- **Episodes (canonical):** RSS `https://anchor.fm/s/2ed56aa0/podcast/rss` (read by the
  tools only; the site links to its own `feed.xml` instead)
  (120+ items). Per item: title (`#NNN …`), description(HTML), `<link>` (Spotify),
  pubDate, `enclosure` mp3, `itunes:duration`, `itunes:episode`. Discord link +
  resource links are parsed out of the description.
  **The descriptions run text into URLs** — `"…to Python.https://github.com/suned/
  statelessPrior attempt at…"` is one URL followed by the words "Prior attempt
  at", not a repo called `statelessPrior`. Same for a URL that swallows the next
  bullet's `-`, a stray `\`, a word-joiner (U+2060) or the word `Discuss`. When a
  URL abuts text, split it where the real URL ends and put the leftover words
  back into the prose; `.scripts/check_links.py` catches what you miss.
  **A description's own "Resources" list goes in the page's Resources list, not
  in the "About this episode" prose**: each `- Label - URL` (or `<li><a>`) item
  becomes a `.res-list` link with the label as its text, the prose keeps only
  the sentences before "Resources", and a sentence that runs into the next one
  (`…explains itself.Aver is…`) gets its space back. Write the head's
  `<meta name="description">` from that same prose (VOICE.md says how).
  Every card for the episode (`.ep-card-summary` on the home, episodes, guest
  and topic pages) carries that meta description exactly, never the full prose
  or a character cut; the CSS clamps it to 3 lines. `verify.py` fails on a card
  whose summary differs from its page's meta description.
  **The feed's CDN can serve a copy up to a week old** (`s-maxage=605009`; it
  ignores cache-busting query strings and `Cache-Control: no-cache`), so a
  single fetch can be missing the newest episode. `hpp.fetch_feed` retries and
  never replaces a newer cached copy with an older one. A YouTube video numbered
  past the feed's newest episode means the feed copy is stale, not that the
  episode is "for next run": `feed.py` fails on it until a fresh copy arrives.
- **Guests:** derived from the `"… with <Name>"` pattern in episode titles
  (use the LAST " with "; split on `&`/`,`/` and `; a name inside parens like
  "Kyo (Flavio Brasil)" → the person). Reject non-names (digits/`;`/stopwords).
  Manual overrides for titles without "with": #117 Bill Venners & Dianne Marsh,
  #105 Nathan Sobo, #122 Barry Warsaw (the title is just the name, so the card
  title is the name too).
- **Host bios:** mindviewllc.com/about (Bruce), jamesward.com (James).
- **Social accounts (fixed, keep on every regen):**
  - Show Bluesky: `https://bsky.app/profile/happypathprogramming.com` and show
    X/Twitter: `https://x.com/happypathprog` → footer "Community" column.
    `@happypathprog` is also the `twitter:site` meta tag on every page.
  - Bruce: `https://bsky.app/profile/bruceeckel.bsky.social`, `https://x.com/BruceEckel`
  - James: `https://bsky.app/profile/jamesward.com`, `https://x.com/JamesWard`
  - Both hosts' handles go on their home-page host cards as chips.
- **Topics:** tag each episode by matching the keyword→topic map in
  "Topic keywords" below against its title + "About this episode" prose; each
  topic gets a page listing its episodes.

## Topic keywords
An episode gets every topic with at least one keyword in its title or "About"
prose (case-insensitive, whole words or phrases: `ai` matches "AI" and
"AI-native", not "said"). Then use judgement on the result. Drop a topic that
only a passing mention matched, and add one the conversation is clearly about
even if no keyword matched (say which in the run report). When that happens,
add the missing keyword to the row so the next run matches it. A new topic gets
a row here and a `topics/<slug>.html` page. Don't retag published episodes to
fit the map: their topics were chosen before it existed (it reproduces 191 of
their 222 tags).

| Topic (`topics/<slug>.html`) | Keywords |
|---|---|
| `ai-and-llms` | ai, llm, llms, agent, agents, agentic, mcp, machine learning, chatgpt, copilot, claude, gpt, genai, generative ai, prompt |
| `architecture-and-design` | architecture, architect, design pattern, design patterns, microservices, modulith, moduliths, domain-driven, ddd, event sourcing, system design, object-oriented, oop, polymorphism, scalability, separation of concerns |
| `build-tools` | build tool, build tools, sbt, maven, gradle, bazel, mill, build system, nix, dhall, pkl, configuration language, package manager, packaging |
| `cloud-and-serverless` | cloud, serverless, aws, lambda, kubernetes, docker, containers, heroku, gcp, azure, infrastructure |
| `concurrency` | concurrency, concurrent, parallelism, threads, virtual threads, loom, async, structured concurrency, actors |
| `databases-and-data` | database, databases, sql, postgres, sqlite, nosql, datomic, crdt, crdts, kafka, streaming, local-first, data engineering |
| `developer-productivity` | productivity, developer experience, dx, ide, intellij, code editor, flow state, developer joy |
| `effect-oriented` | effect, effects, effect oriented, effect system, algebraic effects, zio, kyo, cats effect |
| `functional-programming` | functional programming, functional, fp, monad, monads, haskell, pure functions, immutability, category theory, clojure, elm, ocaml, f#, nix |
| `java-and-jvm` | java, jvm, jdk, openjdk, graalvm, spring, quarkus, clojure, groovy, gatherers, virtual threads, loom |
| `kotlin` | kotlin, kotlinconf, ktor, jetbrains |
| `language-design` | language design, programming language, new language, compiler, compilers, syntax, significant indentation, ai-native |
| `process-and-careers` | career, careers, hiring, interview, management, manager, agile, culture, company culture, community, communities, compassionate, mentoring, organization, software factories |
| `python` | python, pythonic, pypi, django, mojo |
| `rust` | rust, cargo, borrow checker |
| `scala` | scala, scala 3, dotty, akka |
| `testing` | testing, tdd, test-driven, property-based, unit tests, testcontainers |
| `types` | types, type system, type systems, static typing, type checking, type checker, type safety, type inference, dependent types, polymorphism, adts, algebraic data types |
| `typescript` | typescript, javascript, deno, bun |
| `webassembly` | webassembly, wasm, wasi |

## Writing descriptions and resource links
Follow @VOICE.md whenever you write words that describe an episode: drafting a
new episode's show notes (description + resources) for the hosts, writing a
page's `<meta name="description">`, or labeling a resource link that the feed
gave as a bare URL or a vague label. Don't rewrite the hosts' published
description on the site. Copy it and make only the mechanical fixes under
"Episodes (canonical)" above.

## Images (store in `images/`)
Every `<img>` carries `width`/`height` so the layout doesn't shift as it loads;
`verify.py` fails on an unsized one. Where CSS sets the box (`aspect-ratio` or a
fixed size plus `object-fit`, as on cards and avatars) use the displayed size,
e.g. `480`×`270` or `84`×`84`. Where CSS sets only the width (`height: auto`,
as on `.ep-hero-art`) use the file's pixel size (`1280`×`720` for a YouTube
thumbnail, `400`×`400` for the logo) so the reserved box has the image's shape.
Images below the fold get `loading="lazy"`; the episode hero art
(`.ep-hero-art img`) and the home page's `.latest-art` are above the fold, so
they must not (`verify.py` fails if they are).
- **Logo:** `images/hpp.jpg` (also the fallback everywhere).
- **Hosts:** real photos `images/bruce-eckel.jpg`, `images/james-ward.jpg`
  (mindviewllc.com/publicity/BruceEckel.jpg; jamesward.com about-page photo).
- **Guests → `images/guests/<slug>.jpg`:** only from the guest's OWN
  name-linked profile in the description (anchor text == guest name — do NOT grab
  resource/repo links or you get wrong faces/org logos). Resolve via
  `github.com/<user>.png` or `unavatar.io/{twitter|linkedin}/<user>` or
  `unavatar.io/<domain>`. No photo → deterministic gradient initials avatar.
  Those sources often return PNG: convert to a real JPEG before saving as
  `.jpg`, flattening any transparency onto the `.avatar` gradient (`#0f9d58` →
  `#34d399`, 135°) so it looks the same as it would on the page. `verify.py`
  fails on a `.jpg` that isn't a JPEG.
- **Share cards (`images/og/…`) — WRITE ONCE, NEVER RE-RENDER.** Rendered by
  `.scripts/make_cards.py`; don't draw these by hand. Every episode and guest
  page has its own 1200×630 OpenGraph card so a shared link shows that page's own
  title/name, not generic show branding:
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
    duration, guest name — so a card never goes stale, and `make_cards.py` draws
    only files that are MISSING. Keep counts and other changing values OFF the
    images; they live in `twitter:label/data`, which is rewritten on every regen
    for free. Never run `make_cards.py --force` on a routine update — it would
    rewrite ~11MB of unchanged binaries. The one card worth deleting so it
    redraws is an episode whose YouTube thumbnail appeared after its audio-only
    card was made.
- **Episodes → `images/episodes/<slug>.jpg`:** from the YouTube channel
  (`UCJXWVm6uAKh_Nd1mqkKLW5A`). Spotify has NO per-episode art (show cover only).
  `python3 .scripts/youtube.py` lists the channel and reports (or with
  `--apply` saves) every missing real-video thumbnail; then update that
  episode's page and cards to use it. How it works: YouTube uses
  `lockupViewModel` (contentId+title); paginate via
  `youtubei/v1/browse` with the grid's `continuationItemRenderer` token +
  `INNERTUBE_API_KEY` (not the sort chips' tokens, which end in HTTP 403). Match
  video→episode by `#NNN`. Use `maxresdefault`/`mqdefault` (NOT sd/hqdefault —
  those return a gray placeholder). **Only use real videos.** The channel also
  holds the podcast audio that YouTube re-publishes from the feed, often under
  the same title as the real video, with the logo as a still; its thumbnail is
  the logo, sometimes with unique bytes, so `youtube.real_videos` compares each
  thumbnail with `images/hpp.jpg` instead of comparing bytes. Video only started
  at episode #109 (cutoff `#109`). Result: ~14 real thumbnails; the rest use the
  logo.
  **Small copy:** `--apply` also writes `images/episodes/<slug>-sm.jpg`
  (640×360, ~40 KB instead of ~130 KB) for every thumbnail that lacks one
  (write-once, like the share cards). The places that show a thumbnail at card
  size use it: every `.ep-card-art` (`width="480" height="270"`) and the home
  page's `.latest-art` (`width="640" height="360"`; its box is 100% wide and
  128px tall, so the attributes give the file's shape). The episode page's
  `.ep-hero-art` and the share cards use the full-size file. `verify.py` fails
  on a missing `-sm.jpg` or a card that uses the full one.
- **Per-episode listen/watch links (hero `.pills`, written by
  `.scripts/episode_links.py`):** you write the hero row with "Play on Spotify"
  (the RSS `<link>`). The tool then adds "Play on Apple Podcasts" (the
  episode's own Apple page, from the iTunes lookup API for show id
  `1531666706`) and "Watch on YouTube" (the real video from
  `youtube.real_videos`, never the podcast re-publish; no pill when there is no
  real video) after the Spotify pill, and "Discuss on Discord" at the end when
  the feed description has a `discord.gg/…` invite (the last one: an earlier
  link can be a project's own server, as on #115). Don't hand-write the
  `pill--apple`/`pill--youtube`/`pill--discord` pills; the tool replaces them on
  every run.

## Transcripts (episode pages — written by `.scripts/transcripts.py`)
Spotify auto-generates transcripts and, with Spotify for Creators' Settings →
Transcripts → "Distribute transcripts across other platforms via RSS" on,
publishes them in the feed as `<podcast:transcript type="application/x-subrip">`
(not every episode has one; Spotify decides). The tool saves each as
`transcripts/<slug>.srt` (rewritten only when Spotify's copy changes, never
deleted if the feed drops it) and writes a "Transcript" panel at the end of the
page's `.ep-main`, between `<!-- transcript -->` and `<!-- /transcript -->`:
a note that it is machine-generated, a "Download (.srt)" link, and the cues
merged into timestamped paragraphs (`<p id="t-<seconds>">` with an
`<a class="ts">` that seeks the page's player) inside a closed `<details>`.
The page text fixes "Bruce Eckle" → "Bruce Eckel" (`CORRECTIONS`); the `.srt`
stays as Spotify published it. `make_feed.py` points each `feed.xml` item's
`<podcast:transcript>` at the site's own copy, and `make_llms.py` lists it as
`- Transcript:` in `llms-full.txt`. Don't hand-edit the panel.

## Social sharing (every page — written by `.scripts/social.py`)
This whole section is what `social.py` emits. It is idempotent and derives
everything from the pages plus the feed, so just run it rather than hand-writing
any of this; the spec below is here so you can change the tool deliberately.
Head, in this order, ending with `theme-color` (the tool keys off that):
`<link rel="canonical">`, `<link rel="alternate" type="application/rss+xml">`
to the site's `feed.xml`, then `og:type` / `og:site_name` / `og:locale` / `og:title` /
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
  `PodcastSeries` (`webFeed` = the site's `feed.xml`, hosts as `author`, `sameAs` the show's socials) +
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
- `python3 .scripts/verify.py` must pass (it is a step of `update.py`).
  It checks that every page parses, that every `<img>` has `width`/`height`
  (and the hero art isn't lazy-loaded), that every `.jpg` is a real JPEG,
  that there are **0 absolute-internal links**
  (must be relative — the absolute prod URLs in `canonical`/`alternate`/`og:`/JSON-LD/share
  links are intentional), 0 broken internal links, that referenced images exist,
  and that every page has a valid JSON-LD block, a share row, the full
  `og:`/`twitter:` set, and an `og:image` that is its own card at 1200×630.
  It also checks that every `transcripts/*.srt` is shown on its episode page and
  linked from `feed.xml`, that `feed.xml` parses and has exactly one item per episode page,
  and that `llms.txt` links every episode, guest and topic page and `llms-full.txt`
  has a section for every episode.
- `python3 .scripts/check_links.py` must pass — that is the *outbound* half, and
  it is the last step of `update.py`. It requests every external link on the
  site and fails on
  a link that is definitively wrong. Results are cached for 30 days in
  `.scripts/.cache/` (gitignored), so a local re-run only checks new links; a
  fresh cloud session starts with no cache and checks every link (~80 s).
  Whenever you touch a page's links, run
  `python3 .scripts/check_links.py --changed` before you finish; a `Stop` hook in
  `.claude/settings.json` runs exactly that and will hand you the report if you
  forget. Fix what it reports: nearly always the URL ran into the text beside it
  in the RSS description. If the target is genuinely gone from the web, drop the
  `<a>` and keep its text as
  `<span class="res-dead">…</span> <span class="res-note">(link no longer
  online)</span>` rather than shipping a 404 or deleting the reference.
  Links it calls **unverified** (LinkedIn, Medium, X and friends refuse robots)
  are not failures — leave them alone.
- Then serve the parent dir and confirm assets 200 under
  `/happypathprogramming/…` — that path prefix is the one thing the checker
  can't see.
