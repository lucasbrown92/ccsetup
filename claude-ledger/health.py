#!/usr/bin/env python3
"""claude-ledger health — real-time tool health checks.

Reads .mcp.json and .claude/ state files in CWD at call time.
No caching — each call reflects the current filesystem state.
"""

import json
import os
import shutil
from pathlib import Path


def _mcp_json_path() -> Path:
    return Path(".mcp.json")


def _claude_dir() -> Path:
    return Path(".claude")


def load_mcp_servers() -> dict:
    """Read .mcp.json mcpServers dict from CWD."""
    p = _mcp_json_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data.get("mcpServers", {})
    except (json.JSONDecodeError, OSError):
        return {}


# ── Binary checks ─────────────────────────────────────────────────────────────

_BINARY_MAP: dict[str, str] = {
    "serena": "uvx",
    "leann-server": "leann_mcp",
    "context7": "npx",
    "claude-session": "claude-session-mcp",
    "context-mode": "npx",
    "seu-claude": "npx",
    "codegraphcontext": "cgc",
    "cship": "cship",
    "ccusage": "ccusage",
    "cclogviewer": "cclogviewer",
}

# Bundled servers (checked by file existence, not PATH binary)
_BUNDLED = {"claude-mind", "claude-charter", "claude-witness", "claude-afe",
            "claude-retina", "claude-ledger"}

_SHARE_DIR = Path.home() / ".local" / "share" / "ccsetup"


def _check_binary(binary: str) -> bool:
    return shutil.which(binary) is not None


def _check_bundled(mcp_key: str) -> bool:
    return (_SHARE_DIR / mcp_key / "server.py").exists()


def check_tool(mcp_key: str) -> dict:
    """Return health dict for one tool.

    Returns:
        {mcp_key, configured, healthy, status, detail}
    """
    servers = load_mcp_servers()
    configured = mcp_key in servers

    if not configured:
        return {
            "mcp_key": mcp_key,
            "configured": False,
            "healthy": False,
            "status": "not_configured",
            "detail": "Not in .mcp.json",
        }

    # Check binary / server file
    if mcp_key in _BUNDLED:
        installed = _check_bundled(mcp_key)
        if not installed:
            return {
                "mcp_key": mcp_key,
                "configured": True,
                "healthy": False,
                "status": "missing_file",
                "detail": f"server.py not found at {_SHARE_DIR}/{mcp_key}/server.py — run bash install.sh",
            }
        return {
            "mcp_key": mcp_key,
            "configured": True,
            "healthy": True,
            "status": "healthy",
            "detail": str(_SHARE_DIR / mcp_key / "server.py"),
        }

    binary = _BINARY_MAP.get(mcp_key, "")
    if binary:
        if _check_binary(binary):
            return {
                "mcp_key": mcp_key,
                "configured": True,
                "healthy": True,
                "status": "healthy",
                "detail": f"binary '{binary}' found",
            }
        return {
            "mcp_key": mcp_key,
            "configured": True,
            "healthy": False,
            "status": "missing_binary",
            "detail": f"binary '{binary}' not found in PATH",
        }

    # No binary check — assume healthy if configured
    return {
        "mcp_key": mcp_key,
        "configured": True,
        "healthy": True,
        "status": "healthy",
        "detail": "configured",
    }


def check_all() -> list[dict]:
    """Return health for all configured MCP servers."""
    servers = load_mcp_servers()
    results = []
    for key in servers:
        results.append(check_tool(key))
    return results


# ── Active state readers ───────────────────────────────────────────────────────

def _read_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def mind_active_state() -> dict | None:
    """Read claude-mind state from .claude/mind.json."""
    data = _read_json_safe(_claude_dir() / "mind.json")
    if data is None:
        return None
    nodes = data.get("nodes", [])
    open_nodes = [n for n in nodes if n.get("status") in ("open", "active", "pending")]
    inv = data.get("investigation", {})
    return {
        "title": inv.get("title", "unnamed"),
        "total_nodes": len(nodes),
        "open_nodes": len(open_nodes),
        "status": inv.get("status", "unknown"),
    }


def charter_active_state() -> dict | None:
    """Read claude-charter state from .claude/charter.json."""
    data = _read_json_safe(_claude_dir() / "charter.json")
    if data is None:
        return None
    entries = data.get("entries", [])
    active = [e for e in entries if e.get("status") == "active"]
    by_type: dict[str, int] = {}
    for e in active:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_active": len(active),
        "by_type": by_type,
    }


def witness_active_state() -> dict | None:
    """Read claude-witness state — count recent runs from .claude/witness/."""
    witness_dir = _claude_dir() / "witness"
    if not witness_dir.exists():
        return None
    runs = sorted(witness_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        return None
    failures = 0
    latest_ts = ""
    for f in runs[:5]:
        d = _read_json_safe(f)
        if d:
            if d.get("status") == "fail":
                failures += 1
            ts = d.get("timestamp", "")
            if ts and (not latest_ts or ts > latest_ts):
                latest_ts = ts
    return {
        "recent_runs": min(len(runs), 5),
        "total_runs": len(runs),
        "recent_failures": failures,
        "latest_ts": latest_ts[:16].replace("T", " ") if latest_ts else "?",
    }


def retina_active_state() -> dict | None:
    """Read claude-retina state from .claude/retina/retina.json."""
    store_env = os.environ.get("CLAUDE_RETINA_DIR", ".claude/retina")
    data = _read_json_safe(Path(store_env) / "retina.json")
    if data is None:
        return None
    captures = [c for c in data.get("captures", []) if c.get("type") == "capture"]
    baselines = data.get("baselines", {})
    baseline_names = list(baselines.keys())
    return {
        "captures": len(captures),
        "baselines": len(baselines),
        "baseline_names": baseline_names,
    }
