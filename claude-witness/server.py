#!/usr/bin/env python3
"""claude-witness MCP server — execution memory for Python projects.

7 tools:
  witness_runs(limit?)                       list recent runs with pass/fail
  witness_traces(fn_name, run_id?, status?)  calls to fn_name across runs
  witness_exception(exc_type, run_id?)       exception frames with local state
  witness_coverage_gaps(file)                lines in file never executed
  witness_diff(run_a, run_b)                 call delta between two runs
  witness_check_charter(run_id?)             cross-check run against charter invariants
  witness_hotspots(limit?, run_count?)       functions with most exceptions across runs

Storage: .claude/witness/<run_id>.json (override: CLAUDE_WITNESS_DIR).
Charter: .claude/charter.json (override: CLAUDE_CHARTER_DIR).

Transport: stdio MCP (JSON-RPC 2.0). stdlib only.
"""

VERSION = "1.0.1"

import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

_STORE_DIR = os.environ.get("CLAUDE_WITNESS_DIR", ".claude/witness")


def _log(msg):
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------

def _store_path() -> Path:
    p = Path(_STORE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _list_runs(limit: int = 20) -> list[dict]:
    """Return run metadata dicts, newest first."""
    store = _store_path()
    runs = []
    for f in sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        data = _safe_load_json(f)
        if data is None:
            continue
        runs.append({
            "run_id": data.get("run_id", f.stem),
            "timestamp": data.get("timestamp", ""),
            "status": data.get("status", "unknown"),
            "tests": len(data.get("tests", [])),
            "call_count": data.get("call_count", len(data.get("calls", []))),
            "_path": str(f),
        })
        if len(runs) >= limit:
            break
    return runs


def _safe_load_json(path: Path) -> dict | None:
    """Load JSON, returning None on corruption (with backup + log)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError) as exc:
        _log(f"WARNING: {path} is corrupted ({exc}), backing up")
        try:
            path.rename(path.with_suffix(".json.bak"))
        except OSError:
            pass
        return None


def _load_run(run_id: str) -> dict:
    """Load a specific run by run_id. Raises ValueError if not found."""
    store = _store_path()
    # Try exact filename match first
    candidate = store / f"{run_id}.json"
    if candidate.exists():
        data = _safe_load_json(candidate)
        if data is not None:
            return data
    # Prefix match (allow shortened run_ids)
    for f in store.glob("*.json"):
        if f.stem.startswith(run_id) or run_id in f.stem:
            data = _safe_load_json(f)
            if data is not None:
                return data
    raise ValueError(f"No run found with id matching '{run_id}'")


def _latest_run() -> dict:
    """Load the most recent run. Raises ValueError if store is empty."""
    store = _store_path()
    files = sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise ValueError("No witness runs found. Run: pytest --witness")
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def _get_run(run_id: str | None) -> dict:
    if run_id:
        return _load_run(run_id)
    return _latest_run()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def witness_runs(limit: int = 10) -> str:
    runs = _list_runs(limit)
    if not runs:
        return "No witness runs found. Run: pytest --witness"

    lines = [f"Recent witness runs ({len(runs)}):\n"]
    for r in runs:
        ts = r["timestamp"][:19].replace("T", " ") if r["timestamp"] else "?"
        icon = "✓" if r["status"] == "pass" else ("✗" if r["status"] == "fail" else "?")
        lines.append(
            f"  {icon} {r['run_id']}  {ts}  "
            f"{r['tests']} tests  {r['call_count']} calls"
        )
    return "\n".join(lines)


def witness_traces(fn_name: str, run_id: str | None = None, status: str | None = None) -> str:
    run = _get_run(run_id)
    calls = run.get("calls", [])

    # Match by function name (substring match on qualified name)
    fn_lower = fn_name.lower()
    matched = [c for c in calls if fn_lower in c["fn"].lower()]

    if status == "exception":
        matched = [c for c in matched if c.get("exception") is not None]
    elif status == "normal":
        matched = [c for c in matched if c.get("exception") is None]

    if not matched:
        rid = run.get("run_id", "?")
        return (
            f"No calls to '{fn_name}' in run {rid}.\n"
            f"Run has {len(calls)} total calls. Try a shorter function name or check witness_runs()."
        )

    rid = run.get("run_id", "?")
    lines = [f"Calls to '{fn_name}' in run {rid} ({len(matched)} found):\n"]
    for c in matched[:50]:  # cap display at 50
        exc_flag = f"  !! exception: {c['exception']}" if c.get("exception") else ""
        ret_str = f"  → {c['return']}" if c.get("return") is not None else ""
        args_str = ""
        if c.get("args"):
            arg_parts = [f"{k}={v!r}" for k, v in list(c["args"].items())[:6]]
            args_str = f"({', '.join(arg_parts)})"
        lines.append(
            f"  [{c['id']}] {c['fn']}{args_str}\n"
            f"    file: {c['file']}:{c['line']}  depth:{c['depth']}  test:{c['test']}"
            f"{ret_str}{exc_flag}"
        )
    if len(matched) > 50:
        lines.append(f"\n  ... {len(matched) - 50} more (refine with run_id or status filter)")
    return "\n".join(lines)


def witness_exception(exc_type: str, run_id: str | None = None) -> str:
    run = _get_run(run_id)
    exceptions = run.get("exceptions", [])

    exc_lower = exc_type.lower()
    matched = [e for e in exceptions if exc_lower in e["type"].lower()]

    if not matched:
        rid = run.get("run_id", "?")
        all_types = sorted({e["type"] for e in exceptions})
        type_list = ", ".join(all_types) if all_types else "none"
        return (
            f"No '{exc_type}' exceptions in run {rid}.\n"
            f"Exception types in this run: {type_list}"
        )

    rid = run.get("run_id", "?")
    lines = [f"'{exc_type}' exceptions in run {rid} ({len(matched)} found):\n"]
    for e in matched[:20]:
        lines.append(f"  [{e['type']}] {e['file']}:{e['line']}")
        lines.append(f"    test: {e['test']}")
        if e.get("message"):
            lines.append(f"    message: {e['message']}")
        if e.get("locals"):
            loc_parts = [f"{k}={v!r}" for k, v in list(e["locals"].items())[:8]]
            lines.append(f"    locals: {', '.join(loc_parts)}")
        lines.append("")
    return "\n".join(lines)


def witness_coverage_gaps(file: str) -> str:
    """Report lines in file that were never executed across all runs."""
    store = _store_path()
    run_files = sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not run_files:
        return "No witness runs found. Run: pytest --witness"

    # Collect all executed lines for this file across all runs
    executed: set[int] = set()
    runs_checked = 0
    for rf in run_files[:10]:  # look at last 10 runs
        data = _safe_load_json(rf)
        if data is None:
            continue
        coverage = data.get("coverage", {})
        # Match by suffix (handles relative path variations)
        for cov_file, lines in coverage.items():
            if file in cov_file or cov_file in file or cov_file.endswith(file):
                executed.update(lines)
        runs_checked += 1

    if not executed:
        return (
            f"No coverage data for '{file}' in last {runs_checked} runs.\n"
            "Ensure the file is in your project source and tests import it."
        )

    # Read the actual source file to get all non-blank, non-comment lines
    source_path = None
    # Try relative to cwd first, then walk project root
    for candidate in [Path(file), Path(os.getcwd()) / file]:
        if candidate.exists():
            source_path = candidate
            break

    if source_path is None:
        # Can't find source — just report executed lines count
        return (
            f"Coverage data found for '{file}': {len(executed)} lines executed.\n"
            "Cannot find source file to compute gaps (file path not found from cwd)."
        )

    # Parse source for executable lines (non-blank, non-comment, non-decorator-only)
    executable: set[int] = set()
    try:
        with open(source_path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, 1):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    executable.add(i)
    except Exception as e:
        return f"Could not read source file '{file}': {e}"

    never_executed = sorted(executable - executed)
    pct = 100 * len(executed & executable) / len(executable) if executable else 0

    lines = [
        f"Coverage for '{file}' (last {runs_checked} runs):",
        f"  {len(executed & executable)}/{len(executable)} executable lines reached ({pct:.0f}%)",
        "",
    ]
    if not never_executed:
        lines.append("  All executable lines were reached. No gaps.")
    else:
        lines.append(f"  Never-executed lines ({len(never_executed)}):")
        # Group into ranges for readability
        ranges = _to_ranges(never_executed)
        for r in ranges[:40]:
            lines.append(f"    {r}")
        if len(ranges) > 40:
            lines.append(f"    ... {len(ranges) - 40} more ranges")

    return "\n".join(lines)


def witness_diff(run_a: str, run_b: str) -> str:
    """Surface meaningful delta between two runs."""
    ra = _load_run(run_a)
    rb = _load_run(run_b)

    # --- test status diff ---
    tests_a = {t["name"]: t["status"] for t in ra.get("tests", [])}
    tests_b = {t["name"]: t["status"] for t in rb.get("tests", [])}

    newly_failing = [t for t, s in tests_b.items() if s == "fail" and tests_a.get(t) != "fail"]
    newly_passing = [t for t, s in tests_b.items() if s == "pass" and tests_a.get(t) == "fail"]
    added_tests = [t for t in tests_b if t not in tests_a]
    removed_tests = [t for t in tests_a if t not in tests_b]

    # --- call frequency diff ---
    def call_freq(run):
        freq: dict[str, int] = {}
        for c in run.get("calls", []):
            freq[c["fn"]] = freq.get(c["fn"], 0) + 1
        return freq

    freq_a = call_freq(ra)
    freq_b = call_freq(rb)
    all_fns = set(freq_a) | set(freq_b)

    appeared = sorted(fn for fn in all_fns if fn not in freq_a)
    disappeared = sorted(fn for fn in all_fns if fn not in freq_b)
    changed = sorted(
        (fn, freq_a[fn], freq_b[fn])
        for fn in all_fns
        if fn in freq_a and fn in freq_b and freq_a[fn] != freq_b[fn]
    )

    # --- exception diff ---
    exc_a = {e["type"] for e in ra.get("exceptions", [])}
    exc_b = {e["type"] for e in rb.get("exceptions", [])}
    new_exceptions = sorted(exc_b - exc_a)
    resolved_exceptions = sorted(exc_a - exc_b)

    # --- format ---
    id_a = ra.get("run_id", run_a)[:20]
    id_b = rb.get("run_id", run_b)[:20]
    status_a = ra.get("status", "?")
    status_b = rb.get("status", "?")

    lines = [
        f"Diff: {id_a} ({status_a}) → {id_b} ({status_b})",
        "",
    ]

    if newly_failing:
        lines.append(f"NEWLY FAILING ({len(newly_failing)}):")
        for t in newly_failing[:10]:
            lines.append(f"  ✗ {t}")
        lines.append("")
    if newly_passing:
        lines.append(f"NEWLY PASSING ({len(newly_passing)}):")
        for t in newly_passing[:10]:
            lines.append(f"  ✓ {t}")
        lines.append("")
    if new_exceptions:
        lines.append(f"NEW EXCEPTIONS: {', '.join(new_exceptions)}")
    if resolved_exceptions:
        lines.append(f"RESOLVED EXCEPTIONS: {', '.join(resolved_exceptions)}")
    if new_exceptions or resolved_exceptions:
        lines.append("")

    if appeared:
        lines.append(f"FUNCTIONS APPEARED ({len(appeared)}):")
        for fn in appeared[:15]:
            lines.append(f"  + {fn}  ({freq_b[fn]}x)")
        if len(appeared) > 15:
            lines.append(f"  ... {len(appeared) - 15} more")
        lines.append("")
    if disappeared:
        lines.append(f"FUNCTIONS DISAPPEARED ({len(disappeared)}):")
        for fn in disappeared[:15]:
            lines.append(f"  - {fn}")
        if len(disappeared) > 15:
            lines.append(f"  ... {len(disappeared) - 15} more")
        lines.append("")
    if changed:
        lines.append(f"CALL COUNT CHANGED ({len(changed)}):")
        for fn, ca, cb in sorted(changed, key=lambda x: abs(x[2] - x[1]), reverse=True)[:15]:
            arrow = "↑" if cb > ca else "↓"
            lines.append(f"  {arrow} {fn}  {ca} → {cb}")
        lines.append("")

    if added_tests:
        lines.append(f"Tests added: {len(added_tests)}")
    if removed_tests:
        lines.append(f"Tests removed: {len(removed_tests)}")

    if not any([newly_failing, newly_passing, appeared, disappeared, changed,
                new_exceptions, resolved_exceptions]):
        lines.append("No significant differences found between these two runs.")

    return "\n".join(lines)


def witness_check_charter(run_id: str | None = None) -> str:
    """Cross-reference a witness run against active charter invariants/constraints."""
    # Load charter
    charter_dir = os.environ.get("CLAUDE_CHARTER_DIR", ".claude")
    charter_path = Path(charter_dir) / "charter.json"
    if not charter_path.exists():
        return (
            "No charter found. Seed one with charter_add to enable violation detection.\n"
            f"Expected: {charter_path.absolute()}"
        )
    with open(charter_path, "r", encoding="utf-8") as f:
        charter_data = json.load(f)

    normative = [
        e for e in charter_data.get("entries", [])
        if e.get("type") in ("invariant", "constraint", "contract")
        and e.get("status") == "active"
    ]
    if not normative:
        return "Charter has no active invariants, constraints, or contracts to check against."

    # Load witness run
    run = _get_run(run_id)
    calls = run.get("calls", [])
    rid = run.get("run_id", "?")

    if not calls:
        return (
            f"Run {rid} has no captured calls to check.\n"
            "Ensure tests were run with: pytest --witness"
        )

    # Import shared tokenizer from charter's canonical source
    try:
        _charter_dir = str(Path(__file__).resolve().parent.parent / "claude-charter")
        if _charter_dir not in sys.path:
            sys.path.insert(0, _charter_dir)
        from text_utils import tokenize, is_prohibition
    except ImportError:
        # Fallback: inline tokenizer if charter module not co-located
        def tokenize(text: str) -> set:
            return set(re.findall(r"[a-z0-9_]+", text.lower()))
        _PROHIBITION_WORDS = {"never", "not", "without", "avoid", "prevent",
                              "prohibit", "forbidden", "disallow", "no "}
        def is_prohibition(content: str) -> bool:
            lower = content.lower()
            return any(w in lower for w in _PROHIBITION_WORDS)

    violations = []
    warnings = []
    clean = []

    for entry in normative:
        charter_tokens = tokenize(entry["content"])
        is_prohib = is_prohibition(entry["content"])

        # Score each call against this charter entry
        matching: list[tuple[float, dict]] = []
        for call in calls:
            call_text = f"{call['fn']} {call['file']}"
            call_tokens = tokenize(call_text)
            overlap = charter_tokens & call_tokens
            if not overlap:
                continue
            score = len(overlap) / max(len(charter_tokens), 1)
            if score >= 0.15:
                matching.append((score, call))

        matching.sort(key=lambda x: -x[0])

        if matching and is_prohib:
            violations.append((entry, matching[:5]))
        elif matching:
            warnings.append((entry, matching[:3]))
        else:
            clean.append(entry)

    lines = [
        f"Charter audit for run {rid}",
        f"  {len(calls)} calls checked against {len(normative)} normative entries\n",
    ]

    if violations:
        lines.append(f"POSSIBLE VIOLATIONS ({len(violations)}):")
        lines.append("  (entries with prohibition language that match observed calls)")
        for entry, matched in violations:
            label = entry["type"].upper()
            notes_str = f"  — {entry['notes']}" if entry.get("notes") else ""
            lines.append(f"  [{entry['id']}] {label}: {entry['content']}{notes_str}")
            for score, call in matched[:3]:
                exc = "  [exception]" if call.get("exception") else ""
                lines.append(
                    f"    → {call['fn']}  ({call['file']})  "
                    f"overlap:{score:.0%}  test:{call['test']}{exc}"
                )
        lines.append("")

    if warnings:
        lines.append(f"RELATED CALLS ({len(warnings)}):")
        lines.append("  (non-prohibitive entries with matching calls — informational)")
        for entry, matched in warnings:
            label = entry["type"].upper()
            lines.append(f"  [{entry['id']}] {label}: {entry['content']}")
            for score, call in matched[:2]:
                lines.append(f"    → {call['fn']}  overlap:{score:.0%}")
        lines.append("")

    if clean:
        lines.append(f"{len(clean)} entries had no matching calls in this run.")

    if not violations and not warnings:
        lines.append("No charter conflicts or related calls detected in this run.")

    return "\n".join(lines)


def witness_hotspots(limit: int = 15, run_count: int = 5) -> str:
    """Find functions with the most exceptions across recent runs — the 'hot' failure spots."""
    store = _store_path()
    run_files = sorted(store.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not run_files:
        return "No witness runs found. Run: pytest --witness"

    fn_exceptions: Counter = Counter()   # fn_name -> exception count
    fn_files: dict[str, str] = {}        # fn_name -> last seen file
    fn_types: dict[str, Counter] = {}    # fn_name -> Counter of exception types
    runs_checked = 0

    for rf in run_files[:run_count]:
        data = _safe_load_json(rf)
        if data is None:
            continue
        runs_checked += 1
        for exc in data.get("exceptions", []):
            # Build a rough qualified name from the exception's file + context
            fn_key = f"{exc.get('file', '?')}:{exc.get('line', 0)}"
            fn_exceptions[fn_key] += 1
            fn_files[fn_key] = exc.get("file", "?")
            fn_types.setdefault(fn_key, Counter())[exc.get("type", "?")] += 1

        # Also count from calls with exception annotations
        for call in data.get("calls", []):
            if call.get("exception"):
                fn_exceptions[call["fn"]] += 1
                fn_files[call["fn"]] = call.get("file", "?")
                fn_types.setdefault(call["fn"], Counter())[call["exception"]] += 1

    if not fn_exceptions:
        return f"No exceptions found in last {runs_checked} runs. Code is clean."

    top = fn_exceptions.most_common(limit)
    lines = [f"Exception hotspots (last {runs_checked} runs):\n"]
    for loc, count in top:
        file_str = fn_files.get(loc, "")
        types = fn_types.get(loc, {})
        type_str = ", ".join(f"{t}({c})" for t, c in types.most_common(3))
        lines.append(f"  {count:>3}x  {loc}")
        if file_str and file_str != loc:
            lines.append(f"        file: {file_str}")
        lines.append(f"        types: {type_str}")
    return "\n".join(lines)


def _to_ranges(nums: list[int]) -> list[str]:
    """Convert sorted int list to human-readable ranges: [1,2,3,7,8] → ['1-3', '7-8']."""
    if not nums:
        return []
    ranges = []
    start = end = nums[0]
    for n in nums[1:]:
        if n == end + 1:
            end = n
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = n
    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ranges


# ---------------------------------------------------------------------------
# MCP transport (JSON-RPC 2.0 over stdio)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "witness_runs",
        "description": (
            "List recent witness runs with pass/fail status, test count, and call count. "
            "Use this first to get run_ids for the other tools."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max runs to list (default: 10).",
                    "default": 10,
                },
            },
            "required": [],
        },
    },
    {
        "name": "witness_traces",
        "description": (
            "Show all calls to a specific function in a run. "
            "Includes args, return values, call depth, and which test triggered each call. "
            "fn_name is matched as a substring of the qualified function name."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "fn_name": {
                    "type": "string",
                    "description": "Function name to search for (substring match).",
                },
                "run_id": {
                    "type": "string",
                    "description": "Run ID to query. Omit for latest run.",
                },
                "status": {
                    "type": "string",
                    "enum": ["exception", "normal"],
                    "description": "Filter calls by outcome: 'exception' or 'normal'.",
                },
            },
            "required": ["fn_name"],
        },
    },
    {
        "name": "witness_exception",
        "description": (
            "Show exception frames with local variable state — the actual values "
            "in scope when the exception fired. Critical for debugging 'why did this fail'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "exc_type": {
                    "type": "string",
                    "description": "Exception type name (substring match, e.g. 'ValueError', 'KeyError').",
                },
                "run_id": {
                    "type": "string",
                    "description": "Run ID to query. Omit for latest run.",
                },
            },
            "required": ["exc_type"],
        },
    },
    {
        "name": "witness_coverage_gaps",
        "description": (
            "Report lines in a source file that were never executed across recent witness runs. "
            "Reveals dead branches, untested paths, and unreachable code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "description": "Relative path to source file (e.g. 'mymodule/core.py').",
                },
            },
            "required": ["file"],
        },
    },
    {
        "name": "witness_diff",
        "description": (
            "Show what changed between two runs: newly failing/passing tests, "
            "functions that appeared or disappeared, call count changes, new exceptions. "
            "Use run IDs from witness_runs()."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_a": {
                    "type": "string",
                    "description": "Baseline run ID.",
                },
                "run_b": {
                    "type": "string",
                    "description": "Comparison run ID.",
                },
            },
            "required": ["run_a", "run_b"],
        },
    },
    {
        "name": "witness_check_charter",
        "description": (
            "Cross-reference a witness run against the project's active charter invariants "
            "and constraints. Surfaces calls that may violate prohibition-language entries "
            "(invariants/constraints with 'never', 'not', 'without', etc.). "
            "Reads .claude/charter.json — requires claude-charter to be seeded. "
            "Use this before accepting a fix to verify it doesn't violate a constraint."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {
                    "type": "string",
                    "description": "Run ID to audit. Omit for latest run.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "witness_hotspots",
        "description": (
            "Find functions with the most exceptions across recent runs. "
            "Surfaces chronic failure points — the places most likely to need attention. "
            "Use this to prioritize debugging effort."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max hotspots to show (default: 15).",
                    "default": 15,
                },
                "run_count": {
                    "type": "integer",
                    "description": "Number of recent runs to analyze (default: 5).",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
]


def dispatch(method: str, params: dict) -> str:
    if method == "witness_runs":
        return witness_runs(params.get("limit", 10))
    if method == "witness_traces":
        return witness_traces(
            params["fn_name"],
            params.get("run_id"),
            params.get("status"),
        )
    if method == "witness_exception":
        return witness_exception(params["exc_type"], params.get("run_id"))
    if method == "witness_coverage_gaps":
        return witness_coverage_gaps(params["file"])
    if method == "witness_diff":
        return witness_diff(params["run_a"], params["run_b"])
    if method == "witness_check_charter":
        return witness_check_charter(params.get("run_id"))
    if method == "witness_hotspots":
        return witness_hotspots(params.get("limit", 15), params.get("run_count", 5))
    raise ValueError(f"Unknown method: {method}")


def send(obj: dict):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle_request(req: dict):
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
                "serverInfo": {"name": "claude-witness", "version": VERSION},
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
