"""Remove AI-tool Co-authored-by trailers from git commit messages."""
from __future__ import annotations

import sys

BLOCKED = (
    "co-authored-by: cursor",
    "co-authored-by: claude",
    "co-authored-by: copilot",
)

def should_drop(line: str) -> bool:
    lower = line.lower()
    if any(token in lower for token in BLOCKED):
        return True
    return "cursor" in lower


text = sys.stdin.read()
lines = [line for line in text.splitlines() if not should_drop(line)]
sys.stdout.write("\n".join(lines))
if lines:
    sys.stdout.write("\n")
