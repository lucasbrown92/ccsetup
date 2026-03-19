"""Shared text utilities for charter conflict detection.

Canonical source for tokenize(), is_prohibition(), and PROHIBITION_WORDS.
Used by claude-charter (schema.py) and claude-witness (server.py).
"""

import re

# Words that indicate prohibition — entries with these get higher-weight matching
PROHIBITION_WORDS = frozenset({
    "never", "not", "no", "must not", "shall not", "cannot", "without",
    "avoid", "don't", "doesn't", "forbidden", "prohibited", "disallowed",
})


def tokenize(text):
    """Lower-case word tokens for overlap scoring."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def is_prohibition(content):
    """True if the content expresses a prohibition (negative constraint)."""
    lower = content.lower()
    return any(w in lower for w in PROHIBITION_WORDS)
