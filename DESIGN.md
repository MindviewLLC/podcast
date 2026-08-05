# Design

Professional, yet fun podcast site for Happy Path Programming.

- **Logo:** use `images/hpp.jpg`.
- **Hosts:** feature on `index.html` (`#hosts` section) — no separate page.
- **Theme:** "happy path" green (`--green:#0f9d58`) with a sunny yellow accent,
  clean sans UI + monospace for episode numbers/durations, rounded cards, soft
  shadows, sticky translucent header. Light theme, responsive (single column
  ≤860px).
- **Imagery (keep it from feeling text-heavy):** host headshots; per-episode
  YouTube thumbnails where available, else the logo; guests use real photos when
  found, otherwise a colorful deterministic gradient-initials avatar.
- **Home hero:** big title, platform buttons, and 3 stat boxes that link out —
  Episodes → episodes page, Guests → guests page, Hosts → `#hosts`.
- **Platform buttons** (Spotify, Apple, Amazon, Overcast, Pocket Casts, YouTube,
  RSS, Discord): inline brand icons (Simple Icons; Amazon Music has none → a
  generic music glyph).
- **Social:** the footer "Community" column links Discord, the podcast's Bluesky
  and X (Twitter), and the t-shirt shop (brand icons, same style as the platform
  buttons). Host cards on the home page carry Bluesky + X chips alongside their
  other links.
- **Episodes:** unique shareable URL each, cover/thumbnail hero, audio player,
  "Play on Spotify", per-episode Discord link, resources list, guest chips.
- **Topics:** episodes are tagged with topics (derived from title/description via
  a curated keyword map). Topic chips show on episode cards and episode pages; a
  Topics page (`topics/index.html`) is a tag cloud with counts, and each topic
  has its own page (`topics/<slug>.html`) listing its episodes. Nav =
  Episodes / Guests / Topics (the logo links home).
- **Social sharing:** every page carries a full OpenGraph/Twitter-card head
  (canonical + RSS `alternate`, `og:*`, `twitter:*`, JSON-LD) and an on-page
  share row — Bluesky, X, LinkedIn, Hacker News, Reddit, "Copy link", plus a
  native `navigator.share` button that only appears where supported. The share
  row is a `.share-card` band above the footer on every page except episode
  pages, where it is a "Share this episode" panel in the sidebar. Every episode
  and guest page has its own 1200×630 share card under `images/og/` carrying
  that episode's title or that guest's name and face; the home, list and topic
  pages use the branded `images/og-default.jpg`.
- In episode cards, if we have a chip for the guest, we can omit the "with <guest>" in the displayed title
