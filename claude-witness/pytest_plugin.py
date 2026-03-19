"""claude-witness pytest plugin.

Captures function calls, exceptions, and line coverage for project source files
during a pytest run. Writes a compact JSON trace to .claude/witness/<run_id>.json.

USAGE
-----
Option A — project conftest.py (recommended):
    # conftest.py in your project root
    import sys
    sys.path.insert(0, "/path/to/claude-witness")
    from pytest_plugin import *   # noqa: F401, F403

Option B — direct pytest plugin registration (pyproject.toml):
    [tool.pytest.ini_options]
    plugins = ["claude_witness.pytest_plugin"]

Then run with:
    pytest --witness

ENVIRONMENT VARIABLES
---------------------
CLAUDE_WITNESS_DIR   Store directory (default: .claude/witness)
WITNESS_MAX_DEPTH    Max call depth from test entry (default: 3)
WITNESS_MAX_CALLS    Max total calls captured per run (default: 5000)
"""

import json
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Support both direct import and package import
try:
    from claude_witness import serializer as _ser
except ImportError:
    try:
        from . import serializer as _ser
    except ImportError:
        # Last resort: same directory
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "serializer",
            Path(__file__).parent / "serializer.py"
        )
        _ser = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_ser)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_DEPTH = int(os.environ.get("WITNESS_MAX_DEPTH", "3"))
MAX_CALLS = int(os.environ.get("WITNESS_MAX_CALLS", "5000"))
_STORE_DIR = os.environ.get("CLAUDE_WITNESS_DIR", ".claude/witness")

# ---------------------------------------------------------------------------
# Project root detection
# ---------------------------------------------------------------------------

def _find_project_root() -> str:
    """Find project root by walking up from cwd looking for project markers."""
    cwd = Path.cwd()
    markers = ("pyproject.toml", "setup.py", "setup.cfg", ".git", "pytest.ini", "tox.ini")
    p = cwd
    for _ in range(6):
        if any((p / m).exists() for m in markers):
            return str(p)
        parent = p.parent
        if parent == p:
            break
        p = parent
    return str(cwd)


def _is_project_file(filepath: str, project_root: str) -> bool:
    """True if this is a project source file we should trace."""
    if not filepath or filepath == "<string>":
        return False
    try:
        rel = os.path.relpath(filepath, project_root)
    except ValueError:
        return False
    if rel.startswith(".."):
        return False
    # Skip virtualenv / site-packages
    if "site-packages" in filepath or "dist-packages" in filepath:
        return False
    # Skip the witness plugin itself
    if "claude-witness" in filepath or "claude_witness" in filepath:
        return False
    # Only .py files
    if not filepath.endswith(".py"):
        return False
    return True


def _rel(filepath: str, project_root: str) -> str:
    try:
        return os.path.relpath(filepath, project_root)
    except ValueError:
        return filepath


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------

class WitnessTracer:
    """sys.settrace() callback that records calls, exceptions, and line coverage.

    Depth is counted in project-source frames only — pytest's own call stack
    is ignored. This keeps depth semantics intuitive and avoids the issue where
    pytest's internal frames inflate the depth before the test body runs.
    """

    def __init__(self, project_root: str, max_depth: int = MAX_DEPTH, max_calls: int = MAX_CALLS):
        self.project_root = project_root
        self.max_depth = max_depth
        self.max_calls = max_calls

        self.calls: list = []
        self.exceptions: list = []
        self.coverage: dict = {}   # rel_path -> set of int line numbers

        self._call_count = 0
        self._project_depth = 0    # depth within project source files only
        self._current_test: str = ""
        self._exc_seen: set = set()  # (type, file, line) dedup within a test

    # --- test lifecycle ---

    def start_test(self, test_name: str):
        self._current_test = test_name
        self._project_depth = 0    # reset for each test
        self._exc_seen.clear()     # reset dedup per test
        sys.settrace(self.trace)

    def stop_test(self):
        sys.settrace(None)
        self._project_depth = 0

    # --- trace callback ---

    def trace(self, frame, event, arg):
        filepath = frame.f_code.co_filename

        if event == "call":
            if not _is_project_file(filepath, self.project_root):
                # Return self.trace so we still receive line/return/exception
                # in non-project frames (needed for accurate exception capture).
                return self.trace

            self._project_depth += 1
            rel = _rel(filepath, self.project_root)
            self._record_line(rel, frame.f_lineno)

            if self._call_count < self.max_calls and self._project_depth <= self.max_depth:
                fn = frame.f_code.co_name
                module = frame.f_globals.get("__name__", "")
                qualified = f"{module}.{fn}" if module else fn

                self.calls.append({
                    "id": f"c{self._call_count:05d}",
                    "test": self._current_test,
                    "fn": qualified,
                    "file": rel,
                    "line": frame.f_lineno,
                    "depth": self._project_depth,
                    "args": _ser.safe_args(frame),
                    "return": None,
                    "exception": None,
                })
                self._call_count += 1
            return self.trace

        elif event == "line":
            if _is_project_file(filepath, self.project_root):
                self._record_line(_rel(filepath, self.project_root), frame.f_lineno)
            return self.trace

        elif event == "return":
            if _is_project_file(filepath, self.project_root):
                self._project_depth = max(0, self._project_depth - 1)
                rel = _rel(filepath, self.project_root)
                fn = frame.f_code.co_name
                module = frame.f_globals.get("__name__", "")
                qualified = f"{module}.{fn}" if module else fn

                # Annotate the most recent open call for this function
                for call in reversed(self.calls):
                    if (call["fn"] == qualified and call["file"] == rel
                            and call["return"] is None and call["exception"] is None
                            and call["test"] == self._current_test):
                        call["return"] = _ser.safe_serialize(arg)
                        break
            return self.trace

        elif event == "exception":
            exc_type, exc_value, _ = arg
            if not _is_project_file(filepath, self.project_root):
                return self.trace
            rel = _rel(filepath, self.project_root)
            exc_name = exc_type.__name__ if exc_type else "Unknown"
            # Dedup: only record first occurrence of (type, file, line) per test
            dedup_key = (exc_name, rel, frame.f_lineno)
            if dedup_key not in self._exc_seen:
                self._exc_seen.add(dedup_key)
                self.exceptions.append({
                    "test": self._current_test,
                    "type": exc_name,
                    "message": _ser.safe_serialize(str(exc_value)) if exc_value else "",
                    "file": rel,
                    "line": frame.f_lineno,
                    "locals": _ser.safe_locals(frame.f_locals),
                })
            # Annotate the matching open call as exception
            for call in reversed(self.calls):
                if (call["file"] == rel and call["return"] is None
                        and call["exception"] is None
                        and call["test"] == self._current_test):
                    call["exception"] = exc_type.__name__ if exc_type else "Unknown"
                    break
            return self.trace

        return self.trace

    def _record_line(self, rel: str, lineno: int):
        if rel not in self.coverage:
            self.coverage[rel] = set()
        self.coverage[rel].add(lineno)

    def to_dict(self) -> dict:
        return {
            "calls": self.calls,
            "exceptions": self.exceptions,
            "coverage": {k: sorted(v) for k, v in self.coverage.items()},
        }


# ---------------------------------------------------------------------------
# pytest hooks
# ---------------------------------------------------------------------------

# Module-level plugin state (one per pytest session)
_tracer: "WitnessTracer | None" = None
_run_data: "dict | None" = None
_run_id: "str | None" = None
_enabled: bool = False


def pytest_addoption(parser):
    group = parser.getgroup("claude-witness")
    group.addoption(
        "--witness",
        action="store_true",
        default=False,
        help="Enable claude-witness execution tracing. Writes .claude/witness/<run_id>.json.",
    )
    group.addoption(
        "--witness-depth",
        type=int,
        default=MAX_DEPTH,
        metavar="N",
        help=f"Max call depth from test entry point (default: {MAX_DEPTH}).",
    )
    group.addoption(
        "--witness-max-calls",
        type=int,
        default=MAX_CALLS,
        metavar="N",
        help=f"Max calls to capture per run (default: {MAX_CALLS}).",
    )


def pytest_configure(config):
    global _tracer, _run_data, _run_id, _enabled
    try:
        _enabled = config.getoption("--witness")
    except ValueError:
        _enabled = False

    if not _enabled:
        return

    depth = config.getoption("--witness-depth", default=MAX_DEPTH)
    max_calls = config.getoption("--witness-max-calls", default=MAX_CALLS)
    project_root = _find_project_root()
    _tracer = WitnessTracer(project_root, max_depth=depth, max_calls=max_calls)
    _run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    _run_data = {
        "run_id": _run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "project_root": project_root,
        "tests": [],
        "calls": [],
        "exceptions": [],
        "coverage": {},
        "call_count": 0,
    }
    print(f"\nclaude-witness: tracing enabled (run_id={_run_id})", file=sys.stderr)


def pytest_runtest_setup(item):
    if not _enabled or _tracer is None:
        return
    _tracer.start_test(item.nodeid)


def pytest_runtest_teardown(item, nextitem):
    if not _enabled or _tracer is None:
        return
    _tracer.stop_test()


def pytest_runtest_logreport(report):
    global _run_data
    if not _enabled or _run_data is None or report.when != "call":
        return
    status = "pass" if report.passed else ("fail" if report.failed else "skip")
    _run_data["tests"].append({
        "name": report.nodeid,
        "status": status,
        "duration": round(getattr(report, "duration", 0.0), 4),
    })
    if status == "fail":
        _run_data["status"] = "fail"


def pytest_sessionfinish(session, exitstatus):
    global _tracer, _run_data, _run_id
    if not _enabled or _tracer is None or _run_data is None:
        return

    sys.settrace(None)

    # Merge tracer data
    tracer_dict = _tracer.to_dict()
    _run_data["calls"] = tracer_dict["calls"]
    _run_data["exceptions"] = tracer_dict["exceptions"]
    _run_data["coverage"] = tracer_dict["coverage"]
    _run_data["call_count"] = len(_run_data["calls"])

    # Write store (atomic: tempfile + rename)
    store_dir = Path(_STORE_DIR)
    store_dir.mkdir(parents=True, exist_ok=True)
    out_path = store_dir / f"{_run_id}.json"
    fd, tmp_path = tempfile.mkstemp(dir=store_dir, suffix=".tmp", prefix=".witness-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(_run_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(out_path))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    n_tests = len(_run_data["tests"])
    n_calls = _run_data["call_count"]
    n_exc = len(_run_data["exceptions"])
    print(
        f"claude-witness: {n_tests} tests, {n_calls} calls, {n_exc} exceptions → {out_path}",
        file=sys.stderr,
    )
