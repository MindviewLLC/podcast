#!/usr/bin/env python3
"""Write llms.txt and llms-full.txt, the site's summary for LLMs (llmstxt.org).

llms.txt is the index: the show, its hosts, and one link per episode, guest and
topic page, with a short note on each. llms-full.txt is the full text: every
episode's facts, listen links, description and resources, in Markdown.

Everything is read back from the pages on disk (no dates of generation, no
network), so re-running with nothing new rewrites identical files.

    python3 .scripts/make_llms.py
"""
from __future__ import annotations

import os
import re
import sys

import hpp
from hpp import SITE, SITE_FEED, SITE_NAME, TAGLINE

INDEX, FULL = "llms.txt", "llms-full.txt"


def text(fragment: str) -> str:
    """Inline HTML -> Markdown: links become [text](url), other tags go."""
    links: list[str] = []

    def link(m):
        href, label = hpp.unesc(m.group(1)), plain(m.group(2))
        if not href.startswith(("http://", "https://")):
            href = SITE + "/" + re.sub(r'^(\.\./)+', '', href)
        links.append(f"<{href}>" if label == href else
                     "[" + label.replace("[", r"\[").replace("]", r"\]") + f"]({href})")
        return f"\x00{len(links) - 1}\x00"
    # links become placeholders first, so stripping tags can't eat a <url> autolink
    fragment = re.sub(r'<a\b[^>]*?href="([^"]*)"[^>]*>(.*?)</a>', link, fragment, flags=re.S)
    return re.sub(r"\x00(\d+)\x00", lambda m: links[int(m.group(1))], plain(fragment))


def plain(fragment: str) -> str:
    return re.sub(r"\s+", " ", hpp.unesc(re.sub(r"<[^>]+>", "", fragment))).strip()


def first_sentence(s: str, limit: int = 220) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", s)
    s = m.group(1) if m else s
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def hosts() -> list[dict]:
    doc = open("index.html", encoding="utf-8").read()
    urls = {h["name"]: h["url"] for h in hpp.HOSTS}
    out = []
    for card in re.findall(r'<article class="host-card">(.*?)</article>', doc, re.S):
        name = hpp.field(card, r"<h2>(.*?)</h2>")
        out.append({"name": name, "url": urls.get(name, f"{SITE}/#hosts"),
                    "role": hpp.field(card, r'<p class="host-role">(.*?)</p>'),
                    "bio": hpp.field(card, r'<p class="host-bio">(.*?)</p>')})
    return out


def episode(slug: str) -> dict:
    doc = open(f"episodes/{slug}.html", encoding="utf-8").read()
    ep = hpp.episode_page(doc)
    prose = re.search(r'<h2>About this episode</h2>\s*<div class="prose">(.*?)</div>\s*</section>',
                      doc, re.S)
    res = re.search(r'<h2>Resources &amp; links</h2>\s*<ul class="res-list">(.*?)</ul>', doc, re.S)
    pills = re.search(r'<div class="pills">(.*?)</div>', doc, re.S)
    paras = re.findall(r"<p>(.*?)</p>", prose.group(1), re.S) if prose else []
    ep.update(
        slug=slug, summary=first_sentence(plain(paras[0])) if paras else "", url=f"{SITE}/episodes/{slug}.html",
        paragraphs=[text(p) for p in paras],
        resources=[text(li) for li in re.findall(r"<li>(.*?)</li>", res.group(1), re.S)]
        if res else [],
        listen=[(plain(t), h) for h, t in re.findall(
            r'<a class="pill[^"]*" href="([^"]+)"[^>]*>(.*?)</a>', pills.group(1), re.S)]
        if pills else [],
    )
    return ep


def facts(ep: dict) -> str:
    bits = [b for b in (ep["date"], ep["duration"]) if b]
    if ep["guests"]:
        bits.append("with " + ", ".join(n for n, _ in ep["guests"]))
    return " · ".join(bits)


def header(title: str) -> list[str]:
    return [f"# {title}", "", f"> {TAGLINE}", ""]


def write_index(eps: list[dict]) -> None:
    guests = hpp.guest_index_items()
    topics = hpp.topic_index_items()
    out = header(SITE_NAME) + [
        f"A podcast by Bruce Eckel and James Ward: {len(eps)} episodes and "
        f"{len(guests)} guests. Each episode has its own page with its description, "
        f"guests, topics, resources and links to listen on Spotify, Apple Podcasts "
        f"and (from #109) YouTube. The full notes for every episode are in "
        f"[llms-full.txt]({SITE}/{FULL}).",
        "", "## Hosts", "",
    ]
    out += [f"- [{h['name']}]({h['url']}): {h['role']}. {first_sentence(h['bio'])}"
            for h in hosts()]
    out += ["", "## Episodes", ""]
    for ep in eps:
        note = facts(ep)
        if ep["summary"]:
            note += ". " + ep["summary"]
        out.append(f"- [#{ep['number']} {ep['title']}]({ep['url']}): {note}")
    out += ["", "## Guests", ""]
    for slug, name in guests:
        doc = open(f"guests/{slug}.html", encoding="utf-8").read()
        nums = [s.split("-", 1)[0] for s, _ in hpp.appearances(doc)]
        out.append(f"- [{name}]({SITE}/guests/{slug}.html): episode"
                   f"{'s' if len(nums) > 1 else ''} " + ", ".join(f"#{n}" for n in nums))
    out += ["", "## Topics", ""]
    for slug, name in topics:
        doc = open(f"topics/{slug}.html", encoding="utf-8").read()
        n = len(hpp.appearances(doc))
        out.append(f"- [{name}]({SITE}/topics/{slug}.html): {n} episode{'s' if n != 1 else ''}")
    out += ["", "## Optional", "",
            f"- [Full episode notes]({SITE}/{FULL}): every episode's description and resources",
            f"- [RSS feed]({SITE_FEED}): the episodes, with audio",
            f"- [Sitemap]({SITE}/sitemap.xml)"]
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def write_full(eps: list[dict]) -> None:
    out = header(f"{SITE_NAME}: full episode notes") + [
        f"Every episode of the {SITE_NAME} podcast by Bruce Eckel and James Ward, "
        f"newest first. The index is [llms.txt]({SITE}/{INDEX}).", ""]
    for ep in eps:
        out += [f"## #{ep['number']} {ep['title']}", "", f"- Page: {ep['url']}"]
        if facts(ep):
            out.append(f"- Aired: {facts(ep)}")
        if ep["topics"]:
            out.append("- Topics: " + ", ".join(n for n, _ in ep["topics"]))
        if ep["listen"]:
            out.append("- Listen: " + ", ".join(f"[{t}]({h})" for t, h in ep["listen"]))
        if os.path.exists(f"transcripts/{ep['slug']}.srt"):
            out.append(f"- Transcript: {SITE}/transcripts/{ep['slug']}.srt")
        out.append("")
        for p in ep["paragraphs"]:
            out += [p, ""]
        if ep["resources"]:
            out += ["Resources:", ""] + [f"- {r}" for r in ep["resources"]] + [""]
    with open(FULL, "w", encoding="utf-8") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")


def main() -> None:
    hpp.require_root()
    eps = [episode(slug) for slug, _t in hpp.episode_index_items()]
    write_index(eps)
    write_full(eps)
    pages = len(hpp.episode_slugs())
    print(f"{INDEX}, {FULL}: {len(eps)} episodes (episode pages on disk: {pages})")
    if len(eps) != pages:
        sys.exit("llms.txt does not cover every episode page — check episodes/index.html")


if __name__ == "__main__":
    main()
