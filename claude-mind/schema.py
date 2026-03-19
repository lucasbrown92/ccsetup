"""Node types, statuses, filtering, and formatting for claude-mind."""

import uuid
from datetime import datetime, timezone

NODE_TYPES = ["hypothesis", "fact", "question", "assumption", "ruled_out", "next_step"]
NODE_STATUSES = ["open", "confirmed", "refuted", "suspended", "escalated"]

# Plural / alternate forms accepted in mind_query
TYPE_ALIASES = {
    "assumptions": "assumption",
    "hypotheses": "hypothesis",
    "facts": "fact",
    "questions": "question",
    "next_steps": "next_step",
    "nextsteps": "next_step",
    "nextstep": "next_step",
    "ruled_outs": "ruled_out",
}


def make_node(type_, content, confidence=None, files=None, evidence_ids=None,
              notes=None, depends_on=None):
    """Create a new node dict. Raises ValueError on bad input."""
    if not content or not content.strip():
        raise ValueError("content must not be empty")
    if type_ not in NODE_TYPES:
        raise ValueError(f"Invalid type '{type_}'. Valid: {', '.join(NODE_TYPES)}")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            raise ValueError("confidence must be a number between 0 and 1")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": uuid.uuid4().hex[:12],   # 48-bit entropy (was 32-bit)
        "type": type_,
        "content": content.strip(),
        "confidence": confidence,
        "files": files if isinstance(files, list) else [],
        "evidence_ids": evidence_ids if isinstance(evidence_ids, list) else [],
        "depends_on": depends_on if isinstance(depends_on, list) else [],
        "status": "open",
        "notes": (notes or "").strip(),
        "created_at": now,
        "updated_at": now,
    }


def validate_status(status):
    """Raise ValueError if status is invalid, else return it."""
    if status not in NODE_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Valid: {', '.join(NODE_STATUSES)}")
    return status


def normalize_filter(filter_str):
    """Return (kind, value) where kind is 'all'|'type'|'status'|'text'."""
    fl = filter_str.strip().lower()
    if fl in ("all", ""):
        return "all", None
    if fl in TYPE_ALIASES:
        fl = TYPE_ALIASES[fl]
    if fl in NODE_TYPES:
        return "type", fl
    if fl in NODE_STATUSES:
        return "status", fl
    return "text", filter_str.strip()


# ── Filtering ─────────────────────────────────────────────────────────────────

def filter_nodes(nodes, type_=None, status=None):
    """Filter nodes by type and/or status."""
    result = nodes
    if type_:
        result = [n for n in result if n["type"] == type_]
    if status:
        result = [n for n in result if n["status"] == status]
    return result


def find_dependents(nodes, node_id):
    """Return all nodes whose depends_on includes node_id."""
    return [n for n in nodes if node_id in n.get("depends_on", [])]


def find_dependencies(nodes, node_id):
    """Return all nodes that node_id depends on."""
    node = next((n for n in nodes if n["id"] == node_id), None)
    if not node:
        return []
    dep_ids = node.get("depends_on", [])
    return [n for n in nodes if n["id"] in dep_ids]


# ── Formatting ────────────────────────────────────────────────────────────────

def format_node(node, all_nodes=None):
    """Format a node as a multi-line human-readable string.

    If all_nodes is provided, shows dependency relationships.
    """
    flag = " ⚠" if node["type"] == "assumption" else ""
    conf = f" [{node['confidence']:.0%}]" if node.get("confidence") is not None else ""
    status_str = f" ({node['status']})" if node.get("status", "open") != "open" else ""
    parts = [f"[{node['id']}] {node['type'].upper()}{flag}{conf}{status_str}"]
    parts.append(f"  {node['content']}")
    if node.get("files"):
        parts.append(f"  files: {', '.join(node['files'])}")
    if node.get("evidence_ids"):
        parts.append(f"  evidence: {_format_evidence(node['evidence_ids'])}")
    if node.get("depends_on") and all_nodes:
        deps = find_dependencies(all_nodes, node["id"])
        if deps:
            dep_strs = [f"[{d['id']}] {d['type']}" for d in deps]
            parts.append(f"  depends on: {', '.join(dep_strs)}")
    if all_nodes:
        dependents = find_dependents(all_nodes, node["id"])
        if dependents:
            dep_strs = [f"[{d['id']}] {d['type']}" for d in dependents]
            parts.append(f"  depended on by: {', '.join(dep_strs)}")
    if node.get("notes"):
        parts.append(f"  notes: {node['notes']}")
    return "\n".join(parts)


def _format_evidence(evidence_ids: list) -> str:
    """Format evidence IDs, labeling cross-tool references distinctively.

    Conventions:
      witness:<run_id>:<call_id>  → [W]witness:...  (execution evidence)
      witness:<run_id>            → [W]witness:...
      charter:<entry_id>          → [C]charter:...  (normative reference)
    """
    formatted = []
    for eid in evidence_ids:
        if eid.startswith("witness:"):
            formatted.append(f"[W]{eid}")
        elif eid.startswith("charter:"):
            formatted.append(f"[C]{eid}")
        else:
            formatted.append(eid)
    return ", ".join(formatted)
