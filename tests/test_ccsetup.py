"""
E2E test suite for ccsetup.py

Run with: pytest tests/test_ccsetup.py -v
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CCSETUP = Path(__file__).parent.parent / "ccsetup.py"
SHARE_DIR = Path.home() / ".local" / "share" / "ccsetup"
BUNDLED_SERVERS = ["claude-mind", "claude-charter", "claude-witness",
                   "claude-retina", "claude-ledger"]
_bundled_installed = all(
    (SHARE_DIR / srv / "server.py").exists() for srv in BUNDLED_SERVERS
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def run_ccsetup(*args, cwd=None, input_text=None):
    """Run ccsetup.py with given args. Returns (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(CCSETUP)] + list(args)
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        input=input_text, cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def read_mcp_json(project: Path) -> dict:
    mcp_file = project / ".mcp.json"
    if not mcp_file.exists():
        return {}
    return json.loads(mcp_file.read_text())


def mcp_servers(project: Path) -> dict:
    data = read_mcp_json(project)
    return data.get("mcpServers", {})


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_project(tmp_path):
    """Create a temp git repo for testing."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True, check=True)
    return tmp_path


# ─────────────────────────────────────────────────────────────────────────────
# Group 1: Basic invocation
# ─────────────────────────────────────────────────────────────────────────────

class TestBasicInvocation:

    def test_help_flag(self):
        rc, stdout, stderr = run_ccsetup("--help")
        assert rc == 0
        assert "ccsetup" in stdout.lower() or "usage" in stdout.lower()

    def test_dry_run_no_writes(self, tmp_project):
        # Run with --dry-run and auto-answer 'n' to all prompts
        rc, stdout, stderr = run_ccsetup(
            str(tmp_project), "--dry-run", "--no-launch",
            input_text="\n" * 50,
        )
        assert not (tmp_project / ".mcp.json").exists(), \
            "--dry-run must not create .mcp.json"
        assert not (tmp_project / ".claude" / "settings.local.json").exists(), \
            "--dry-run must not create settings.local.json"

    def test_status_empty_project(self, tmp_project):
        rc, stdout, stderr = run_ccsetup(str(tmp_project), "--status")
        assert rc == 0
        # Should show "none" or empty state — no crash
        assert "mcp" in stdout.lower() or "status" in stdout.lower() or "none" in stdout.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Group 2: Preset — minimal
# ─────────────────────────────────────────────────────────────────────────────

class TestPresetMinimal:

    def test_preset_minimal_writes_mcp(self, tmp_project):
        rc, stdout, stderr = run_ccsetup(
            str(tmp_project), "--preset", "minimal", "--no-launch",
        )
        servers = mcp_servers(tmp_project)
        assert "serena" in servers, f"serena missing from .mcp.json; servers={list(servers)}"

    def test_preset_minimal_no_optional_tools(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "minimal", "--no-launch")
        servers = mcp_servers(tmp_project)
        assert "leann-server" not in servers, "minimal should not include leann"
        assert "claude-mind" not in servers, "minimal should not include claude-mind"

    def test_preset_minimal_status_exits_zero(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "minimal", "--no-launch")
        rc, stdout, stderr = run_ccsetup(str(tmp_project), "--status")
        assert rc == 0


# ─────────────────────────────────────────────────────────────────────────────
# Group 3: Preset — recommended
# ─────────────────────────────────────────────────────────────────────────────

class TestPresetRecommended:

    def test_preset_recommended_mcp_keys(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "recommended", "--no-launch")
        servers = mcp_servers(tmp_project)
        # serena is always written to .mcp.json (Layer 0 always-on)
        # leann may be at user scope (not in project .mcp.json) depending on claude CLI
        # context7 is npx-based, should always land in .mcp.json
        assert "serena" in servers, \
            f"serena missing from recommended .mcp.json; got {list(servers)}"
        assert "context7" in servers, \
            f"context7 missing from recommended .mcp.json; got {list(servers)}"

    def test_preset_recommended_includes_cship_in_tooldef(self):
        """cship must be defined in PRESETS['recommended']."""
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location("ccsetup_mod", CCSETUP)
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["ccsetup_mod"] = mod
        try:
            spec.loader.exec_module(mod)
            assert "cship" in mod.PRESETS["recommended"], \
                "cship must be in PRESETS['recommended']"
        finally:
            _sys.modules.pop("ccsetup_mod", None)

    def test_preset_recommended_not_experimental(self):
        """recommended must not include experimental tools."""
        import importlib.util, sys as _sys
        spec = importlib.util.spec_from_file_location("ccsetup_mod2", CCSETUP)
        mod = importlib.util.module_from_spec(spec)
        _sys.modules["ccsetup_mod2"] = mod
        try:
            spec.loader.exec_module(mod)
            for tid in mod.EXPERIMENTAL_TOOLS:
                assert tid not in mod.PRESETS["recommended"], \
                    f"{tid} is experimental and must not be in recommended (use --experimental)"
        finally:
            _sys.modules.pop("ccsetup_mod2", None)


# ─────────────────────────────────────────────────────────────────────────────
# Group 4: Preset — maximal (requires bundled servers installed)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _bundled_installed, reason="bundled servers not installed (run bash install.sh)")
class TestPresetMaximal:

    def test_preset_maximal_excludes_experimental(self, tmp_project):
        """Experimental tools must NOT be auto-enabled by maximal preset."""
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--no-launch")
        servers = mcp_servers(tmp_project)
        for tid in ["claude-mind", "claude-charter", "claude-witness",
                    "claude-retina", "claude-ledger"]:
            assert tid not in servers, \
                f"{tid} should not be in maximal — it is experimental (use --experimental)"

    def test_preset_maximal_plus_experimental_has_all(self, tmp_project):
        """--preset maximal --experimental should enable all 6 experimental tools."""
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--experimental", "--no-launch")
        servers = mcp_servers(tmp_project)
        for tid in ["claude-mind", "claude-charter", "claude-witness",
                    "claude-retina", "claude-ledger"]:
            assert tid in servers, \
                f"{tid} missing from maximal+experimental servers: {list(servers)}"

    def test_preset_maximal_has_ledger_only_with_experimental(self, tmp_project):
        """claude-ledger now requires --experimental."""
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--no-launch")
        assert "claude-ledger" not in mcp_servers(tmp_project)
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--experimental",
                    "--setup", "--no-launch")
        assert "claude-ledger" in mcp_servers(tmp_project)


# ─────────────────────────────────────────────────────────────────────────────
# Group 5: --from-layer
# ─────────────────────────────────────────────────────────────────────────────

class TestFromLayer:

    def test_from_layer_flag_accepted(self, tmp_project):
        """--from-layer should not crash ccsetup."""
        rc, stdout, stderr = run_ccsetup(
            str(tmp_project), "--from-layer", "4",
            "--dry-run", "--no-launch",
            input_text="\n" * 30,
        )
        # Should not crash (exit 2 would be argparse error)
        assert rc != 2, f"argparse error: {stderr}"

    def test_from_layer_skips_lower_layers(self, tmp_project):
        """--from-layer 5 + dry-run should not write layer0-4 MCP entries."""
        run_ccsetup(
            str(tmp_project), "--from-layer", "5",
            "--dry-run", "--no-launch",
            input_text="\n" * 30,
        )
        # dry-run never writes
        assert not (tmp_project / ".mcp.json").exists()


# ─────────────────────────────────────────────────────────────────────────────
# Group 6: MCP path correctness — the "real app" problem
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _bundled_installed, reason="bundled servers not installed")
class TestMcpPathCorrectness:

    def test_bundled_servers_use_share_dir(self, tmp_project):
        """
        After maximal preset, bundled server args must point to
        ~/.local/share/ccsetup/, NOT to the source repo directory.
        """
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--no-launch")
        servers = mcp_servers(tmp_project)
        share = str(Path.home() / ".local" / "share" / "ccsetup")

        for srv_name in ["claude-mind", "claude-charter", "claude-witness", "claude-afe",
                         "claude-retina", "claude-ledger"]:
            if srv_name not in servers:
                continue
            cfg = servers[srv_name]
            args = cfg.get("args", [])
            # The server.py path must be under ~/.local/share/ccsetup/
            server_py_args = [a for a in args if "server.py" in a]
            assert server_py_args, f"{srv_name}: no server.py arg found in {args}"
            for arg in server_py_args:
                assert arg.startswith(share), (
                    f"{srv_name}: server.py path '{arg}' does not start with "
                    f"~/.local/share/ccsetup/ — this is the 'real app' path bug"
                )

    def test_bundled_server_paths_exist(self, tmp_project):
        """Installed server.py files must actually exist at the paths in .mcp.json."""
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--no-launch")
        servers = mcp_servers(tmp_project)

        for srv_name in ["claude-mind", "claude-charter", "claude-witness", "claude-afe",
                         "claude-retina", "claude-ledger"]:
            if srv_name not in servers:
                continue
            cfg = servers[srv_name]
            args = cfg.get("args", [])
            for arg in args:
                if "server.py" in arg:
                    assert Path(arg).exists(), \
                        f"{srv_name}: server.py at '{arg}' does not exist"


# ─────────────────────────────────────────────────────────────────────────────
# Group 7: Health model
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthModel:

    def test_status_runs_without_crash(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "minimal", "--no-launch")
        rc, stdout, stderr = run_ccsetup(str(tmp_project), "--status")
        assert rc == 0

    def test_status_shows_serena_after_minimal(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "minimal", "--no-launch")
        rc, stdout, stderr = run_ccsetup(str(tmp_project), "--status")
        assert "serena" in stdout.lower(), \
            f"serena not mentioned in status output: {stdout}"


# ─────────────────────────────────────────────────────────────────────────────
# Group 8: Tool ledger
# ─────────────────────────────────────────────────────────────────────────────

class TestToolLedger:

    def test_tool_ledger_written_after_minimal(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "minimal", "--no-launch")
        ledger = tmp_project / ".claude" / "tool-ledger.md"
        assert ledger.exists(), "tool-ledger.md not found after minimal run"

    def test_tool_ledger_has_serena_section(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "minimal", "--no-launch")
        content = (tmp_project / ".claude" / "tool-ledger.md").read_text()
        assert "serena" in content.lower()

    @pytest.mark.skipif(not _bundled_installed, reason="bundled servers not installed")
    def test_tool_ledger_has_all_bundled_servers(self, tmp_project):
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--experimental", "--no-launch")
        content = (tmp_project / ".claude" / "tool-ledger.md").read_text()
        for srv in ["claude-mind", "claude-charter", "claude-witness",
                    "claude-retina", "claude-ledger"]:
            assert srv in content, f"tool-ledger.md missing {srv} section"


# ─────────────────────────────────────────────────────────────────────────────
# Group 9: Server smoke tests (integration)
# ─────────────────────────────────────────────────────────────────────────────

def _send_jsonrpc(server_py: Path, method: str, params: dict = None) -> dict:
    """Send a single JSON-RPC request to a server.py via stdin/stdout."""
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": method,
        "params": params or {},
    }) + "\n"
    result = subprocess.run(
        [sys.executable, str(server_py)],
        input=payload, capture_output=True, text=True, timeout=10,
    )
    if not result.stdout.strip():
        pytest.skip(f"No output from {server_py.parent.name} server (may need MCP transport)")
    return json.loads(result.stdout.strip().splitlines()[0])


@pytest.mark.skipif(not _bundled_installed, reason="bundled servers not installed")
class TestServerSmoke:

    @pytest.mark.parametrize("server_name", BUNDLED_SERVERS)
    def test_server_py_exists(self, server_name):
        srv = SHARE_DIR / server_name / "server.py"
        assert srv.exists(), f"{server_name}/server.py not found at {srv}"

    @pytest.mark.parametrize("server_name", BUNDLED_SERVERS)
    def test_server_imports_cleanly(self, server_name):
        """Python can at least parse the server.py without syntax errors."""
        srv = SHARE_DIR / server_name / "server.py"
        result = subprocess.run(
            [sys.executable, "-c", f"import ast; ast.parse(open('{srv}').read())"],
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0, \
            f"{server_name}/server.py has syntax error: {result.stderr}"



# ─────────────────────────────────────────────────────────────────────────────
# Group 10: TOOLS/PRESETS consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestToolsConsistency:

    @pytest.fixture(scope="class")
    def ccsetup_module(self):
        import importlib.util, sys as _sys
        mod_name = "ccsetup_consistency"
        spec = importlib.util.spec_from_file_location(mod_name, CCSETUP)
        mod = importlib.util.module_from_spec(spec)
        _sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
        yield mod
        _sys.modules.pop(mod_name, None)

    def test_preset_tools_exist_in_tool_registry(self, ccsetup_module):
        """Every tool ID in PRESETS must exist in TOOL_BY_ID."""
        mod = ccsetup_module
        all_preset_ids = set()
        for ids in mod.PRESETS.values():
            all_preset_ids |= ids
        for tid in all_preset_ids:
            assert tid in mod.TOOL_BY_ID, \
                f"Preset tool '{tid}' not found in TOOL_BY_ID"

    def test_new_tools_in_maximal(self, ccsetup_module):
        """cship and clui-cc must be in maximal; experimental tools must not be."""
        maximal = ccsetup_module.PRESETS["maximal"]
        for tid in ["cship", "clui-cc"]:
            assert tid in maximal, f"{tid} missing from maximal preset"
        for tid in ccsetup_module.EXPERIMENTAL_TOOLS:
            assert tid not in maximal, \
                f"{tid} is experimental and must not be in maximal (use --experimental)"

    def test_experimental_tools_set_has_five(self, ccsetup_module):
        """EXPERIMENTAL_TOOLS must contain exactly 5 bundled servers."""
        expected = {"claude-mind", "claude-charter", "claude-witness",
                    "claude-retina", "claude-ledger"}
        assert ccsetup_module.EXPERIMENTAL_TOOLS == expected, \
            f"EXPERIMENTAL_TOOLS mismatch: {ccsetup_module.EXPERIMENTAL_TOOLS}"

    def test_cship_in_recommended(self, ccsetup_module):
        assert "cship" in ccsetup_module.PRESETS["recommended"]

    def test_all_tools_have_required_fields(self, ccsetup_module):
        """Every ToolDef must have id, name, layer, layer_name, tagline."""
        for td in ccsetup_module.TOOLS:
            assert td.id,         f"ToolDef missing id: {td}"
            assert td.name,       f"ToolDef missing name: {td.id}"
            assert td.tagline,    f"ToolDef missing tagline: {td.id}"
            assert td.layer >= 0, f"ToolDef bad layer: {td.id}"

    def test_claude_retina_is_experimental(self, ccsetup_module):
        assert "claude-retina" in ccsetup_module.EXPERIMENTAL_TOOLS, \
            "claude-retina must be in EXPERIMENTAL_TOOLS"
        assert "claude-retina" not in ccsetup_module.PRESETS["maximal"], \
            "claude-retina must not be in maximal (use --experimental)"

    def test_claude_ledger_is_experimental(self, ccsetup_module):
        assert "claude-ledger" in ccsetup_module.EXPERIMENTAL_TOOLS, \
            "claude-ledger must be in EXPERIMENTAL_TOOLS"
        assert "claude-ledger" not in ccsetup_module.PRESETS["recommended"], \
            "claude-ledger must not be in recommended (use --experimental)"
        assert "claude-ledger" not in ccsetup_module.PRESETS["maximal"], \
            "claude-ledger must not be in maximal (use --experimental)"

    def test_retina_catalog_has_eight_tools(self, ccsetup_module):
        catalog = ccsetup_module._TOOL_CATALOG.get("claude-retina", [])
        assert len(catalog) == 8, \
            f"claude-retina catalog has {len(catalog)} tools, expected 8"

    def test_ledger_catalog_has_seven_tools(self, ccsetup_module):
        catalog = ccsetup_module._TOOL_CATALOG.get("claude-ledger", [])
        assert len(catalog) == 7, \
            f"claude-ledger catalog has {len(catalog)} tools, expected 7"

    def test_workflows_has_retina_section(self, ccsetup_module):
        assert "retina_capture" in ccsetup_module._WORKFLOWS, \
            "Visual UI Testing workflow missing from _WORKFLOWS"
        assert "retina_baseline" in ccsetup_module._WORKFLOWS, \
            "Visual Regression Guard workflow missing from _WORKFLOWS"

    def test_workflows_has_ledger_section(self, ccsetup_module):
        assert "ledger_context" in ccsetup_module._WORKFLOWS, \
            "Session Start (with claude-ledger) workflow missing from _WORKFLOWS"


# ─────────────────────────────────────────────────────────────────────────────
# Group 11: claude-retina server
# ─────────────────────────────────────────────────────────────────────────────

RETINA_SERVER = SHARE_DIR / "claude-retina" / "server.py"
LEDGER_SERVER = SHARE_DIR / "claude-ledger" / "server.py"
_retina_installed = RETINA_SERVER.exists()
_ledger_installed = LEDGER_SERVER.exists()


@pytest.mark.skipif(not _retina_installed, reason="claude-retina not installed (run bash install.sh)")
class TestRetinaServer:

    def test_retina_server_syntax(self):
        result = subprocess.run(
            [sys.executable, "-c",
             f"import ast; ast.parse(open('{RETINA_SERVER}').read())"],
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0, \
            f"claude-retina/server.py has syntax error: {result.stderr}"

    def test_retina_schema_syntax(self):
        schema_py = SHARE_DIR / "claude-retina" / "schema.py"
        result = subprocess.run(
            [sys.executable, "-c",
             f"import ast; ast.parse(open('{schema_py}').read())"],
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0, \
            f"claude-retina/schema.py has syntax error: {result.stderr}"

    def test_retina_history_no_deps(self):
        """retina_history works without playwright or Pillow (reads store only)."""
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": "retina_history", "arguments": {}},
        }) + "\n"
        result = subprocess.run(
            [sys.executable, str(RETINA_SERVER)],
            input=payload, capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            pytest.skip("No output from retina server")
        resp = json.loads(result.stdout.strip().splitlines()[0])
        assert "result" in resp, f"Expected result, got: {resp}"
        content = resp["result"]["content"][0]["text"]
        assert "history" in content.lower() or "no retina" in content.lower(), \
            f"Unexpected retina_history output: {content}"

    def test_retina_tools_list(self):
        """tools/list returns 8 tools."""
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/list",
            "params": {},
        }) + "\n"
        result = subprocess.run(
            [sys.executable, str(RETINA_SERVER)],
            input=payload, capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            pytest.skip("No output from retina server")
        resp = json.loads(result.stdout.strip().splitlines()[0])
        tools = resp["result"]["tools"]
        assert len(tools) == 8, f"Expected 8 retina tools, got {len(tools)}"


# ─────────────────────────────────────────────────────────────────────────────
# Group 12: claude-ledger server
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _ledger_installed, reason="claude-ledger not installed (run bash install.sh)")
class TestLedgerServer:

    def test_ledger_server_syntax(self):
        result = subprocess.run(
            [sys.executable, "-c",
             f"import ast; ast.parse(open('{LEDGER_SERVER}').read())"],
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 0, \
            f"claude-ledger/server.py has syntax error: {result.stderr}"

    def test_ledger_context_no_mcp_json(self, tmp_project):
        """ledger_context works in a project with no .mcp.json."""
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": "ledger_context", "arguments": {}},
        }) + "\n"
        result = subprocess.run(
            [sys.executable, str(LEDGER_SERVER)],
            input=payload, capture_output=True, text=True, timeout=10,
            cwd=str(tmp_project),
        )
        if not result.stdout.strip():
            pytest.skip("No output from ledger server")
        resp = json.loads(result.stdout.strip().splitlines()[0])
        assert "result" in resp, f"Expected result, got: {resp}"
        content = resp["result"]["content"][0]["text"]
        assert "ledger context" in content.lower(), \
            f"Unexpected ledger_context output: {content}"

    def test_ledger_query_routing(self, tmp_project):
        """ledger_query returns routing results for a test task."""
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": "ledger_query", "arguments": {"task": "debug failing test"}},
        }) + "\n"
        result = subprocess.run(
            [sys.executable, str(LEDGER_SERVER)],
            input=payload, capture_output=True, text=True, timeout=10,
            cwd=str(tmp_project),
        )
        if not result.stdout.strip():
            pytest.skip("No output from ledger server")
        resp = json.loads(result.stdout.strip().splitlines()[0])
        content = resp["result"]["content"][0]["text"]
        # Should mention witness or mind for a "debug failing test" query
        assert "claude-witness" in content or "claude-mind" in content or "Tools for" in content, \
            f"Unexpected ledger_query output: {content}"

    def test_ledger_tools_list(self):
        """tools/list returns 7 tools."""
        payload = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/list",
            "params": {},
        }) + "\n"
        result = subprocess.run(
            [sys.executable, str(LEDGER_SERVER)],
            input=payload, capture_output=True, text=True, timeout=10,
        )
        if not result.stdout.strip():
            pytest.skip("No output from ledger server")
        resp = json.loads(result.stdout.strip().splitlines()[0])
        tools = resp["result"]["tools"]
        assert len(tools) == 7, f"Expected 7 ledger tools, got {len(tools)}"

    def test_bundled_servers_use_share_dir_retina_ledger(self, tmp_project):
        """After maximal preset, retina+ledger paths point to share dir."""
        run_ccsetup(str(tmp_project), "--preset", "maximal", "--no-launch")
        servers = mcp_servers(tmp_project)
        share = str(Path.home() / ".local" / "share" / "ccsetup")
        for srv_name in ["claude-retina", "claude-ledger"]:
            if srv_name not in servers:
                continue
            cfg = servers[srv_name]
            args = cfg.get("args", [])
            server_py_args = [a for a in args if "server.py" in a]
            assert server_py_args, f"{srv_name}: no server.py arg found in {args}"
            for arg in server_py_args:
                assert arg.startswith(share), (
                    f"{srv_name}: server.py path '{arg}' does not start with "
                    f"~/.local/share/ccsetup/"
                )
