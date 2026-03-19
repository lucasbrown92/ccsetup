"""Read/write for .claude/afe.json store.

The store path defaults to .claude/afe.json in the current working directory
(the target project). Override the directory with CLAUDE_AFE_DIR env var.

Limits: specs max 50 (FIFO), ecologies max 20, history max 100.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_DEFAULT = {"specs": [], "ecologies": [], "history": []}

MAX_SPECS = 50
MAX_ECOLOGIES = 20
MAX_HISTORY = 100


def _log(msg):
    print(msg, file=sys.stderr)


def get_store_path():
    store_dir = Path(os.environ.get("CLAUDE_AFE_DIR", ".claude"))
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir / "afe.json"


def load():
    """Load the AFE store. Returns a clean default on missing/corrupt file."""
    path = get_store_path()
    if not path.exists():
        return dict(_DEFAULT)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, ValueError) as exc:
        _log(f"WARNING: {path} is corrupted ({exc}), backing up and starting fresh")
        backup = path.with_suffix(".json.bak")
        try:
            path.rename(backup)
            _log(f"  Backup saved to {backup}")
        except OSError:
            pass
        return dict(_DEFAULT)
    # Back-fill missing keys
    data.setdefault("specs", [])
    data.setdefault("ecologies", [])
    data.setdefault("history", [])
    return data


def save(data):
    """Atomic write: temp file + rename prevents data loss on crash/concurrent writes."""
    # Enforce limits with FIFO eviction
    specs = data.get("specs", [])
    if len(specs) > MAX_SPECS:
        evicted = specs[:len(specs) - MAX_SPECS]
        data["specs"] = specs[len(specs) - MAX_SPECS:]
        data["history"].extend(evicted)

    ecologies = data.get("ecologies", [])
    if len(ecologies) > MAX_ECOLOGIES:
        data["ecologies"] = ecologies[len(ecologies) - MAX_ECOLOGIES:]

    history = data.get("history", [])
    if len(history) > MAX_HISTORY:
        data["history"] = history[len(history) - MAX_HISTORY:]

    path = get_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".afe-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))  # atomic on POSIX
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def find_spec(data, spec_id):
    """Return the spec with this ID from active specs, or None."""
    for s in data.get("specs", []):
        if s["id"] == spec_id:
            return s
    return None


def find_ecology(data, eco_id):
    """Return the ecology with this ID, or None."""
    for e in data.get("ecologies", []):
        if e["id"] == eco_id:
            return e
    return None


def find_any(data, item_id):
    """Search specs, ecologies, and history for an item by ID."""
    for s in data.get("specs", []):
        if s["id"] == item_id:
            return s
    for e in data.get("ecologies", []):
        if e["id"] == item_id:
            return e
    for h in data.get("history", []):
        if h.get("id") == item_id:
            return h
    return None
