#!/usr/bin/env python3
"""Fetch the podcast feed once, make sure it isn't a stale copy, and say which
episodes still need pages.

    python3 .scripts/feed.py                    # check the cached feed against the site
    python3 .scripts/feed.py --refresh          # re-fetch (with the stale-copy guard) first
    python3 .scripts/feed.py --refresh --feed-behind-ok   # report, don't fail, when YouTube is ahead

`update.py --refresh` runs this first; every later step reads the copy it saved.
It fails when:
- the feed has episodes with no page yet (write them per AGENTS.md, then re-run);
- YouTube has an episode newer than the feed's newest, even after retries. The
  feed is the source of truth, but its CDN can serve a copy up to a week old, so
  a newer YouTube video is a sign of a stale feed, not something for "next run".
  If the episode really isn't in the feed yet (a video published before the
  audio), report it and re-run with --feed-behind-ok.
A YouTube listing that fails is a warning, not a failure: the feed is still
checked against the site's own newest page.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hpp  # noqa: E402
import youtube  # noqa: E402


def main() -> None:
    hpp.require_root()
    args = sys.argv[1:]
    yt_newest = 0
    if "--refresh" in args:
        try:
            yt_newest = youtube.newest_episode()
            print(f"youtube: newest video is #{yt_newest}")
        except Exception as e:  # noqa: BLE001 - any listing failure is only a warning
            print(f"WARNING: couldn't list the YouTube channel ({e}); "
                  "checking the feed against the site's pages only", file=sys.stderr)
    path = hpp.fetch_feed("--refresh" in args, expect=yt_newest)
    built, newest = hpp.feed_facts(open(path, "rb").read())
    feed = hpp.episodes_from_feed()
    print(f"feed: {len(feed)} episodes, newest #{newest}, built {built}")

    problems = []
    slugs = hpp.episode_slugs()
    no_page = sorted(n for n in feed if n not in slugs)
    if no_page:
        problems.append("in the feed but no episode page yet: "
                        + ", ".join(f"#{n}" for n in no_page)
                        + " (write the pages per AGENTS.md, then re-run)")
    site_newest = max(slugs, default=0)
    if site_newest > newest:
        problems.append(f"the site has #{site_newest} but the feed's newest is #{newest}: "
                        "the feed copy is stale; re-run with --refresh")
    if yt_newest > newest:
        msg = (f"YouTube has #{yt_newest} but the feed's newest is #{newest} after retries: "
               "the feed is probably a stale CDN copy. Re-run later; if the episode "
               "really isn't in the feed yet, report it and re-run with --feed-behind-ok")
        if "--feed-behind-ok" in args:
            print("WARNING: " + msg, file=sys.stderr)
        else:
            problems.append(msg)
    if problems:
        print("\n".join("FAIL: " + p for p in problems))
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
