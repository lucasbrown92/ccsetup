"""Entry types, statuses, and formatting for claude-charter."""

import re
import uuid
from datetime import datetime, timezone

from text_utils import tokenize, is_prohibition, PROHIBITION_WORDS

ENTRY_TYPES = ["invariant", "constraint", "non_goal", "contract", "goal"]
ENTRY_STATUSES = ["active", "archived", "suspended"]

# Plural / alternate forms accepted in charter_query
TYPE_ALIASES = {
    "invariants": "invariant",
    "constraints": "constraint",
    "non_goals": "non_goal",
    "nongoal": "non_goal",
    "non-goal": "non_goal",
    "non-goals": "non_goal",
    "contracts": "contract",
    "goals": "goal",
}

TYPE_LABELS = {
    "invariant": "INVARIANT",
    "constraint": "CONSTRAINT",
    "non_goal": "NON-GOAL",
    "contract": "CONTRACT",
    "goal": "GOAL",
}

# Entry types that charter_check evaluates against
NORMATIVE_TYPES = {"invariant", "constraint", "contract"}

STATUS_EMOJI = {
    "active": "",
    "archived": " [archived]",
    "suspended": " [suspended]",
}

# Semantic synonym map — maps tokens to related concepts for conflict detection.
# When "requests" appears in a change description, it also matches entries about
# "http", "dependency", "third_party" etc. — catching conflicts that pure token
# overlap would miss.
SYNONYM_MAP = {
    "requests": {"http", "network", "dependency", "third_party", "third", "party", "pip", "package", "deps"},
    "httpx": {"http", "network", "dependency", "third_party", "third", "party", "pip", "package", "deps"},
    "axios": {"http", "network", "dependency", "third_party", "third", "party", "npm", "package"},
    "fetch": {"http", "network", "request", "api"},
    "http": {"network", "request", "requests", "fetch", "connection", "remote"},
    "stdlib": {"standard_library", "no_deps", "no_third_party", "builtin", "no", "deps"},
    "no": {"not", "never", "without", "avoid"},
    "deps": {"dependency", "dependencies", "package", "third_party", "third", "party"},
    "third": {"third_party", "external", "dependency", "package"},
    "party": {"third_party", "external", "dependency"},
    "third_party": {"external", "dependency", "pip", "npm", "package", "third", "party"},
    "database": {"db", "sql", "orm", "sqlite", "postgres", "query", "storage"},
    "async": {"await", "coroutine", "asyncio", "concurrent", "parallel"},
    "test": {"testing", "pytest", "unittest", "spec", "assertion"},
    "security": {"auth", "authentication", "authorization", "token", "secret", "credential"},
    "api": {"endpoint", "route", "rest", "graphql", "interface", "contract"},
    "dependency": {"package", "pip", "npm", "install", "third_party", "external"},
    "refactor": {"restructure", "reorganize", "redesign", "rewrite", "move"},
    "delete": {"remove", "drop", "destroy", "clean", "purge"},
    "rename": {"move", "restructure", "change", "alias"},
    "cache": {"memoize", "store", "persist", "ttl", "invalidate"},
    "log": {"logging", "debug", "trace", "print", "output", "telemetry"},
    "config": {"configuration", "settings", "env", "environment", "options"},
    "deploy": {"release", "publish", "ship", "production", "ci", "cd"},
    "type": {"typing", "annotation", "hint", "mypy", "typescript", "schema"},
    "error": {"exception", "raise", "catch", "handle", "failure", "crash"},
    "performance": {"speed", "latency", "throughput", "optimize", "slow", "fast"},
    "file": {"filesystem", "path", "directory", "io", "read", "write"},
    "network": {"http", "socket", "tcp", "connection", "request", "remote"},
    "class": {"object", "inheritance", "method", "instance", "oop"},
    "function": {"method", "callable", "lambda", "closure", "procedure"},
}


def _expand_tokens(tokens):
    """Expand a set of tokens with their semantic synonyms.

    For each token in the set, if it appears in SYNONYM_MAP, add all
    associated synonyms to the result set.
    """
    expanded = set(tokens)
    for token in tokens:
        synonyms = SYNONYM_MAP.get(token)
        if synonyms:
            expanded |= synonyms
    return expanded


def make_entry(type_, content, notes=None, scope=None, expires_at=None, deadline=None):
    """Create a new entry dict. Raises ValueError on bad input.

    scope: optional list of file/directory paths this entry applies to.
           If empty/None, entry applies to entire project.
    expires_at: ISO datetime string — entry auto-expires after this date.
    deadline: ISO datetime string — goal/contract approaching this date gets flagged.
    """
    if not content or not content.strip():
        raise ValueError("content must not be empty")
    if type_ not in ENTRY_TYPES:
        raise ValueError(f"Invalid type '{type_}'. Valid: {', '.join(ENTRY_TYPES)}")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": uuid.uuid4().hex[:12],
        "type": type_,
        "content": content.strip(),
        "notes": (notes or "").strip(),
        "scope": scope if isinstance(scope, list) else [],
        "status": "active",
        "expires_at": expires_at,
        "deadline": deadline,
        "created_at": now,
        "updated_at": now,
    }


def validate_status(status):
    """Raise ValueError if status is invalid, else return it."""
    if status not in ENTRY_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Valid: {', '.join(ENTRY_STATUSES)}")
    return status


def normalize_filter(filter_str):
    """Return (kind, value) where kind is 'all'|'type'|'status'|'text'."""
    fl = filter_str.strip().lower()
    if fl in ("all", ""):
        return "all", None
    if fl in TYPE_ALIASES:
        fl = TYPE_ALIASES[fl]
    if fl in ENTRY_TYPES:
        return "type", fl
    if fl in ENTRY_STATUSES:
        return "status", fl
    return "text", filter_str.strip()


# ── Conflict detection ────────────────────────────────────────────────────────

def conflict_score(change_tokens, entry_content):
    """Return overlap ratio [0,1] between change tokens and entry content.

    Both sides are expanded with semantic synonyms before computing overlap.
    Prohibition entries get a 1.5x boost — violating a "never do X" is
    more dangerous than overlapping with a "prefer X".
    """
    entry_tokens = tokenize(entry_content)
    if not entry_tokens:
        return 0.0
    expanded_change = _expand_tokens(change_tokens)
    expanded_entry = _expand_tokens(entry_tokens)
    overlap = expanded_change & expanded_entry
    base = len(overlap) / len(expanded_entry)
    if is_prohibition(entry_content) and base > 0:
        return min(base * 1.5, 1.0)
    return base


def entries_for_scope(entries, file_path=None):
    """Filter entries relevant to a specific file path.

    Returns all entries with empty scope (project-wide) plus any
    scoped entries matching the file path prefix.
    """
    if not file_path:
        return entries
    result = []
    for e in entries:
        scope = e.get("scope", [])
        if not scope:
            result.append(e)  # project-wide entries always match
        elif any(file_path.startswith(s) or s.startswith(file_path) for s in scope):
            result.append(e)
    return result


# ── Formatting ────────────────────────────────────────────────────────────────

def format_entry(entry):
    """Format an entry as a multi-line human-readable string."""
    label = TYPE_LABELS.get(entry["type"], entry["type"].upper())
    status_str = STATUS_EMOJI.get(entry["status"], f" [{entry['status']}]")
    parts = [f"[{entry['id']}] {label}{status_str}"]
    parts.append(f"  {entry['content']}")
    scope = entry.get("scope", [])
    if scope:
        parts.append(f"  scope: {', '.join(scope)}")
    if entry.get("notes"):
        parts.append(f"  notes: {entry['notes']}")
    return "\n".join(parts)
