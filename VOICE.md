# Happy Path Programming voice

How we write episode descriptions and resource links. It is drawn from the
show's own descriptions (roughly #79 to #122 in the feed; #123's long summary
is not the usual style). Use it when you draft a new episode's show notes,
label a resource link, or write a page's `<meta name="description">`.

The show: *No-frills discussions between Bruce Eckel and James Ward about
programming, what it is, and what it should be.* The descriptions should be
no-frills too.

## The voice

- **We, the hosts, talking to other programmers.** Write in the first person
  plural: "We chat with…", "We learn about…", "Lize Raes teaches us about…",
  "We dive in and learn how…". "We chat with" is the house verb, so use it
  freely. On host-only episodes, name the hosts: "Bruce & James recap…",
  "Bruce and James chat about the future of programming."
- **Lead with the guest and what they made.** Give the name first, then one
  clause of credentials, then the thing you talked about:
  - "Rod Johnson, creator of the Spring Framework, has created a JVM-based AI
    Agent framework called Embabel."
  - "We chat with Dave Thomas, co-author of The Pragmatic Programmer, about…"
  - "Nathan Sobo is co-founder of Zed, a super-fast, collaborative,
    AI-powered, code editor."
- **Short.** One to three sentences, usually under 60 words. Name the topics
  rather than summarizing the conversation. Don't write section headings, a
  "key takeaways" list, a timestamp list, or a recap of the guest's arguments.
- **Concrete and technical.** Name the actual languages, libraries, papers and
  ideas: "lessons learned from building Atom, Electron and its challenges,
  CRDTs, Rust native GPU GUIs, AI Code Assistants". Assume the listener is a
  programmer. Expand an acronym once when it's niche: "Infrastructure as Code
  (IaC)", "MCP (Model Context Protocol)".
- **A point of view is welcome.** Some of the best openings state a tension
  or an opinion plainly:
  - "Infrastructure as Code (IaC) is "code" but without most of the benefits
    of being code."
  - "Most of us have managers but they aren't always great."
  - "Paul Snively helps us see the future of programming. Spoiler: It's
    Typed & Functional."
- **Dry, light humor, used sparingly.** It is usually self-deprecating or a
  small aside, never a joke at the guest's expense:
  - "…AI Code Assistants, and more CRDTs."
  - "Ironically our recording software crashed near the end of the episode
    but we recovered and wrapped things up."
  - "James' very slow Scala ZIO implementation"
  - "James rants about SemVer for the 3.1.4'th time."
- **Warm toward guests and the community.** "our friend", "we are grateful
  for all his contributions", "happily coding the fun stuff".

## Avoid

- Hype and marketing words: "groundbreaking", "game-changing",
  "revolutionary", "deep dive into the fascinating world of", "unlock",
  "supercharge", "must-listen".
- AI-sounding filler: "delve", "landscape", "leverage", "In today's
  fast-paced world", "Join us as we explore", and closing lines like "Tune
  in to find out!"
- Restating the title as the first sentence.
- Claims we can't back up: don't make up what the guest said, invent
  numbers, or describe a project beyond what its own site says. If you
  haven't heard the episode or read a transcript, stay at the level of the
  title, the guest and their project.
- Emoji, hashtags, and exclamation marks (one is fine for real news, as in
  "our book is out!").

## Resource links

The resource list is where the episode's links go. Keep the description's
prose free of bare URLs and of lines that only point at a resource
("Referenced blog: …", "Repo:", "Learn more at …").

- **Heading.** Use `Resources:`.
- **One item per line**, written `- Label: URL`. In the Spotify for Creators
  editor, put each item in its own paragraph so no URL runs into the next
  line's text. The feed's run-together URLs (see `AGENTS.md`) come from
  pasting a block without line breaks.
- **Order.** Start with the guest's own profile, then their project (site,
  repo, docs), then everything else in the order it came up.
- **Labels** say what the link is, in a few words. They should not be the URL
  or a bare domain, and should not be "here" or "link":
  - The guest's profile: their name, `Trisha Gee`. A second profile gets a
    qualifier: `Johannes' website`.
  - A project: the project name, plus a qualifier when it's ambiguous or
    there are several links: `Effect (TypeScript library)`, `Graboo on
    GitHub`, `Pyrefly Discord`.
  - An article, paper or essay: `Author, "Title"`, plus a short note when
    the title doesn't say why it's there: `James Long, "Using CRDTs in the
    Wild" (hybrid logical clocks)`, `Eugenio Moggi, "Notions of Computation
    and Monads" (1991)`.
  - A book: `Diana's book: Title`, or `"Title" by Author`.
  - A talk or video: `Paul Snively's LambdaConf Talk on Verse`,
    `Arty Starr at SpringOne 2021 (talk)`.
  - Something a host made: `James' Pkl for GitHub Actions` (always
    `James'`, never `James's`).
  - A past episode: `Happy Path Programming #37: The Future of Everything
    with Paul Snively`. On the site, link it to the episode's page
    (`37-….html`), not to Spotify.
- **URLs.** Use the canonical `https://` URL with no tracking parameters or
  link shorteners. Prefer the project's own site or repo over Wikipedia or a
  news article. Include only links that the hosts or guest mentioned, or the
  guest's own profile. Never guess at a URL, and check that each one resolves
  (`python3 .scripts/check_links.py` does this for the site).

## Template

```
We chat with <Guest Name>, <one-clause credential>, about <project/topic>.
<Optional: one sentence with a point of view, or the topics covered as one
comma-separated run.>

Resources:
- <Guest Name>: https://…
- <Project>: https://…
- <Author>, "<Title>": https://…
```

## Example

```
Infrastructure as Code (IaC) is "code" but without most of the benefits of
being code. We chat with Sam Goodwin about reinventing IaC with Alchemy and
the upcoming Alchemy Effect project, which aims to manage infrastructure
dependencies & provisioning the same way we manage requirements in Effect
Oriented Programming.

Resources:
- Sam Goodwin: https://x.com/samgoodwin89
- Alchemy: https://alchemy.run
```

## On the site

The feed's description is the hosts' published text. Don't rewrite it on the
episode page: copy the prose over and only make the mechanical fixes that
`AGENTS.md` describes (split run-together URLs, restore missing spaces, move
the resources into the list). Use this guide for the text you write
yourself:

- **`<meta name="description">`**: whole sentences from the start of the
  prose, as many as fit in about 160 characters, and always at least the
  first. When the first sentence is a short hook (under about 100
  characters, like "No doubt that Rust is hot right now."), add the next one
  as long as the total stays under about 220. Never cut mid-word, and never
  include resource lines. `social.py`
  copies it into `og:description`, `twitter:description` and the JSON-LD,
  so it is the text people see in search results and link previews.
- **Resource labels**: when the feed gives a bare URL, a bare domain or a
  vague label, write the label using the rules above. Take it from the feed
  when the feed has one in front of the URL ("Challenge details:
  www.morling.dev/…").
