#!/usr/bin/env python3
"""claude-retina MCP server — visual browser automation for Claude Code.

8 tools:
  retina_capture    url, selector?, viewport?, scheme?, label?, wait_ms?
  retina_diff       capture_a, capture_b, threshold?
  retina_inspect    url, selector?, depth?, roles_only?
  retina_console    url, actions?, categories?, wait_ms?
  retina_interact   url, actions[], viewport?, label?
  retina_baseline   name, url, selector?, viewport?, scheme?, notes?
  retina_regress    name, url?, threshold?, pixel_threshold?
  retina_history    limit?, type?, url_filter?

Storage: .claude/retina/retina.json (override: CLAUDE_RETINA_DIR)
Transport: stdio MCP (JSON-RPC 2.0).
Optional deps: playwright (all browser tools), Pillow (retina_diff pixel mode).
"""

VERSION = "1.0.1"

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make sibling modules importable when server.py is run from any CWD
sys.path.insert(0, str(Path(__file__).parent))

import schema as _schema
import store as _store


# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _short_id(seed: str = "") -> str:
    raw = f"{time.time()}{seed}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]


def _resolve_viewport(viewport: str | None) -> str:
    vp = viewport or _schema.DEFAULT_VIEWPORT
    return _schema.VIEWPORT_ALIASES.get(vp, vp)


# ─────────────────────────────────────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────────────────────────────────────

def retina_capture(
    url: str,
    selector: str | None = None,
    viewport: str | None = None,
    scheme: str | None = None,
    label: str | None = None,
    wait_ms: int | None = None,
) -> str:
    try:
        import capture as _capture
    except ImportError:
        return "Error: capture.py not found in server directory."

    vp = _resolve_viewport(viewport)
    sc = scheme or _schema.DEFAULT_SCHEME
    wms = wait_ms if wait_ms is not None else _schema.DEFAULT_WAIT_MS
    cap_id = _short_id(url)
    out_file = _store.captures_dir() / f"{cap_id}.png"

    try:
        _capture.screenshot_url(url, out_file, selector=selector,
                                 viewport=vp, scheme=sc, wait_ms=wms)
    except RuntimeError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error capturing {url}: {exc}"

    entry = {
        "id": cap_id,
        "type": "capture",
        "url": url,
        "label": label or "",
        "selector": selector,
        "viewport": vp,
        "scheme": sc,
        "wait_ms": wms,
        "file": str(out_file),
        "created_at": _now(),
    }
    data = _store.load()
    _store.add_capture(data, entry)
    _store.save(data)

    return (
        f"Captured: {url}\n"
        f"  ID:       {cap_id}\n"
        f"  File:     {out_file}\n"
        f"  Viewport: {vp} | Scheme: {sc}\n"
        f"\nUse: Read(file_path='{out_file}') to view the screenshot."
    )


def retina_diff(
    capture_a: str,
    capture_b: str,
    threshold: float | None = None,
) -> str:
    thresh = threshold if threshold is not None else _schema.DEFAULT_THRESHOLD
    data = _store.load()
    ca = _store.find_capture(data, capture_a)
    cb = _store.find_capture(data, capture_b)

    if ca is None:
        return f"Error: capture '{capture_a}' not found. Use retina_history() to list captures."
    if cb is None:
        return f"Error: capture '{capture_b}' not found. Use retina_history() to list captures."

    path_a = Path(ca["file"])
    path_b = Path(cb["file"])
    if not path_a.exists():
        return f"Error: capture file missing: {path_a}"
    if not path_b.exists():
        return f"Error: capture file missing: {path_b}"

    try:
        import diff as _diff
    except ImportError:
        return "Error: diff.py not found in server directory."

    diff_id = f"diff_{ca['id']}_{cb['id']}"
    out_file = _store.captures_dir() / f"{diff_id}.png"
    result = _diff.pixel_diff(path_a, path_b, out_file, threshold=thresh)

    entry = {
        "id": diff_id,
        "type": "diff",
        "capture_a": ca["id"],
        "capture_b": cb["id"],
        "change_pct": result["change_pct"],
        "changed_pixels": result["changed_pixels"],
        "total_pixels": result["total_pixels"],
        "threshold": thresh,
        "regions": result.get("regions", []),
        "file": result.get("diff_file"),
        "created_at": _now(),
    }
    _store.add_capture(data, entry)
    _store.save(data)

    lines = [
        f"Diff: {ca['id']} → {cb['id']}",
        f"  Change:    {result['change_pct']:.4f}%  "
        f"({result['changed_pixels']} / {result['total_pixels']} pixels)",
        f"  Threshold: {thresh}",
    ]
    if result.get("regions"):
        lines.append(f"  Changed regions ({len(result['regions'])}):")
        for r in result["regions"]:
            lines.append(f"    [{r['x1']},{r['y1']}] → [{r['x2']},{r['y2']}]")
    if result.get("diff_file"):
        lines.append(f"\n  Diff image: {result['diff_file']}")
        lines.append(f"  Use: Read(file_path='{result['diff_file']}') to view.")
    if result.get("note"):
        lines.append(f"\n  Note: {result['note']}")

    return "\n".join(lines)


def retina_inspect(
    url: str,
    selector: str | None = None,
    depth: int | None = None,
    roles_only: bool = False,
) -> str:
    max_depth = depth if depth is not None else 4

    try:
        import capture as _capture
    except ImportError:
        return "Error: capture.py not found in server directory."

    try:
        snapshot = _capture.accessibility_snapshot(url, selector=selector)
    except RuntimeError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error inspecting {url}: {exc}"

    if snapshot is None:
        return f"No accessibility tree found for {url}. The page may be empty or inaccessible."

    header = f"Accessibility tree: {url}"
    if selector:
        header += f" (selector: {selector!r})"
    lines = [header, ""]

    def _walk(node, indent: int = 0):
        if node is None or indent > max_depth:
            return
        role = node.get("role", "")
        name = node.get("name", "")
        if roles_only and not role:
            for child in (node.get("children") or []):
                _walk(child, indent)
            return
        prefix = "  " * indent
        label = role if role else "(group)"
        if name:
            label += f": {name!r}"
        if node.get("value"):
            label += f" = {node['value']!r}"
        lines.append(f"{prefix}{label}")
        for child in (node.get("children") or []):
            _walk(child, indent + 1)

    _walk(snapshot)
    return "\n".join(lines)


def retina_console(
    url: str,
    actions: list | None = None,
    categories: list | None = None,
    wait_ms: int | None = None,
) -> str:
    wms = wait_ms if wait_ms is not None else _schema.DEFAULT_WAIT_MS

    try:
        import capture as _capture
    except ImportError:
        return "Error: capture.py not found in server directory."

    try:
        messages = _capture.capture_console(url, actions=actions, wait_ms=wms)
    except RuntimeError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error monitoring {url}: {exc}"

    if categories:
        cats = {c.lower() for c in categories}
        messages = [m for m in messages if m.get("type", "").lower() in cats]

    if not messages:
        return f"No console messages captured from {url}."

    _ICONS = {
        "ERROR": "🔴", "WARNING": "🟡", "WARN": "🟡",
        "LOG": "⬜", "INFO": "🔵", "DEBUG": "⚪",
        "UNCAUGHT_EXCEPTION": "💥",
    }

    lines = [f"Console messages from {url} ({len(messages)}):\n"]
    for m in messages:
        mtype = m.get("type", "?").upper()
        icon = _ICONS.get(mtype, "  ")
        line = f"  {icon} [{mtype}] {m.get('text', '')}"
        loc = m.get("location", "")
        if loc:
            line += f"\n    at {loc}"
        lines.append(line)

    return "\n".join(lines)


def retina_interact(
    url: str,
    actions: list,
    viewport: str | None = None,
    label: str | None = None,
) -> str:
    if not actions:
        return "Error: actions list is empty. Provide at least one action."

    vp = _resolve_viewport(viewport)

    try:
        import capture as _capture
    except ImportError:
        return "Error: capture.py not found in server directory."

    seq_id = _short_id(url + str(len(actions)))
    out_dir = _store.captures_dir()

    try:
        steps = _capture.run_interaction(url, actions, out_dir, seq_id, viewport=vp)
    except RuntimeError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error running interaction on {url}: {exc}"

    entry = {
        "id": seq_id,
        "type": "interaction",
        "url": url,
        "label": label or "",
        "viewport": vp,
        "steps": steps,
        "created_at": _now(),
    }
    data = _store.load()
    _store.add_capture(data, entry)
    _store.save(data)

    lines = [f"Interaction: {url}  (ID: {seq_id})"]
    if label:
        lines.append(f"  Label: {label}")
    lines.append(f"  Steps: {len(steps)}\n")

    for s in steps:
        icon = "✓" if s["success"] else "✗"
        atype = s["action"].get("type", "?")
        lines.append(f"  {icon} Step {s['step']}: {atype}")
        if s.get("file"):
            lines.append(f"    Screenshot: {s['file']}")
            lines.append(f"    Read: Read(file_path='{s['file']}')")
        if s.get("error"):
            lines.append(f"    Error: {s['error']}")

    return "\n".join(lines)


def retina_baseline(
    name: str,
    url: str,
    selector: str | None = None,
    viewport: str | None = None,
    scheme: str | None = None,
    notes: str | None = None,
) -> str:
    vp = _resolve_viewport(viewport)
    sc = scheme or _schema.DEFAULT_SCHEME

    data = _store.load()
    if name in data.get("baselines", {}):
        existing = data["baselines"][name]
        return (
            f"Baseline '{name}' already exists (created {existing['created_at'][:10]}).\n"
            f"  URL:  {existing['url']}\n"
            f"  File: {existing['file']}\n"
            "To replace: delete the baseline entry and re-run retina_baseline()."
        )

    try:
        import capture as _capture
    except ImportError:
        return "Error: capture.py not found in server directory."

    cap_id = _short_id(name + url)
    safe_name = name.replace("/", "-").replace(" ", "_")
    out_file = _store.baselines_dir() / f"{safe_name}.png"

    try:
        _capture.screenshot_url(url, out_file, selector=selector,
                                 viewport=vp, scheme=sc)
    except RuntimeError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error capturing baseline '{name}': {exc}"

    # Register capture too (for retina_diff references)
    cap_entry = {
        "id": cap_id,
        "type": "capture",
        "url": url,
        "label": f"baseline:{name}",
        "selector": selector,
        "viewport": vp,
        "scheme": sc,
        "wait_ms": _schema.DEFAULT_WAIT_MS,
        "file": str(out_file),
        "created_at": _now(),
    }
    _store.add_capture(data, cap_entry)

    baseline_entry = {
        "name": name,
        "url": url,
        "selector": selector,
        "viewport": vp,
        "scheme": sc,
        "notes": notes or "",
        "file": str(out_file),
        "source_capture_id": cap_id,
        "created_at": _now(),
    }
    _store.add_baseline(data, name, baseline_entry)
    _store.save(data)

    return (
        f"Baseline saved: '{name}'\n"
        f"  URL:      {url}\n"
        f"  File:     {out_file}\n"
        f"  Viewport: {vp} | Scheme: {sc}\n"
        f"\n"
        f"Use retina_regress('{name}') to compare future state against this baseline.\n"
        f"Use Read(file_path='{out_file}') to view the baseline image."
    )


def retina_regress(
    name: str,
    url: str | None = None,
    threshold: float | None = None,
    pixel_threshold: float | None = None,
) -> str:
    change_threshold = threshold if threshold is not None else _schema.DEFAULT_CHANGE_PCT
    px_threshold = pixel_threshold if pixel_threshold is not None else _schema.DEFAULT_THRESHOLD

    data = _store.load()
    baseline = data.get("baselines", {}).get(name)
    if baseline is None:
        names = list(data.get("baselines", {}).keys())
        return (
            f"Baseline '{name}' not found.\n"
            f"Available baselines: {names or 'none'}\n"
            f"Use retina_baseline('{name}', url) to create it."
        )

    target_url = url or baseline["url"]
    vp = baseline.get("viewport", _schema.DEFAULT_VIEWPORT)
    sc = baseline.get("scheme", _schema.DEFAULT_SCHEME)
    selector = baseline.get("selector")

    try:
        import capture as _capture
        import diff as _diff
    except ImportError as exc:
        return f"Error importing module: {exc}"

    cap_id = _short_id(name + target_url + _now())
    cap_file = _store.captures_dir() / f"{cap_id}.png"

    try:
        _capture.screenshot_url(target_url, cap_file, selector=selector,
                                 viewport=vp, scheme=sc)
    except RuntimeError as exc:
        return f"Error: {exc}"
    except Exception as exc:
        return f"Error capturing for regression '{name}': {exc}"

    cap_entry = {
        "id": cap_id,
        "type": "capture",
        "url": target_url,
        "label": f"regress:{name}",
        "selector": selector,
        "viewport": vp,
        "scheme": sc,
        "wait_ms": _schema.DEFAULT_WAIT_MS,
        "file": str(cap_file),
        "created_at": _now(),
    }
    _store.add_capture(data, cap_entry)

    baseline_file = Path(baseline["file"])
    safe_name = name.replace("/", "-").replace(" ", "_")
    diff_id = f"diff_baseline_{safe_name}_{cap_id}"
    diff_file = _store.captures_dir() / f"{diff_id}.png"

    result = _diff.pixel_diff(baseline_file, cap_file, diff_file,
                               threshold=px_threshold)

    passed = result["change_pct"] <= change_threshold

    regress_entry = {
        "id": _short_id(name + cap_id),
        "baseline_name": name,
        "capture_id": cap_id,
        "change_pct": result["change_pct"],
        "threshold": change_threshold,
        "passed": passed,
        "diff_file": result.get("diff_file"),
        "created_at": _now(),
    }
    _store.add_regression(data, regress_entry)
    _store.save(data)

    status = "✓ PASS" if passed else "✗ FAIL"
    lines = [
        f"Regression: '{name}'  →  {status}",
        f"  Change:    {result['change_pct']:.4f}%",
        f"  Threshold: {change_threshold}%",
        f"  Baseline:  {baseline_file}",
        f"  Current:   {cap_file}",
    ]

    if not passed and result.get("diff_file"):
        lines.append(f"\n  Diff image: {result['diff_file']}")
        lines.append(f"  Use: Read(file_path='{result['diff_file']}') to inspect differences.")
        if result.get("regions"):
            lines.append(f"  Changed regions ({len(result['regions'])}):")
            for r in result["regions"]:
                lines.append(f"    [{r['x1']},{r['y1']}] → [{r['x2']},{r['y2']}]")

    if result.get("note"):
        lines.append(f"\n  Note: {result['note']}")

    return "\n".join(lines)


def retina_history(
    limit: int | None = None,
    type_filter: str | None = None,
    url_filter: str | None = None,
) -> str:
    max_items = limit if limit is not None else 20
    data = _store.load()

    items: list[dict] = []

    for c in data.get("captures", []):
        if type_filter and c.get("type", "") != type_filter:
            continue
        if url_filter and url_filter not in c.get("url", ""):
            continue
        items.append(c)

    if not type_filter or type_filter == "baseline":
        for bname, b in data.get("baselines", {}).items():
            if url_filter and url_filter not in b.get("url", ""):
                continue
            items.append({**b, "type": "baseline", "id": f"baseline:{bname}"})

    if not type_filter or type_filter == "regression":
        for r in data.get("regression_history", []):
            items.append({**r, "type": "regression", "id": r.get("id", "?")})

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    items = items[:max_items]

    if not items:
        msg = "No retina history found."
        if type_filter:
            msg += f" (type filter: {type_filter!r})"
        return msg

    lines = [f"Retina history ({len(items)} items):\n"]
    for item in items:
        itype = item.get("type", "?")
        iid = item.get("id", "?")
        ts = item.get("created_at", "")[:16].replace("T", " ")

        if itype == "capture":
            lbl = f"  [{item['label']}]" if item.get("label") else ""
            lines.append(f"  capture      {iid}  {ts}{lbl}")
            lines.append(f"               {item.get('url', '')}  {item.get('viewport', '')} {item.get('scheme', '')}")
            lines.append(f"               {item.get('file', '')}")

        elif itype == "diff":
            lines.append(f"  diff         {iid}  {ts}")
            lines.append(f"               {item.get('capture_a', '?')} → {item.get('capture_b', '?')}")
            lines.append(f"               change: {item.get('change_pct', '?')}%")

        elif itype == "interaction":
            lbl = f"  [{item['label']}]" if item.get("label") else ""
            steps = item.get("steps", [])
            lines.append(f"  interaction  {iid}  {ts}{lbl}")
            lines.append(f"               {item.get('url', '')}  {len(steps)} steps")

        elif itype == "baseline":
            bname = item.get("name", iid.replace("baseline:", ""))
            lines.append(f"  baseline     {bname}  {ts}")
            lines.append(f"               {item.get('url', '')}  {item.get('file', '')}")

        elif itype == "regression":
            status = "PASS" if item.get("passed") else "FAIL"
            lines.append(f"  regression   {iid}  {ts}  {status}")
            lines.append(
                f"               baseline: {item.get('baseline_name', '?')}  "
                f"change: {item.get('change_pct', '?')}%"
            )

        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MCP protocol
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = _schema.TOOLS


def dispatch(method: str, params: dict) -> str:
    if method == "retina_capture":
        return retina_capture(
            params["url"],
            selector=params.get("selector"),
            viewport=params.get("viewport"),
            scheme=params.get("scheme"),
            label=params.get("label"),
            wait_ms=params.get("wait_ms"),
        )
    if method == "retina_diff":
        return retina_diff(
            params["capture_a"],
            params["capture_b"],
            threshold=params.get("threshold"),
        )
    if method == "retina_inspect":
        return retina_inspect(
            params["url"],
            selector=params.get("selector"),
            depth=params.get("depth"),
            roles_only=params.get("roles_only", False),
        )
    if method == "retina_console":
        return retina_console(
            params["url"],
            actions=params.get("actions"),
            categories=params.get("categories"),
            wait_ms=params.get("wait_ms"),
        )
    if method == "retina_interact":
        return retina_interact(
            params["url"],
            params["actions"],
            viewport=params.get("viewport"),
            label=params.get("label"),
        )
    if method == "retina_baseline":
        return retina_baseline(
            params["name"],
            params["url"],
            selector=params.get("selector"),
            viewport=params.get("viewport"),
            scheme=params.get("scheme"),
            notes=params.get("notes"),
        )
    if method == "retina_regress":
        return retina_regress(
            params["name"],
            url=params.get("url"),
            threshold=params.get("threshold"),
            pixel_threshold=params.get("pixel_threshold"),
        )
    if method == "retina_history":
        return retina_history(
            limit=params.get("limit"),
            type_filter=params.get("type"),
            url_filter=params.get("url_filter"),
        )
    raise ValueError(f"Unknown method: {method}")


def send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle_request(req: dict) -> None:
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    if method == "initialize":
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "claude-retina", "version": VERSION},
            },
        })
        return

    if method == "notifications/initialized":
        return

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

    if req_id is not None:
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            send({"jsonrpc": "2.0", "id": None,
                  "error": {"code": -32700, "message": "Parse error"}})
            continue
        handle_request(req)


if __name__ == "__main__":
    main()
