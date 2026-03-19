#!/usr/bin/env python3
"""
ccsetup — Per-repo Claude Code stack bootstrapper

Designed from Claude's perspective as the primary user.
Configures a curated, hierarchical tool ecosystem for any repository.

Usage:
  ccsetup [.]                    Interactive setup
  ccsetup . --status             Health-aware status report
  ccsetup . --manifest           Generate .claude/tool-ledger.md (capability matrix)
  ccsetup . --dry-run            Preview without writing
  ccsetup . --no-launch          Skip 'dgc .' at the end
  ccsetup . --from-layer N       Resume from layer N (0–6)
  ccsetup . --preset minimal     Layer 0 only (Serena + GrapeRoot)
  ccsetup . --preset recommended Layers 0–2 + ccusage
  ccsetup . --preset maximal     All layers, sane defaults
  ccsetup . --yes                Accept all defaults non-interactively
  ccsetup . --scope-mode repo    All MCPs to .mcp.json (project only)
  ccsetup . --scope-mode user    Global installs preferred
  ccsetup . --scope-mode hybrid  Smart split — default

Tool Layers:
  0  Foundation      Serena (LSP) + GrapeRoot (dgc)              always-on
  1  Context         LEANN, Context7, claude-witness              smart retrieval
  2  Memory          claude-mind, claude-charter, claude-session cross-session
  3  Safety          parry, claude-plan-reviewer, TDD Guard      guardrails
  4  Observability   ccusage, claude-esp, cclogviewer, claudio   telemetry
  5  Orchestration   seu-claude                                  scaling
  6  Workflow        CodeGraphContext, remote-approver, smart-fork utilities
"""

from __future__ import annotations

import argparse
import http.server
import io
import json
import os
import queue
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

VERSION = "1.0.1"

_USE_COLOR = sys.stdout.isatty()
RESET  = "\033[0m"   if _USE_COLOR else ""
BOLD   = "\033[1m"   if _USE_COLOR else ""
DIM    = "\033[2m"   if _USE_COLOR else ""
GREEN  = "\033[32m"  if _USE_COLOR else ""
YELLOW = "\033[33m"  if _USE_COLOR else ""
RED    = "\033[31m"  if _USE_COLOR else ""
CYAN   = "\033[36m"  if _USE_COLOR else ""
BLUE   = "\033[34m"  if _USE_COLOR else ""

# ─────────────────────────────────────────────────────────────────────────────
# Health model
# ─────────────────────────────────────────────────────────────────────────────

class ToolHealth(Enum):
    HEALTHY         = "healthy"           # installed, configured, likely runnable
    CONFIGURED_ONLY = "configured_only"   # in .mcp.json but binary not found
    MISSING_BINARY  = "missing_binary"    # binary absent from PATH
    MISSING_ENV     = "missing_env"       # required env vars not set
    MANUAL_REQUIRED = "manual_required"   # documented only, no automation yet
    USER_SCOPE      = "user_scope"        # installed globally, not in .mcp.json
    NOT_CONFIGURED  = "not_configured"    # not set up at all
    SKIPPED         = "skipped"           # user declined

_HEALTH_DISPLAY: dict[ToolHealth, tuple[str, str, str]] = {
    # health                       color    icon  label
    ToolHealth.HEALTHY:         (GREEN,  "✔",  "healthy"),
    ToolHealth.CONFIGURED_ONLY: (YELLOW, "◐",  "configured (binary missing)"),
    ToolHealth.MISSING_BINARY:  (RED,    "✘",  "missing binary"),
    ToolHealth.MISSING_ENV:     (YELLOW, "!",  "missing env vars"),
    ToolHealth.MANUAL_REQUIRED: (CYAN,   "→",  "manual steps needed"),
    ToolHealth.USER_SCOPE:      (BLUE,   "◉",  "user-scope (all repos)"),
    ToolHealth.NOT_CONFIGURED:  (DIM,    "○",  "not configured"),
    ToolHealth.SKIPPED:         (DIM,    "—",  "skipped"),
}


@dataclass
class SetupResult:
    tool_id:    str
    tool_name:  str
    layer:      int
    health:     ToolHealth
    notes:      list[str] = field(default_factory=list)
    env_vars:   list[str] = field(default_factory=list)
    manual_steps: list[str] = field(default_factory=list)


@dataclass
class ToolDef:
    id:            str
    name:          str
    layer:         int
    layer_name:    str
    tagline:       str
    description:   str
    why_i_want_it: str
    skip_when:     str
    always_on:     bool       = False
    deprecated:    bool       = False
    invasive:      bool       = False
    manual_only:   bool       = False
    privacy_concern: bool     = False
    experimental:  bool       = False
    presets:       list[str]  = field(default_factory=list)
    binary:        str        = ""
    mcp_key:       str        = ""
    env_vars:      list[str]  = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Global state
# ─────────────────────────────────────────────────────────────────────────────

_DRY_RUN:        bool = False
_ASSUME_YES:     bool = False
_SCOPE_MODE:     str  = "hybrid"   # "repo" | "user" | "hybrid"
_PRESET_TOOLS:   set[str] = set()  # tool IDs auto-enabled by preset
_EXPERIMENTAL:   bool = False       # --experimental flag: enables mind/charter/witness/afe
_results:        list[SetupResult] = []

PRESETS: dict[str, set[str]] = {
    "minimal": {
        "serena", "graperoot",
    },
    "recommended": {
        "serena", "graperoot",
        "leann", "context7",
        "claude-session", "context-mode",
        "ccusage", "cship",
    },
    "maximal": {
        "serena", "graperoot",
        "leann", "context7",
        "claude-session", "context-mode",
        "ccusage", "cclogviewer", "claudio", "cship",
        "seu-claude", "codegraphcontext", "smart-fork",
        # Deliberately excluded from maximal: parry/tdd-guard/plan-reviewer (manual only),
        # claude-context (cloud deps), claude-esp (manual), remote-approver (manual),
        # clui-cc (manual-only macOS app), experimental tools (mind/charter/witness/retina/ledger)
    },
}

# Tools marked experimental — opt-in only, enabled via --experimental flag
EXPERIMENTAL_TOOLS: set[str] = {
    "claude-mind", "claude-charter", "claude-witness",
    "claude-retina", "claude-ledger",
}

# ─────────────────────────────────────────────────────────────────────────────
# Tool registry (drives GUI cards and CLI prompts)
# ─────────────────────────────────────────────────────────────────────────────

TOOLS: list[ToolDef] = [
    ToolDef("serena", "Serena", 0, "Foundation",
        tagline="IDE-like semantic codebase navigation via LSP",
        description="Symbol-aware navigation, definition/usage tracing, and structured code retrieval. Understands imports, classes, and functions across the entire project.",
        why_i_want_it="Without Serena, I'm grep-and-guessing. With it, I know exactly where every symbol is defined and referenced, which makes refactors safe and navigation instant.",
        skip_when="Never. Always-on.",
        always_on=True, presets=["minimal","recommended","maximal"],
        binary="uvx", mcp_key="serena"),

    ToolDef("graperoot", "GrapeRoot", 0, "Foundation",
        tagline="Precomputed dual graph of files, functions, imports, and calls",
        description="Builds a static call/import graph and pre-injects relevant context before I start thinking. Tracks session memory so follow-up turns route faster.",
        why_i_want_it="I stop rereading the repo every turn. The graph tells me what's connected before I ask. Cost and latency drop significantly on medium-to-large projects.",
        skip_when="Never. Launched via 'dgc .' at end of setup.",
        always_on=True, presets=["minimal","recommended","maximal"],
        binary="dgc"),

    ToolDef("leann", "LEANN", 1, "Context Intelligence",
        tagline="Local-first semantic code search — no cloud, no keys",
        description="AST-aware chunking with automatic language detection. Retrieves code by meaning, not exact text. Runs entirely on your machine.",
        why_i_want_it="When I need to find 'the function that handles authentication' without knowing its name, LEANN finds it. Privacy-first is the right default for most code.",
        skip_when="Serena + normal grep already covers retrieval needs, or the repo is small.",
        presets=["recommended","maximal"], binary="leann_mcp", mcp_key="leann-server"),

    ToolDef("claude-context", "Claude Context", 1, "Context Intelligence",
        tagline="Semantic search via Zilliz Cloud vector DB — enterprise scale",
        description="Similar to LEANN but cloud-hosted with external embedding models. Best for very large repos where enterprise-scale retrieval matters.",
        why_i_want_it="For massive monorepos where LEANN's local index becomes slow. The cloud infrastructure handles the heavy lifting.",
        skip_when="LEANN meets your needs, or data residency/privacy matters. Do NOT run both.",
        presets=[], binary="npx", mcp_key="Claude Context",
        env_vars=["ZILLIZ_CLOUD_URI","ZILLIZ_CLOUD_API_KEY","EMBEDDING_API_KEY"]),

    ToolDef("context7", "Context7", 1, "Context Intelligence",
        tagline="Live, version-accurate library docs injected into context",
        description="Fetches real-time documentation for external libraries and injects it before I answer. Eliminates hallucinations from stale post-training API knowledge.",
        why_i_want_it="I'm often wrong about library APIs that changed after my training cutoff. Context7 fetches the actual current docs so my answers are accurate.",
        skip_when="Work is almost entirely internal code with no external API surface.",
        presets=["recommended","maximal"], binary="npx", mcp_key="context7"),

    ToolDef("claude-witness", "claude-witness", 1, "Context Intelligence",
        tagline="Execution memory — what actually ran, with what args, from which tests",
        description="pytest plugin (+ vitest/jest/Go hooks) captures real function calls via sys.settrace. Queryable by function name, run, status, coverage gaps, and cross-run diff.",
        why_i_want_it="I confuse source truth with execution truth. Decorators, monkey-patching, DI, and async behavior mean what I infer from code isn't what ran. Witness gives empirical evidence.",
        skip_when="Project has no tests, or static code analysis covers your debugging needs.",
        experimental=True, presets=[], mcp_key="claude-witness"),

    ToolDef("claude-session", "claude-session-mcp", 2, "Memory & Continuity",
        tagline="Lossless session clone, archive, restore, and cross-machine transfer",
        description="Fork sessions, resume exact state across machines, archive project snapshots. Nothing gets trapped in a fragile terminal session.",
        why_i_want_it="Long sessions on complex projects accumulate critical context. Without session persistence, every restart means re-explaining everything from scratch.",
        skip_when="Workflow is short-lived or disposable. Pick ONE continuity tool — don't stack all three.",
        presets=["recommended","maximal"], binary="claude-session-mcp", mcp_key="claude-session"),

    ToolDef("context-mode", "context-mode", 2, "Memory & Continuity",
        tagline="Virtualizes tool outputs — keeps raw data out of the context window",
        description="Runs tools normally but only compressed/filtered outputs enter the model context. Indexes outputs locally for on-demand search. Resists auto-compaction.",
        why_i_want_it="Long tool-heavy sessions bloat context fast. Context-mode lets me run dozens of tool calls without burning the context window on repeated large outputs.",
        skip_when="Sessions are short or tool outputs are typically small. The overhead only pays off with heavy usage.",
        presets=["recommended","maximal"], binary="npx", mcp_key="context-mode"),

    ToolDef("claude-mind", "claude-mind", 2, "Memory & Continuity",
        tagline="Persistent investigation reasoning board — survives context compaction",
        description="Externalizes investigation state: hypotheses, facts, ruled-out paths, flagged assumptions. mind_summary() recovers full investigation state in ≤15 lines after compaction.",
        why_i_want_it="I reconstruct the same investigation from scratch every session after compaction. claude-mind stores what I've reasoned through so I don't re-eliminate already-dead paths.",
        skip_when="Work is single-session or never involves multi-turn debugging across compactions.",
        experimental=True, presets=[], mcp_key="claude-mind"),

    ToolDef("claude-charter", "claude-charter", 2, "Memory & Continuity",
        tagline="Project constitution — invariants, constraints, and non-goals that must hold",
        description="Stores architectural invariants, constraints, and non-goals. charter_check() flags conflicts before you make a change. The normative layer that tells me what matters.",
        why_i_want_it="I make technically correct but architecturally wrong changes without a clear model of what must stay true. charter_check is the normative feedback loop that doesn't exist elsewhere.",
        skip_when="Project has no stable architectural invariants, or is fully exploratory.",
        experimental=True, presets=[], mcp_key="claude-charter"),

    ToolDef("parry", "parry", 3, "Safety & Guardrails",
        tagline="Prompt injection + data exfiltration scanner via PreToolUse hook",
        description="Uses Aho-Corasick for known jailbreak patterns, optional DeBERTa ML for semantic classification, Tree-sitter AST to block ~/.ssh and .env leakage. Sub-10ms.",
        why_i_want_it="When I process untrusted tool outputs, web content, or tickets, I need a firewall between external data and my decision-making. Parry provides that.",
        skip_when="Workflow is fully trusted, developer-only, with no external input.",
        manual_only=True, presets=[], binary=""),

    ToolDef("plan-reviewer", "claude-plan-reviewer", 3, "Safety & Guardrails",
        tagline="Rival model critiques my plan before I execute it",
        description="Intercepts Claude's plan and sends it to GPT-4 or Gemini for critique. Feeds the review back, forcing revision. Reduces hallucinated architectures.",
        why_i_want_it="I have blind spots. A rival model reviewing my plan catches the assumptions I can't see. Especially valuable for architecture decisions and complex refactors.",
        skip_when="Privacy concerns or latency sensitivity. Plan contents are sent externally.",
        manual_only=True, privacy_concern=True, presets=[],
        env_vars=["OPENAI_API_KEY or GOOGLE_API_KEY"]),

    ToolDef("tdd-guard", "TDD Guard", 3, "Safety & Guardrails",
        tagline="Blocks file writes unless a failing test exists first",
        description="Hard-enforces Red-Green-Refactor via PreToolUse hook. Monitors Vitest, Pytest, Go test, PHPUnit before allowing Write/Edit/MultiEdit.",
        why_i_want_it="Left to my own judgment, I sometimes write the implementation before the test. TDD Guard removes that option and keeps the discipline enforced mechanically.",
        skip_when="You don't follow strict TDD, or the overhead outweighs the discipline benefit.",
        manual_only=True, presets=[], binary=""),

    ToolDef("ccusage", "ccusage", 4, "Observability",
        tagline="Terminal dashboard for token usage and costs — zero cloud exfiltration",
        description="Parses ~/.claude/*.jsonl locally. Daily, weekly, monthly, and per-session breakdowns. Runs in any terminal, no setup beyond install.",
        why_i_want_it="I burn tokens fast on complex tasks. Visibility into where tokens go lets me tune my approach and catch runaway sessions before they get expensive.",
        skip_when="Cost is irrelevant and you don't want another dashboard tool.",
        presets=["recommended","maximal"], binary="ccusage"),

    ToolDef("claude-esp", "claude-esp", 4, "Observability",
        tagline="Streams hidden thinking blocks and tool calls to a separate terminal",
        description="Real-time logic debugging without cluttering the main chat. Shows subagent communications and reasoning traces as they happen.",
        why_i_want_it="When I make a surprising decision, ESP lets you see exactly why. Invaluable for building trust, auditing autonomous operation, and catching reasoning errors.",
        skip_when="You just want to ship and don't need to inspect reasoning.",
        manual_only=True, presets=[], binary=""),

    ToolDef("cclogviewer", "cclogviewer", 4, "Observability",
        tagline="Converts session .jsonl logs to interactive HTML with full tool chains",
        description="Nested task views, complete tool-call chain transparency, shareable audit artifacts. After-the-fact session archaeology.",
        why_i_want_it="For post-session review, audits, and retrospectives. I can share a complete trace of exactly what I did and why with any stakeholder.",
        skip_when="ccusage already covers what you care about, or you rarely inspect logs.",
        presets=["maximal"], binary="cclogviewer"),

    ToolDef("claudio", "claudio", 4, "Observability",
        tagline="macOS system sounds on tool events — ambient session awareness",
        description="Plays a sound on PreToolUse and PostToolUse. Non-intrusive way to know a long background task finished without watching the terminal.",
        why_i_want_it="When I'm running a long autonomous task, you don't need to watch the screen. The sound tells you when something happens so you can check in when relevant.",
        skip_when="Non-macOS, or audio feedback is distracting.",
        presets=["maximal"], binary="/usr/bin/afplay"),

    # claude-retina (Layer 4 — Observability)
    ToolDef("claude-retina", "claude-retina", 4, "Observability",
        tagline="Visual browser automation — Claude gets eyes on the running UI",
        description="Headless Chromium via Playwright. Screenshot any URL, diff before/after, inspect accessibility trees, capture JS console errors, run click/type interaction sequences, and do visual regression testing against named baselines. Claude reads PNG files via the Read tool.",
        why_i_want_it="Currently I can only read HTML source and guess what it looks like. With retina I can see the actual rendered UI, verify that my changes look correct visually, and catch regressions before users do.",
        skip_when="Backend-only work with no frontend. Adds Playwright dependency.",
        experimental=True, presets=[], binary="", mcp_key="claude-retina"),

    ToolDef("seu-claude", "seu-claude", 5, "Orchestration",
        tagline="Persistent memory + tasks + sandbox + multi-agent orchestration",
        description="Persistent task state, dependency analysis, sandboxed execution, and multi-agent coordination in one package. Described as a 'nervous system for the terminal.'",
        why_i_want_it="For complex multi-session projects where I need crash recovery and task persistence. This is an operating environment, not just a helper — it changes how I work.",
        skip_when="Normal sessions are sufficient. This is powerful but heavy. Don't use it unless you need it.",
        presets=["maximal"], binary="npx", mcp_key="seu-claude"),

    ToolDef("codegraphcontext", "CodeGraphContext", 6, "Workflow",
        tagline="Explicit graph queries: callers, callees, call chains, class hierarchies",
        description="Indexes code into a knowledge graph for structural queries. Live updates, works across files. Answers 'what calls this function?' precisely.",
        why_i_want_it="Complements Serena's LSP for explicit graph traversal. When I need to trace a full call chain from an entry point, CGC gives me a direct answer.",
        skip_when="Serena or GrapeRoot already provide sufficient structural understanding. Avoid graph-tool redundancy.",
        presets=["maximal"], binary="cgc", mcp_key="codegraphcontext"),

    ToolDef("remote-approver", "claude-remote-approver", 6, "Workflow",
        tagline="Approval prompts forwarded to your phone via ntfy.sh",
        description="Forwards tool approval prompts to mobile via ntfy.sh. Approve or deny commands remotely. Supports configurable timeouts and Always Approve lists.",
        why_i_want_it="For overnight autonomous pipelines, I still need a human supervisor. Remote approver lets you stay in the loop without being at the keyboard.",
        skip_when="You prefer to be present for approvals, or don't want another operational service in the trust chain.",
        manual_only=True, presets=[], env_vars=["NTFY_TOPIC"]),

    ToolDef("smart-fork", "Smart Fork Detection", 6, "Workflow",
        tagline="Semantic search across past Claude Code session transcripts",
        description="Indexes old sessions into a vector database, searches by meaning, resumes the most relevant prior thread. Turns session history into a knowledge base.",
        why_i_want_it="When resuming a project after a break, I can find the exact prior session where we discussed this problem instead of starting from scratch.",
        skip_when="claude-session-mcp or seu-claude already cover your continuity needs. Don't stack memory systems.",
        presets=["maximal"], binary=""),

    # claude-ledger (Layer 5 — Orchestration)
    ToolDef("claude-ledger", "claude-ledger", 5, "Orchestration",
        tagline="Live capability map — routes Claude to the right tool for any task",
        description="Replaces the static tool-ledger.md with a live, queryable MCP server. Reads .mcp.json and .claude/ state in real time. ledger_query('task') returns an opinionated workflow. ledger_context() gives a session-start briefing with health + active investigation state.",
        why_i_want_it="Instead of scanning a stale markdown file, I can ask 'what should I use for X?' and get a structured, context-aware answer. ledger_context() replaces the need to read tool-ledger.md at session start.",
        skip_when="You prefer the static tool-ledger.md. No real downside to enabling this.",
        experimental=True, presets=[], binary="", mcp_key="claude-ledger"),

    # cship (Layer 4 — Observability)
    ToolDef("cship", "cship", 4, "Observability",
        tagline="Live Claude Code metrics in your shell prompt — cost, context %, model",
        description="Rust binary (<10ms) that renders real-time session metrics inline in the terminal prompt: cost, context window %, model name, API usage limits, sub-agent names. Integrates with Starship. Wires into ~/.claude/settings.json as the statusline provider.",
        why_i_want_it="I can see at a glance how much context I've used and what the session is costing without running a separate dashboard. Essential for autonomous long-running sessions where I need budget awareness.",
        skip_when="ccusage already covers your cost monitoring needs. cship is complementary but redundant if you're watching ccusage constantly.",
        presets=["recommended", "maximal"], binary="cship"),

]

TOOL_BY_ID: dict[str, ToolDef] = {t.id: t for t in TOOLS}

# ─────────────────────────────────────────────────────────────────────────────
# Output helpers
# ─────────────────────────────────────────────────────────────────────────────

def ok(msg: str)   -> None: print(f"  {GREEN}✔{RESET}  {msg}")
def warn(msg: str) -> None: print(f"  {YELLOW}⚠{RESET}  {msg}")
def err(msg: str)  -> None: print(f"  {RED}✘{RESET}  {msg}")
def info(msg: str) -> None: print(f"  {CYAN}→{RESET}  {msg}")
def dim(msg: str)  -> None: print(f"     {DIM}{msg}{RESET}")
def hr()           -> None: print(f"  {DIM}{'─' * 57}{RESET}")


def section(layer: int, name: str) -> None:
    print()
    label = f"LAYER {layer}" if layer >= 0 else "      "
    pad   = max(0, 44 - len(name) - len(label))
    print(f"{BOLD}{CYAN}  ══ {label}: {name.upper()} {'═' * pad}{RESET}")
    print()


def record(result: SetupResult) -> None:
    _results.append(result)


# ─────────────────────────────────────────────────────────────────────────────
# Prompting (preset- and --yes-aware)
# ─────────────────────────────────────────────────────────────────────────────

def ask_yes_no(prompt: str, default: bool = True, tool_id: str = "") -> bool:
    """Prompt user, respecting --yes and preset overrides."""
    if tool_id and tool_id in _PRESET_TOOLS:
        dim(f"[preset] {prompt.splitlines()[0]}")
        return True
    if _ASSUME_YES:
        return default
    hint = f"{DIM}[Y/n]{RESET}" if default else f"{DIM}[y/N]{RESET}"
    while True:
        try:
            val = input(f"  {BOLD}?{RESET}  {prompt.splitlines()[0]} {hint} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if val == "":
            return default
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False
        print("    Please answer y or n.")


def ask_choice(prompt: str, choices: list[str], default_index: int = 0) -> str:
    if _ASSUME_YES:
        return choices[default_index]
    print(f"  {BOLD}?{RESET}  {prompt}")
    for i, c in enumerate(choices):
        marker = f"{GREEN}▸{RESET}" if i == default_index else " "
        print(f"       {marker} [{i + 1}] {c}")
    while True:
        try:
            val = input(f"     {DIM}Enter number (default {default_index + 1}): {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)
        if val == "":
            return choices[default_index]
        try:
            idx = int(val) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        print(f"    Enter 1–{len(choices)}.")


# ─────────────────────────────────────────────────────────────────────────────
# Shell helpers
# ─────────────────────────────────────────────────────────────────────────────

def which(name: str) -> bool:
    return shutil.which(name) is not None


def run(
    cmd: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    loc = f"  {DIM}(in {cwd}){RESET}" if cwd else ""
    print(f"  {DIM}+ {' '.join(cmd)}{loc}{RESET}")
    if _DRY_RUN:
        return subprocess.CompletedProcess(cmd, 0, b"", b"")
    merged = os.environ.copy()
    if env:
        merged.update(env)
    kwargs: dict[str, Any] = {"cwd": str(cwd) if cwd else None, "env": merged}
    if capture:
        kwargs["capture_output"] = True
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result


def _run_install(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """Run an install command; captures output and returns (success, error_detail).
    Use instead of run() for installs so failures surface in GUI mode too."""
    print(f"  {DIM}+ {' '.join(cmd)}{RESET}")
    if _DRY_RUN:
        return True, ""
    merged = os.environ.copy()
    result = subprocess.run(cmd, capture_output=True, text=True,
                            cwd=str(cwd) if cwd else None, env=merged)
    if result.returncode == 0:
        return True, ""
    combined = ((result.stderr or "") + "\n" + (result.stdout or "")).strip()
    lower = combined.lower()
    if any(k in lower for k in ["eacces", "permission denied", "eperm", "access denied"]):
        return False, (
            "Permission denied. If using system npm/pip, try one of:\n"
            "    • Use nvm (https://github.com/nvm-sh/nvm) to manage Node.js without sudo\n"
            "    • Or: sudo " + " ".join(cmd)
        )
    if any(k in lower for k in ["not found", "no matching distribution", "404", "not exist"]):
        return False, f"Package not found or unavailable. Details: {combined[:200]}"
    return False, combined[:400] if combined else "Install returned non-zero exit code."


# ─────────────────────────────────────────────────────────────────────────────
# JSON + backup helpers
# ─────────────────────────────────────────────────────────────────────────────

def backup_file(path: Path) -> Path | None:
    """Create a timestamped backup before mutating. Returns backup path or None."""
    if not path.exists() or _DRY_RUN:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.parent / f".{path.name}.{ts}.bak"
    shutil.copy2(path, backup)
    return backup


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        bak = backup_file(path)
        path.unlink()
        warn(f"Malformed {path.name} — backed up to {bak.name if bak else '?'}, starting fresh.")
        return {}


def save_json(path: Path, data: dict[str, Any], backup: bool = True) -> None:
    if _DRY_RUN:
        info(f"[dry-run] Would write: {path}")
        return
    if backup:
        backup_file(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Project root resolution
# ─────────────────────────────────────────────────────────────────────────────

def resolve_project_root(start: Path) -> Path:
    if (start / ".git").exists():
        return start
    if which("git"):
        try:
            out = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=str(start), stderr=subprocess.DEVNULL,
            )
            root = Path(out.decode().strip())
            if root.exists():
                return root
        except Exception:
            pass
    return start


# ─────────────────────────────────────────────────────────────────────────────
# Prerequisite checks
# ─────────────────────────────────────────────────────────────────────────────

def ensure_claude_code() -> None:
    if which("claude"):
        ok("Claude Code CLI (claude)")
        return
    err("'claude' not found.")
    info("Install: npm install -g @anthropic-ai/claude-code")
    raise SystemExit(2)


def ensure_uvx() -> None:
    if which("uvx"):
        ok("uvx (Astral uv)")
        return
    warn("'uvx' not found — needed for Serena.")
    if which("brew") and ask_yes_no("Install uv via Homebrew?", default=True):
        run(["brew", "install", "uv"])
        if which("uvx"):
            ok("uvx installed")
            return
    err("Install uv: https://docs.astral.sh/uv/getting-started/installation/")
    raise SystemExit(2)


def ensure_node() -> None:
    if which("node") and which("npx"):
        ok("Node.js + npx")
    else:
        warn("Node.js / npx not found — several tools will be unavailable.")
        info("Install: https://nodejs.org/en/download/")


def ensure_graperoot_dgc() -> None:
    if which("dgc"):
        ok("GrapeRoot (dgc)")
        return
    err("'dgc' (GrapeRoot) not found — required for final launch.")
    info("Repo: https://github.com/kunal12203/Codex-CLI-Compact")
    if not ask_yes_no("Attempt automatic GrapeRoot install?", default=True):
        raise SystemExit(2)
    url = "https://raw.githubusercontent.com/kunal12203/Codex-CLI-Compact/main/install.sh"
    info(f"Downloading from: {url}")
    warn("You are about to run a remote shell script. Review it first if this is a concern.")
    try:
        with tempfile.TemporaryDirectory() as td:
            installer = Path(td) / "graperoot-install.sh"
            if which("curl"):
                run(["curl", "-fsSL", "-o", str(installer), url], check=True)
            else:
                urllib.request.urlretrieve(url, installer)
            run(["bash", str(installer)], check=True)
    except Exception as e:
        err(f"Install failed: {e}")
        raise SystemExit(2)
    if not which("dgc"):
        err("'dgc' still not on PATH. Open a new terminal and re-run.")
        raise SystemExit(2)
    ok("GrapeRoot installed")


# ─────────────────────────────────────────────────────────────────────────────
# .mcp.json helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_mcp_servers(project_root: Path) -> dict[str, Any]:
    return load_json(project_root / ".mcp.json").get("mcpServers", {})


def has_mcp_server(project_root: Path, name: str) -> bool:
    return name in get_mcp_servers(project_root)


def set_mcp_server(project_root: Path, name: str, cfg: dict[str, Any]) -> None:
    path = project_root / ".mcp.json"
    data = load_json(path)
    data.setdefault("mcpServers", {})[name] = cfg
    save_json(path, data)
    ok(f"MCP '{name}' → .mcp.json")


def remove_mcp_server(project_root: Path, name: str) -> None:
    path = project_root / ".mcp.json"
    data = load_json(path)
    if name in data.get("mcpServers", {}):
        del data["mcpServers"][name]
        save_json(path, data)


# ─────────────────────────────────────────────────────────────────────────────
# .claude/settings.local.json helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_local_settings(project_root: Path) -> dict[str, Any]:
    return load_json(project_root / ".claude" / "settings.local.json")


def save_local_settings(project_root: Path, data: dict[str, Any]) -> None:
    data.setdefault("$schema", "https://json.schemastore.org/claude-code-settings.json")
    save_json(project_root / ".claude" / "settings.local.json", data)


def add_hook(project_root: Path, event: str, matcher: str, command: str) -> None:
    """Idempotently add a hook. Deduplication checks event + matcher + command."""
    data  = get_local_settings(project_root)
    hooks = data.setdefault("hooks", {})
    elist = hooks.setdefault(event, [])
    for entry in elist:
        if entry.get("matcher") == matcher:
            for h in entry.get("hooks", []):
                if h.get("command") == command:
                    return  # exact duplicate
    elist.append({"matcher": matcher, "hooks": [{"type": "command", "command": command}]})
    save_local_settings(project_root, data)
    snippet = command[:52] + ("…" if len(command) > 52 else "")
    ok(f"Hook: {event} [{matcher}] → {snippet}")


def get_hook_commands(project_root: Path) -> list[tuple[str, str]]:
    settings = get_local_settings(project_root)
    out = []
    for event, entries in settings.get("hooks", {}).items():
        for entry in entries:
            for h in entry.get("hooks", []):
                if cmd := h.get("command"):
                    out.append((event, cmd))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Per-tool health detection
# ─────────────────────────────────────────────────────────────────────────────

def health_mcp_tool(project_root: Path, mcp_key: str, binary: str,
                    env_vars: list[str] | None = None) -> ToolHealth:
    """Standard health check for an MCP-backed tool."""
    configured = has_mcp_server(project_root, mcp_key)
    binary_ok  = which(binary)
    env_ok     = all(os.environ.get(v) for v in (env_vars or []))

    if not configured and not binary_ok:
        return ToolHealth.NOT_CONFIGURED
    if configured and binary_ok and env_ok:
        return ToolHealth.HEALTHY
    if configured and not binary_ok:
        return ToolHealth.CONFIGURED_ONLY
    if configured and not env_ok:
        return ToolHealth.MISSING_ENV
    if binary_ok and not configured:
        # May be at user scope
        return ToolHealth.USER_SCOPE
    return ToolHealth.NOT_CONFIGURED


def health_global_binary(binary: str) -> ToolHealth:
    return ToolHealth.HEALTHY if which(binary) else ToolHealth.NOT_CONFIGURED


def health_user_scope_mcp(binary: str) -> ToolHealth:
    """Tool expected at user scope — healthy if binary exists."""
    return ToolHealth.USER_SCOPE if which(binary) else ToolHealth.NOT_CONFIGURED


# ─────────────────────────────────────────────────────────────────────────────
# MCP server config builders
# ─────────────────────────────────────────────────────────────────────────────

def _mcp(command: str, *args: str, env: dict | None = None) -> dict[str, Any]:
    return {"type": "stdio", "command": command, "args": list(args), "env": env or {}}


def mcp_serena(project_root: Path) -> dict[str, Any]:
    return _mcp("uvx",
        "--from", "git+https://github.com/oraios/serena",
        "serena", "start-mcp-server",
        "--context", "ide-assistant",
        "--project", str(project_root),
    )

def mcp_leann()         -> dict[str, Any]: return _mcp("leann_mcp")
def mcp_context7()      -> dict[str, Any]: return _mcp("npx", "-y", "@upstash/context7-mcp")
def mcp_claude_context()-> dict[str, Any]: return _mcp("npx", "@zilliz/claude-context-mcp@latest")
def mcp_claude_session()-> dict[str, Any]: return _mcp("claude-session-mcp")
def mcp_context_mode()  -> dict[str, Any]: return _mcp("npx", "-y", "context-mode")
def mcp_seu_claude()    -> dict[str, Any]: return _mcp("npx", "seu-claude")
def mcp_cgc()           -> dict[str, Any]: return _mcp("cgc", "mcp", "start")

def _ccsetup_share() -> Path:
    """Returns the ccsetup data directory: ~/.local/share/ccsetup/"""
    return Path.home() / ".local" / "share" / "ccsetup"

def mcp_claude_mind()    -> dict[str, Any]:
    return _mcp("python3", str(_ccsetup_share() / "claude-mind"    / "server.py"))

def mcp_claude_charter() -> dict[str, Any]:
    return _mcp("python3", str(_ccsetup_share() / "claude-charter" / "server.py"))

def mcp_claude_witness() -> dict[str, Any]:
    return _mcp("python3", str(_ccsetup_share() / "claude-witness" / "server.py"))

def mcp_claude_retina() -> dict[str, Any]:
    return _mcp("python3", str(_ccsetup_share() / "claude-retina" / "server.py"))

def mcp_claude_ledger() -> dict[str, Any]:
    return _mcp("python3", str(_ccsetup_share() / "claude-ledger" / "server.py"))

def _ccsetup_server_installed(server_name: str) -> bool:
    """True if the bundled server.py exists at ~/.local/share/ccsetup/<server>/server.py"""
    return (_ccsetup_share() / server_name / "server.py").exists()

def health_ccsetup_server(server_name: str) -> ToolHealth:
    """Health for a ccsetup-bundled MCP server."""
    if not which("python3"):
        return ToolHealth.MISSING_BINARY
    if not _ccsetup_server_installed(server_name):
        return ToolHealth.NOT_CONFIGURED
    return ToolHealth.HEALTHY


# ─────────────────────────────────────────────────────────────────────────────
# Scope-aware MCP install helper
# ─────────────────────────────────────────────────────────────────────────────

def install_mcp_scoped(
    project_root: Path,
    mcp_key:      str,
    mcp_cfg:      dict[str, Any],
    binary:       str,
    user_cmd:     list[str],
    prompt:       str = "",
) -> ToolHealth:
    """
    Install an MCP server, respecting _SCOPE_MODE.
    Returns the resulting ToolHealth.
    """
    scope = _SCOPE_MODE

    if scope == "repo":
        set_mcp_server(project_root, mcp_key, mcp_cfg)
        return ToolHealth.HEALTHY if which(binary) else ToolHealth.CONFIGURED_ONLY

    if scope == "user":
        try:
            run(user_cmd)
            return ToolHealth.USER_SCOPE
        except subprocess.CalledProcessError:
            err(f"User-scope install failed — falling back to .mcp.json")
            set_mcp_server(project_root, mcp_key, mcp_cfg)
            return ToolHealth.HEALTHY if which(binary) else ToolHealth.CONFIGURED_ONLY

    # hybrid: try user scope first, fall back to project
    try:
        run(user_cmd)
        ok(f"'{mcp_key}' added at user scope (applies to all repos)")
        return ToolHealth.USER_SCOPE
    except subprocess.CalledProcessError:
        set_mcp_server(project_root, mcp_key, mcp_cfg)
        return ToolHealth.HEALTHY if which(binary) else ToolHealth.CONFIGURED_ONLY


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 0 — Foundation (always-on)
# ─────────────────────────────────────────────────────────────────────────────

def layer0_foundation(project_root: Path) -> None:
    section(0, "Foundation")
    dim("Serena (LSP symbol resolution) and GrapeRoot (call/import graph) — always-on.")
    dim("These are Claude's eyes into the codebase. No prompts; both always configured.")
    print()

    # Serena
    if has_mcp_server(project_root, "serena"):
        ok("Serena already in .mcp.json")
        h = ToolHealth.HEALTHY if which("uvx") else ToolHealth.CONFIGURED_ONLY
    else:
        set_mcp_server(project_root, "serena", mcp_serena(project_root))
        h = ToolHealth.HEALTHY if which("uvx") else ToolHealth.CONFIGURED_ONLY
    record(SetupResult("serena", "Serena", 0, h,
                       notes=["Always-on. Provides LSP symbol resolution via uvx."]))

    # GrapeRoot
    if which("dgc"):
        ok("GrapeRoot (dgc) ready")
        record(SetupResult("graperoot", "GrapeRoot", 0, ToolHealth.HEALTHY,
                           notes=["Available for standalone graph queries via 'dgc .'."]))
    else:
        warn("GrapeRoot not found — 'dgc .' will be skipped")
        record(SetupResult("graperoot", "GrapeRoot", 0, ToolHealth.MISSING_BINARY,
                           manual_steps=["Install dgc: https://github.com/kunal12203/Codex-CLI-Compact"]))

    # Ensure .dual-graph/ context store exists (part of GrapeRoot workflow)
    dg_dir = project_root / ".dual-graph"
    if not dg_dir.exists():
        dg_dir.mkdir(exist_ok=True)
        ctx = dg_dir / "context-store.json"
        if not ctx.exists():
            save_json(ctx, [], backup=False)
        ok(".dual-graph/ created")
        info("Open Claude Code and run 'graph_scan .' to index this repo")


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1 — Context Intelligence
# ─────────────────────────────────────────────────────────────────────────────

def layer1_context(project_root: Path) -> None:
    section(1, "Context Intelligence")
    dim("Smart retrieval: Claude finds relevant code by meaning, not exhaustive reads.")
    print()

    # Semantic search: LEANN vs Claude Context (mutually exclusive)
    if has_mcp_server(project_root, "leann-server"):
        ok("LEANN already in .mcp.json")
        h = ToolHealth.HEALTHY if which("leann_mcp") else ToolHealth.CONFIGURED_ONLY
        record(SetupResult("leann", "LEANN", 1, h))
    elif has_mcp_server(project_root, "Claude Context"):
        ok("Claude Context already in .mcp.json")
        record(SetupResult("claude-context", "Claude Context", 1,
                           health_mcp_tool(project_root, "Claude Context", "npx",
                                           ["ZILLIZ_CLOUD_URI", "ZILLIZ_CLOUD_API_KEY",
                                            "EMBEDDING_API_KEY"])))
    elif ask_yes_no(
        "Enable semantic codebase search?\n"
        "    Retrieves relevant code by meaning — not just text matching.",
        default=True, tool_id="leann",
    ):
        choice = ask_choice(
            "Which semantic search backend?",
            [
                "LEANN — local-first, AST-aware, no cloud deps  [recommended]",
                "Claude Context — Zilliz Cloud vector DB, requires 3 API keys",
                "Skip",
            ],
            default_index=0,
        )
        if "LEANN" in choice:
            _setup_leann(project_root)
        elif "Claude Context" in choice:
            _setup_claude_context(project_root)
        else:
            record(SetupResult("leann", "LEANN", 1, ToolHealth.SKIPPED))
    else:
        record(SetupResult("leann", "LEANN", 1, ToolHealth.SKIPPED))

    hr()

    # Context7
    if has_mcp_server(project_root, "context7"):
        ok("Context7 already configured")
        h = ToolHealth.HEALTHY if which("npx") else ToolHealth.CONFIGURED_ONLY
        record(SetupResult("context7", "Context7", 1, h))
    elif ask_yes_no(
        "Enable Context7? (injects live library docs — eliminates stale API hallucinations)",
        default=False, tool_id="context7",
    ):
        if not which("npx"):
            err("npx required for Context7.")
            record(SetupResult("context7", "Context7", 1, ToolHealth.MISSING_BINARY,
                               manual_steps=["Install Node.js to get npx."]))
        else:
            set_mcp_server(project_root, "context7", mcp_context7())
            record(SetupResult("context7", "Context7", 1, ToolHealth.HEALTHY,
                               notes=["Use 'use context7' or '@<libname>' in prompts."]))
    else:
        record(SetupResult("context7", "Context7", 1, ToolHealth.SKIPPED))

    hr()

    # claude-witness
    if has_mcp_server(project_root, "claude-witness"):
        ok("claude-witness already configured")
        record(SetupResult("claude-witness", "claude-witness", 1,
                           health_ccsetup_server("claude-witness")))
    elif ask_yes_no(
        "[experimental] Enable claude-witness? (captures function calls/exceptions from pytest runs — queryable execution evidence)",
        default=False, tool_id="claude-witness",
    ):
        _setup_claude_witness(project_root)
    else:
        record(SetupResult("claude-witness", "claude-witness", 1, ToolHealth.SKIPPED))


def _setup_leann(project_root: Path) -> None:
    if not which("uv"):
        err("'uv' required for LEANN.")
        record(SetupResult("leann", "LEANN", 1, ToolHealth.MISSING_BINARY,
                           manual_steps=["Install uv: https://docs.astral.sh/uv/",
                                         "Then: uv tool install leann-core --with leann"]))
        return
    if not which("leann_mcp"):
        info("Installing LEANN…")
        ok, detail = _run_install(["uv", "tool", "install", "leann-core", "--with", "leann"])
        if not ok:
            err("LEANN install failed.")
            if detail:
                info(detail)
            record(SetupResult("leann", "LEANN", 1, ToolHealth.MISSING_BINARY,
                               manual_steps=["uv tool install leann-core --with leann"]))
            return
    h = install_mcp_scoped(
        project_root, "leann-server", mcp_leann(), "leann_mcp",
        ["claude", "mcp", "add", "--scope", "user", "leann-server", "--", "leann_mcp"],
    )
    record(SetupResult("leann", "LEANN", 1, h,
                       notes=["Local semantic search. Indexes all repos when at user scope."]))


def _setup_claude_context(project_root: Path) -> None:
    required_env = ["ZILLIZ_CLOUD_URI", "ZILLIZ_CLOUD_API_KEY", "EMBEDDING_API_KEY"]
    missing = [v for v in required_env if not os.environ.get(v)]
    info("Claude Context requires: " + ", ".join(required_env))
    set_mcp_server(project_root, "Claude Context", mcp_claude_context())
    h = ToolHealth.MISSING_ENV if missing else ToolHealth.HEALTHY
    record(SetupResult("claude-context", "Claude Context", 1, h,
                       env_vars=required_env,
                       notes=["Add env vars to shell profile before use."]))


def _setup_claude_witness(project_root: Path) -> None:
    if not _ccsetup_server_installed("claude-witness"):
        err("claude-witness not found. Run 'bash install.sh' from the ccsetup repo to install it.")
        record(SetupResult("claude-witness", "claude-witness", 1, ToolHealth.NOT_CONFIGURED,
                           manual_steps=["Run 'bash install.sh' from the ccsetup source directory.",
                                         "Then re-run ccsetup."]))
        return
    set_mcp_server(project_root, "claude-witness", mcp_claude_witness())
    h = health_ccsetup_server("claude-witness")
    record(SetupResult("claude-witness", "claude-witness", 1, h,
                       notes=["Add --witness to pytest runs to capture execution evidence.",
                              "See claude-witness/README.md for conftest.py setup."]))


def _setup_claude_retina(project_root: Path) -> None:
    if not _ccsetup_server_installed("claude-retina"):
        err("claude-retina not found. Run 'bash install.sh' from the ccsetup repo.")
        record(SetupResult("claude-retina", "claude-retina", 4, ToolHealth.NOT_CONFIGURED,
                           manual_steps=["Run 'bash install.sh' from the ccsetup source directory.",
                                         "Then: pip install playwright Pillow && playwright install chromium"]))
        return
    set_mcp_server(project_root, "claude-retina", mcp_claude_retina())
    h = health_ccsetup_server("claude-retina")
    record(SetupResult("claude-retina", "claude-retina", 4, h,
                       notes=["Install deps: pip install playwright Pillow && playwright install chromium",
                              "Usage: retina_capture('http://localhost:3000'), then Read the PNG",
                              "Visual regression: retina_baseline('name', url) → retina_regress('name')"]))


def _setup_claude_ledger(project_root: Path) -> None:
    if not _ccsetup_server_installed("claude-ledger"):
        err("claude-ledger not found. Run 'bash install.sh' from the ccsetup repo.")
        record(SetupResult("claude-ledger", "claude-ledger", 5, ToolHealth.NOT_CONFIGURED,
                           manual_steps=["Run 'bash install.sh' from the ccsetup source directory.",
                                         "Then re-run ccsetup."]))
        return
    set_mcp_server(project_root, "claude-ledger", mcp_claude_ledger())
    h = health_ccsetup_server("claude-ledger")
    record(SetupResult("claude-ledger", "claude-ledger", 5, h,
                       notes=["Use ledger_context() at session start instead of reading tool-ledger.md",
                              "Use ledger_query('task') to get opinionated tool routing",
                              "Use ledger_health() for real-time health check of all tools"]))


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2 — Memory & Continuity
# ─────────────────────────────────────────────────────────────────────────────

def layer2_memory(project_root: Path) -> None:
    section(2, "Memory & Continuity")
    dim("Cross-session persistence and anti-compaction defenses.")
    print()

    # claude-session-mcp
    if has_mcp_server(project_root, "claude-session"):
        ok("claude-session-mcp already configured")
        h = ToolHealth.HEALTHY if which("claude-session-mcp") else ToolHealth.CONFIGURED_ONLY
        record(SetupResult("claude-session", "claude-session-mcp", 2, h))
    elif ask_yes_no(
        "Enable claude-session-mcp? (session clone / archive / restore)",
        default=False, tool_id="claude-session",
    ):
        _setup_claude_session(project_root)
    else:
        record(SetupResult("claude-session", "claude-session-mcp", 2, ToolHealth.SKIPPED))

    hr()

    # context-mode
    if has_mcp_server(project_root, "context-mode"):
        ok("context-mode already configured")
        h = ToolHealth.HEALTHY if which("npx") else ToolHealth.CONFIGURED_ONLY
        record(SetupResult("context-mode", "context-mode", 2, h))
    elif ask_yes_no(
        "Enable context-mode? (virtualizes tool outputs — resists auto-compaction)",
        default=False, tool_id="context-mode",
    ):
        if not which("npx"):
            err("npx required.")
            record(SetupResult("context-mode", "context-mode", 2, ToolHealth.MISSING_BINARY,
                               manual_steps=["Install Node.js to get npx."]))
        else:
            set_mcp_server(project_root, "context-mode", mcp_context_mode())
            record(SetupResult("context-mode", "context-mode", 2, ToolHealth.HEALTHY,
                               notes=["Use /context in Claude Code to inspect status."]))
    else:
        record(SetupResult("context-mode", "context-mode", 2, ToolHealth.SKIPPED))

    hr()

    # claude-mind
    if has_mcp_server(project_root, "claude-mind"):
        ok("claude-mind already configured")
        record(SetupResult("claude-mind", "claude-mind", 2,
                           health_ccsetup_server("claude-mind")))
    elif ask_yes_no(
        "[experimental] Enable claude-mind? (investigation reasoning board — hypotheses, facts, assumptions survive compaction)",
        default=False, tool_id="claude-mind",
    ):
        _setup_claude_mind(project_root)
    else:
        record(SetupResult("claude-mind", "claude-mind", 2, ToolHealth.SKIPPED))

    hr()

    # claude-charter
    if has_mcp_server(project_root, "claude-charter"):
        ok("claude-charter already configured")
        record(SetupResult("claude-charter", "claude-charter", 2,
                           health_ccsetup_server("claude-charter")))
    elif ask_yes_no(
        "[experimental] Enable claude-charter? (project constitution — invariants, constraints, charter_check before changes)",
        default=False, tool_id="claude-charter",
    ):
        _setup_claude_charter(project_root)
    else:
        record(SetupResult("claude-charter", "claude-charter", 2, ToolHealth.SKIPPED))


def _setup_claude_session(project_root: Path) -> None:
    if not which("claude-session-mcp"):
        if not which("uv"):
            err("'uv' required.")
            record(SetupResult("claude-session", "claude-session-mcp", 2, ToolHealth.MISSING_BINARY,
                               manual_steps=["Install uv, then:",
                                             "uv tool install git+https://github.com/chrisguillory/claude-session-mcp"]))
            return
        info("Installing claude-session-mcp…")
        try:
            run(["uv", "tool", "install",
                 "git+https://github.com/chrisguillory/claude-session-mcp"])
        except subprocess.CalledProcessError:
            err("Install failed.")
            record(SetupResult("claude-session", "claude-session-mcp", 2, ToolHealth.MISSING_BINARY,
                               manual_steps=["uv tool install git+https://github.com/chrisguillory/claude-session-mcp"]))
            return
    h = install_mcp_scoped(
        project_root, "claude-session", mcp_claude_session(), "claude-session-mcp",
        ["claude", "mcp", "add", "--scope", "user",
         "claude-session", "--", "claude-session-mcp"],
    )
    record(SetupResult("claude-session", "claude-session-mcp", 2, h,
                       notes=["Fork, archive, and restore sessions with full fidelity."]))


def _setup_claude_mind(project_root: Path) -> None:
    if not _ccsetup_server_installed("claude-mind"):
        err("claude-mind not found. Run 'bash install.sh' from the ccsetup repo to install it.")
        record(SetupResult("claude-mind", "claude-mind", 2, ToolHealth.NOT_CONFIGURED,
                           manual_steps=["Run 'bash install.sh' from the ccsetup source directory.",
                                         "Then re-run ccsetup."]))
        return
    set_mcp_server(project_root, "claude-mind", mcp_claude_mind())
    h = health_ccsetup_server("claude-mind")
    record(SetupResult("claude-mind", "claude-mind", 2, h,
                       notes=["Use mind_open() to start an investigation.",
                              "mind_summary() recovers full state after context compaction."]))


def _setup_claude_charter(project_root: Path) -> None:
    if not _ccsetup_server_installed("claude-charter"):
        err("claude-charter not found. Run 'bash install.sh' from the ccsetup repo to install it.")
        record(SetupResult("claude-charter", "claude-charter", 2, ToolHealth.NOT_CONFIGURED,
                           manual_steps=["Run 'bash install.sh' from the ccsetup source directory.",
                                         "Then re-run ccsetup."]))
        return
    set_mcp_server(project_root, "claude-charter", mcp_claude_charter())
    h = health_ccsetup_server("claude-charter")
    record(SetupResult("claude-charter", "claude-charter", 2, h,
                       notes=["Use charter_add() to seed invariants and constraints.",
                              "charter_check() before any structural change."]))


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3 — Safety & Quality Guardrails
# ─────────────────────────────────────────────────────────────────────────────

def layer3_safety(project_root: Path) -> None:
    section(3, "Safety & Quality Guardrails")
    dim("Hook-based defenses. These run independently of Claude's stochastic judgment.")
    dim("All Layer 3 tools require manual hook configuration — ccsetup documents the steps.")
    print()

    existing_cmds = [c for _, c in get_hook_commands(project_root)]

    # parry
    if any("parry" in c for c in existing_cmds):
        ok("parry hook already present in .claude/settings.local.json")
        record(SetupResult("parry", "parry", 3, ToolHealth.HEALTHY))
    elif ask_yes_no(
        "Note manual steps for parry? (prompt injection + exfiltration scanner)\n"
        "    Uses Aho-Corasick + DeBERTa ML. Sub-10ms. Blocks ~/.ssh and .env leakage.",
        default=False, tool_id="parry",
    ):
        record(SetupResult("parry", "parry", 3, ToolHealth.MANUAL_REQUIRED,
                           manual_steps=[
                               "Install parry: https://github.com/anthropics/parry",
                               "Start daemon: parry serve",
                               "Add PreToolUse hook in .claude/settings.local.json:",
                               '  command: "parry check --tool \'{{tool_name}}\' --input \'{{tool_input}}\'"',
                           ]))
        info("Manual steps recorded in ccsetup report.")
    else:
        record(SetupResult("parry", "parry", 3, ToolHealth.SKIPPED))

    hr()

    # claude-plan-reviewer
    if ask_yes_no(
        "Note manual steps for adversarial plan review?\n"
        "    Rival model (Gemini/GPT-4) critiques Claude's plan before implementation.",
        default=False, tool_id="plan-reviewer",
    ):
        record(SetupResult("plan-reviewer", "claude-plan-reviewer", 3,
                           ToolHealth.MANUAL_REQUIRED,
                           env_vars=["OPENAI_API_KEY or GOOGLE_API_KEY"],
                           manual_steps=[
                               "Install: https://github.com/anthropics/claude-plan-reviewer",
                               "Add OPENAI_API_KEY or GOOGLE_API_KEY to shell profile.",
                               "NOTE: plan contents are sent to an external model — review privacy implications.",
                           ]))
    else:
        record(SetupResult("plan-reviewer", "claude-plan-reviewer", 3, ToolHealth.SKIPPED))

    hr()

    # TDD Guard
    if ask_yes_no(
        "Note manual steps for TDD Guard? (blocks writes without prior failing test)\n"
        "    Enforces Red-Green-Refactor. Supports Vitest, Pytest, Go test, PHPUnit.",
        default=False, tool_id="tdd-guard",
    ):
        record(SetupResult("tdd-guard", "TDD Guard", 3, ToolHealth.MANUAL_REQUIRED,
                           manual_steps=[
                               "Install: https://github.com/anthropics/tdd-guard",
                               "Registers as a PreToolUse hook on Write/Edit/MultiEdit.",
                               "Be aware: can be restrictive — tune for your workflow.",
                           ]))
    else:
        record(SetupResult("tdd-guard", "TDD Guard", 3, ToolHealth.SKIPPED))


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4 — Observability & Telemetry
# ─────────────────────────────────────────────────────────────────────────────

def layer4_observability(project_root: Path) -> None:
    section(4, "Observability & Telemetry")
    dim("See where tokens go, trace session decisions, get ambient awareness of progress.")
    print()

    # ccusage
    if which("ccusage"):
        ok("ccusage already installed")
        record(SetupResult("ccusage", "ccusage", 4, ToolHealth.HEALTHY,
                           notes=["Run 'ccusage' anywhere for live usage dashboard."]))
    elif ask_yes_no(
        "Install ccusage? (terminal dashboard for token usage and costs)\n"
        "    Parses ~/.claude/*.jsonl locally — zero cloud exfiltration.",
        default=True, tool_id="ccusage",
    ):
        if not which("npm"):
            err("npm required.")
            record(SetupResult("ccusage", "ccusage", 4, ToolHealth.MISSING_BINARY,
                               manual_steps=["Install Node.js, then: npm install -g ccusage"]))
        else:
            try:
                run(["npm", "install", "-g", "ccusage"])
                ok("ccusage installed — run 'ccusage' in any terminal")
                record(SetupResult("ccusage", "ccusage", 4, ToolHealth.HEALTHY))
            except subprocess.CalledProcessError:
                err("Install failed.")
                record(SetupResult("ccusage", "ccusage", 4, ToolHealth.MISSING_BINARY,
                                   manual_steps=["npm install -g ccusage"]))
    else:
        record(SetupResult("ccusage", "ccusage", 4, ToolHealth.SKIPPED))

    hr()

    # claude-esp
    if ask_yes_no(
        "Note manual steps for claude-esp? (streams hidden thinking blocks to separate terminal)",
        default=False, tool_id="claude-esp",
    ):
        record(SetupResult("claude-esp", "claude-esp", 4, ToolHealth.MANUAL_REQUIRED,
                           manual_steps=[
                               "Install: https://github.com/anthropics/claude-esp (check for latest)",
                               "Run 'claude-esp' in a separate pane before starting Claude Code.",
                           ]))
    else:
        record(SetupResult("claude-esp", "claude-esp", 4, ToolHealth.SKIPPED))

    hr()

    # cclogviewer
    if which("cclogviewer"):
        ok("cclogviewer already installed")
        record(SetupResult("cclogviewer", "cclogviewer", 4, ToolHealth.HEALTHY))
    elif ask_yes_no(
        "Install cclogviewer? (converts session .jsonl logs to interactive HTML)",
        default=False, tool_id="cclogviewer",
    ):
        if which("go"):
            try:
                run(["go", "install",
                     "github.com/brads3290/cclogviewer/cmd/cclogviewer@latest"])
                ok("cclogviewer installed")
                record(SetupResult("cclogviewer", "cclogviewer", 4, ToolHealth.HEALTHY))
            except subprocess.CalledProcessError:
                err("Install failed.")
                record(SetupResult("cclogviewer", "cclogviewer", 4, ToolHealth.MISSING_BINARY,
                                   manual_steps=["Install Go, then: go install github.com/brads3290/cclogviewer/cmd/cclogviewer@latest"]))
        else:
            err("Go required. Install: https://go.dev/doc/install")
            record(SetupResult("cclogviewer", "cclogviewer", 4, ToolHealth.MISSING_BINARY,
                               manual_steps=["Install Go, then: go install github.com/brads3290/cclogviewer/cmd/cclogviewer@latest"]))
    else:
        record(SetupResult("cclogviewer", "cclogviewer", 4, ToolHealth.SKIPPED))

    hr()

    # cship
    if which("cship"):
        ok("cship already installed")
        record(SetupResult("cship", "cship", 4, ToolHealth.HEALTHY,
                           notes=["Live metrics in shell prompt. Check: cship explain",
                                  "Config: ~/.config/cship.toml"]))
    elif ask_yes_no(
        "Install cship? (live Claude metrics in shell prompt — cost, context %, model name)\n"
        "    Rust binary, <10ms render. Wires into ~/.claude/settings.json as statusline provider.\n"
        "    Complements ccusage — cship is inline, ccusage is a dashboard.",
        default=True, tool_id="cship",
    ):
        info("Installing cship via curl installer…")
        try:
            run(["bash", "-c",
                 "curl -fsSL https://cship.dev/install.sh | bash"])
            if which("cship"):
                ok("cship installed — statusline active in next Claude session")
                record(SetupResult("cship", "cship", 4, ToolHealth.HEALTHY,
                                   notes=["Edit ~/.config/cship.toml to customize tokens.",
                                          "Run 'cship explain' to debug current metric values."]))
            else:
                warn("cship installed but not yet on PATH — restart shell")
                record(SetupResult("cship", "cship", 4, ToolHealth.CONFIGURED_ONLY,
                                   manual_steps=["Restart shell or add ~/.local/bin to PATH",
                                                 "Verify: cship explain"]))
        except subprocess.CalledProcessError:
            err("Install failed. Manual: curl -fsSL https://cship.dev/install.sh | bash")
            record(SetupResult("cship", "cship", 4, ToolHealth.MISSING_BINARY,
                               manual_steps=["curl -fsSL https://cship.dev/install.sh | bash"]))
    else:
        record(SetupResult("cship", "cship", 4, ToolHealth.SKIPPED))

    hr()

    # claudio (ambient audio hooks)
    afplay = Path("/usr/bin/afplay")
    if any("afplay" in c for _, c in get_hook_commands(project_root)):
        ok("claudio hooks already present")
        record(SetupResult("claudio", "claudio", 4, ToolHealth.HEALTHY))
    elif ask_yes_no(
        "Enable claudio? (macOS system sounds on tool start/end — ambient session awareness)",
        default=False, tool_id="claudio",
    ):
        if afplay.exists():
            add_hook(project_root, "PreToolUse",  ".*", f"{afplay} /System/Library/Sounds/Tink.aiff")
            add_hook(project_root, "PostToolUse", ".*", f"{afplay} /System/Library/Sounds/Glass.aiff")
            record(SetupResult("claudio", "claudio", 4, ToolHealth.HEALTHY,
                               notes=["macOS afplay hooks. Non-invasive — remove from settings.local.json to disable."]))
        else:
            warn("afplay not found (non-macOS?). Skipping.")
            record(SetupResult("claudio", "claudio", 4, ToolHealth.MISSING_BINARY))
    else:
        record(SetupResult("claudio", "claudio", 4, ToolHealth.SKIPPED))

    hr()

    # claude-retina
    if has_mcp_server(project_root, "claude-retina"):
        ok("claude-retina already configured")
        record(SetupResult("claude-retina", "claude-retina", 4, health_ccsetup_server("claude-retina")))
    elif ask_yes_no(
        "[experimental] Enable claude-retina? (visual browser automation — screenshot, diff, interact, regress)\n"
        "    Headless Chromium via Playwright. Claude gets eyes on the running UI.\n"
        "    Requires: pip install playwright Pillow && playwright install chromium",
        default=False, tool_id="claude-retina",
    ):
        _setup_claude_retina(project_root)
    else:
        record(SetupResult("claude-retina", "claude-retina", 4, ToolHealth.SKIPPED))


# ─────────────────────────────────────────────────────────────────────────────
# LAYER 5 — Orchestration & Scaling
# ─────────────────────────────────────────────────────────────────────────────

def layer5_orchestration(project_root: Path) -> None:
    section(5, "Orchestration & Scaling")
    dim("Multi-agent coordination, spec-driven development, tool-surface compression.")
    print()

    hr()

    # claude-ledger
    if has_mcp_server(project_root, "claude-ledger"):
        ok("claude-ledger already configured")
        record(SetupResult("claude-ledger", "claude-ledger", 5, health_ccsetup_server("claude-ledger")))
    elif ask_yes_no(
        "[experimental] Enable claude-ledger? (live capability map — routes Claude to the right tool for any task)\n"
        "    Replaces static tool-ledger.md with a live MCP server.\n"
        "    ledger_context() = session-start briefing. ledger_query('task') = opinionated routing.",
        default=False, tool_id="claude-ledger",
    ):
        _setup_claude_ledger(project_root)
    else:
        record(SetupResult("claude-ledger", "claude-ledger", 5, ToolHealth.SKIPPED))

    hr()

    # seu-claude
    if has_mcp_server(project_root, "seu-claude"):
        ok("seu-claude already configured")
        h = ToolHealth.HEALTHY if which("npx") else ToolHealth.CONFIGURED_ONLY
        record(SetupResult("seu-claude", "seu-claude", 5, h))
    elif ask_yes_no(
        "Enable seu-claude? (persistent memory + task tracking + multi-agent orchestration)\n"
        "    Heavy but comprehensive. Best for long, complex, multi-session projects.",
        default=False, tool_id="seu-claude",
    ):
        if not which("npx"):
            err("npx required.")
            record(SetupResult("seu-claude", "seu-claude", 5, ToolHealth.MISSING_BINARY,
                               manual_steps=["Install Node.js, then: npm install -g seu-claude"]))
        else:
            ok, detail = _run_install(["npm", "install", "-g", "seu-claude"])
            if ok:
                set_mcp_server(project_root, "seu-claude", mcp_seu_claude())
                record(SetupResult("seu-claude", "seu-claude", 5, ToolHealth.HEALTHY,
                                   notes=["Provides persistent tasks, AST analysis, sandbox execution."]))
            else:
                err("Install failed.")
                if detail:
                    info(detail)
                record(SetupResult("seu-claude", "seu-claude", 5, ToolHealth.MISSING_BINARY,
                                   manual_steps=["npm install -g seu-claude"]))
    else:
        record(SetupResult("seu-claude", "seu-claude", 5, ToolHealth.SKIPPED))

    hr()

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 6 — Workflow Utilities
# ─────────────────────────────────────────────────────────────────────────────

def layer6_workflow(project_root: Path) -> None:
    section(6, "Workflow Utilities")
    dim("Callers/callees graph, mobile approvals, past-session recovery.")
    print()

    # CodeGraphContext
    if has_mcp_server(project_root, "codegraphcontext"):
        ok("CodeGraphContext already configured")
        h = ToolHealth.HEALTHY if which("cgc") else ToolHealth.CONFIGURED_ONLY
        record(SetupResult("codegraphcontext", "CodeGraphContext", 6, h))
    elif ask_yes_no(
        "Enable CodeGraphContext? (call-chain queries: callers, callees, cross-file impact)\n"
        "    Note: overlaps with Serena — most useful if you need explicit graph queries.",
        default=False, tool_id="codegraphcontext",
    ):
        if not which("cgc"):
            info("Installing CodeGraphContext via pip…")
            ok, detail = _run_install(
                [sys.executable, "-m", "pip", "install", "--user", "codegraphcontext"])
            if not ok:
                err("Install failed.")
                if detail:
                    info(detail)
                record(SetupResult("codegraphcontext", "CodeGraphContext", 6,
                                   ToolHealth.MISSING_BINARY,
                                   manual_steps=["pip install --user codegraphcontext",
                                                 "Ensure Python user bin is on PATH."]))
                return
        if which("cgc"):
            set_mcp_server(project_root, "codegraphcontext", mcp_cgc())
            record(SetupResult("codegraphcontext", "CodeGraphContext", 6, ToolHealth.HEALTHY))
        else:
            warn("'cgc' not on PATH yet. Add Python user bin to PATH and re-run.")
            record(SetupResult("codegraphcontext", "CodeGraphContext", 6, ToolHealth.MISSING_BINARY,
                               manual_steps=["Add Python user bin dir to PATH (check: python3 -m site --user-base)",
                                             "Then re-run: ccsetup . --from-layer 6"]))
    else:
        record(SetupResult("codegraphcontext", "CodeGraphContext", 6, ToolHealth.SKIPPED))

    hr()

    # claude-remote-approver
    if ask_yes_no(
        "Note manual steps for claude-remote-approver? (approval prompts → your phone via ntfy.sh)\n"
        "    Approve/deny commands remotely. Run pipelines overnight without watching the terminal.",
        default=False, tool_id="remote-approver",
    ):
        record(SetupResult("remote-approver", "claude-remote-approver", 6,
                           ToolHealth.MANUAL_REQUIRED,
                           env_vars=["NTFY_TOPIC"],
                           manual_steps=[
                               "Create a free topic at https://ntfy.sh",
                               "Set NTFY_TOPIC env var in your shell profile",
                               "Install ntfy app on your phone",
                               "Install: https://github.com/anthropics/claude-remote-approver",
                               "Add UserPromptSubmit hook — see repo README for format",
                           ]))
    else:
        record(SetupResult("remote-approver", "claude-remote-approver", 6, ToolHealth.SKIPPED))

    hr()

    # Smart Fork Detection
    sf_dir = Path("~/.local/tools/smart-fork").expanduser()
    if sf_dir.exists():
        ok("Smart Fork Detection already at ~/.local/tools/smart-fork")
        record(SetupResult("smart-fork", "Smart Fork Detection", 6, ToolHealth.HEALTHY,
                           notes=["Semantic search of past sessions.",
                                  "NOTE: overlaps with claude-session-mcp — choose one primary memory tool."]))
    elif ask_yes_no(
        "Set up Smart Fork Detection? (semantic search across past Claude sessions)\n"
        "    Resume the most relevant prior session instead of re-explaining from scratch.\n"
        "    NOTE: overlaps with claude-session-mcp. Pick one as your primary.",
        default=False, tool_id="smart-fork",
    ):
        tools_dir = Path("~/.local/tools").expanduser()
        if not which("git"):
            err("git required.")
            record(SetupResult("smart-fork", "Smart Fork Detection", 6, ToolHealth.MISSING_BINARY))
        else:
            tools_dir.mkdir(parents=True, exist_ok=True)
            try:
                run(["git", "clone",
                     "https://github.com/recursive-vibe/smart-fork.git", str(sf_dir)])
                ok("Smart Fork Detection cloned to ~/.local/tools/smart-fork")
                record(SetupResult("smart-fork", "Smart Fork Detection", 6,
                                   ToolHealth.MANUAL_REQUIRED,
                                   manual_steps=["Set up Python venv per repo README.",
                                                 "Build the session vector index before first use."]))
            except subprocess.CalledProcessError:
                err("git clone failed.")
                record(SetupResult("smart-fork", "Smart Fork Detection", 6, ToolHealth.MISSING_BINARY))
    else:
        record(SetupResult("smart-fork", "Smart Fork Detection", 6, ToolHealth.SKIPPED))



# ─────────────────────────────────────────────────────────────────────────────
# Status display (health-aware)
# ─────────────────────────────────────────────────────────────────────────────

def show_status(project_root: Path) -> None:
    """Health-aware status report — shows configured, installed, degraded, and pending."""
    print()
    print(f"{BOLD}{CYAN}  ccsetup status{RESET}  {DIM}{project_root}{RESET}")
    print()

    servers  = get_mcp_servers(project_root)
    settings = get_local_settings(project_root)
    hooks    = get_hook_commands(project_root)

    # ── MCP servers with health checks ───────────────────────────────────────
    print(f"  {BOLD}MCP Servers (.mcp.json){RESET}")
    if servers:
        # Canonical tool registry for health checks
        mcp_checks: list[tuple[str, str, str, list[str]]] = [
            # (mcp_key,         display_name,          binary,        env_vars)
            ("serena",          "Serena",               "uvx",         []),
            ("leann-server",    "LEANN",                "leann_mcp",   []),
            ("Claude Context",  "Claude Context",       "npx",
             ["ZILLIZ_CLOUD_URI", "ZILLIZ_CLOUD_API_KEY", "EMBEDDING_API_KEY"]),
            ("context7",        "Context7",             "npx",         []),
            ("claude-session",  "claude-session-mcp",   "claude-session-mcp", []),
            ("context-mode",    "context-mode",         "npx",         []),
            ("claude-mind",     "claude-mind",           "python3",     []),
            ("claude-charter",  "claude-charter",        "python3",     []),
            ("claude-witness",  "claude-witness",        "python3",     []),
            ("claude-retina",   "claude-retina",         "python3",     []),
            ("claude-ledger",   "claude-ledger",         "python3",     []),
            ("seu-claude",      "seu-claude",           "npx",         []),
            ("codegraphcontext","CodeGraphContext",     "cgc",         []),
        ]
        _ccsetup_bundled = {"claude-mind", "claude-charter", "claude-witness",
                            "claude-retina", "claude-ledger"}
        for key, name, binary, envs in mcp_checks:
            if key not in servers:
                continue
            if key in _ccsetup_bundled:
                h = health_ccsetup_server(key)
            else:
                h = health_mcp_tool(project_root, key, binary, envs or None)
            color, icon, label = _HEALTH_DISPLAY[h]
            degraded_detail = ""
            if h == ToolHealth.CONFIGURED_ONLY:
                degraded_detail = f"  {DIM}(binary '{binary}' not found){RESET}"
            if h == ToolHealth.NOT_CONFIGURED:
                degraded_detail = f"  {DIM}(run 'bash install.sh' in ccsetup repo){RESET}"
            if h == ToolHealth.MISSING_ENV:
                missing = [v for v in envs if not os.environ.get(v)]
                degraded_detail = f"  {DIM}(missing: {', '.join(missing)}){RESET}"
            exp_tag = f"  {YELLOW}[experimental]{RESET}" if key in EXPERIMENTAL_TOOLS else ""
            print(f"    {color}{icon}{RESET}  {name:<22} {DIM}{label}{RESET}{degraded_detail}{exp_tag}")
        # Any unchecked servers
        checked_keys = {k for k, *_ in mcp_checks}
        for key in servers:
            if key not in checked_keys:
                print(f"    {CYAN}◉{RESET}  {key}")
    else:
        print(f"    {DIM}none{RESET}")
    print()

    # ── Hooks ─────────────────────────────────────────────────────────────────
    print(f"  {BOLD}Hooks (.claude/settings.local.json){RESET}")
    if hooks:
        for event, cmd in hooks:
            snippet = cmd[:55] + ("…" if len(cmd) > 55 else "")
            print(f"    {GREEN}✔{RESET}  {CYAN}{event}{RESET}: {snippet}")
    else:
        print(f"    {DIM}none{RESET}")
    print()

    # ── Global binaries ───────────────────────────────────────────────────────
    print(f"  {BOLD}Global CLI Tools{RESET}")
    global_tools = [
        ("claude",          "Claude Code CLI"),
        ("uvx",             "uv (Serena runtime)"),
        ("dgc",             "GrapeRoot"),
        ("npx",             "Node.js / npx"),
        ("ccusage",         "ccusage (token dashboard)"),
        ("leann_mcp",       "LEANN"),
        ("claude-session-mcp", "claude-session-mcp"),
        ("cgc",             "CodeGraphContext"),
        ("go",              "Go (cclogviewer etc.)"),
    ]
    for binary, label in global_tools:
        ok_flag = which(binary)
        color = GREEN if ok_flag else DIM
        icon  = "✔" if ok_flag else "○"
        print(f"    {color}{icon}{RESET}  {label:<26} {DIM}({binary}){RESET}")
    print()

    # ── Missing env vars check ────────────────────────────────────────────────
    env_checks = [
        ("Claude Context", ["ZILLIZ_CLOUD_URI", "ZILLIZ_CLOUD_API_KEY", "EMBEDDING_API_KEY"]),
        ("remote-approver", ["NTFY_TOPIC"]),
    ]
    env_issues = []
    for tool_name, evars in env_checks:
        missing = [v for v in evars if not os.environ.get(v)]
        if missing and (tool_name == "remote-approver" or "Claude Context" in servers):
            env_issues.append((tool_name, missing))
    if env_issues:
        print(f"  {BOLD}{YELLOW}Missing Environment Variables{RESET}")
        for tool_name, missing in env_issues:
            print(f"    {YELLOW}!{RESET}  {tool_name}: {', '.join(missing)}")
        print()

    # ── ccsetup report ────────────────────────────────────────────────────────
    report = project_root / ".claude" / "ccsetup-report.md"
    if report.exists():
        print(f"  {DIM}Last setup report: {report}{RESET}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# Post-run manifest
# ─────────────────────────────────────────────────────────────────────────────

def write_manifest(project_root: Path) -> None:
    """Write .claude/ccsetup-report.md — the persistent record of setup state."""
    if _DRY_RUN or not _results:
        return

    lines: list[str] = [
        "# ccsetup Report",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"Project: `{project_root}`  ",
        f"ccsetup version: {VERSION}",
        "",
    ]

    # Group by health
    healthy     = [r for r in _results if r.health in (ToolHealth.HEALTHY, ToolHealth.USER_SCOPE)]
    degraded    = [r for r in _results if r.health in (ToolHealth.CONFIGURED_ONLY,
                                                        ToolHealth.MISSING_BINARY,
                                                        ToolHealth.MISSING_ENV)]
    manual_only = [r for r in _results if r.health == ToolHealth.MANUAL_REQUIRED]
    skipped     = [r for r in _results if r.health == ToolHealth.SKIPPED]

    if healthy:
        lines.append("## ✔ Enabled")
        lines.append("")
        for r in healthy:
            scope = " *(user scope)*" if r.health == ToolHealth.USER_SCOPE else ""
            lines.append(f"- **{r.tool_name}** (Layer {r.layer}){scope}")
            for note in r.notes:
                lines.append(f"  - {note}")
        lines.append("")

    if degraded:
        lines.append("## ⚠ Configured but Degraded")
        lines.append("")
        lines.append("These are in your config but may not work until the issue is resolved.")
        lines.append("")
        for r in degraded:
            _, _, label = _HEALTH_DISPLAY[r.health]
            lines.append(f"- **{r.tool_name}** — {label}")
            for step in r.manual_steps:
                lines.append(f"  - {step}")
            for ev in r.env_vars:
                lines.append(f"  - Set env var: `{ev}`")
        lines.append("")

    if manual_only:
        lines.append("## → Manual Steps Required")
        lines.append("")
        lines.append("These tools were selected but require manual configuration.")
        lines.append("")
        for r in manual_only:
            lines.append(f"### {r.tool_name} (Layer {r.layer})")
            for step in r.manual_steps:
                lines.append(f"- {step}")
            for ev in r.env_vars:
                lines.append(f"- Set env var: `{ev}`")
            lines.append("")

    if skipped:
        lines.append("## — Skipped")
        lines.append("")
        skipped_names = ", ".join(r.tool_name for r in skipped)
        lines.append(skipped_names)
        lines.append("")

    # Env var summary
    all_env = []
    for r in _results:
        if r.env_vars and r.health != ToolHealth.SKIPPED:
            all_env.extend(r.env_vars)
    if all_env:
        lines.append("## Environment Variables Needed")
        lines.append("")
        for ev in dict.fromkeys(all_env):  # deduplicated, ordered
            set_val = "✔ set" if os.environ.get(ev) else "✘ not set"
            lines.append(f"- `{ev}` — {set_val}")
        lines.append("")

    path = project_root / ".claude" / "ccsetup-report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    ok(f"Setup report → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Tool Ledger — capability matrix for session-start context loading
# ─────────────────────────────────────────────────────────────────────────────

# Known MCP tool catalogs: (mcp_key, server_name, tools_list)
# Each tool is (name, params_summary, when_to_use)
_TOOL_CATALOG: dict[str, list[tuple[str, str, str]]] = {
    "serena": [
        ("get_symbols_overview",      "relative_path",                    "Need file structure / symbol list"),
        ("find_symbol",               "name_path_pattern, depth?, include_body?", "Looking for a specific symbol by name"),
        ("find_referencing_symbols",  "name, relative_path?",             "Need callers / usages of a symbol"),
        ("replace_symbol_body",       "symbol, new_body",                 "Editing an entire function/method/class body"),
        ("insert_after_symbol",       "symbol, code",                     "Adding code after an existing symbol"),
        ("insert_before_symbol",      "symbol, code",                     "Adding code before an existing symbol"),
        ("rename_symbol",             "symbol, new_name",                 "Renaming across all references"),
        ("search_for_pattern",        "pattern, relative_path?",          "Regex search when symbol name is unknown"),
        ("list_dir",                  "relative_path?",                   "Directory listing within project"),
        ("find_file",                 "filename, relative_path?",         "Searching for file by name"),
    ],
    "claude-mind": [
        ("mind_open",       "title",                             "Starting or resuming an investigation"),
        ("mind_add",        "type, content, confidence?, files?, evidence_ids?, depends_on?", "Recording hypothesis/fact/assumption/question/ruled_out/next_step"),
        ("mind_update",     "node_id, status, notes?",           "Confirming/refuting hypothesis or assumption"),
        ("mind_query",      "filter",                            "Reviewing nodes by type/status/text search"),
        ("mind_summary",    "(none)",                            "Recovering full investigation state after compaction"),
        ("mind_resolve",    "conclusion, node_ids?",             "Closing investigation with conclusion"),
        ("mind_import_witness", "fn_name, run_id?",              "Importing witness execution data as a FACT node"),
        ("mind_graph",      "(none)",                            "Visualize reasoning chains and dependency trees"),
    ],
    "claude-charter": [
        ("charter_add",     "type, content, notes?, scope?",     "Recording invariant/constraint/non_goal/contract/goal"),
        ("charter_update",  "id, status?, content?, notes?",     "Modifying or archiving an entry"),
        ("charter_query",   "filter",                            "Reviewing entries by type or text search"),
        ("charter_summary", "(none)",                            "Full project constitution overview"),
        ("charter_check",   "change_description, file_path?",   "Before any structural change — checks for conflicts"),
        ("charter_audit",   "(none)",                            "Charter health report: gaps, imbalances, prohibitions"),
    ],
    "claude-witness": [
        ("witness_runs",         "limit?",                        "Listing recent test runs with pass/fail"),
        ("witness_traces",       "fn_name, run_id?, status?",     "Investigating specific function call behavior"),
        ("witness_exception",    "exc_type, run_id?",             "Exception details with local variable state"),
        ("witness_coverage_gaps","file",                           "Finding untested code paths"),
        ("witness_diff",         "run_a, run_b",                   "Comparing two test runs — what changed"),
        ("witness_check_charter","run_id?",                        "Cross-checking execution against charter entries"),
        ("witness_hotspots",     "limit?, run_count?",             "Functions with most exceptions — prioritize debugging"),
    ],
    "leann-server": [
        ("leann_search",   "query, limit?",                       "Semantic code search — find by meaning"),
        ("leann_index",    "directory?",                           "Build/refresh the local search index"),
    ],
    "context7": [
        ("resolve-library-id", "libraryName",                     "Find library ID for docs lookup"),
        ("get-library-docs",   "context7CompatibleLibraryID, topic?", "Fetch live library documentation"),
    ],
    "claude-session": [
        ("session_list",    "(none)",                             "List available sessions"),
        ("session_clone",   "session_id",                         "Fork a session for parallel investigation"),
        ("session_archive", "session_id",                         "Archive a session snapshot"),
        ("session_restore", "session_id",                         "Restore a previous session state"),
    ],
    "context-mode": [
        ("context_status",  "(none)",                             "Check what's virtualized vs. in context"),
        ("context_search",  "query",                              "Search across virtualized tool outputs"),
    ],
    "seu-claude": [
        ("memory_store",    "key, value",                         "Persist data across sessions"),
        ("memory_recall",   "key",                                "Retrieve persisted data"),
        ("task_create",     "title, description?",                "Create task for orchestration"),
        ("task_list",       "status?",                            "List tracked tasks"),
    ],
    "codegraphcontext": [
        ("get_callers",     "symbol, depth?",                     "Find all callers of a function"),
        ("get_callees",     "symbol, depth?",                     "Find all functions called by a symbol"),
        ("get_impact",      "file_or_symbol",                     "Cross-file change impact analysis"),
    ],
    "token-counter": [
        ("count_tokens",     "text",                              "Estimate token cost before reading large content"),
        ("get_session_stats","(none)",                             "Running session cost dashboard"),
        ("log_usage",        "input_tokens, output_tokens, description?", "Record usage for cost tracking"),
    ],
    "claude-retina": [
        ("retina_capture",   "url, selector?, viewport?, scheme?, label?, wait_ms?",  "See what the running UI actually looks like"),
        ("retina_diff",      "capture_a, capture_b, threshold?",                       "Compare two screenshots pixel-by-pixel — find what changed"),
        ("retina_inspect",   "url, selector?, depth?, roles_only?",                    "Get accessibility/semantic DOM tree of a rendered page"),
        ("retina_console",   "url, actions?, categories?, wait_ms?",                   "Capture JS console errors/warnings during page load or interaction"),
        ("retina_interact",  "url, actions[], viewport?, label?",                      "Multi-step browser interaction — click/type/scroll with screenshot at each step"),
        ("retina_baseline",  "name, url, selector?, viewport?, scheme?, notes?",       "Save named visual baseline for regression testing"),
        ("retina_regress",   "name, url?, threshold?, pixel_threshold?",               "Compare current UI against a saved baseline — PASS/FAIL + diff"),
        ("retina_history",   "limit?, type?, url_filter?",                             "List recent captures, diffs, baselines, interactions"),
    ],
    "claude-ledger": [
        ("ledger_query",     "task, healthy_only?",         "What tools to use for a given task — opinionated routing"),
        ("ledger_available", "layer?, healthy_only?",        "List all configured tools by layer with health status"),
        ("ledger_health",    "tool?",                        "Real-time health check for all or one tool"),
        ("ledger_workflows", "tag?",                         "Canonical workflow patterns for common tasks"),
        ("ledger_catalog",   "mcp_key?, configured_only?",  "Full tool signatures for one or all MCP servers"),
        ("ledger_context",   "(none)",                       "Session-start briefing: health + active state + next steps"),
        ("ledger_rules",     "section?",                    "Operational rules: anti-patterns, mandatory gates, priority chains, token habits, skills catalog"),
    ],
}

_WORKFLOWS = """## Workflows

### Investigation (multi-session debugging)
```
1. mind_open("title")                    → start investigation
2. mind_add("assumption", "...")         → record what you're treating as true
3. pytest --witness                      → capture execution evidence
4. witness_traces("fn_name")            → check what actually ran
5. mind_update(id, "confirmed/refuted") → update based on evidence
6. charter_check("proposed change")     → verify change is safe
7. mind_resolve("conclusion")           → close investigation
```

### After Context Compaction
```
1. mind_summary()      → recover investigation state
2. charter_summary()   → recover project constraints
3. graph_continue()    → recover file context
4. Resume work with full context restored
```

### Before Structural Changes
```
1. charter_check("description of change")
2. If conflict → reconsider or discuss with user
3. If clear → proceed with implementation
```

### Debugging Runtime Behavior
```
1. pytest --witness                    → capture execution
2. witness_runs()                      → check recent runs
3. witness_hotspots()                  → find chronic failure points
4. witness_traces("fn", status="exception") → find failing calls
5. witness_exception("ErrorType")      → get locals at crash
6. witness_coverage_gaps("file.py")    → find untested paths
```

### Understanding New Codebase
```
1. graph_continue("overview")          → get recommended files
2. get_symbols_overview("src/")        → file-by-file symbol maps
3. find_symbol("MainClass", depth=1)   → class structure
4. find_referencing_symbols("key_fn")  → understand call graph
```

### Visual UI Testing
```
1. retina_capture("http://localhost:3000")    → see the rendered UI
2. Read(file_path=".claude/retina/captures/<id>.png")  → view screenshot
3. retina_inspect("http://localhost:3000")    → get accessibility tree
4. retina_console("http://localhost:3000")    → check for JS errors
5. <make code changes>
6. retina_diff(id_before, id_after)           → verify visual change
```

### Visual Regression Guard
```
1. retina_baseline("feature-x", url)         → save baseline before changes
2. <implement changes>
3. retina_regress("feature-x")               → PASS/FAIL + diff if changed
4. If FAIL → retina_diff(baseline_id, new_id) → inspect changed regions
```

### Session Start (with claude-ledger)
```
1. ledger_context()    → health + active state + recommended next tools in one call
   (Replaces manual reading of tool-ledger.md)
2. Follow RECOMMENDED NEXT steps from ledger_context output
```
"""


def generate_tool_ledger(project_root: Path) -> None:
    """Generate .claude/tool-ledger.md — the complete capability matrix.

    This is the document Claude should read at session start to know
    every tool available, what it does, and when to use it.
    """
    servers = get_mcp_servers(project_root)
    hooks   = get_hook_commands(project_root)

    lines: list[str] = [
        "# Tool Ledger",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"Project: `{project_root.name}` | ccsetup {VERSION}*",
        "",
        "Read this at session start. It tells you every tool available and when to use each one.",
        "",
    ]

    # ── Active MCP Servers ────────────────────────────────────────────────────
    lines.append("## Active MCP Servers")
    lines.append("")

    if not servers:
        lines.append("*No MCP servers configured.*")
        lines.append("")
    else:
        # Map mcp_key to ToolDef for metadata
        tooldef_by_mcp: dict[str, ToolDef] = {}
        for td in TOOLS:
            if td.mcp_key:
                tooldef_by_mcp[td.mcp_key] = td

        for mcp_key in servers:
            td = tooldef_by_mcp.get(mcp_key)
            if td:
                lines.append(f"### {td.name} — Layer {td.layer} ({td.layer_name})")
                lines.append(f"*{td.tagline}*")
            else:
                lines.append(f"### {mcp_key}")
            lines.append("")

            # Tool table from catalog
            if mcp_key in _TOOL_CATALOG:
                lines.append("| Tool | Params | Use When |")
                lines.append("|------|--------|----------|")
                for tname, params, when in _TOOL_CATALOG[mcp_key]:
                    lines.append(f"| `{tname}` | {params} | {when} |")
                lines.append("")
            else:
                lines.append(f"*Tool list not cataloged — run tools/list to discover.*")
                lines.append("")

    # ── Hooks ─────────────────────────────────────────────────────────────────
    lines.append("## Active Hooks")
    lines.append("")
    if hooks:
        lines.append("| Event | Command |")
        lines.append("|-------|---------|")
        for event, cmd in hooks:
            snippet = cmd[:80] + ("…" if len(cmd) > 80 else "")
            lines.append(f"| {event} | `{snippet}` |")
        lines.append("")
    else:
        lines.append("*No hooks configured.*")
        lines.append("")

    # ── CLI Commands ──────────────────────────────────────────────────────────
    lines.append("## CLI Commands Available")
    lines.append("")
    cli_tools = [
        ("claude",    "Claude Code CLI — primary interface"),
        ("dgc",       "GrapeRoot — precomputed dual graph builder"),
        ("ccsetup",   "Stack bootstrapper — this tool"),
        ("ccusage",   "Token usage dashboard"),
        ("uvx",       "Python tool runner (Serena, etc.)"),
        ("npx",       "Node.js package runner"),
        ("pytest",    "Python test runner (add --witness for execution capture)"),
    ]
    for binary, desc in cli_tools:
        available = "✔" if which(binary) else "○"
        lines.append(f"- {available} `{binary}` — {desc}")
    lines.append("")

    # ── State Files ───────────────────────────────────────────────────────────
    lines.append("## State Files")
    lines.append("")
    state_files = [
        (".claude/mind.json",       "claude-mind",    "Investigation reasoning state"),
        (".claude/charter.json",    "claude-charter",  "Project constitution entries"),
        (".claude/witness/",        "claude-witness",  "Execution trace files (one per run)"),
        (".mcp.json",               "(config)",        "MCP server configuration"),
        (".claude/settings.local.json", "(config)",    "Hooks and local settings"),
        (".dual-graph/",            "graperoot",       "Graph index and context store"),
        ("CLAUDE.md",               "(directives)",    "Project instructions for Claude"),
    ]
    for fpath, tool, desc in state_files:
        full = project_root / fpath
        exists = "✔" if full.exists() else "○"
        lines.append(f"- {exists} `{fpath}` ({tool}) — {desc}")
    lines.append("")

    # ── Workflows ─────────────────────────────────────────────────────────────
    lines.append(_WORKFLOWS)

    # ── Cross-Tool Integration Map ────────────────────────────────────────────
    lines.append("## Cross-Tool Integration")
    lines.append("")
    lines.append("| From | To | Via | Purpose |")
    lines.append("|------|----|----|---------|")
    lines.append("| witness | mind | `mind_import_witness(fn_name)` | Import execution evidence as FACT node |")
    lines.append("| witness | charter | `witness_check_charter(run_id?)` | Flag execution that violates constraints |")
    lines.append("| mind | witness | `evidence_ids: [\"witness:run:call\"]` | Link hypothesis to execution proof |")
    lines.append("| mind | charter | `evidence_ids: [\"charter:entry_id\"]` | Link reasoning to normative entry |")
    lines.append("| graph | all | `graph_continue` → context → tools | Routes to relevant files before any work |")
    lines.append("| serena | all | Symbol-level reads/edits | Precise code navigation for any task |")
    lines.append("")

    # ── Write ─────────────────────────────────────────────────────────────────
    path = project_root / ".claude" / "tool-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    ok(f"Tool ledger → {path}")
    info("Add to CLAUDE.md: 'Read .claude/tool-ledger.md at session start for full capability awareness.'")


# ─────────────────────────────────────────────────────────────────────────────
# GUI — HTML template (dark SPA)
# ─────────────────────────────────────────────────────────────────────────────

_LAYER_NAMES = {
    0: ("Foundation",         "Always-on — Claude's core eyes into the codebase"),
    1: ("Context Intelligence","Smart retrieval by meaning, not exhaustive reads"),
    2: ("Memory & Continuity", "Cross-session persistence and anti-compaction"),
    3: ("Safety & Guardrails", "Hook-based defenses that run independently of Claude"),
    4: ("Observability",       "See where tokens go, trace decisions, ambient awareness"),
    5: ("Orchestration",       "Multi-agent coordination and MCP surface compression"),
    6: ("Workflow",            "Call graphs, remote approvals, session archaeology"),
}

_LAYER_COLORS = {
    0: "#8b5cf6", 1: "#3b82f6", 2: "#10b981",
    3: "#ef4444", 4: "#f59e0b", 5: "#ec4899", 6: "#06b6d4",
}


def _build_html(project_root: Path) -> str:
    """Build the GUI HTML page with the full tool registry embedded as JSON."""
    tools_json = json.dumps([{
        "id": t.id, "name": t.name, "layer": t.layer,
        "layer_name": t.layer_name, "tagline": t.tagline,
        "description": t.description, "why": t.why_i_want_it,
        "skip": t.skip_when, "always_on": t.always_on,
        "deprecated": t.deprecated, "invasive": t.invasive,
        "manual_only": t.manual_only, "privacy": t.privacy_concern,
        "presets": t.presets, "env_vars": t.env_vars,
    } for t in TOOLS], indent=2)

    layer_meta = json.dumps({str(k): {"name": v[0], "desc": v[1], "color": _LAYER_COLORS[k]}
                             for k, v in _LAYER_NAMES.items()})

    presets_json = json.dumps({k: list(v) for k, v in PRESETS.items()})

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ccsetup — Claude Code Bootstrapper</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0 }}
:root {{
  --bg: #0f1117; --card: #161b22; --card2: #1c2128;
  --border: #30363d; --accent: #8b5cf6; --text: #e6edf3;
  --muted: #8b949e; --green: #3fb950; --yellow: #d29922;
  --red: #f85149; --blue: #58a6ff; --radius: 8px;
}}
body {{ background: var(--bg); color: var(--text); font: 14px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; min-height: 100vh }}
a {{ color: var(--accent) }}

/* ── Top bar ── */
.topbar {{ background: var(--card); border-bottom: 1px solid var(--border); padding: 14px 24px; display: flex; align-items: center; gap: 16px; position: sticky; top: 0; z-index: 100 }}
.topbar-title {{ font-size: 1.1rem; font-weight: 700; color: var(--accent) }}
.topbar-sub {{ color: var(--muted); font-size: .85rem; flex: 1 }}
.version-badge {{ background: #21262d; border: 1px solid var(--border); border-radius: 20px; padding: 2px 10px; font-size: .78rem; color: var(--muted) }}

/* ── Controls strip ── */
.controls {{ background: var(--card2); border-bottom: 1px solid var(--border); padding: 12px 24px; display: flex; flex-wrap: wrap; align-items: center; gap: 12px; position: sticky; top: 53px; z-index: 99 }}
.preset-group {{ display: flex; gap: 6px }}
.preset-btn {{ background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 5px 14px; border-radius: 20px; cursor: pointer; font-size: .82rem; transition: all .15s }}
.preset-btn:hover {{ border-color: var(--accent); color: var(--text) }}
.preset-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600 }}
.scope-select {{ background: var(--card); border: 1px solid var(--border); color: var(--text); padding: 5px 10px; border-radius: 6px; font-size: .82rem }}
.scope-label {{ color: var(--muted); font-size: .82rem }}
.spacer {{ flex: 1 }}
.configure-btn {{ background: var(--accent); color: #fff; border: none; padding: 8px 20px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: .9rem; transition: opacity .15s }}
.configure-btn:hover {{ opacity: .85 }}
.configure-btn:disabled {{ opacity: .4; cursor: not-allowed }}

/* ── Main content ── */
.content {{ max-width: 900px; margin: 0 auto; padding: 24px }}

/* ── Layer section ── */
.layer-section {{ margin-bottom: 32px }}
.layer-header {{ display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 2px solid }}
.layer-num {{ font-size: .75rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; color: #fff }}
.layer-title {{ font-size: 1rem; font-weight: 700 }}
.layer-desc {{ font-size: .82rem; color: var(--muted) }}

/* ── Tool cards ── */
.tool-card {{ background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 8px; overflow: hidden; transition: border-color .15s }}
.tool-card:hover {{ border-color: #444c56 }}
.tool-card.always-on {{ border-left: 3px solid var(--accent) }}
.tool-card.deprecated {{ opacity: .65 }}

.tool-header {{ padding: 12px 16px; display: flex; align-items: center; gap: 12px; cursor: pointer }}
.tool-toggle {{ width: 38px; height: 22px; position: relative; flex-shrink: 0 }}
.tool-toggle input {{ opacity: 0; width: 0; height: 0 }}
.slider {{ position: absolute; inset: 0; background: #30363d; border-radius: 22px; transition: .2s; cursor: pointer }}
.slider:before {{ content:""; position: absolute; width: 16px; height: 16px; left: 3px; top: 3px; background: #8b949e; border-radius: 50%; transition: .2s }}
input:checked + .slider {{ background: var(--accent) }}
input:checked + .slider:before {{ transform: translateX(16px); background: #fff }}
input:disabled + .slider {{ cursor: not-allowed; opacity: .7 }}

.tool-info {{ flex: 1; min-width: 0 }}
.tool-name-row {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap }}
.tool-name {{ font-weight: 600; font-size: .92rem }}
.badge {{ font-size: .68rem; padding: 1px 7px; border-radius: 20px; font-weight: 600 }}
.badge.always-on  {{ background: rgba(139,92,246,.2); color: var(--accent) }}
.badge.deprecated {{ background: rgba(248,81,73,.15); color: var(--red) }}
.badge.invasive   {{ background: rgba(212,153,34,.15); color: var(--yellow) }}
.badge.manual     {{ background: rgba(88,166,255,.12); color: var(--blue) }}
.badge.privacy    {{ background: rgba(248,81,73,.1); color: #ff8b8b }}
.tool-tagline {{ font-size: .82rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis }}

.expand-btn {{ background: transparent; border: none; color: var(--muted); cursor: pointer; font-size: .82rem; padding: 4px 8px; border-radius: 4px; flex-shrink: 0; transition: background .1s }}
.expand-btn:hover {{ background: #21262d }}

.tool-details {{ display: none; padding: 0 16px 14px 66px; border-top: 1px solid var(--border) }}
.tool-details.open {{ display: block }}
.detail-section {{ margin-top: 10px }}
.detail-label {{ font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: 3px }}
.detail-text {{ font-size: .85rem; color: #c9d1d9; line-height: 1.55 }}
.why-text {{ color: #a5d6ff; font-style: italic }}
.skip-text {{ color: var(--muted) }}
.env-pills {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px }}
.env-pill {{ background: #21262d; border: 1px solid var(--border); border-radius: 4px; font-size: .75rem; padding: 2px 8px; font-family: monospace; color: var(--yellow) }}

/* ── Terminal ── */
#terminal-wrap {{ position: fixed; bottom: 0; left: 0; right: 0; background: var(--card); border-top: 2px solid var(--accent); transform: translateY(100%); transition: transform .25s ease; z-index: 200; max-height: 40vh; display: flex; flex-direction: column }}
#terminal-wrap.open {{ transform: translateY(0) }}
.terminal-bar {{ padding: 8px 16px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--border) }}
.terminal-bar-title {{ font-size: .82rem; font-weight: 600; color: var(--accent); flex: 1 }}
.terminal-close {{ background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 2px 10px; border-radius: 4px; cursor: pointer; font-size: .8rem }}
#terminal-output {{ flex: 1; overflow-y: auto; padding: 12px 16px; font: 12px/1.5 'SF Mono','Fira Code',monospace; background: #0d1117; white-space: pre-wrap; word-break: break-all }}
.t-ok   {{ color: #3fb950 }} .t-warn {{ color: #d29922 }} .t-err  {{ color: #f85149 }}
.t-info {{ color: #58a6ff }} .t-dim  {{ color: #8b949e }} .t-bold {{ color: #e6edf3; font-weight:700 }}
.t-section {{ color: #8b5cf6; font-weight: 700 }}

/* ── Done banner ── */
#done-banner {{ display: none; background: rgba(63,185,80,.12); border: 1px solid rgba(63,185,80,.3); border-radius: var(--radius); padding: 12px 16px; margin-top: 16px; color: var(--green) }}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-title">⬡ ccsetup</div>
  <div class="topbar-sub">Claude Code Stack Bootstrapper &mdash; <code style="font-size:.8rem;color:#aaa">{project_root}</code></div>
  <div class="version-badge">v{VERSION}</div>
</div>

<div class="controls">
  <div class="preset-group">
    <span style="font-size:.8rem;color:var(--muted);margin-right:4px">Preset:</span>
    <button class="preset-btn" data-preset="minimal">Minimal</button>
    <button class="preset-btn active" data-preset="recommended">Recommended</button>
    <button class="preset-btn" data-preset="maximal">Maximal</button>
    <button class="preset-btn" data-preset="none">Custom</button>
  </div>
  <span class="scope-label">Scope:</span>
  <select id="scope-mode" class="scope-select">
    <option value="hybrid" selected>Hybrid (smart default)</option>
    <option value="repo">Repo only</option>
    <option value="user">User global</option>
  </select>
  <div class="spacer"></div>
  <button id="configure-btn" class="configure-btn" onclick="startSetup()">
    ▶ Configure Selected Tools
  </button>
</div>

<div class="content" id="content"></div>
<div id="done-banner">✔ Setup complete — check <code>.claude/ccsetup-report.md</code> for the full report.</div>

<div id="terminal-wrap">
  <div class="terminal-bar">
    <span class="terminal-bar-title">⬡ Setup Terminal</span>
    <span id="terminal-status" style="font-size:.78rem;color:var(--muted)">idle</span>
    <button class="terminal-close" onclick="document.getElementById('terminal-wrap').classList.toggle('open')">▼ hide</button>
  </div>
  <div id="terminal-output"></div>
</div>

<script>
const TOOLS = {tools_json};
const LAYER_META = {layer_meta};
const PRESETS = {presets_json};

let activePreset = 'recommended';
let checkedTools = new Set(PRESETS.recommended);

function renderTools() {{
  const content = document.getElementById('content');
  const layers = [0,1,2,3,4,5,6];
  content.innerHTML = layers.map(l => {{
    const meta = LAYER_META[l];
    const tools = TOOLS.filter(t => t.layer === l);
    if (!tools.length) return '';
    const color = meta.color;
    return `<div class="layer-section">
      <div class="layer-header" style="border-color:${{color}}20">
        <span class="layer-num" style="background:${{color}}">${{l}}</span>
        <span class="layer-title">${{meta.name}}</span>
        <span class="layer-desc">${{meta.desc}}</span>
      </div>
      ${{tools.map(t => renderCard(t)).join('')}}
    </div>`;
  }}).join('');
}}

function renderCard(t) {{
  const checked  = checkedTools.has(t.id) || t.always_on;
  const disabled = t.always_on;
  const badges = [
    t.always_on    ? '<span class="badge always-on">Always On</span>' : '',
    t.deprecated   ? '<span class="badge deprecated">Deprecated</span>' : '',
    t.invasive     ? '<span class="badge invasive">Invasive</span>' : '',
    t.manual_only  ? '<span class="badge manual">Manual Setup</span>' : '',
    t.privacy      ? '<span class="badge privacy">Sends Data Externally</span>' : '',
  ].filter(Boolean).join('');
  const envHtml = t.env_vars.length
    ? `<div class="detail-section"><div class="detail-label">Requires env vars</div>
       <div class="env-pills">${{t.env_vars.map(e => `<span class="env-pill">${{e}}</span>`).join('')}}</div></div>`
    : '';
  return `<div class="tool-card${{t.always_on?' always-on':''}}${{t.deprecated?' deprecated':''}}" id="card-${{t.id}}">
    <div class="tool-header" onclick="toggleDetails('${{t.id}}')">
      <label class="tool-toggle" onclick="event.stopPropagation()">
        <input type="checkbox" id="chk-${{t.id}}" ${{checked?'checked':''}} ${{disabled?'disabled':''}}
               onchange="onToggle('${{t.id}}', this.checked)">
        <span class="slider"></span>
      </label>
      <div class="tool-info">
        <div class="tool-name-row">
          <span class="tool-name">${{t.name}}</span>${{badges}}
        </div>
        <div class="tool-tagline">${{t.tagline}}</div>
      </div>
      <button class="expand-btn" id="expand-${{t.id}}">details ▼</button>
    </div>
    <div class="tool-details" id="details-${{t.id}}">
      <div class="detail-section"><div class="detail-label">What it does</div>
        <div class="detail-text">${{t.description}}</div></div>
      <div class="detail-section"><div class="detail-label">Why I want this</div>
        <div class="detail-text why-text">${{t.why}}</div></div>
      <div class="detail-section"><div class="detail-label">Skip when</div>
        <div class="detail-text skip-text">${{t.skip}}</div></div>
      ${{envHtml}}
    </div>
  </div>`;
}}

function toggleDetails(id) {{
  const d = document.getElementById('details-' + id);
  const b = document.getElementById('expand-' + id);
  const open = d.classList.toggle('open');
  b.textContent = open ? 'details ▲' : 'details ▼';
}}

function onToggle(id, checked) {{
  if (checked) checkedTools.add(id); else checkedTools.delete(id);
  // Deactivate preset label if custom
  document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('[data-preset="none"]').classList.add('active');
  activePreset = 'none';
}}

function applyPreset(name) {{
  activePreset = name;
  document.querySelectorAll('.preset-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.preset === name));
  if (name === 'none') return;
  const ids = PRESETS[name] || [];
  checkedTools = new Set(ids);
  TOOLS.forEach(t => {{
    const el = document.getElementById('chk-' + t.id);
    if (el && !el.disabled) el.checked = checkedTools.has(t.id);
  }});
}}

document.querySelectorAll('.preset-btn').forEach(b =>
  b.addEventListener('click', () => applyPreset(b.dataset.preset)));

function startSetup() {{
  const btn = document.getElementById('configure-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Running…';

  const scope = document.getElementById('scope-mode').value;
  const selected = TOOLS
    .filter(t => t.always_on || checkedTools.has(t.id))
    .map(t => t.id);

  fetch('/api/configure', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{ tools: selected, scope_mode: scope }}),
  }}).then(r => r.json()).then(d => {{
    if (d.ok) openTerminal();
    else alert('Error: ' + d.error);
  }}).catch(e => alert('Request failed: ' + e));
}}

function openTerminal() {{
  const wrap = document.getElementById('terminal-wrap');
  wrap.classList.add('open');
  const out = document.getElementById('terminal-output');
  out.innerHTML = '';
  document.getElementById('terminal-status').textContent = 'running';

  const es = new EventSource('/api/events');
  es.onmessage = e => {{
    if (e.data === '__DONE__') {{
      es.close();
      document.getElementById('terminal-status').textContent = 'done';
      document.getElementById('configure-btn').textContent = '✔ Done';
      document.getElementById('configure-btn').disabled = false;
      document.getElementById('done-banner').style.display = 'block';
      return;
    }}
    const line = document.createElement('div');
    line.innerHTML = ansiToHtml(e.data);
    out.appendChild(line);
    out.scrollTop = out.scrollHeight;
  }};
  es.onerror = () => {{
    es.close();
    document.getElementById('terminal-status').textContent = 'disconnected';
  }};
}}

function ansiToHtml(s) {{
  const map = {{'\\033[32m':'<span class="t-ok">','\\033[33m':'<span class="t-warn">',
    '\\033[31m':'<span class="t-err">','\\033[36m':'<span class="t-info">',
    '\\033[2m':'<span class="t-dim">','\\033[1m':'<span class="t-bold">',
    '\\033[34m':'<span class="t-info">','\\033[0m':'</span>'}};
  let html = s.replace(/&/g,'&amp;').replace(/</g,'&lt;');
  // Strip remaining ANSI if any
  html = html.replace(/\\033\\[[0-9;]*m/g, '');
  return html;
}}

// Init
renderTools();
applyPreset('recommended');
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# GUI — HTTP server
# ─────────────────────────────────────────────────────────────────────────────

_gui_event_queue: "queue.Queue[str]" = queue.Queue()
_gui_project_root: Path | None = None


class _GUIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        pass  # suppress default access log

    def do_GET(self) -> None:
        if self.path == "/":
            html = _build_html(_gui_project_root or Path(".")).encode()
            self._send(200, "text/html; charset=utf-8", html)
        elif self.path == "/api/status":
            data = json.dumps({"version": VERSION, "project": str(_gui_project_root)}).encode()
            self._send(200, "application/json", data)
        elif self.path == "/api/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    try:
                        msg = _gui_event_queue.get(timeout=30)
                        data = f"data: {msg}\n\n".encode()
                        self.wfile.write(data)
                        self.wfile.flush()
                        if msg == "__DONE__":
                            break
                    except queue.Empty:
                        # Send keepalive comment
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self) -> None:
        if self.path == "/api/configure":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            selected: list[str] = body.get("tools", [])
            scope: str = body.get("scope_mode", "hybrid")
            self._send(200, "application/json", json.dumps({"ok": True}).encode())
            # Run setup in background thread
            t = threading.Thread(target=_run_setup_gui,
                                 args=(_gui_project_root, selected, scope),
                                 daemon=True)
            t.start()
        else:
            self._send(404, "text/plain", b"Not found")

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send(self, code: int, ctype: str, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


class _QueueWriter(io.TextIOBase):
    """Redirects print() output to the SSE event queue."""
    def __init__(self, q: "queue.Queue[str]", original: Any) -> None:
        self._q   = q
        self._orig = original

    def write(self, s: str) -> int:
        if s and s != "\n":
            for line in s.splitlines():
                if line.strip():
                    self._q.put(line)
        return len(s)

    def flush(self) -> None:
        pass


def _run_setup_gui(project_root: Path, selected_ids: list[str], scope_mode: str) -> None:
    global _DRY_RUN, _ASSUME_YES, _SCOPE_MODE, _PRESET_TOOLS, _EXPERIMENTAL, _results

    _DRY_RUN      = False
    _ASSUME_YES   = True
    _SCOPE_MODE   = scope_mode
    _PRESET_TOOLS = set(selected_ids)
    _EXPERIMENTAL = bool(EXPERIMENTAL_TOOLS & _PRESET_TOOLS)
    _results      = []

    writer = _QueueWriter(_gui_event_queue, sys.stdout)
    old_stdout = sys.stdout
    sys.stdout = writer  # type: ignore[assignment]

    try:
        layer_fns = [
            layer0_foundation, layer1_context, layer2_memory,
            layer3_safety, layer4_observability, layer5_orchestration,
            layer6_workflow,
        ]
        for fn in layer_fns:
            fn(project_root)
        write_manifest(project_root)
    except Exception as exc:
        _gui_event_queue.put(f"  ERROR: {exc}")
    finally:
        sys.stdout = old_stdout
        _gui_event_queue.put("__DONE__")


def _find_free_port(start: int = 7437) -> int:
    import socket
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def run_gui_server(project_root: Path) -> None:
    global _gui_project_root
    _gui_project_root = project_root

    port = _find_free_port()
    url  = f"http://127.0.0.1:{port}"

    class _Server(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = _Server(("127.0.0.1", port), _GUIHandler)

    print()
    print(f"{BOLD}{BLUE}  ╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}  ║        ccsetup GUI — opening in browser…            ║{RESET}")
    print(f"{BOLD}{BLUE}  ╚══════════════════════════════════════════════════════╝{RESET}")
    print(f"  {DIM}URL:     {url}{RESET}")
    print(f"  {DIM}Project: {project_root}{RESET}")
    print(f"  {DIM}Press Ctrl-C to stop{RESET}")
    print()

    webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
        info("GUI server stopped.")
        httpd.shutdown()


# ─────────────────────────────────────────────────────────────────────────────
# Launch helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_configured(project_root: Path) -> bool:
    """Return True if this project has already been through ccsetup."""
    return (project_root / ".claude" / ".ccsetup-stamp").exists()


def write_stamp(project_root: Path) -> None:
    """Write a stamp file so subsequent runs know setup is complete."""
    if _DRY_RUN:
        return
    stamp = project_root / ".claude" / ".ccsetup-stamp"
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(
        json.dumps({
            "version": VERSION,
            "configured_at": datetime.now().isoformat(),
            "scope_mode": _SCOPE_MODE,
        }, indent=2),
        encoding="utf-8",
    )


def launch_claude(project_root: Path, claude_args: list[str]) -> None:
    """Launch Claude Code in project_root, forwarding any pass-through args."""
    if not which("claude"):
        err("'claude' not found. Install: npm install -g @anthropic-ai/claude-code")
        raise SystemExit(2)
    cmd = ["claude"] + claude_args
    if claude_args:
        print(f"  {BOLD}Launching Claude Code…{RESET}  {DIM}({' '.join(claude_args)}){RESET}")
    else:
        print(f"  {BOLD}Launching Claude Code…{RESET}")
    print()
    subprocess.run(cmd, cwd=str(project_root))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    global _DRY_RUN, _ASSUME_YES, _SCOPE_MODE, _PRESET_TOOLS, _EXPERIMENTAL

    ap = argparse.ArgumentParser(
        prog="ccsetup",
        description="Per-repo Claude Code stack bootstrapper — 7-layer tool hierarchy.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Unknown flags (e.g. --continue, --resume) are forwarded to 'claude' on launch.",
    )
    ap.add_argument("project",      nargs="?",  default=".", help="Project dir (default: .)")
    ap.add_argument("--status",     action="store_true", help="Health-aware status report and exit")
    ap.add_argument("--manifest",   action="store_true", help="Generate .claude/tool-ledger.md and exit")
    ap.add_argument("--dry-run",    action="store_true", help="Preview without writing")
    ap.add_argument("--no-launch",  action="store_true", help="Skip Claude Code launch at end")
    ap.add_argument("--yes", "-y",  action="store_true", help="Accept all defaults non-interactively")
    ap.add_argument("--from-layer", type=int, default=0, metavar="N",
                    help="Start from layer N (0–6)")
    ap.add_argument("--preset",     choices=["minimal", "recommended", "maximal"],
                    help="Auto-enable a curated tool set")
    ap.add_argument("--experimental", action="store_true",
                    help="Enable experimental tools (claude-mind, charter, witness, afe) on top of preset")
    ap.add_argument("--scope-mode", choices=["repo", "user", "hybrid"], default="hybrid",
                    help="MCP install scope policy (default: hybrid)")
    ap.add_argument("--setup",      action="store_true",
                    help="Force re-run full setup even if project is already configured")
    ap.add_argument("--version",    action="version", version=f"ccsetup {VERSION}")
    args, claude_args = ap.parse_known_args()

    _DRY_RUN      = args.dry_run
    _ASSUME_YES   = args.yes
    _SCOPE_MODE   = args.scope_mode
    _EXPERIMENTAL = args.experimental
    if args.preset:
        _PRESET_TOOLS = set(PRESETS[args.preset])
        _ASSUME_YES   = True  # presets run non-interactively
    if args.experimental:
        _PRESET_TOOLS |= EXPERIMENTAL_TOOLS

    project_root = resolve_project_root(Path(args.project).expanduser().resolve())

    # Greenfield: create the directory if it doesn't exist yet
    project_root.mkdir(parents=True, exist_ok=True)

    if args.status:
        show_status(project_root)
        return

    if args.manifest:
        generate_tool_ledger(project_root)
        return

    # ── Quick-launch: already configured ─────────────────────────────────────
    # If setup has already run for this project (stamp file present) and the
    # user hasn't asked to re-run it, skip all layers and go straight to launch.
    if is_configured(project_root) and not args.setup and not args.dry_run and not args.from_layer:
        print()
        print(f"  {DIM}Project already configured.  "
              f"Use '--setup' to re-run or '--status' to check health.{RESET}")
        print()
        if args.no_launch:
            info("Skipping launch (--no-launch)")
            return
        launch_claude(project_root, claude_args)
        return

    # ── Interface mode ────────────────────────────────────────────────────────
    # Skip the prompt when non-interactive (preset/yes/dry-run/from-layer)
    _noninteractive = bool(args.preset or args.yes or args.dry_run or args.from_layer > 0)
    if not _noninteractive:
        print()
        print(f"{BOLD}{BLUE}  ╔══════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{BLUE}  ║        ccsetup — Claude Code Bootstrapper  v{VERSION}    ║{RESET}")
        print(f"{BOLD}{BLUE}  ╚══════════════════════════════════════════════════════╝{RESET}")
        print()
        mode = ask_choice(
            "Interface preference?",
            ["CLI — step-by-step prompts in this terminal",
             "GUI — full tool browser, launch in browser (127.0.0.1)"],
            default_index=0,
        )
        if "GUI" in mode:
            run_gui_server(project_root)
            return

    # ── Banner ────────────────────────────────────────────────────────────────
    print()
    print(f"{BOLD}{BLUE}  ╔══════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{BLUE}  ║        ccsetup — Claude Code Bootstrapper  v{VERSION}    ║{RESET}")
    print(f"{BOLD}{BLUE}  ╚══════════════════════════════════════════════════════╝{RESET}")
    print(f"  {DIM}Project:    {project_root}{RESET}")
    print(f"  {DIM}Scope mode: {_SCOPE_MODE}{RESET}")
    if args.preset:
        print(f"  {DIM}Preset:     {args.preset} ({len(_PRESET_TOOLS)} tools){RESET}")
    if _EXPERIMENTAL:
        print(f"  {YELLOW}Experimental tools enabled: {', '.join(sorted(EXPERIMENTAL_TOOLS))}{RESET}")
    if _DRY_RUN:
        print(f"  {YELLOW}DRY RUN — no files will be written{RESET}")
    print()

    # ── Prerequisites ─────────────────────────────────────────────────────────
    section(-1, "Prerequisites")
    ensure_claude_code()
    ensure_uvx()
    ensure_node()

    # ── Layers ────────────────────────────────────────────────────────────────
    layer_fns = [
        layer0_foundation,
        layer1_context,
        layer2_memory,
        layer3_safety,
        layer4_observability,
        layer5_orchestration,
        layer6_workflow,
    ]
    for i, fn in enumerate(layer_fns):
        if i >= args.from_layer:
            fn(project_root)

    # ── Manifest + Tool Ledger ───────────────────────────────────────────────
    write_manifest(project_root)
    generate_tool_ledger(project_root)
    write_stamp(project_root)

    # ── Final summary ─────────────────────────────────────────────────────────
    healthy_count = sum(1 for r in _results
                        if r.health in (ToolHealth.HEALTHY, ToolHealth.USER_SCOPE))
    manual_count  = sum(1 for r in _results if r.health == ToolHealth.MANUAL_REQUIRED)
    degraded_count= sum(1 for r in _results if r.health in (ToolHealth.CONFIGURED_ONLY,
                                                              ToolHealth.MISSING_BINARY,
                                                              ToolHealth.MISSING_ENV))
    print()
    print(f"{BOLD}{GREEN}  ════ Setup Complete ════{RESET}")
    print()
    if healthy_count:  ok(f"{healthy_count} tool(s) healthy")
    if degraded_count: warn(f"{degraded_count} tool(s) degraded — check .claude/ccsetup-report.md")
    if manual_count:   info(f"{manual_count} tool(s) require manual steps — see .claude/ccsetup-report.md")
    info("Re-run anytime: ccsetup . --status")
    print()

    if args.no_launch:
        info("Skipping launch (--no-launch)")
        return

    launch_claude(project_root, claude_args)


if __name__ == "__main__":
    main()
