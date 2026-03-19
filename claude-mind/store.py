"""Read/write for .claude/mind.json store.

The store path defaults to .claude/mind.json in the current working directory
(the target project). Override the directory with CLAUDE_MIND_DIR env var.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

_DEFAULT = {"investigation": None, "nodes": [], "history": []}


def _log(msg):
    print(msg, file=sys.stderr)


def get_store_path():
    store_dir = Path(os.environ.get("CLAUDE_MIND_DIR", ".claude"))
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir / "mind.json"


def load():
    """Load the mind store. Returns a clean default on missing/corrupt file."""
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
    # Back-fill missing keys from older versions
    data.setdefault("history", [])
    data.setdefault("nodes", [])
    data.setdefault("investigation", None)
    return data


def save(data):
    """Atomic write: temp file + rename prevents data loss on crash/concurrent writes."""
    path = get_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp", prefix=".mind-")
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


def find_node(data, node_id):
    """Return the node with this ID, or None."""
    for node in data.get("nodes", []):
        if node["id"] == node_id:
            return node
    return None
