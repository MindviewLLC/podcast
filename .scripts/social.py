#!/usr/bin/env python3
"""Rewrite the social-sharing parts of every page: the OpenGraph/Twitter-card
head, the JSON-LD block, the on-page share row and its inline script.

Everything it writes is derived from the page itself plus the podcast feed, so
it is idempotent — run it after any regeneration of the HTML and it brings the
whole site back into agreement. It only ever REPLACES its own output, so it is
safe to re-run.

    python3 .scripts/social.py                # uses the cached feed
    python3 .scripts/social.py --refresh      # re-fetch the feed first

The head it writes runs from <link rel="canonical"> to <meta name="theme-color">
inclusive, and the JSON-LD sits at the end of <head>; those two markers are how
it finds its own output next time, so keep them if you hand-edit a page.
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
import urllib.parse

import hpp
from hpp import (FEED, HOSTS, OG_DEFAULT, OG_DEFAULT_ALT, SERIES_SAME_AS, SITE,
                 SITE_NAME, TAGLINE, TWITTER, unesc)

# Brand icon paths from Simple Icons (simpleicons.org), plus two utility glyphs.
ICONS = {
    "bluesky": "M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566.944 1.561 1.266.902 1.565.139 1.908 0 3.08 0 3.768c0 .69.378 5.65.624 6.479.815 2.736 3.713 3.66 6.383 3.364.136-.02.275-.039.415-.056-.138.022-.276.04-.415.056-3.912.58-7.387 2.005-2.83 7.078 5.013 5.19 6.87-1.113 7.823-4.308.953 3.195 2.05 9.271 7.733 4.308 4.267-4.308 1.172-6.498-2.74-7.078a8.741 8.741 0 0 1-.415-.056c.14.017.279.036.415.056 2.67.297 5.568-.628 6.383-3.364.246-.828.624-5.79.624-6.478 0-.69-.139-1.861-.902-2.206-.659-.298-1.664-.62-4.3 1.24C16.046 4.748 13.087 8.687 12 10.8Z",
    "x": "M18.901 1.153h3.68l-8.04 9.19L24 22.846h-7.406l-5.8-7.584-6.638 7.584H.474l8.6-9.83L0 1.154h7.594l5.243 6.932ZM17.61 20.644h2.039L6.486 3.24H4.298Z",
    "linkedin": "M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z",
    "hn": "M0 24V0h24v24H0zM6.951 5.896l4.112 7.708v5.064h1.583v-4.972l4.148-7.799h-1.749l-2.457 4.875c-.372.745-.688 1.434-.688 1.434s-.297-.708-.651-1.434L8.831 5.896h-1.88z",
    "reddit": "M12 0C5.373 0 0 5.373 0 12c0 3.314 1.343 6.314 3.515 8.485l-2.286 2.286C.775 23.225 1.097 24 1.738 24H12c6.627 0 12-5.373 12-12S18.627 0 12 0Zm4.388 3.199c1.104 0 1.999.895 1.999 1.999 0 1.105-.895 2-1.999 2-.946 0-1.739-.657-1.947-1.539v.002c-1.147.162-2.032 1.15-2.032 2.341v.007c1.776.067 3.4.567 4.686 1.363.473-.363 1.064-.58 1.707-.58 1.547 0 2.802 1.254 2.802 2.802 0 1.117-.655 2.081-1.601 2.531-.088 3.256-3.637 5.876-7.997 5.876-4.361 0-7.905-2.617-7.998-5.87-.954-.447-1.614-1.415-1.614-2.538 0-1.548 1.255-2.802 2.803-2.802.645 0 1.239.218 1.712.585 1.275-.79 2.881-1.291 4.64-1.365v-.01c0-1.663 1.263-3.034 2.88-3.207.188-.911.993-1.595 1.959-1.595Zm-8.085 8.376c-.784 0-1.459.78-1.506 1.797-.047 1.016.64 1.429 1.426 1.429.786 0 1.371-.369 1.418-1.385.047-1.017-.553-1.841-1.338-1.841Zm7.406 0c-.786 0-1.385.824-1.338 1.841.047 1.017.634 1.385 1.418 1.385.785 0 1.473-.413 1.426-1.429-.046-1.017-.721-1.797-1.506-1.797Zm-3.703 4.013c-.974 0-1.907.048-2.77.135-.147.015-.241.168-.183.305.483 1.154 1.622 1.964 2.953 1.964 1.33 0 2.47-.81 2.953-1.964.057-.137-.037-.29-.184-.305-.863-.087-1.795-.135-2.769-.135Z",
    "link": "M10.59 13.41a1 1 0 0 1 0-1.41l3.54-3.54a3 3 0 1 1 4.24 4.24l-1.42 1.42a1 1 0 0 1-1.41-1.42l1.41-1.41a1 1 0 1 0-1.41-1.41l-3.54 3.53a1 1 0 0 1-1.41 0Zm2.82-2.82a1 1 0 0 1 0 1.41l-3.54 3.54a3 3 0 1 1-4.24-4.24l1.42-1.42a1 1 0 1 1 1.41 1.42l-1.41 1.41a1 1 0 1 0 1.41 1.41l3.54-3.53a1 1 0 0 1 1.41 0Z",
    "share": "M18 16.08a2.9 2.9 0 0 0-1.96.77L8.91 12.7a3.3 3.3 0 0 0 0-1.4l7.05-4.11A2.99 2.99 0 1 0 15 5c0 .24.03.47.09.7L8.04 9.81a3 3 0 1 0 0 4.38l7.12 4.16c-.05.21-.08.43-.08.65a2.92 2.92 0 1 0 2.92-2.92Z",
}

# How this tool recognises its own output on a re-run.
RE_META_BLOCK = re.compile(
    r'<link rel="canonical".*?<meta name="theme-color" content="#0f9d58">', re.S)
RE_LD = re.compile(r'\n*<script type="application/ld\+json">.*?</script>', re.S)
RE_SHARE_SECTION = re.compile(
    r'\n*<section class="wrap share-section">.*?</section>\n*', re.S)
RE_SHARE_PANEL = re.compile(
    r'\n*      <section class="panel share-panel">.*?</section>\n*', re.S)
RE_SHARE_SCRIPT = re.compile(
    r'\n*<script>\n\(function\(\)\{var d=document.*?</script>', re.S)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def meta(name: str, content: str, prop: bool = False) -> str:
    return f'<meta {"property" if prop else "name"}="{name}" content="{esc(content)}">'


def attr(doc: str, pattern: str) -> str:
    m = re.search(pattern, doc, re.S)
    return m.group(1) if m else ""


# ------------------------------------------------------------------- share
def icon(key: str) -> str:
    return (f'<svg class="pico" viewBox="0 0 24 24" fill="currentColor" '
            f'aria-hidden="true"><path d="{ICONS[key]}"/></svg>')


def share_buttons(url: str, title: str, thing: str) -> str:
    q = urllib.parse.quote
    u, t = q(url, safe=""), q(title, safe="")
    text = q(f"{title} 🎧", safe="")
    targets = [
        ("bluesky", "Bluesky", f"https://bsky.app/intent/compose?text={text}%20{u}"),
        ("x", "X", f"https://x.com/intent/post?text={text}&url={u}&via=happypathprog"),
        ("linkedin", "LinkedIn",
         f"https://www.linkedin.com/sharing/share-offsite/?url={u}"),
        ("hn", "Hacker News", f"https://news.ycombinator.com/submitlink?u={u}&t={t}"),
        ("reddit", "Reddit", f"https://www.reddit.com/submit?url={u}&title={t}"),
    ]
    out = [
        f'<a class="share-btn share-btn--{key}" href="{esc(href)}" target="_blank" '
        f'rel="noopener" aria-label="Share {esc(thing)} on {label}">'
        f'{icon(key)}<span class="share-label">{label}</span></a>'
        for key, label, href in targets]
    out.append(
        f'<button type="button" class="share-btn js-copy" data-share-url="{esc(url)}" '
        f'aria-label="Copy link to {esc(thing)}">{icon("link")}'
        f'<span class="share-label">Copy link</span></button>')
    out.append(
        f'<button type="button" class="share-btn js-native" hidden '
        f'data-share-url="{esc(url)}" data-share-title="{esc(title)}" '
        f'aria-label="Share {esc(thing)}">{icon("share")}'
        f'<span class="share-label">Share…</span></button>')
    return "".join(out)


SHARE_SCRIPT = """<script>
(function(){var d=document;
function copy(t){if(navigator.clipboard&&window.isSecureContext)return navigator.clipboard.writeText(t);
var a=d.createElement('textarea');a.value=t;a.setAttribute('readonly','');
a.style.cssText='position:fixed;top:-9999px;opacity:0';d.body.appendChild(a);a.select();
try{d.execCommand('copy')}catch(e){}d.body.removeChild(a);return Promise.resolve();}
d.querySelectorAll('.js-copy').forEach(function(b){b.addEventListener('click',function(){
var l=b.querySelector('.share-label'),o=l.textContent;
copy(b.dataset.shareUrl).then(function(){l.textContent='Copied!';b.classList.add('is-copied');
setTimeout(function(){l.textContent=o;b.classList.remove('is-copied');},1600);}).catch(function(){});});});
if(navigator.share){d.querySelectorAll('.js-native').forEach(function(b){b.hidden=false;
b.addEventListener('click',function(){navigator.share({title:b.dataset.shareTitle,url:b.dataset.shareUrl}).catch(function(){});});});}
})();
</script>"""


def share_section(url, title, thing, heading) -> str:
    return (f'\n<section class="wrap share-section">\n'
            f'  <div class="share-card">\n'
            f'    <p class="share-title">{heading}</p>\n'
            f'    <div class="share-row">{share_buttons(url, title, thing)}</div>\n'
            f'  </div>\n'
            f'</section>\n')


def share_panel(url, title, thing) -> str:
    return (f'\n      <section class="panel share-panel">\n'
            f'        <h2>Share this episode</h2>\n'
            f'        <div class="share-row">{share_buttons(url, title, thing)}</div>\n'
            f'      </section>\n')


# ----------------------------------------------------------------- JSON-LD
def json_ld(graph: list) -> str:
    payload = {"@context": "https://schema.org", "@graph": graph}
    return ('\n<script type="application/ld+json">'
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


def series_ref() -> dict:
    return {"@type": "PodcastSeries", "@id": f"{SITE}/#podcast",
            "name": SITE_NAME, "url": f"{SITE}/"}


def crumbs(trail: list[tuple[str, str]]) -> dict:
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
        for i, (name, url) in enumerate(trail)]}


def collection(page_url, title, desc, items, extra=None) -> dict:
    node = {"@type": "CollectionPage", "url": page_url, "name": title,
            "description": desc, "isPartOf": series_ref()}
    if extra:
        node.update(extra)
    node["mainEntity"] = {
        "@type": "ItemList", "numberOfItems": len(items),
        "itemListElement": [{"@type": "ListItem", "position": i + 1,
                             "name": n, "url": u}
                            for i, (n, u) in enumerate(items)]}
    return node


# ------------------------------------------------------------------- head
def build_meta(*, page_url, title, description, image, image_w, image_h,
               image_alt, card, og_type, extra_og=(), extra_tw=()) -> str:
    lines = [
        f'<link rel="canonical" href="{esc(page_url)}">',
        f'<link rel="alternate" type="application/rss+xml" '
        f'title="{esc(SITE_NAME)} podcast feed" href="{esc(FEED)}">',
        meta("og:type", og_type, prop=True),
        meta("og:site_name", SITE_NAME, prop=True),
        meta("og:locale", "en_US", prop=True),
        meta("og:title", title, prop=True),
        meta("og:description", description, prop=True),
        meta("og:url", page_url, prop=True),
        meta("og:image", image, prop=True),
        meta("og:image:type", "image/jpeg", prop=True),
        meta("og:image:width", str(image_w), prop=True),
        meta("og:image:height", str(image_h), prop=True),
        meta("og:image:alt", image_alt, prop=True),
        *extra_og,
        meta("twitter:card", card),
        meta("twitter:site", TWITTER),
        meta("twitter:creator", TWITTER),
        meta("twitter:title", title),
        meta("twitter:description", description),
        meta("twitter:image", image),
        meta("twitter:image:alt", image_alt),
        *extra_tw,
        meta("author", "Bruce Eckel & James Ward"),
        meta("theme-color", "#0f9d58"),
    ]
    return "\n".join(lines)


def share_card(kind: str, slug: str) -> str:
    """Absolute URL of this page's own 1200x630 card, else the site default."""
    path = f"images/og/{kind}/{slug}.jpg"
    return f"{SITE}/{path}" if os.path.exists(path) else OG_DEFAULT


def strip_generated(doc: str) -> str:
    doc = RE_LD.sub("", doc)
    doc = RE_SHARE_SECTION.sub("\n", doc)
    doc = RE_SHARE_PANEL.sub("\n", doc)
    doc = RE_SHARE_SCRIPT.sub("", doc)
    doc = re.sub(r'(<link rel="icon" href="[^"]*">)\n+</head>', r"\1\n</head>", doc)
    return doc


# ------------------------------------------------------------------- pages
def process(path: str, feed: dict[int, dict]) -> None:
    doc = strip_generated(open(path, encoding="utf-8").read())
    kind, section, slug = hpp.classify(path)

    head_title = unesc(attr(doc, r'<meta property="og:title" content="(.*?)">'))
    desc = unesc(attr(doc, r'<meta name="description" content="(.*?)">'))
    page_url = unesc(attr(doc, r'<meta property="og:url" content="(.*?)">'))

    ld: list = []
    extra_og: list[str] = []
    extra_tw: list[str] = []
    og_type, card = "website", "summary_large_image"
    image, iw, ih = OG_DEFAULT, 1200, 630
    image_alt = OG_DEFAULT_ALT
    share_title, share_thing, share_heading = head_title, "this page", "Share"
    in_aside = False
    home = ("Home", f"{SITE}/")

    if kind == "episode":
        og_type = "article"
        ep = hpp.episode_page(doc)
        num, ep_title = ep["number"], ep["title"]
        image = share_card("episodes", slug)
        image_alt = (f"{SITE_NAME} episode #{num}: {ep_title}" if num
                     else f"{SITE_NAME}: {ep_title}")

        info = feed.get(num, {}) if num else {}
        published = info.get("published") or ""
        if not published and ep["date"]:
            try:
                published = datetime.datetime.strptime(
                    ep["date"], "%B %d, %Y").strftime("%Y-%m-%dT00:00:00Z")
            except ValueError:
                published = ""
        audio = info.get("audio") or ep["audio"]
        audio_type = info.get("audio_type") or (
            "audio/mp4" if audio.endswith(".m4a") else "audio/mpeg")

        if published:
            extra_og.append(meta("article:published_time", published, prop=True))
        extra_og.append(meta("article:section", "Technology", prop=True))
        extra_og += [meta("article:tag", n, prop=True) for n, _ in ep["topics"]]
        extra_og += [meta("article:author", h["name"], prop=True) for h in HOSTS]
        if audio:
            extra_og.append(meta("og:audio", audio, prop=True))
            extra_og.append(meta("og:audio:type", audio_type, prop=True))

        if ep["duration"]:
            extra_tw += [meta("twitter:label1", "Duration"),
                         meta("twitter:data1", ep["duration"])]
        if ep["guests"]:
            extra_tw += [
                meta("twitter:label2",
                     "Guest" if len(ep["guests"]) == 1 else "Guests"),
                meta("twitter:data2", ", ".join(n for n, _ in ep["guests"]))]
        elif ep["date"]:
            extra_tw += [meta("twitter:label2", "Published"),
                         meta("twitter:data2", ep["date"])]

        episode: dict = {
            "@type": "PodcastEpisode", "@id": page_url + "#episode",
            "url": page_url, "name": (f"#{num} {ep_title}" if num else ep_title),
            "description": desc, "image": image, "partOfSeries": series_ref(),
            "author": HOSTS, "inLanguage": "en",
        }
        if num:
            episode["episodeNumber"] = num
        if published:
            episode["datePublished"] = published
        if info.get("duration"):
            episode["timeRequired"] = info["duration"]
        if audio:
            media = {"@type": "AudioObject", "contentUrl": audio,
                     "encodingFormat": audio_type}
            if info.get("duration"):
                media["duration"] = info["duration"]
            episode["associatedMedia"] = media
        if ep["guests"]:
            episode["actor"] = [{"@type": "Person", "name": n,
                                 "url": f"{SITE}/guests/{s}.html"}
                                for n, s in ep["guests"]]
        if ep["topics"]:
            episode["keywords"] = ", ".join(n for n, _ in ep["topics"])
        ld = [episode, crumbs([home, ("Episodes", f"{SITE}/episodes/"),
                               (ep_title, page_url)])]
        share_title = f"#{num} {ep_title}" if num else ep_title
        share_thing = f"episode {share_title}"
        in_aside = True

    elif kind == "guest":
        og_type = "profile"
        g = hpp.guest_page(doc)
        name, eps = g["name"], g["episodes"]
        image = share_card("guests", slug)
        image_alt = f"{name}, guest on {SITE_NAME}"
        parts = name.split()
        if len(parts) >= 2:
            extra_og.append(meta("profile:first_name", parts[0], prop=True))
            extra_og.append(meta("profile:last_name", " ".join(parts[1:]), prop=True))
        if eps:
            extra_tw += [meta("twitter:label1", "Episodes"),
                         meta("twitter:data1", str(len(eps)))]
        person = {"@type": "Person", "@id": page_url + "#person", "name": name,
                  "url": page_url}
        if g["photo"]:
            # schema.org wants the person's actual likeness, not the wide card
            person["image"] = f"{SITE}/{g['photo']}"
        person["performerIn"] = [{"@type": "PodcastEpisode", "name": t,
                                  "url": f"{SITE}/episodes/{s}.html"}
                                 for s, t in eps]
        ld = [{"@type": "ProfilePage", "url": page_url, "name": head_title,
               "description": desc, "mainEntity": {"@id": page_url + "#person"}},
              person,
              crumbs([home, ("Guests", f"{SITE}/guests/"), (name, page_url)])]
        share_title = f"{name} on {SITE_NAME}"
        share_thing = f"{name}'s guest page"

    elif kind == "topic":
        t = hpp.topic_page(doc)
        topic, eps = t["name"], t["episodes"]
        extra_tw += [meta("twitter:label1", "Episodes"),
                     meta("twitter:data1", str(len(eps)))]
        image_alt = f"{SITE_NAME} episodes about {topic}"
        ld = [collection(page_url, head_title, desc,
                         [(title, f"{SITE}/episodes/{s}.html") for s, title in eps],
                         {"about": {"@type": "Thing", "name": topic}}),
              crumbs([home, ("Topics", f"{SITE}/topics/"), (topic, page_url)])]
        share_title = f"{SITE_NAME}: {topic} episodes"
        share_thing = f"the {topic} topic page"

    elif kind == "list":
        label = section.capitalize()
        if section == "guests":
            items = [(n, f"{SITE}/guests/{s}.html")
                     for s, n in hpp.guest_index_items()]
        elif section == "topics":
            items = [(n, f"{SITE}/topics/{s}.html")
                     for s, n in hpp.topic_index_items()]
        else:
            items = [(t, f"{SITE}/episodes/{s}.html")
                     for s, t in hpp.episode_index_items()]
        image_alt = f"{label} — {SITE_NAME}"
        ld = [collection(page_url, head_title, desc, items),
              crumbs([home, (label, page_url)])]
        share_title = f"{label} — {SITE_NAME}"
        share_thing = f"the {section} page"

    else:  # home
        ld = [{"@type": "PodcastSeries", "@id": f"{SITE}/#podcast",
               "name": SITE_NAME, "url": f"{SITE}/", "description": TAGLINE,
               "webFeed": FEED, "image": f"{SITE}/images/hpp.jpg",
               "inLanguage": "en", "author": HOSTS, "sameAs": SERIES_SAME_AS},
              {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/",
               "name": SITE_NAME, "description": TAGLINE,
               "publisher": {"@id": f"{SITE}/#podcast"}}]
        share_title = f"{SITE_NAME} — the podcast"
        share_thing = "the podcast"
        share_heading = "Share the show"

    new_meta = build_meta(page_url=page_url, title=head_title, description=desc,
                          image=image, image_w=iw, image_h=ih, image_alt=image_alt,
                          card=card, og_type=og_type, extra_og=extra_og,
                          extra_tw=extra_tw)
    if not RE_META_BLOCK.search(doc):
        sys.exit(f"{path}: could not find the canonical..theme-color head block")
    doc = RE_META_BLOCK.sub(lambda _m: new_meta, doc, count=1)
    doc = doc.replace("</head>", json_ld(ld) + "\n</head>", 1)

    if in_aside:
        doc = doc.replace(
            "\n    </aside>",
            share_panel(page_url, share_title, share_thing) + "    </aside>", 1)
    else:
        doc = doc.replace(
            "\n</main>",
            share_section(page_url, share_title, share_thing, share_heading)
            + "\n</main>", 1)
    doc = doc.replace("</body>", SHARE_SCRIPT + "\n</body>", 1)
    open(path, "w", encoding="utf-8").write(doc)


def main() -> None:
    hpp.require_root()
    feed = hpp.episodes_from_feed(refresh="--refresh" in sys.argv)
    paths = hpp.pages()
    for path in paths:
        process(path, feed)
    print(f"feed episodes: {len(feed)}; pages rewritten: {len(paths)}")


if __name__ == "__main__":
    main()
