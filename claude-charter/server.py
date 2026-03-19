#!/usr/bin/env python3
"""claude-charter MCP server — normative project constitution store.

5 tools:
  charter_add(type, content, notes?)        add an entry
  charter_update(id, status?, content?,     modify or archive an entry
                 notes?)
  charter_query(filter)                     show entries by type/status/text/"all"
  charter_summary()                         full project constitution briefing
  charter_check(change_description)         conflict-check against invariants/constraints

Storage: .claude/charter.json in the working directory (override: CLAUDE_CHARTER_DIR).

Transport: stdio MCP (JSON-RPC 2.0). No third-party dependencies — stdlib only.
"""

import json
import sys
from datetime import datetime, timezone

import schema as _schema
import store as _store

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def charter_add(type_, content, notes=None, scope=None):
    data = _store.load()
    entry = _schema.make_entry(type_, content, notes, scope=scope)
    data["entries"].append(entry)
    _store.save(data)
    label = _schema.TYPE_LABELS.get(type_, type_.upper())
    scope_str = f" (scope: {', '.join(entry['scope'])})" if entry.get("scope") else ""
    return f"Added {label} [{entry['id']}]: {entry['content']}{scope_str}"


def charter_update(id_, status=None, content=None, notes=None):
    data = _store.load()
    entry = _store.find_entry(data, id_)
    if entry is None:
        raise ValueError(f"No entry with id '{id_}'")
    if status is not None:
        _schema.validate_status(status)
        entry["status"] = status
    if content is not None:
        content = content.strip()
        if not content:
            raise ValueError("content must not be empty")
        entry["content"] = content
    if notes is not None:
        entry["notes"] = notes.strip()
    entry["updated_at"] = datetime.now(timezone.utc).isoformat()
    _store.save(data)
    return f"Updated [{id_}]: {_schema.format_entry(entry)}"


def charter_query(filter_str="all"):
    data = _store.load()
    entries = data["entries"]
    if not entries:
        return "Charter is empty. Use charter_add to populate it."

    kind, value = _schema.normalize_filter(filter_str)

    if kind == "all":
        matched = entries
    elif kind == "type":
        matched = [e for e in entries if e["type"] == value]
    elif kind == "status":
        matched = [e for e in entries if e["status"] == value]
    else:  # text search
        q = value.lower()
        matched = [e for e in entries if q in e["content"].lower() or q in e.get("notes", "").lower()]

    if not matched:
        return f"No entries matching '{filter_str}'."

    lines = [f"Charter entries ({len(matched)}):\n"]
    for e in matched:
        lines.append(_schema.format_entry(e))
    return "\n".join(lines)


def charter_summary():
    data = _store.load()
    entries = data["entries"]
    project = data.get("project") or "(unnamed project)"

    if not entries:
        return f"Charter for {project} is empty. Use charter_add to establish invariants, constraints, goals, and non-goals."

    active = [e for e in entries if e["status"] == "active"]
    archived = [e for e in entries if e["status"] == "archived"]

    by_type = {}
    for e in active:
        by_type.setdefault(e["type"], []).append(e)

    lines = [f"# Charter: {project}", ""]

    type_order = ["invariant", "constraint", "contract", "goal", "non_goal"]
    for t in type_order:
        group = by_type.get(t, [])
        if not group:
            continue
        label = _schema.TYPE_LABELS[t]
        lines.append(f"## {label}S ({len(group)})")
        for e in group:
            note = f"  ↳ {e['notes']}" if e.get("notes") else ""
            lines.append(f"  [{e['id']}] {e['content']}{note}")
        lines.append("")

    if archived:
        lines.append(f"({len(archived)} archived entries not shown)")

    return "\n".join(lines)


def charter_check(change_description, file_path=None):
    data = _store.load()
    entries = data["entries"]

    # Filter to normative + active entries, optionally scoped to file
    normative = [
        e for e in entries
        if e["type"] in _schema.NORMATIVE_TYPES and e["status"] == "active"
    ]
    if file_path:
        normative = _schema.entries_for_scope(normative, file_path)

    if not normative:
        scope_str = f" for {file_path}" if file_path else ""
        return f"No active normative entries{scope_str}. Charter is empty for this scope."

    change_tokens = _schema.tokenize(change_description)
    conflicts = []
    warnings = []

    for e in normative:
        score = _schema.conflict_score(change_tokens, e["content"])
        if score >= 0.25:
            conflicts.append((score, e))
        elif score >= 0.10:
            warnings.append((score, e))

    conflicts.sort(key=lambda x: -x[0])
    warnings.sort(key=lambda x: -x[0])

    scope_str = f" (scope: {file_path})" if file_path else ""
    if not conflicts and not warnings:
        return f"No conflicts detected. Checked {len(normative)} active normative entries{scope_str}."

    lines = []
    if conflicts:
        lines.append(f"CONFLICTS ({len(conflicts)}):")
        for score, e in conflicts:
            label = _schema.TYPE_LABELS.get(e["type"], e["type"].upper())
            prohibition = " ⛔" if _schema.is_prohibition(e["content"]) else ""
            note = f" — {e['notes']}" if e.get("notes") else ""
            lines.append(f"  [{e['id']}] {label}{prohibition}: {e['content']}{note}  (overlap {score:.0%})")
        lines.append("")
    if warnings:
        lines.append(f"POSSIBLE CONFLICTS ({len(warnings)}):")
        for score, e in warnings:
            label = _schema.TYPE_LABELS.get(e["type"], e["type"].upper())
            prohibition = " ⛔" if _schema.is_prohibition(e["content"]) else ""
            note = f" — {e['notes']}" if e.get("notes") else ""
            lines.append(f"  [{e['id']}] {label}{prohibition}: {e['content']}{note}  (overlap {score:.0%})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP transport (JSON-RPC 2.0 over stdio)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "charter_add",
        "description": (
            "Add a new entry to the project charter. "
            "Types: invariant (must-always-be-true), constraint (implementation rule), "
            "non_goal (out of scope), contract (API guarantee), goal (active objective)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": _schema.ENTRY_TYPES,
                    "description": "Entry type.",
                },
                "content": {
                    "type": "string",
                    "description": "The charter statement.",
                },
                "notes": {
                    "type": "string",
                    "description": "Optional elaboration or rationale.",
                },
                "scope": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File/directory paths this entry applies to. Empty = project-wide.",
                },
            },
            "required": ["type", "content"],
        },
    },
    {
        "name": "charter_update",
        "description": "Modify or archive an existing charter entry by id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Entry id (8-char hex)."},
                "status": {
                    "type": "string",
                    "enum": _schema.ENTRY_STATUSES,
                    "description": "New status.",
                },
                "content": {"type": "string", "description": "Replacement content."},
                "notes": {"type": "string", "description": "Replacement notes."},
            },
            "required": ["id"],
        },
    },
    {
        "name": "charter_query",
        "description": (
            "Query charter entries. filter can be a type name, status, free-text search, "
            "or 'all'. Examples: 'invariants', 'active', 'stdlib', 'all'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Type, status, keyword, or 'all'.",
                    "default": "all",
                },
            },
            "required": [],
        },
    },
    {
        "name": "charter_summary",
        "description": (
            "Return the full project constitution briefing — all active entries grouped by type. "
            "Use at session start to orient yourself to project invariants and goals."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "charter_check",
        "description": (
            "Check a proposed change against active invariants, constraints, and contracts. "
            "Returns conflicts and possible conflicts with overlap scores. "
            "Call before structural changes, dependency additions, or API modifications."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "change_description": {
                    "type": "string",
                    "description": "Plain-language description of the proposed change.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional file path to scope the check to relevant entries only.",
                },
            },
            "required": ["change_description"],
        },
    },
    {
        "name": "charter_audit",
        "description": (
            "Report on charter health: coverage gaps, stale entries, type imbalances, "
            "and prohibition inventory. Use periodically to ensure the charter is well-formed."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
]


def charter_audit():
    """Report on charter health: coverage gaps, stale entries, imbalances."""
    data = _store.load()
    entries = data["entries"]
    active = [e for e in entries if e["status"] == "active"]

    if not active:
        return (
            "Charter is empty. Recommended starting entries:\n"
            "  1. charter_add('invariant', '<something that must always be true>')\n"
            "  2. charter_add('constraint', '<implementation rule>')\n"
            "  3. charter_add('non_goal', '<what this project deliberately does NOT do>')"
        )

    by_type = {}
    for e in active:
        by_type.setdefault(e["type"], []).append(e)

    lines = [f"Charter audit: {len(active)} active entries\n"]

    # Type distribution
    lines.append("TYPE DISTRIBUTION:")
    for t in _schema.ENTRY_TYPES:
        count = len(by_type.get(t, []))
        bar = "█" * count
        lines.append(f"  {_schema.TYPE_LABELS[t]:<12} {count:>2}  {bar}")
    lines.append("")

    # Coverage gaps
    gaps = []
    if "invariant" not in by_type:
        gaps.append("No INVARIANTS — what must always be true?")
    if "constraint" not in by_type:
        gaps.append("No CONSTRAINTS — what implementation rules exist?")
    if "non_goal" not in by_type:
        gaps.append("No NON-GOALS — what is explicitly out of scope?")
    if gaps:
        lines.append("⚠ COVERAGE GAPS:")
        for g in gaps:
            lines.append(f"  - {g}")
        lines.append("")

    # Scoped vs unscoped
    scoped = [e for e in active if e.get("scope")]
    unscoped = len(active) - len(scoped)
    lines.append(f"SCOPE: {len(scoped)} scoped, {unscoped} project-wide")

    # Prohibition detection
    prohibitions = [e for e in active if _schema.is_prohibition(e["content"])]
    if prohibitions:
        lines.append(f"\n⛔ PROHIBITIONS ({len(prohibitions)}):")
        for e in prohibitions:
            label = _schema.TYPE_LABELS.get(e["type"], e["type"].upper())
            lines.append(f"  [{e['id']}] {label}: {e['content']}")

    return "\n".join(lines)


def dispatch(method, params):
    if method == "charter_add":
        return charter_add(params["type"], params["content"],
                           params.get("notes"), scope=params.get("scope"))
    if method == "charter_update":
        return charter_update(
            params["id"],
            status=params.get("status"),
            content=params.get("content"),
            notes=params.get("notes"),
        )
    if method == "charter_query":
        return charter_query(params.get("filter", "all"))
    if method == "charter_summary":
        return charter_summary()
    if method == "charter_check":
        return charter_check(params["change_description"],
                             file_path=params.get("file_path"))
    if method == "charter_audit":
        return charter_audit()
    raise ValueError(f"Unknown method: {method}")


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle_request(req):
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    # ---- MCP lifecycle ----
    if method == "initialize":
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "claude-charter", "version": "2.0.0"},
            },
        })
        return

    if method == "notifications/initialized":
        return  # no response needed

    if method == "tools/list":
        send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        return

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_input = params.get("arguments", {})
        try:
            result_text = dispatch(tool_name, tool_input)
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False,
                },
            })
        except Exception as exc:
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            })
        return

    # Unknown method
    if req_id is not None:
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
            continue
        handle_request(req)


if __name__ == "__main__":
    main()
