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
_BUNDLED = {"claude-mind", "claude-charter", "claude-witness",
            "claude-retina", "claude-ledger"}

_SHARE_DIR = Path.home() / ".local" / "share" / "ccsetup"


def _check_binary(binary: str) -> bool:
    return shutil.which(binary) is not None


def _check_bundled(mcp_key: str) -> bool:
    return (_SHARE_DIR / mcp_key / "server.py").exists()


def _get_extension_health(mcp_key: str) -> dict | None:
    """Check if an extension has health config for this key."""
    try:
        import extensions as _ext
        ext_health = _ext.get_extended_health()
        return ext_health.get(mcp_key)
    except Exception:
        return None


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

    # Check extension health config
    ext_health = _get_extension_health(mcp_key)
    if ext_health:
        htype = ext_health.get("type", "none")
        if htype == "binary":
            ext_binary = ext_health.get("binary", "")
            if ext_binary:
                if _check_binary(ext_binary):
                    return {
                        "mcp_key": mcp_key,
                        "configured": True,
                        "healthy": True,
                        "status": "healthy",
                        "detail": f"binary '{ext_binary}' found (extension)",
                    }
                return {
                    "mcp_key": mcp_key,
                    "configured": True,
                    "healthy": False,
                    "status": "missing_binary",
                    "detail": f"binary '{ext_binary}' not found in PATH (extension)",
                }
        elif htype == "bundled":
            bundled_path = ext_health.get("path", "")
            if bundled_path and Path(bundled_path).exists():
                return {
                    "mcp_key": mcp_key,
                    "configured": True,
                    "healthy": True,
                    "status": "healthy",
                    "detail": f"bundled at {bundled_path} (extension)",
                }
            elif bundled_path:
                return {
                    "mcp_key": mcp_key,
                    "configured": True,
                    "healthy": False,
                    "status": "missing_file",
                    "detail": f"file not found at {bundled_path} (extension)",
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


# ── Diagnostic engine ─────────────────────────────────────────────────────────

def _load_global_settings() -> dict:
    """Load ~/.claude/settings.json."""
    p = Path.home() / ".claude" / "settings.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_global_settings(data: dict) -> None:
    """Write ~/.claude/settings.json."""
    p = Path.home() / ".claude" / "settings.json"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _check_hook_present(event: str, match_command: str) -> bool:
    """Return True if a hook matching match_command exists under the given event."""
    settings = _load_global_settings()
    for hook_group in settings.get("hooks", {}).get(event, []):
        for hook in hook_group.get("hooks", []):
            if match_command in hook.get("command", ""):
                return True
    return False


def _fix_hook_add(event: str, hook_entry: dict) -> str:
    """Append hook_entry to settings.hooks[event]. Returns description of what changed."""
    settings = _load_global_settings()
    hooks = settings.setdefault("hooks", {})
    event_list = hooks.setdefault(event, [])
    event_list.append(hook_entry)
    _save_global_settings(settings)
    cmd = hook_entry.get("hooks", [{}])[0].get("command", "?")
    return f"Added {event} hook: {cmd!r} → ~/.claude/settings.json"


# Language extension → Serena language name
_LANG_EXT: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".jsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".sh": "bash",
    ".bash": "bash",
    ".c": "cpp",
    ".cpp": "cpp",
    ".h": "cpp",
    ".lua": "lua",
    ".swift": "swift",
    ".kt": "kotlin",
    ".tf": "terraform",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _detect_project_languages() -> set[str]:
    """Return language names for file types found in CWD (excludes common non-source dirs)."""
    skip = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache"}
    found: set[str] = set()
    cwd = Path(".")
    for p in cwd.rglob("*"):
        if any(part in skip for part in p.parts):
            continue
        lang = _LANG_EXT.get(p.suffix.lower())
        if lang:
            found.add(lang)
    return found


def _read_serena_languages() -> list[str]:
    """Parse the languages list from .serena/project.yml (no PyYAML needed)."""
    yml = Path(".serena") / "project.yml"
    if not yml.exists():
        return []
    langs: list[str] = []
    in_langs = False
    for raw_line in yml.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("languages:"):
            in_langs = True
            continue
        if in_langs:
            if stripped.startswith("- "):
                langs.append(stripped[2:].strip())
            elif stripped and not stripped.startswith("#") and ":" in stripped:
                break  # next yaml key
    return langs


def _fix_serena_languages(add_langs: list[str]) -> str:
    """Append missing languages to .serena/project.yml. Returns description."""
    yml = Path(".serena") / "project.yml"
    if not yml.exists():
        return "No .serena/project.yml found — cannot fix automatically."
    lines = yml.read_text(encoding="utf-8").splitlines(keepends=True)
    # Find the line after the last "- <lang>" in the languages block
    insert_after = -1
    in_langs = False
    for i, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped.startswith("languages:"):
            in_langs = True
            continue
        if in_langs:
            if stripped.startswith("- "):
                insert_after = i
            elif stripped and not stripped.startswith("#") and ":" in stripped:
                break
    if insert_after == -1:
        return "Could not locate languages list in .serena/project.yml."
    new_lines = lines[: insert_after + 1]
    for lang in add_langs:
        new_lines.append(f"- {lang}\n")
    new_lines.extend(lines[insert_after + 1 :])
    yml.write_text("".join(new_lines), encoding="utf-8")
    return f"Added to .serena/project.yml languages: {', '.join(add_langs)}"


def _check_serena_languages() -> dict:
    """Compare .serena/project.yml against detected project languages."""
    configured = set(_read_serena_languages())
    detected = _detect_project_languages()
    if not configured:
        return {"ok": True, "note": "no .serena/project.yml — skipping"}
    missing = detected - configured
    if missing:
        return {
            "ok": False,
            "configured": sorted(configured),
            "detected": sorted(detected),
            "missing": sorted(missing),
            "fix": f"Add to .serena/project.yml languages: {', '.join(sorted(missing))}",
        }
    return {"ok": True, "configured": sorted(configured), "detected": sorted(detected)}


def _fix_leann_env(mcp_json_path: Path = Path(".mcp.json")) -> str:
    """Add a default LEANN_INDEX_PATH to the leann-server entry in .mcp.json."""
    if not mcp_json_path.exists():
        return "No .mcp.json found."
    data = json.loads(mcp_json_path.read_text(encoding="utf-8"))
    server = data.get("mcpServers", {}).get("leann-server")
    if not server:
        return "leann-server not in .mcp.json — nothing to fix."
    env = server.setdefault("env", {})
    if "LEANN_INDEX_PATH" in env:
        return "LEANN_INDEX_PATH already set."
    env["LEANN_INDEX_PATH"] = ".leann/index"
    mcp_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return 'Added "LEANN_INDEX_PATH": ".leann/index" to leann-server env in .mcp.json'


def diagnose_tool(mcp_key: str) -> dict:
    """Full prerequisite check for one tool.

    Returns:
        {mcp_key, base_health, issues, fixes, fixable_count, why}

    Each fix entry:
        {step: str, auto: bool, target?: str, action?: str, payload?: any}
    """
    import catalog as _cat

    base = check_tool(mcp_key)
    issues: list[str] = []
    fixes: list[dict] = []

    req_spec = _cat.get_full_requirements().get(mcp_key, {})
    for req in req_spec.get("requires", []):
        rtype = req["type"]

        if rtype == "binary":
            name = req["name"]
            if not shutil.which(name):
                issues.append(f"Missing binary: {name}")
                fixes.append({
                    "step": req.get("fix", f"Install {name}"),
                    "auto": False,
                    "action": "install_binary",
                    "name": name,
                })

        elif rtype == "hook":
            event = req["event"]
            match_cmd = req.get("match_command", "")
            if not _check_hook_present(event, match_cmd):
                issues.append(f"Missing {event} hook ({match_cmd}) in ~/.claude/settings.json")
                fixes.append({
                    "step": req.get("fix_description", f"Add {event} hook"),
                    "auto": req.get("auto_fixable", False),
                    "action": "add_hook",
                    "event": event,
                    "hook_entry": req.get("fix_hook_entry"),
                    "target": "~/.claude/settings.json",
                })

        elif rtype == "file":
            raw_path = req["path"]
            path = Path(raw_path.replace("~", str(Path.home())))
            if not path.exists():
                issues.append(f"Missing file: {raw_path}")
                fixes.append({
                    "step": req.get("fix", f"Create {raw_path}"),
                    "auto": False,
                    "action": "manual",
                })

        elif rtype == "env":
            var = req["var"]
            if not os.environ.get(var):
                issues.append(f"Env var {var} not set")
                fixes.append({
                    "step": req.get("fix", f"Set {var}"),
                    "auto": req.get("auto_fixable", False),
                    "action": "set_env_in_mcp_json",
                    "var": var,
                    "target": ".mcp.json",
                })

        elif rtype == "auto_configure":
            check = req.get("check")
            if check == "serena_languages":
                result = _check_serena_languages()
                if not result.get("ok"):
                    missing = result.get("missing", [])
                    issues.append(f"Serena missing languages: {', '.join(missing)}")
                    fixes.append({
                        "step": req.get("fix_description", result.get("fix", "Fix serena languages")),
                        "auto": req.get("auto_fixable", False),
                        "action": "fix_serena_languages",
                        "add_langs": missing,
                        "target": ".serena/project.yml",
                    })

    return {
        "mcp_key": mcp_key,
        "base_health": base,
        "issues": issues,
        "fixes": fixes,
        "fixable_count": sum(1 for f in fixes if f.get("auto")),
        "why": req_spec.get("why", ""),
        "docs": req_spec.get("docs", ""),
    }


def apply_fix(fix: dict) -> str:
    """Apply a single auto-fixable fix. Returns a description of what was done."""
    action = fix.get("action")
    if not fix.get("auto"):
        return f"Not auto-fixable: {fix.get('step', '?')}"

    if action == "add_hook":
        event = fix["event"]
        hook_entry = fix["hook_entry"]
        if hook_entry is None:
            return "No hook_entry defined — cannot auto-fix."
        return _fix_hook_add(event, hook_entry)

    if action == "fix_serena_languages":
        add_langs = fix.get("add_langs", [])
        if not add_langs:
            return "No missing languages to add."
        return _fix_serena_languages(add_langs)

    if action == "set_env_in_mcp_json" and fix.get("var") == "LEANN_INDEX_PATH":
        return _fix_leann_env()

    return f"No handler for action={action!r}"


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
