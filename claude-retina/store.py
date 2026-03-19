#!/usr/bin/env python3
"""claude-retina store — .claude/retina/retina.json persistence.

Atomic write pattern: write to .tmp, then replace.
Override store root with CLAUDE_RETINA_DIR env var.
"""

import json
import os
from pathlib import Path

_STORE_ENV = "CLAUDE_RETINA_DIR"
_DEFAULT_SUBDIR = ".claude/retina"
_STORE_FILE = "retina.json"
_CAPTURES_SUBDIR = "captures"
_BASELINES_SUBDIR = "baselines"

_EMPTY_STORE = {
    "version": 1,
    "captures": [],
    "baselines": {},
    "regression_history": [],
}


def _store_root() -> Path:
    root = Path(os.environ.get(_STORE_ENV, _DEFAULT_SUBDIR))
    root.mkdir(parents=True, exist_ok=True)
    return root


def captures_dir() -> Path:
    d = _store_root() / _CAPTURES_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def baselines_dir() -> Path:
    d = _store_root() / _BASELINES_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _store_file() -> Path:
    return _store_root() / _STORE_FILE


def load() -> dict:
    f = _store_file()
    if not f.exists():
        return dict(_EMPTY_STORE, captures=[], baselines={}, regression_history=[])
    try:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Ensure all keys exist (forward-compat)
        for key, default in _EMPTY_STORE.items():
            if key not in data:
                data[key] = type(default)()
        return data
    except (json.JSONDecodeError, ValueError):
        return dict(_EMPTY_STORE, captures=[], baselines={}, regression_history=[])


def save(data: dict) -> None:
    f = _store_file()
    tmp = f.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        tmp.replace(f)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def add_capture(data: dict, entry: dict) -> dict:
    data["captures"].append(entry)
    return data


def add_baseline(data: dict, name: str, entry: dict) -> dict:
    data["baselines"][name] = entry
    return data


def add_regression(data: dict, entry: dict) -> dict:
    if "regression_history" not in data:
        data["regression_history"] = []
    data["regression_history"].append(entry)
    return data


def find_capture(data: dict, capture_id: str) -> dict | None:
    """Find a capture by exact ID or prefix match."""
    for c in data.get("captures", []):
        cid = c.get("id", "")
        if cid == capture_id or cid.startswith(capture_id):
            return c
    return None
