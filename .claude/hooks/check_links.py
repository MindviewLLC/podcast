#!/usr/bin/env python3
"""Stop hook: validate the outbound links on any page edited this turn.

Wired up in .claude/settings.json. Runs `.scripts/check_links.py --changed`,
which only touches the network for URLs it has not already seen, so a turn that
edited nothing (or edited only known-good links) costs a fraction of a second.

A broken link exits 2, which hands the report back to Claude to fix. The
`stop_hook_active` guard means that only happens once per turn — if the link is
dead at the source rather than mistyped, the second stop goes through and the
report is the human's to act on.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "..", "..", ".scripts", "check_links.py")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    if event.get("stop_hook_active"):
        return 0

    done = subprocess.run([sys.executable, os.path.abspath(CHECKER), "--changed"],
                          capture_output=True, text=True)
    report = (done.stdout + done.stderr).strip()
    if done.returncode == 0:
        return 0
    print(f"{report}\n\nFix the broken link(s) above: the URL usually ran into "
          f"the text next to it in the RSS description. If the page really is "
          f"gone, drop the anchor and keep the title as text.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
