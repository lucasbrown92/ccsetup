"""Entry types, statuses, and formatting for claude-charter."""

import re
import uuid
from datetime import datetime, timezone

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

# Words that indicate prohibition — entries with these get higher-weight matching
PROHIBITION_WORDS = frozenset({
    "never", "not", "no", "must not", "shall not", "cannot", "without",
    "avoid", "don't", "doesn't", "forbidden", "prohibited", "disallowed",
})


def make_entry(type_, content, notes=None, scope=None):
    """Create a new entry dict. Raises ValueError on bad input.

    scope: optional list of file/directory paths this entry applies to.
           If empty/None, entry applies to entire project.
    """
    if not content or not content.strip():
        raise ValueError("content must not be empty")
    if type_ not in ENTRY_TYPES:
        raise ValueError(f"Invalid type '{type_}'. Valid: {', '.join(ENTRY_TYPES)}")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": uuid.uuid4().hex[:12],   # 48-bit entropy (was 32-bit)
        "type": type_,
        "content": content.strip(),
        "notes": (notes or "").strip(),
        "scope": scope if isinstance(scope, list) else [],
        "status": "active",
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

def tokenize(text):
    """Lower-case word tokens for overlap scoring."""
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def is_prohibition(content):
    """True if the entry content expresses a prohibition (negative constraint)."""
    lower = content.lower()
    return any(w in lower for w in PROHIBITION_WORDS)


def conflict_score(change_tokens, entry_content):
    """Return overlap ratio [0,1] between change tokens and entry content.

    Prohibition entries get a 1.5x boost — violating a "never do X" is
    more dangerous than overlapping with a "prefer X".
    """
    entry_tokens = tokenize(entry_content)
    if not entry_tokens:
        return 0.0
    overlap = change_tokens & entry_tokens
    base = len(overlap) / len(entry_tokens)
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
