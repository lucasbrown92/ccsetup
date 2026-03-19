#!/usr/bin/env python3
"""
claude-mind: persistent investigation reasoning board

MCP server (stdlib only, stdio transport). Stores reasoning nodes in
.claude/mind.json in the current working directory (the target project).

11 tools (6 core + 1 cross-tool + 4 cognitive):
  mind_open, mind_add, mind_update, mind_query, mind_summary, mind_resolve
  mind_import_witness  — create a fact node from a claude-witness run
  mind_recall, mind_sweep, mind_replay, mind_export_watch — cognitive extensions

Usage:
  python server.py                          # run as MCP server
  CLAUDE_MIND_DIR=.mydir python server.py   # custom store directory

Add to your project's .mcp.json:
  {
    "mcpServers": {
      "claude-mind": {
        "command": "python",
        "args": ["/absolute/path/to/claude-mind/server.py"]
      }
    }
  }
"""

VERSION = "1.0.1"

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make sibling modules importable when server.py is invoked from any CWD
sys.path.insert(0, str(Path(__file__).parent))

from schema import (
    NODE_TYPES,
    NODE_STATUSES,
    make_node,
    validate_status,
    normalize_filter,
    format_node,
    filter_nodes,
    find_dependents,
    find_dependencies,
    search_history,
    compute_risk_score,
)
from store import load, save, find_node


# ── MCP wire protocol (newline-delimited JSON over stdio) ─────────────────────

def _read():
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError as e:
        _log(f"JSON parse error: {e}")
        return None


def _write(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _log(msg):
    sys.stderr.write(f"[claude-mind] {msg}\n")
    sys.stderr.flush()


def _respond(msg_id, result):
    _write({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _error_response(msg_id, code, message):
    _write({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}})


def _tool_result(text, is_error=False):
    result = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    return result


# ── Tool schemas ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "mind_open",
        "description": (
            "Open or resume an investigation. Returns a state summary. "
            "If a different investigation is currently open, it is archived and the new one begins. "
            "Call this at the start of any complex debugging, analysis, or multi-step task."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title for this investigation (e.g. 'auth regression 2026-03-17')",
                }
            },
            "required": ["title"],
        },
    },
    {
        "name": "mind_add",
        "description": (
            "Add a reasoning node to the current investigation. "
            "Types: hypothesis (candidate explanation, testable), "
            "fact (confirmed finding with evidence), "
            "question (open probe to investigate), "
            "assumption (treating as true, UNVERIFIED — flagged as risk), "
            "ruled_out (explicitly eliminated path + reason), "
            "next_step (concrete action queued)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": NODE_TYPES,
                    "description": "Node type",
                },
                "content": {
                    "type": "string",
                    "description": "The content of this node",
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Confidence 0–1 (most useful for hypotheses)",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Relevant file paths",
                },
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Cross-tool evidence refs. Conventions: witness:<run_id>:<call_id>, charter:<entry_id>, retina:<capture_id>, mind:<investigation_id>:<node_id>",
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Node IDs this reasoning depends on (e.g. hypothesis depends on assumption)",
                },
            },
            "required": ["type", "content"],
        },
    },
    {
        "name": "mind_update",
        "description": (
            "Update the status or notes on an existing node. "
            "Use to confirm/refute hypotheses, resolve questions, suspend or escalate assumptions. "
            "Statuses: open, confirmed, refuted, suspended, escalated."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "The node ID from mind_add or mind_query output",
                },
                "status": {
                    "type": "string",
                    "enum": NODE_STATUSES,
                    "description": "New status for this node",
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or evidence to attach (appended to existing notes)",
                },
            },
            "required": ["node_id", "status"],
        },
    },
    {
        "name": "mind_query",
        "description": (
            "Query nodes in the current investigation. "
            "Filter options: a type name (hypothesis, fact, question, assumption, ruled_out, next_step), "
            "a status (open, confirmed, refuted, suspended, escalated), 'all', or free-text search."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filter": {
                    "type": "string",
                    "description": "Type name, status, 'all', or search text",
                }
            },
            "required": ["filter"],
        },
    },
    {
        "name": "mind_summary",
        "description": (
            "Get a ≤15-line recovery briefing for the current investigation. "
            "Use after context compaction or at session start to restore full investigation state. "
            "Shows: title, open hypotheses with confidence, flagged assumptions, "
            "ruled-out paths, queued next steps."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mind_resolve",
        "description": (
            "Close the current investigation with a conclusion. "
            "Archives the full investigation and all nodes to history. Clears the active state."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "conclusion": {
                    "type": "string",
                    "description": "The final conclusion or resolution of this investigation",
                },
                "node_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs of nodes that support this conclusion (optional)",
                },
            },
            "required": ["conclusion"],
        },
    },
]


# ── Tool implementations ──────────────────────────────────────────────────────

def tool_mind_open(args):
    title = (args.get("title") or "").strip()
    if not title:
        return _tool_result("Error: title is required.", is_error=True)

    data = load()
    inv = data.get("investigation")

    if inv and inv["status"] == "open":
        if inv["title"].lower() == title.lower():
            return _tool_result(_format_resume_summary(data))
        # Archive current investigation before opening the new one
        data.setdefault("history", []).append({
            "investigation": dict(inv),
            "nodes": list(data["nodes"]),
        })
        data["nodes"] = []
        data["investigation"] = None

    now = datetime.now(timezone.utc).isoformat()
    data["investigation"] = {
        "id": uuid.uuid4().hex[:8],
        "title": title,
        "status": "open",
        "opened_at": now,
        "resolved_at": None,
        "conclusion": None,
    }
    save(data)
    return _tool_result(
        f"Investigation opened: {title}\n\n"
        "No nodes yet. Use mind_add to begin recording your reasoning.\n"
        "Tip: start with what you know (fact), what you're testing (hypothesis), "
        "and what you're assuming (assumption)."
    )


def tool_mind_add(args):
    data = load()
    if not data.get("investigation") or data["investigation"]["status"] != "open":
        return _tool_result("No active investigation. Call mind_open first.", is_error=True)

    depends_on = args.get("depends_on") or []
    # Validate depends_on references exist
    if depends_on:
        for dep_id in depends_on:
            if not find_node(data, dep_id):
                return _tool_result(
                    f"depends_on references unknown node '{dep_id}'. "
                    f"Use mind_query('all') to list valid node IDs.",
                    is_error=True,
                )

    try:
        node = make_node(
            type_=args.get("type", ""),
            content=args.get("content", ""),
            confidence=args.get("confidence"),
            files=args.get("files"),
            evidence_ids=args.get("evidence_ids"),
            depends_on=depends_on,
        )
    except ValueError as e:
        return _tool_result(f"Validation error: {e}", is_error=True)

    data["nodes"].append(node)
    save(data)

    flag = (
        " ⚠ flagged as unverified risk — verify before building on this"
        if node["type"] == "assumption"
        else ""
    )
    conf_str = f" (confidence: {node['confidence']:.0%})" if node["confidence"] is not None else ""
    dep_str = f"\n  depends on: {', '.join(depends_on)}" if depends_on else ""
    return _tool_result(
        f"Added [{node['id']}] {node['type']}{conf_str}: {node['content']}{flag}{dep_str}"
    )


def tool_mind_update(args):
    node_id = (args.get("node_id") or "").strip()
    status = (args.get("status") or "").strip()
    notes = (args.get("notes") or "").strip()

    if not node_id:
        return _tool_result("Error: node_id is required.", is_error=True)

    try:
        validate_status(status)
    except ValueError as e:
        return _tool_result(f"Validation error: {e}", is_error=True)

    data = load()
    node = find_node(data, node_id)
    if not node:
        return _tool_result(
            f"Node '{node_id}' not found. Use mind_query('all') to list current nodes.",
            is_error=True,
        )

    old_status = node["status"]
    node["status"] = status
    if notes:
        existing = node.get("notes", "")
        node["notes"] = f"{existing}\n{notes}".strip() if existing else notes
    node["updated_at"] = datetime.now(timezone.utc).isoformat()
    save(data)

    return _tool_result(
        f"Updated [{node_id}]: {old_status} → {status}\n"
        f"Content: {node['content']}"
        + (f"\nNotes: {node['notes']}" if node.get("notes") else "")
    )


def tool_mind_query(args):
    filter_str = (args.get("filter") or "all").strip()

    data = load()
    if not data.get("investigation"):
        return _tool_result("No active investigation. Call mind_open first.")

    nodes = data["nodes"]
    kind, value = normalize_filter(filter_str)

    if kind == "all":
        matched = nodes
    elif kind == "type":
        matched = [n for n in nodes if n["type"] == value]
    elif kind == "status":
        matched = [n for n in nodes if n["status"] == value]
    else:  # free text
        fl = value.lower()
        matched = [
            n for n in nodes
            if fl in n["content"].lower() or fl in n.get("notes", "").lower()
        ]

    if not matched:
        return _tool_result(f"No nodes matching '{filter_str}'.")

    title = data["investigation"]["title"]
    lines = [f"Investigation: {title}", f"Filter: {filter_str} — {len(matched)} node(s)\n"]
    all_nodes = data["nodes"]
    for node in matched:
        lines.append(format_node(node, all_nodes=all_nodes))
        lines.append("")

    return _tool_result("\n".join(lines).rstrip())


def tool_mind_summary(args):
    data = load()
    inv = data.get("investigation")

    if not inv:
        history = data.get("history", [])
        if history:
            last = history[-1]["investigation"]
            return _tool_result(
                f"No active investigation.\n"
                f"Last archived: {last['title']} ({last.get('status', 'unknown')})\n"
                f"Use mind_open to start a new investigation."
            )
        return _tool_result("No investigations found. Use mind_open to start one.")

    nodes = data["nodes"]
    hypotheses  = filter_nodes(nodes, type_="hypothesis",  status="open")
    assumptions = filter_nodes(nodes, type_="assumption",  status="open")
    ruled_out   = filter_nodes(nodes, type_="ruled_out")
    next_steps  = filter_nodes(nodes, type_="next_step",   status="open")
    conf_facts  = filter_nodes(nodes, type_="fact",        status="confirmed")
    open_qs     = filter_nodes(nodes, type_="question",    status="open")

    # Status counts for the header
    by_status = {}
    for n in nodes:
        by_status[n["status"]] = by_status.get(n["status"], 0) + 1
    status_str = ", ".join(f"{v} {k}" for k, v in sorted(by_status.items()))

    lines = [
        "═══ MIND SUMMARY ═══",
        f"Investigation: {inv['title']}",
        f"Opened: {inv['opened_at'][:10]}  |  {len(nodes)} nodes ({status_str})",
    ]

    # NEVER truncate assumptions — these are the highest-risk items
    if assumptions:
        now = datetime.now(timezone.utc)
        assumption_risks = [(compute_risk_score(n, nodes, now), n) for n in assumptions]
        assumption_risks.sort(key=lambda x: -x[0]["risk_score"])
        lines.append(f"\n⚠  ASSUMPTIONS — unverified risks ({len(assumptions)}):")
        for risk_info, n in assumption_risks:
            deps = risk_info["dependent_count"]
            age = risk_info["age_hours"]
            risk_label = " ← HIGH RISK" if risk_info["risk_score"] > 5.0 else ""
            dep_str = f", {deps} deps" if deps else ""
            lines.append(f"  [{n['id']}] {n['content']} ({age:.1f}h old{dep_str}){risk_label}")

    if hypotheses:
        lines.append(f"\nHYPOTHESES — open ({len(hypotheses)}):")
        for n in sorted(hypotheses, key=lambda x: x.get("confidence") or 0, reverse=True):
            conf = f" [{n['confidence']:.0%}]" if n.get("confidence") is not None else ""
            lines.append(f"  [{n['id']}]{conf} {n['content']}")

    # NEVER truncate open questions — they're action items
    if open_qs:
        lines.append(f"\nOPEN QUESTIONS ({len(open_qs)}):")
        for n in open_qs:
            lines.append(f"  [{n['id']}] {n['content']}")

    if next_steps:
        lines.append(f"\nNEXT STEPS ({len(next_steps)}):")
        for n in next_steps:
            lines.append(f"  [{n['id']}] {n['content']}")

    # OK to truncate confirmed facts and ruled-out — they're settled knowledge
    if conf_facts:
        lines.append(f"\nCONFIRMED FACTS ({len(conf_facts)}):")
        for n in conf_facts[-5:]:
            lines.append(f"  [{n['id']}] {n['content']}")
        if len(conf_facts) > 5:
            lines.append(f"  ... +{len(conf_facts) - 5} more (use mind_query('facts') for all)")

    if ruled_out:
        lines.append(f"\nRULED OUT ({len(ruled_out)}):")
        for n in ruled_out[-3:]:
            lines.append(f"  [{n['id']}] {n['content']}")
        if len(ruled_out) > 3:
            lines.append(f"  ... +{len(ruled_out) - 3} more")

    if not nodes:
        lines.append("\nNo nodes yet. Use mind_add to begin.")

    return _tool_result("\n".join(lines))


def tool_mind_resolve(args):
    conclusion = (args.get("conclusion") or "").strip()
    node_ids = args.get("node_ids") or []

    if not conclusion:
        return _tool_result("Error: conclusion is required.", is_error=True)

    data = load()
    inv = data.get("investigation")
    if not inv or inv["status"] != "open":
        return _tool_result("No active open investigation.", is_error=True)

    now = datetime.now(timezone.utc).isoformat()
    inv["status"] = "resolved"
    inv["resolved_at"] = now
    inv["conclusion"] = conclusion
    node_count = len(data["nodes"])

    data.setdefault("history", []).append({
        "investigation": dict(inv),
        "nodes": list(data["nodes"]),
        "supporting_node_ids": [nid for nid in node_ids if find_node(data, nid)],
    })
    data["investigation"] = None
    data["nodes"] = []
    save(data)

    return _tool_result(
        f"Investigation resolved: {inv['title']}\n"
        f"Conclusion: {conclusion}\n"
        f"Archived {node_count} node(s) to history.\n"
        f"Use mind_open to start a new investigation."
    )


def tool_mind_graph(args):
    """Show the dependency graph of reasoning nodes."""
    data = load()
    if not data.get("investigation"):
        return _tool_result("No active investigation. Call mind_open first.")

    nodes = data["nodes"]
    if not nodes:
        return _tool_result("No nodes yet.")

    node_by_id = {n["id"]: n for n in nodes}

    # Find root nodes (not depended on by anyone)
    has_parent = set()
    for n in nodes:
        for dep_id in n.get("depends_on", []):
            has_parent.add(n["id"])

    roots = [n for n in nodes if n["id"] not in has_parent]
    orphans = [n for n in nodes if not n.get("depends_on") and n["id"] not in has_parent]

    lines = [
        f"═══ REASONING GRAPH ═══",
        f"Investigation: {data['investigation']['title']}",
        f"{len(nodes)} nodes, {sum(1 for n in nodes if n.get('depends_on'))} with dependencies",
        "",
    ]

    # Show dependency chains
    shown = set()

    def _render(node, indent=0):
        if node["id"] in shown:
            lines.append(f"{'  ' * indent}[{node['id']}] (see above)")
            return
        shown.add(node["id"])
        flag = " ⚠" if node["type"] == "assumption" else ""
        conf = f" [{node['confidence']:.0%}]" if node.get("confidence") is not None else ""
        status = f" ({node['status']})" if node["status"] != "open" else ""
        lines.append(f"{'  ' * indent}[{node['id']}] {node['type'].upper()}{flag}{conf}{status}")
        lines.append(f"{'  ' * indent}  {node['content']}")
        # Find children (nodes that depend on this one)
        children = find_dependents(nodes, node["id"])
        for child in children:
            _render(child, indent + 1)

    # Render from roots
    for root in roots:
        if root["id"] not in shown:
            _render(root)
            lines.append("")

    # Any nodes not in chains
    unchained = [n for n in nodes if n["id"] not in shown]
    if unchained:
        lines.append("STANDALONE NODES:")
        for n in unchained:
            flag = " ⚠" if n["type"] == "assumption" else ""
            conf = f" [{n['confidence']:.0%}]" if n.get("confidence") is not None else ""
            lines.append(f"  [{n['id']}] {n['type'].upper()}{flag}{conf} {n['content']}")

    return _tool_result("\n".join(lines))


# ── Cognitive tools ───────────────────────────────────────────────────────────

def tool_mind_recall(args):
    query = (args.get("query") or "").strip()
    if not query:
        return _tool_result("Error: query is required.", is_error=True)

    limit = args.get("limit", 5)
    node_types = args.get("node_types")

    data = load()
    results = search_history(data, query, limit=limit, node_types=node_types)

    if not results:
        history_count = len(data.get("history", []))
        return _tool_result(
            f"No matches for '{query}' in {history_count} archived investigation(s).\n"
            "Try broader search terms or check mind_query for the active investigation."
        )

    lines = [f"RECALL: '{query}' — {len(results)} match(es)\n"]
    for r in results:
        inv = r["investigation"]
        nodes = r["matching_nodes"]
        resolved = inv.get("resolved_at", "")[:10] if inv.get("resolved_at") else "unresolved"
        lines.append(f"━ {inv.get('title', '?')}  ({resolved})")
        if inv.get("conclusion"):
            lines.append(f"  conclusion: {inv['conclusion']}")
        for n in nodes:
            status_str = f" ({n['status']})" if n.get("status", "open") != "open" else ""
            lines.append(f"  [{n['id']}] {n['type'].upper()}{status_str}: {n['content']}")
        lines.append("")

    return _tool_result("\n".join(lines).rstrip())


def tool_mind_sweep(args):
    data = load()
    if not data.get("investigation") or data["investigation"]["status"] != "open":
        return _tool_result("No active investigation. Call mind_open first.", is_error=True)

    nodes = data["nodes"]
    now = datetime.now(timezone.utc)

    # Stale assumptions (>2h old, still open)
    open_assumptions = [n for n in nodes if n["type"] == "assumption" and n["status"] == "open"]
    risks = [compute_risk_score(n, nodes, now) for n in open_assumptions]
    risks.sort(key=lambda r: -r["risk_score"])

    stale = [r for r in risks if r["age_hours"] > 2.0]
    high_risk = [r for r in risks if r["dependent_count"] >= 2]

    # Overdue next_steps (>1h old, still open)
    open_steps = [n for n in nodes if n["type"] == "next_step" and n["status"] == "open"]
    overdue_steps = []
    for n in open_steps:
        created = n.get("created_at", "")
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_h = (now - created_dt).total_seconds() / 3600
        except (ValueError, TypeError):
            age_h = 0.0
        if age_h > 1.0:
            overdue_steps.append((age_h, n))
    overdue_steps.sort(key=lambda x: -x[0])

    lines = ["═══ MIND SWEEP ═══", ""]

    if not stale and not high_risk and not overdue_steps:
        lines.append("All clear — no stale assumptions, no high-risk nodes, no overdue steps.")
        return _tool_result("\n".join(lines))

    if stale:
        lines.append(f"⚠  STALE ASSUMPTIONS — unverified >2h ({len(stale)}):")
        for r in stale:
            lines.append(
                f"  [{r['node_id']}] {r['content']}"
                f"  ({r['age_hours']:.1f}h old, {r['dependent_count']} deps, risk={r['risk_score']:.1f})"
            )
        lines.append("")

    if high_risk:
        lines.append(f"🔴 HIGH-RISK — ≥2 dependents ({len(high_risk)}):")
        for r in high_risk:
            lines.append(
                f"  [{r['node_id']}] {r['content']}"
                f"  ({r['dependent_count']} deps, {r['age_hours']:.1f}h old, risk={r['risk_score']:.1f})"
            )
        lines.append("")

    if overdue_steps:
        lines.append(f"OVERDUE NEXT STEPS — open >1h ({len(overdue_steps)}):")
        for age_h, n in overdue_steps:
            lines.append(f"  [{n['id']}] {n['content']}  ({age_h:.1f}h old)")
        lines.append("")

    return _tool_result("\n".join(lines).rstrip())


def tool_mind_replay(args):
    investigation_id = (args.get("investigation_id") or "").strip()

    data = load()

    if investigation_id:
        # Search history for matching investigation
        target = None
        for entry in data.get("history", []):
            inv = entry.get("investigation", {})
            if inv.get("id", "").startswith(investigation_id) or investigation_id in inv.get("title", "").lower():
                target = entry
                break
        if not target:
            return _tool_result(f"No archived investigation matching '{investigation_id}'.", is_error=True)
        inv = target["investigation"]
        nodes = target.get("nodes", [])
    else:
        # Use current investigation
        inv = data.get("investigation")
        if not inv:
            return _tool_result("No active investigation. Provide investigation_id for archived ones.", is_error=True)
        nodes = data["nodes"]

    if not nodes:
        return _tool_result(f"Investigation '{inv.get('title', '?')}' has no nodes.")

    # Sort by created_at
    opened_at = inv.get("opened_at", "")
    try:
        base_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        base_dt = None

    sorted_nodes = sorted(nodes, key=lambda n: n.get("created_at", ""))

    lines = [
        f"═══ REPLAY: {inv.get('title', '?')} ═══",
        f"Opened: {opened_at[:16] if opened_at else '?'}",
        "",
    ]

    for n in sorted_nodes:
        created = n.get("created_at", "")
        # Compute relative time
        if base_dt and created:
            try:
                node_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                delta_min = (node_dt - base_dt).total_seconds() / 60
                t_str = f"T+{delta_min:.0f}m"
            except (ValueError, TypeError):
                t_str = "T+?m"
        else:
            t_str = "T+?m"

        status_change = ""
        if n.get("status", "open") != "open":
            status_change = f" -> {n['status'].upper()}"

        conf = f" ({n['confidence']:.0%})" if n.get("confidence") is not None else ""
        lines.append(f"  {t_str:>8}  [{n['id']}] {n['type'].upper()}{conf} added: {n['content']}{status_change}")
        if n.get("notes"):
            lines.append(f"           notes: {n['notes'][:80]}")

    if inv.get("conclusion"):
        resolved = inv.get("resolved_at", "")
        if base_dt and resolved:
            try:
                res_dt = datetime.fromisoformat(resolved.replace("Z", "+00:00"))
                delta_min = (res_dt - base_dt).total_seconds() / 60
                t_str = f"T+{delta_min:.0f}m"
            except (ValueError, TypeError):
                t_str = "T+?m"
        else:
            t_str = "T+?m"
        lines.append(f"  {t_str:>8}  RESOLVED: {inv['conclusion']}")

    return _tool_result("\n".join(lines))


def tool_mind_export_watch(args):
    assumption_ids = args.get("assumption_ids") or []

    data = load()
    if not data.get("investigation") or data["investigation"]["status"] != "open":
        return _tool_result("No active investigation. Call mind_open first.", is_error=True)

    import re as _re
    nodes = data["nodes"]

    # Select nodes to extract watches from
    if assumption_ids:
        targets = [n for n in nodes if n["id"] in assumption_ids]
    else:
        targets = [n for n in nodes if n["type"] in ("assumption", "hypothesis") and n["status"] == "open"]

    if not targets:
        return _tool_result("No open assumptions or hypotheses to generate watches from.")

    watches = []
    for n in targets:
        text = f"{n.get('content', '')} {n.get('notes', '')}"
        # Extract function-like identifiers
        fn_calls = _re.findall(r'\b([a-z_]\w*)\(', text)
        methods = _re.findall(r'\b([A-Z]\w+\.\w+)', text)
        files = n.get("files", [])

        functions = list(set(fn_calls + [m.split(".")[-1] for m in methods]))

        if files or functions:
            watches.append({
                "files": files,
                "functions": functions[:5],
                "reason": f"[{n['id']}] {n['type']}: {n['content'][:60]}",
            })

    if not watches:
        return _tool_result(
            "No file paths or function names found in open assumptions/hypotheses.\n"
            "Tip: add files= when creating nodes with mind_add to enable directed observation."
        )

    # Format as JSON for structured output
    import json as _json
    output = {"watches": watches}

    lines = [
        "═══ EXPORT WATCH LIST ═══",
        f"{len(watches)} watch(es) from {len(targets)} node(s)\n",
        "Use these to guide witness_traces() calls after the next test run:",
        "",
        _json.dumps(output, indent=2),
    ]

    return _tool_result("\n".join(lines))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_resume_summary(data):
    inv = data["investigation"]
    nodes = data["nodes"]
    open_nodes = [n for n in nodes if n["status"] == "open"]
    assumptions = [n for n in nodes if n["type"] == "assumption" and n["status"] == "open"]

    lines = [
        f"Resuming: {inv['title']}",
        f"Opened: {inv['opened_at'][:10]}  |  {len(nodes)} nodes ({len(open_nodes)} open)",
    ]
    if assumptions:
        lines.append(f"\n⚠  {len(assumptions)} open assumption(s) — unverified risks:")
        for n in assumptions:
            lines.append(f"  [{n['id']}] {n['content']}")
    elif nodes:
        lines.append("\nNo unverified assumptions. Call mind_summary for full state.")
    return "\n".join(lines)


# ── Cross-tool: mind_import_witness ──────────────────────────────────────────

def _load_witness_run(run_id: str | None) -> dict:
    """Load a witness run from .claude/witness/. Raises ValueError if not found."""
    witness_dir = Path(os.environ.get("CLAUDE_WITNESS_DIR", ".claude/witness"))
    if not witness_dir.exists():
        raise ValueError(
            f"No witness store found at {witness_dir.absolute()}. "
            "Run tests with: pytest --witness"
        )
    files = sorted(witness_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise ValueError("No witness runs found. Run: pytest --witness")
    if run_id:
        for f in files:
            if f.stem.startswith(run_id) or run_id in f.stem:
                with open(f, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        raise ValueError(f"No witness run matching '{run_id}'")
    with open(files[0], "r", encoding="utf-8") as fh:
        return json.load(fh)


def tool_mind_import_witness(args):
    """Create a fact node in the current investigation from witness evidence."""
    fn_name = (args.get("fn_name") or "").strip()
    run_id = (args.get("run_id") or "").strip() or None

    if not fn_name:
        return _tool_result("Error: fn_name is required.", is_error=True)

    data = load()
    if not data.get("investigation") or data["investigation"]["status"] != "open":
        return _tool_result("No active investigation. Call mind_open first.", is_error=True)

    try:
        run = _load_witness_run(run_id)
    except ValueError as e:
        return _tool_result(f"Error: {e}", is_error=True)

    calls = run.get("calls", [])
    rid = run.get("run_id", "?")
    fn_lower = fn_name.lower()
    matched = [c for c in calls if fn_lower in c["fn"].lower()]

    if not matched:
        all_fns = sorted({c["fn"] for c in calls})
        sample = ", ".join(all_fns[:8])
        return _tool_result(
            f"No calls to '{fn_name}' found in witness run {rid}.\n"
            f"Functions captured in this run: {sample}"
            + (" ..." if len(all_fns) > 8 else "")
        )

    total = len(matched)
    with_exception = sum(1 for c in matched if c.get("exception"))
    normal = total - with_exception
    files_seen = sorted({c["file"] for c in matched if c.get("file")})

    # Build summary content
    parts = [f"witness:{rid} — {fn_name} called {total}x"]
    if normal:
        parts.append(f"{normal} normal")
    if with_exception:
        parts.append(f"{with_exception} raised exception")
    if matched[0].get("args"):
        sample_args = ", ".join(f"{k}={v!r}" for k, v in list(matched[0]["args"].items())[:3])
        parts.append(f"sample args: ({sample_args})")

    content = "; ".join(parts)
    evidence_ids = [f"witness:{rid}:{matched[0]['id']}"]

    try:
        node = make_node(
            type_="fact",
            content=content,
            files=files_seen[:5],
            evidence_ids=evidence_ids,
        )
    except ValueError as e:
        return _tool_result(f"Validation error: {e}", is_error=True)

    data["nodes"].append(node)
    save(data)

    return _tool_result(
        f"Imported witness evidence as FACT [{node['id']}]:\n"
        f"  {content}\n"
        f"  evidence: [W]{evidence_ids[0]}\n\n"
        f"Use mind_update({node['id']!r}, 'confirmed', notes='...') "
        f"to mark this fact confirmed after reviewing the trace."
    )


# ── Tool schema additions ─────────────────────────────────────────────────────

TOOLS_EXTRA = [
    {
        "name": "mind_graph",
        "description": (
            "Show the dependency graph of reasoning nodes. "
            "Visualizes how hypotheses depend on assumptions, which facts support which conclusions. "
            "Use to trace reasoning chains and spot assumptions with many dependents (high-risk)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mind_recall",
        "description": (
            "Search archived investigations for similar past work. "
            "Returns matching investigations with titles, conclusions, and relevant nodes. "
            "Use this at the start of any investigation to check if a similar issue was solved before."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms to match against past investigations (titles, conclusions, node content)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 5).",
                    "default": 5,
                },
                "node_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter to specific node types (e.g. ['hypothesis', 'fact']). Omit for all types.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "mind_sweep",
        "description": (
            "Risk detection for the current investigation. "
            "Reports: STALE ASSUMPTIONS (>2h unverified), HIGH-RISK (many dependents), "
            "OVERDUE NEXT_STEPS (>1h old, still open). "
            "Use periodically during long investigations to catch forgotten risks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mind_replay",
        "description": (
            "Show how an investigation's reasoning progressed as a timeline. "
            "Displays nodes in chronological order with relative timestamps from investigation start. "
            "Use to understand the strategy that led to a conclusion — the playbook for similar future problems."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "investigation_id": {
                    "type": "string",
                    "description": "ID or title substring of an archived investigation. Omit for current investigation.",
                },
            },
        },
    },
    {
        "name": "mind_export_watch",
        "description": (
            "Generate a structured watch list from open assumptions and hypotheses. "
            "Extracts file paths and function names from node content to guide which "
            "witness_traces() calls to make after the next test run. "
            "Closes the observe→reason→observe loop."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "assumption_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific node IDs to extract watches from. Omit for all open assumptions/hypotheses.",
                },
            },
        },
    },
]

TOOLS_CROSS = [
    {
        "name": "mind_import_witness",
        "description": (
            "Import execution evidence from a claude-witness run into the current investigation. "
            "Creates a FACT node linking to the witness run ID and call ID. "
            "Use this to bridge witness traces into your reasoning board: "
            "e.g. after witness_traces() confirms/refutes an assumption, import the evidence. "
            "Reads .claude/witness/ — requires pytest --witness to have been run."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "fn_name": {
                    "type": "string",
                    "description": "Function name to import evidence for (substring match).",
                },
                "run_id": {
                    "type": "string",
                    "description": "Witness run ID to import from. Omit for latest run.",
                },
            },
            "required": ["fn_name"],
        },
    },
]


# ── MCP message router ────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "mind_open":            tool_mind_open,
    "mind_add":             tool_mind_add,
    "mind_update":          tool_mind_update,
    "mind_query":           tool_mind_query,
    "mind_summary":         tool_mind_summary,
    "mind_resolve":         tool_mind_resolve,
    "mind_graph":           tool_mind_graph,
    "mind_import_witness":  tool_mind_import_witness,
    "mind_recall":          tool_mind_recall,
    "mind_sweep":           tool_mind_sweep,
    "mind_replay":          tool_mind_replay,
    "mind_export_watch":    tool_mind_export_watch,
}


def handle_tool_call(msg_id, params):
    name = params.get("name", "")
    arguments = params.get("arguments") or {}
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        _respond(msg_id, _tool_result(f"Unknown tool: {name}", is_error=True))
        return
    try:
        _respond(msg_id, handler(arguments))
    except Exception as e:
        _log(f"Tool error ({name}): {e}")
        _respond(msg_id, _tool_result(f"Internal error in {name}: {e}", is_error=True))


def handle_message(msg):
    if not msg:
        return
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "initialize":
        _respond(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "claude-mind", "version": VERSION},
        })
    elif method in ("initialized", "notifications/cancelled", "notifications/progress"):
        pass  # notifications — no response needed
    elif method == "ping":
        _respond(msg_id, {})
    elif method == "tools/list":
        _respond(msg_id, {"tools": TOOLS + TOOLS_EXTRA + TOOLS_CROSS})
    elif method == "tools/call":
        handle_tool_call(msg_id, params)
    else:
        if msg_id is not None:
            _error_response(msg_id, -32601, f"Method not found: {method}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    store_hint = Path(".claude/mind.json").absolute()
    _log(f"claude-mind v2.0.0 starting  (store: {store_hint})")
    while True:
        try:
            msg = _read()
        except (KeyboardInterrupt, EOFError):
            break
        if msg is None:
            break
        try:
            handle_message(msg)
        except Exception as e:
            _log(f"Unhandled error: {e}")


if __name__ == "__main__":
    main()
