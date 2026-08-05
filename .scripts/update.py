#!/usr/bin/env python3
"""Run the whole post-regeneration pass in order, then verify.

Use this after the HTML pages have been (re)written from the RSS feed — it
draws cards for anything new, brings every page's social metadata back into
agreement, refreshes the sitemap, and checks the result.

    python3 .scripts/update.py
    python3 .scripts/update.py --refresh    # re-fetch the podcast feed first
    python3 .scripts/update.py --skip-links # no network check of outbound links

It does NOT generate the site's pages; that is the AI's job, per AGENTS.md.
"""
import subprocess
import sys
import os

STEPS = [
    ("make_cards.py", "draw share cards for new episodes and guests"),
    ("social.py", "rewrite OpenGraph/Twitter/JSON-LD and share rows"),
    ("make_sitemap.py", "regenerate sitemap.xml"),
    ("verify.py", "check the site"),
    ("check_links.py", "check that outbound links still resolve"),
]


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    passthrough = [a for a in sys.argv[1:] if a == "--refresh"]
    for script, what in STEPS:
        if script == "check_links.py" and "--skip-links" in sys.argv[1:]:
            print(f"\n==> {script}: skipped (--skip-links)")
            continue
        print(f"\n==> {script}: {what}")
        args = passthrough if script in ("social.py", "make_sitemap.py") else []
        result = subprocess.run([sys.executable, os.path.join(here, script), *args])
        if result.returncode != 0:
            sys.exit(f"\n{script} failed ({result.returncode})")
    print("\nAll steps passed.")


if __name__ == "__main__":
    main()
