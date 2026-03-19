#!/usr/bin/env python3
"""claude-ledger extensions — dynamic MCP server registration.

Stores extension data in .claude/ledger-extensions.json (project-level).
Merged at runtime with hardcoded catalog/router/health data.

Each extension entry:
{
    "mcp_key": "vele",
    "catalog": [
        {"name": "vele/ask", "params": "question, mode?", "when": "Query VELE..."}
    ],
    "router": {
        "keywords": ["knowledge", "epistemic"],
        "intent_phrases": ["what does vele know"],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "VELE epistemic engine..."
    },
    "health": {
        "type": "binary",         # binary | bundled | none
        "binary": "vele"          # for type=binary
    },
    "layer": 1,
    "requirements": {}            # optional TOOL_REQUIREMENTS entry
}
"""

import json
from pathlib import Path


def _ext_path() -> Path:
    return Path(".claude") / "ledger-extensions.json"


def load_extensions() -> dict[str, dict]:
    """Load all extensions. Returns {mcp_key: extension_data}."""
    p = _ext_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("servers", {})
    except (json.JSONDecodeError, OSError):
        return {}


def _save_extensions(servers: dict[str, dict]) -> None:
    p = _ext_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"servers": servers}, indent=2), encoding="utf-8")


def register(mcp_key: str, catalog: list[dict], router: dict | None = None,
             health: dict | None = None, layer: int = 6,
             requirements: dict | None = None) -> str:
    """Register or update an MCP server extension.

    Args:
        mcp_key: MCP server key (e.g. "vele")
        catalog: List of {name, params, when} tool entries
        router: {keywords, intent_phrases, anti_keywords, weight, description}
        health: {type: "binary"|"bundled"|"none", binary?: str}
        layer: Layer number (0-6, default 6)
        requirements: Optional TOOL_REQUIREMENTS-format entry

    Returns:
        Status message
    """
    servers = load_extensions()
    is_update = mcp_key in servers

    entry = {
        "mcp_key": mcp_key,
        "catalog": catalog,
        "router": router or {},
        "health": health or {"type": "none"},
        "layer": layer,
    }
    if requirements:
        entry["requirements"] = requirements

    servers[mcp_key] = entry
    _save_extensions(servers)

    verb = "Updated" if is_update else "Registered"
    return f"{verb} {mcp_key}: {len(catalog)} tools, layer {layer}"


def unregister(mcp_key: str) -> str:
    """Remove an MCP server extension."""
    servers = load_extensions()
    if mcp_key not in servers:
        return f"{mcp_key} not found in extensions."
    del servers[mcp_key]
    _save_extensions(servers)
    return f"Removed {mcp_key} from extensions."


def list_extensions() -> list[dict]:
    """List all registered extensions with summary info."""
    servers = load_extensions()
    result = []
    for key, entry in servers.items():
        result.append({
            "mcp_key": key,
            "tool_count": len(entry.get("catalog", [])),
            "layer": entry.get("layer", 6),
            "has_router": bool(entry.get("router", {}).get("keywords")),
            "health_type": entry.get("health", {}).get("type", "none"),
        })
    return result


# ── Merge helpers (called by catalog.py, router.py, health.py) ──────────────

def get_extended_catalog() -> dict[str, list[tuple[str, str, str]]]:
    """Return extension catalog entries as tuples matching TOOL_CATALOG format."""
    servers = load_extensions()
    result: dict[str, list[tuple[str, str, str]]] = {}
    for key, entry in servers.items():
        tools = []
        for t in entry.get("catalog", []):
            tools.append((t["name"], t.get("params", ""), t.get("when", "")))
        if tools:
            result[key] = tools
    return result


def get_extended_layers() -> dict[str, int]:
    """Return extension layer assignments."""
    servers = load_extensions()
    return {key: entry.get("layer", 6) for key, entry in servers.items()}


def get_extended_routes() -> list[dict]:
    """Return extension router entries matching ROUTE_INDEX format."""
    servers = load_extensions()
    routes = []
    for key, entry in servers.items():
        router = entry.get("router", {})
        if router.get("keywords"):
            routes.append({
                "mcp_key": key,
                "keywords": router.get("keywords", []),
                "intent_phrases": router.get("intent_phrases", []),
                "anti_keywords": router.get("anti_keywords", []),
                "weight": router.get("weight", 1.0),
                "description": router.get("description", f"{key} MCP server"),
            })
    return routes


def get_extended_health() -> dict[str, dict]:
    """Return extension health check configs.

    Returns: {mcp_key: {type, binary?}}
    """
    servers = load_extensions()
    return {key: entry.get("health", {"type": "none"})
            for key, entry in servers.items()}


def get_extended_requirements() -> dict[str, dict]:
    """Return extension TOOL_REQUIREMENTS entries."""
    servers = load_extensions()
    return {key: entry["requirements"]
            for key, entry in servers.items()
            if "requirements" in entry}
