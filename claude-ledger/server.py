#!/usr/bin/env python3
"""claude-ledger MCP server — operational router and meta-orchestrator.

12 tools:
  ledger_context    (none)                       — CALL THIS FIRST: full operational brief
  ledger_query      task, healthy_only?           — concrete call sequence for any task
  ledger_rules      section?                      — operational rules (anti-patterns, gates)
  ledger_available  layer?, healthy_only?         — configured tools by layer with health
  ledger_health     tool?                         — real-time health check
  ledger_workflows  tag?                          — canonical workflow patterns
  ledger_catalog    mcp_key?, configured_only?    — full tool signatures
  ledger_diagnose   tool?                         — full prerequisite diagnosis + fix steps
  ledger_fix        tool                          — apply auto-fixable fixes (hooks, env, langs)
  ledger_mode       mode?                         — get or set token priority mode
  ledger_preflight  change, files?               — pre-change impact synthesis (CLEAR/CAUTION/BLOCKED)
  ledger_correlate  query, scope?                — unified cross-tool search

Design intent: ledger_context() is the FIRST call every session. It returns the complete
operational brief Claude needs to route correctly without reminders from the user.
ledger_query(task) returns the concrete call sequence — not just which server, but which
functions to call in which order.
ledger_diagnose/ledger_fix: when a tool is degraded, diagnose root cause and fix it —
never accept a broken tool and silently route around it.

Reads .mcp.json and .claude/ state in CWD at runtime (never cached).
Transport: stdio MCP (JSON-RPC 2.0). stdlib only.
"""

VERSION = "1.0.1"

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import catalog as _catalog
import health as _health
import router as _router
import rules as _rules


# ─────────────────────────────────────────────────────────────────────────────
# Mode persistence helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_mode() -> str:
    p = Path(".claude") / "ledger-mode.json"
    try:
        return json.loads(p.read_text())["mode"]
    except Exception:
        return "balanced"


def _save_mode(mode: str) -> None:
    p = Path(".claude") / "ledger-mode.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"mode": mode}))


# ─────────────────────────────────────────────────────────────────────────────
# Workflows (canonical step sequences — used by ledger_workflows)
# ─────────────────────────────────────────────────────────────────────────────

_WORKFLOWS: dict[str, dict] = {
    "session-start": {
        "tags": ["session", "start"],
        "title": "Session Start",
        "steps": [
            "ledger_context()              → full operational brief + active state",
            "graph_continue(query)         → MANDATORY: get recommended files for your task",
            "Follow RECOMMENDED NEXT from ledger_context output",
        ],
    },
    "compaction-recovery": {
        "tags": ["session", "compaction", "recovery"],
        "title": "After Context Compaction",
        "steps": [
            "mind_summary()                → recover investigation state (≤15 lines)",
            "mind_sweep()                  → check for stale assumptions after recovery",
            "charter_summary()             → recover project constraints",
            "graph_continue(query)         → recover file context",
            "(all three can run in parallel)",
        ],
    },
    "investigation": {
        "tags": ["debug", "investigation", "multi-session"],
        "title": "Multi-Session Investigation",
        "steps": [
            "mind_open('title')            → start investigation",
            "mind_add('assumption', '...') → externalize what you're treating as true",
            "pytest --witness              → capture execution evidence",
            "witness_traces('fn_name')     → check what actually ran",
            "mind_update(id, 'confirmed')  → update based on evidence",
            "charter_check('change')       → verify change is safe",
            "mind_resolve('conclusion')    → close investigation",
        ],
    },
    "structural-change": {
        "tags": ["refactor", "change", "safety"],
        "title": "Before Any Structural Change",
        "steps": [
            "charter_check('description of change')   → MANDATORY gate",
            "CLEAR → proceed",
            "CONFLICT → surface to user before touching code",
        ],
    },
    "debugging": {
        "tags": ["debug", "test", "runtime"],
        "title": "Debug Runtime Behavior",
        "steps": [
            "witness_runs(limit=5)                     → recent run history",
            "witness_hotspots(run_count=5)             → chronic failure points",
            "witness_traces('fn', status='exception')  → failing calls",
            "witness_exception('ErrorType')            → locals at crash",
            "witness_coverage_gaps('file.py')          → untested paths",
        ],
    },
    "new-codebase": {
        "tags": ["explore", "new", "understand"],
        "title": "Understand a New Codebase",
        "steps": [
            "graph_continue('overview')               → recommended files",
            "get_symbols_overview('src/')             → file structure",
            "find_symbol('MainClass', depth=1)        → class without bodies",
            "find_referencing_symbols('key_fn')       → call graph",
            "(steps 2+3+4 can run in parallel after step 1)",
        ],
    },
    "agent-spawn": {
        "tags": ["agent", "spawn", "afe"],
        "title": "Agent Compilation Before Spawn",
        "steps": [
            "afe_context()                             → read mind/charter/witness state",
            "afe_compile(task='...')                   → compile spec",
            "afe_validate(spec_id)                     → check against charter",
            "Agent(prompt=spec.system_prompt_fragment) → structured spawn",
        ],
    },
    "visual-ui": {
        "tags": ["visual", "ui", "retina", "browser"],
        "title": "Visual UI Testing",
        "steps": [
            "retina_capture(url)                       → screenshot",
            "Read(file_path=capture.file)              → view PNG",
            "retina_inspect(url)                       → accessibility tree",
            "retina_console(url)                       → JS errors",
            "<make changes>",
            "retina_diff(id_before, id_after)          → verify change",
            "(steps 1+3+4 can run in parallel)",
        ],
    },
    "visual-regression": {
        "tags": ["visual", "regression", "baseline", "retina"],
        "title": "Visual Regression Guard",
        "steps": [
            "retina_baseline('name', url)              → save baseline before changes",
            "<implement changes>",
            "retina_regress('name')                    → PASS/FAIL + diff",
            "If FAIL → Read(diff_file)                 → inspect changed regions",
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Tool implementations
# ─────────────────────────────────────────────────────────────────────────────

def ledger_context() -> str:
    """Primary session-start tool. Returns the complete operational brief.

    This is the single call that eliminates the need for human reminders
    about tool use. It tells Claude:
    1. HOW to use tools (anti-patterns + substitutions)
    2. WHEN to use mandatory gates
    3. WHAT is currently active (investigations, failures, state)
    4. WHAT to do next
    """
    mode = _load_mode()
    profile = _rules.MODE_PROFILES[mode]
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    servers = _health.load_mcp_servers()
    all_healths = _health.check_all()
    healthy_count = sum(1 for h in all_healths if h["healthy"])
    degraded = [h for h in all_healths if not h["healthy"]]

    lines = [
        f"LEDGER CONTEXT — {now_str}",
        "═" * 60,
        f"PRIORITY MODE: {profile['label']}",
        "─" * 21,
        profile["description"],
        "",
    ]

    # ── HOW TO USE YOUR TOOLS ──────────────────────────────────────────────
    lines += [
        "HOW TO USE YOUR TOOLS",
        "─" * 40,
        "",
        "ALWAYS START WITH:  graph_continue(query)",
        "  Returns ranked recommended_files. Trust the ranking.",
        "  Stop at confidence=high — do NOT grep further.",
        "  Call graph_read(file) in parallel for all recommended_files.",
        "",
        "FOR CODE NAVIGATION (prefer in this order):",
        "  get_symbols_overview → find_symbol(name, depth=1) → graph_read(file::symbol)",
        "  NEVER: Read(full_file) for code — reads 10x more than needed",
        "",
        "FOR DEBUGGING:",
        "  witness_runs() → witness_hotspots() → witness_traces() → witness_exception()",
        "  NEVER: Read source without checking execution evidence first",
        "",
        "FOR LIBRARY APIs:",
        "  context7: resolve-library-id → get-library-docs",
        "  NEVER: Use training knowledge for library APIs — it may be stale",
        "",
        "FOR GIT COMMITS:  Skill(skill='commit')  — not bash git commit",
        "FOR PR REVIEWS:   Skill(skill='review-pr', args='N')  — not manual gh commands",
        "FOR CODE QUALITY: Skill(skill='simplify')  — after significant edits",
        "",
    ]

    # ── MANDATORY GATES ────────────────────────────────────────────────────
    lines += [
        "MANDATORY GATES (call these BEFORE the action — non-negotiable)",
        "─" * 40,
    ]
    for g in _rules.MANDATORY_GATES:
        lines.append(f"  before {g['before'].lower()}")
        lines.append(f"    → {g['call']}")
        lines.append("")

    # ── DO NOT ──────────────────────────────────────────────────────────────
    lines += [
        "DO NOT (common mistakes — use the alternative instead)",
        "─" * 40,
    ]
    for s in _rules.TOOL_SUBSTITUTIONS[:6]:  # top 6 most important
        lines.append(f"  ✗  {s['avoid']}")
        lines.append(f"  ✓  {s['use_instead']}")
        lines.append("")

    lines += [
        "  → ledger_rules() for the complete substitution list",
        "",
    ]

    # ── CONFIGURED TOOLS ──────────────────────────────────────────────────
    lines += [
        "CONFIGURED TOOLS",
        "─" * 40,
        f"  {len(servers)} servers  ({healthy_count} healthy"
        + (f", {len(degraded)} degraded" if degraded else "")
        + ")",
    ]
    for h in degraded:
        mcp_key = h["mcp_key"]
        lines.append(f"  ⚠  {mcp_key} — {h['detail']}")
        # Run prerequisite diagnosis for additional context
        diag = _health.diagnose_tool(mcp_key)
        for issue in diag.get("issues", []):
            lines.append(f"       root cause: {issue}")
        fixes = diag.get("fixes", [])
        if fixes:
            auto_fixes = [f for f in fixes if f.get("auto")]
            manual_fixes = [f for f in fixes if not f.get("auto")]
            if auto_fixes:
                lines.append(f"       → ledger_fix('{mcp_key}') will auto-apply {len(auto_fixes)} fix(es)")
            for f in manual_fixes:
                lines.append(f"       manual: {f['step'].splitlines()[0]}")
    lines.append("")

    # ── ACTIVE STATE ──────────────────────────────────────────────────────
    lines += [
        "ACTIVE STATE",
        "─" * 40,
    ]
    has_state = False

    if "claude-mind" in servers:
        mind = _health.mind_active_state()
        if mind:
            has_state = True
            lines.append(
                f"  claude-mind:    investigation '{mind['status']}' — "
                f"\"{mind['title']}\" ({mind['total_nodes']} nodes, {mind['open_nodes']} open)"
            )

    if "claude-charter" in servers:
        charter = _health.charter_active_state()
        if charter and charter["total_active"] > 0:
            has_state = True
            by_type_str = ", ".join(
                f"{c} {t}s" for t, c in charter["by_type"].items()
            )
            lines.append(
                f"  claude-charter: {charter['total_active']} active entries"
                + (f" ({by_type_str})" if by_type_str else "")
            )

    if "claude-witness" in servers:
        witness = _health.witness_active_state()
        if witness:
            has_state = True
            fail_str = f", {witness['recent_failures']} failures" if witness["recent_failures"] else ""
            lines.append(
                f"  claude-witness: {witness['recent_runs']} recent runs"
                f" (last: {witness['latest_ts']}{fail_str})"
            )

    if "claude-retina" in servers:
        retina = _health.retina_active_state()
        if retina and (retina["captures"] or retina["baselines"]):
            has_state = True
            bn = retina["baseline_names"]
            bn_str = " (" + ", ".join(bn[:3]) + ("…" if len(bn) > 3 else "") + ")" if bn else ""
            lines.append(
                f"  claude-retina:  {retina['captures']} captures, "
                f"{retina['baselines']} baselines{bn_str}"
            )

    if not has_state:
        lines.append("  (no active state — fresh project or tools not yet seeded)")

    lines.append("")

    # ── PATTERNS (recurring problem areas) ────────────────────────────────
    if "claude-mind" in servers:
        mind_data = _health._read_json_safe(_health._claude_dir() / "mind.json")
        if mind_data:
            file_counts: dict[str, int] = {}
            for entry in mind_data.get("history", []):
                seen_files: set[str] = set()
                for n in entry.get("nodes", []):
                    for f in n.get("files", []):
                        seen_files.add(f)
                for f in seen_files:
                    file_counts[f] = file_counts.get(f, 0) + 1

            chronic = [(f, c) for f, c in file_counts.items() if c >= 3]
            if chronic:
                chronic.sort(key=lambda x: -x[1])
                lines += [
                    "PATTERNS (recurring problem areas)",
                    "─" * 40,
                ]
                for f, c in chronic[:5]:
                    lines.append(f"  {f} — appeared in {c} past investigations")
                lines.append("")

    # ── RECOMMENDED NEXT ──────────────────────────────────────────────────
    lines += [
        "RECOMMENDED NEXT",
        "─" * 40,
    ]
    recs: list[tuple[str, str]] = []

    # Priority 1: open investigation
    if "claude-mind" in servers:
        mind = _health.mind_active_state()
        if mind and mind["open_nodes"] > 0:
            recs.append(("mind_summary()", "open investigation needs attention"))

    # Priority 2: test failures
    if "claude-witness" in servers:
        witness = _health.witness_active_state()
        if witness and witness["recent_failures"] > 0:
            recs.append(("witness_hotspots()", f"{witness['recent_failures']} recent test failures to investigate"))

    # Priority 3: charter state
    if "claude-charter" in servers:
        charter = _health.charter_active_state()
        if charter and charter["total_active"] > 0:
            recs.append(("charter_summary()", f"review {charter['total_active']} active project constraints"))

    # Always: start with graph_continue
    recs.append(("graph_continue(query)", "get ranked file context before any work"))

    rec_limit = profile["context_rec_limit"]
    for i, (call, reason) in enumerate(recs[:rec_limit], 1):
        lines.append(f"  {i}. {call}")
        lines.append(f"     → {reason}")

    lines.append("")

    # ── MISSING TOOLS ──────────────────────────────────────────────────────
    if profile["show_not_configured"]:
        configured_keys = set(servers.keys())
        all_catalog_keys = set(_catalog.TOOL_CATALOG.keys())
        missing = all_catalog_keys - configured_keys - {"claude-ledger"}

        if missing:
            lines += [
                "NOT CONFIGURED (run ccsetup to add)",
                "─" * 40,
            ]
            for key in sorted(missing)[:4]:
                tools = _catalog.TOOL_CATALOG.get(key, [])
                if tools:
                    layer = _catalog.LAYER_MAP.get(key, "?")
                    layer_name = _catalog.LAYER_NAMES.get(layer, f"Layer {layer}")
                    lines.append(f"  {key} (Layer {layer} — {layer_name}): {tools[0][2].lower()}")
            lines.append("")

    lines += [
        "─" * 60,
        "ledger_query('task') → concrete call sequence for any task",
        "ledger_rules()       → full anti-pattern guide",
        "ledger_workflows()   → canonical step sequences",
    ]

    return "\n".join(lines)


def ledger_query(task: str, healthy_only: bool = False, mode: str | None = None) -> str:
    """Return the concrete call sequence for a task description.

    Not just 'use serena' — but 'call get_symbols_overview, then find_symbol,
    then graph_read(file::symbol)' with notes on parallelism and what to avoid.
    """
    if mode is None:
        mode = _load_mode()
    profile = _rules.MODE_PROFILES.get(mode, _rules.MODE_PROFILES["balanced"])

    servers = _health.load_mcp_servers()
    all_healths = {r["mcp_key"]: r for r in _health.check_all()}

    available_keys = None
    if healthy_only:
        available_keys = {k for k, h in all_healths.items() if h.get("healthy")}

    # 1. Match PRIORITY_CHAINS by task keywords (mode applies chain_limit + chain_truncate)
    matched_chains = _rules.match_chain(task, mode=mode)

    # 2. Score MCP routes (mode applies route_max, route_min_score, weight muls)
    routes = _router.route(task, available_keys=available_keys, mode=mode)

    if not matched_chains and not routes:
        return (
            f"No routing match for: {task!r}\n\n"
            "Try: ledger_workflows() for canonical patterns\n"
            "Or:  ledger_available() to see all configured tools"
        )

    lines = [f"ROUTING: {task!r}", ""]

    # Show matched playbooks first (most useful)
    if matched_chains:
        top_key, top_chain = matched_chains[0]
        lines += [
            f"CALL SEQUENCE ({top_chain['goal']})",
            "─" * 40,
        ]
        for step in top_chain["chain"]:
            lines.append(f"  {step}")
        lines.append("")

        if profile["show_parallel_tips"] and top_chain.get("parallel_tip"):
            lines.append(f"  PARALLEL: {top_chain['parallel_tip']}")
            lines.append("")

        if top_chain.get("avoid"):
            lines.append(f"  AVOID: {top_chain['avoid']}")
            lines.append("")

        # Show other matched chains if different
        if profile["show_alt_chains"]:
            for _, chain in matched_chains[1:2]:
                if chain["goal"] != top_chain["goal"]:
                    lines += [
                        f"ALSO RELEVANT ({chain['goal']})",
                        "─" * 40,
                    ]
                    for step in chain["chain"][:4]:
                        lines.append(f"  {step}")
                    lines.append("")

    # Show MCP server scores
    if routes:
        lines += [
            "CONFIGURED TOOLS (by relevance score)",
            "─" * 40,
        ]
        for r in routes:
            key = r["mcp_key"]
            h = all_healths.get(key, {})
            status = "✓" if h.get("healthy") else ("⚠" if h.get("configured") else "○")
            configured = key in servers

            lines.append(f"  {status} {key}  (score {r['score']:.2f}) — {r['description']}")
            if not configured:
                lines.append(f"    [not configured — run ccsetup to add]")
            elif not h.get("healthy", True):
                lines.append(f"    [degraded: {h.get('detail', '?')}]")

            # Show 2-3 most relevant tools
            tools = _catalog.TOOL_CATALOG.get(key, [])
            task_tokens = set(task.lower().split())
            relevant = sorted(
                tools,
                key=lambda t: sum(1 for tok in task_tokens if tok in t[0] or tok in t[2].lower()),
                reverse=True,
            )[:2]
            for tname, params, when in relevant:
                lines.append(f"    • {tname}({params})")
            lines.append("")

    # Check for applicable skills
    if profile["show_skills"]:
        applicable_skills = [
            s for s in _rules.SKILLS_CATALOG
            if any(t in task.lower() for t in s["trigger"].split())
        ]
        if applicable_skills:
            lines += ["SKILLS (Skill tool)", "─" * 40]
            for s in applicable_skills[:2]:
                lines.append(f"  {s['invoke']}  — {s['description']}")
            lines.append("")

    lines.append("→ ledger_rules() for anti-pattern guide")
    return "\n".join(lines)


def ledger_rules(section: str | None = None) -> str:
    """Return the operational rules — concise, token-efficient.

    Sections: substitutions | gates | chains | tokens | skills | builtins | all
    """
    sec = (section or "all").lower()
    lines: list[str] = []

    if sec in ("all", "substitutions"):
        lines += [
            "TOOL SUBSTITUTIONS (do X instead of Y)",
            "─" * 40,
        ]
        for s in _rules.TOOL_SUBSTITUTIONS:
            lines.append(f"  ✗  {s['avoid']}")
            lines.append(f"  ✓  {s['use_instead']}")
            if s.get("exception"):
                lines.append(f"     except: {s['exception']}")
            lines.append("")

    if sec in ("all", "gates"):
        lines += [
            "MANDATORY GATES",
            "─" * 40,
        ]
        for g in _rules.MANDATORY_GATES:
            lines.append(f"  before: {g['before']}")
            lines.append(f"  call:   {g['call']}")
            lines.append(f"  then:   {g['then']}")
            if g.get("skip_if"):
                lines.append(f"  skip:   {g['skip_if']}")
            lines.append("")

    if sec in ("all", "chains"):
        lines += [
            "PRIORITY CHAINS (concrete sequences per task type)",
            "─" * 40,
        ]
        for key, chain in _rules.PRIORITY_CHAINS.items():
            lines.append(f"  [{chain['goal']}]")
            for step in chain["chain"]:
                lines.append(f"    {step}")
            if chain.get("avoid"):
                lines.append(f"    AVOID: {chain['avoid']}")
            if chain.get("parallel_tip"):
                lines.append(f"    PARALLEL: {chain['parallel_tip']}")
            lines.append("")

    if sec in ("all", "tokens"):
        lines += [
            "TOKEN EFFICIENCY",
            "─" * 40,
        ]
        for rule in _rules.TOKEN_RULES:
            lines.append(f"  • {rule}")
        lines.append("")

    if sec in ("all", "skills"):
        lines += [
            "SKILLS (Claude Code Skill tool — slash commands)",
            "─" * 40,
        ]
        for s in _rules.SKILLS_CATALOG:
            lines.append(f"  {s['skill']:15}  trigger: {s['trigger']}")
            lines.append(f"  {'':15}  invoke:  {s['invoke']}")
            lines.append(f"  {'':15}  note:    {s['note']}")
            lines.append("")

    if sec in ("all", "builtins"):
        lines += [
            "BUILT-IN TOOL GUIDE",
            "─" * 40,
        ]
        for b in _rules.BUILTIN_TOOLS:
            lines.append(f"  {b['tool']:8}  use for: {b['best_for']}")
            if b.get("prefer_mcp") and b["prefer_mcp"] != "N/A":
                lines.append(f"  {'':8}  prefer:  {b['prefer_mcp']}")
            lines.append(f"  {'':8}  tip:     {b['tip']}")
            lines.append("")

    if not lines:
        valid = "substitutions | gates | chains | tokens | skills | builtins | all"
        return f"Unknown section {section!r}. Valid: {valid}"

    return "\n".join(lines).rstrip()


def ledger_available(layer: int | None = None, healthy_only: bool = False) -> str:
    servers = _health.load_mcp_servers()
    all_healths = {r["mcp_key"]: r for r in _health.check_all()}

    if not servers:
        return "No MCP servers configured in .mcp.json.\nRun: ccsetup . to configure tools."

    by_layer: dict[int, list[str]] = {}
    for key in servers:
        lyr = _catalog.LAYER_MAP.get(key, 99)
        by_layer.setdefault(lyr, []).append(key)

    lines = [f"Configured tools ({len(servers)} servers):\n"]

    for lyr in sorted(by_layer.keys()):
        layer_name = _catalog.LAYER_NAMES.get(lyr, f"Layer {lyr}")
        if layer is not None and lyr != layer:
            continue
        lines.append(f"  Layer {lyr} — {layer_name}")
        for key in sorted(by_layer[lyr]):
            h = all_healths.get(key, {})
            healthy = h.get("healthy", False)
            if healthy_only and not healthy:
                continue
            icon = "✓" if healthy else "✗"
            detail = h.get("detail", "")
            tool_count = len(_catalog.TOOL_CATALOG.get(key, []))
            lines.append(f"    {icon} {key}  ({tool_count} tools)")
            if not healthy and detail:
                lines.append(f"      ⚠ {detail}")
        lines.append("")

    return "\n".join(lines)


def ledger_health(tool: str | None = None) -> str:
    if tool:
        h = _health.check_tool(tool)
        icon = "✓" if h["healthy"] else "✗"
        return "\n".join([
            f"{icon} {tool}",
            f"  Configured: {h['configured']}",
            f"  Healthy:    {h['healthy']}",
            f"  Status:     {h['status']}",
            f"  Detail:     {h['detail']}",
        ])

    results = _health.check_all()
    if not results:
        return "No MCP servers configured in .mcp.json."

    healthy = [r for r in results if r["healthy"]]
    degraded = [r for r in results if not r["healthy"]]
    lines = [f"Health: {len(healthy)}/{len(results)} healthy\n"]

    if healthy:
        lines.append("  Healthy:")
        for r in healthy:
            lines.append(f"    ✓ {r['mcp_key']}")
        lines.append("")
    if degraded:
        lines.append("  Degraded:")
        for r in degraded:
            lines.append(f"    ✗ {r['mcp_key']}  — {r['detail']}")
        lines.append("")

    return "\n".join(lines)


def ledger_diagnose(tool: str | None = None) -> str:
    """Full prerequisite diagnosis for one or all configured tools.

    For each tool: checks binaries, hooks, files, env vars, and config drift.
    Returns root cause + exact fix steps for every issue found.
    """
    servers = _health.load_mcp_servers()
    keys = [tool] if tool else list(servers.keys())

    if not keys:
        return "No MCP servers configured in .mcp.json.\nRun: ccsetup . to configure tools."

    all_clean = True
    lines: list[str] = []

    for key in keys:
        diag = _health.diagnose_tool(key)
        issues = diag.get("issues", [])
        fixes = diag.get("fixes", [])
        base = diag.get("base_health", {})

        if not issues and base.get("healthy"):
            lines.append(f"✓  {key}  — all prerequisites satisfied")
            continue

        all_clean = False
        lines.append(f"✗  {key}")

        if not base.get("healthy"):
            lines.append(f"   base: {base.get('detail', 'unhealthy')}")

        why = diag.get("why", "")
        if why:
            lines.append(f"   why:  {why[:120]}")

        for i, issue in enumerate(issues, 1):
            lines.append(f"   [{i}] {issue}")

        if fixes:
            lines.append("   fixes:")
            for f in fixes:
                auto_tag = " (auto-fixable)" if f.get("auto") else " (manual)"
                target = f"  → {f['target']}" if f.get("target") else ""
                lines.append(f"     {'✓' if f.get('auto') else '!'} {f['step'].splitlines()[0]}{target}{auto_tag}")

        docs = diag.get("docs", "")
        if docs:
            lines.append(f"   docs: {docs}")

        fixable = diag.get("fixable_count", 0)
        if fixable:
            lines.append(f"   → call ledger_fix('{key}') to auto-apply {fixable} fix(es)")

        lines.append("")

    if all_clean and keys:
        lines.append("")
        lines.append("All diagnosed tools are fully configured.")

    return "\n".join(lines).rstrip()


def ledger_fix(tool: str) -> str:
    """Apply all auto-fixable prerequisite fixes for a tool.

    Writes to ~/.claude/settings.json (hooks), .mcp.json (env vars),
    or .serena/project.yml (language list) as needed.
    Reports exactly what was changed. Non-auto-fixable issues are listed
    with manual instructions.
    """
    diag = _health.diagnose_tool(tool)
    fixes = diag.get("fixes", [])

    if not fixes:
        base = diag.get("base_health", {})
        if base.get("healthy") and not diag.get("issues"):
            return f"✓ {tool} — no fixes needed, all prerequisites satisfied."
        return f"{tool} — no fix specs available. Check: ledger_diagnose('{tool}')"

    applied: list[str] = []
    skipped: list[str] = []

    for f in fixes:
        if f.get("auto"):
            result = _health.apply_fix(f)
            applied.append(result)
        else:
            first_line = f["step"].splitlines()[0]
            skipped.append(f"  (manual) {first_line}")
            # Show full multi-line fix instructions for manual steps
            full = f["step"]
            if "\n" in full:
                for line in full.splitlines()[1:]:
                    skipped.append(f"    {line}")

    lines = [f"ledger_fix({tool!r})"]
    lines.append("")

    if applied:
        lines.append(f"Applied ({len(applied)}):")
        for a in applied:
            lines.append(f"  ✓ {a}")
        lines.append("")
        lines.append("Restart Claude Code (or reload MCP) for changes to take effect.")
        lines.append("")

    if skipped:
        lines.append(f"Still needs manual action ({len(skipped)}):")
        for s in skipped:
            lines.append(s)
        docs = diag.get("docs", "")
        if docs:
            lines.append(f"  docs: {docs}")
        lines.append("")

    if not applied and not skipped:
        lines.append("Nothing to fix.")

    return "\n".join(lines).rstrip()


def ledger_mode(mode: str | None = None) -> str:
    """Get or set the token priority mode (economy | balanced | performance)."""
    if mode is None:
        current = _load_mode()
        p = _rules.MODE_PROFILES[current]
        return (
            f"Current mode: {p['label']}\n"
            f"{p['description']}\n\n"
            "Available: economy | balanced | performance"
        )
    if mode not in ("economy", "balanced", "performance"):
        return f"Invalid mode {mode!r}. Choose: economy | balanced | performance"
    _save_mode(mode)
    p = _rules.MODE_PROFILES[mode]
    return f"Mode set to {p['label']}: {p['description']}"


def ledger_workflows(tag: str | None = None) -> str:
    if tag:
        tag_lower = tag.lower()
        workflows = {k: v for k, v in _WORKFLOWS.items()
                     if any(tag_lower in t for t in v["tags"])}
        if not workflows:
            all_tags = sorted({t for v in _WORKFLOWS.values() for t in v["tags"]})
            return f"No workflows match tag {tag!r}.\nAvailable tags: {', '.join(all_tags)}"
    else:
        workflows = _WORKFLOWS

    lines = [f"Workflows ({len(workflows)}):\n"]
    for wf in workflows.values():
        lines.append(f"### {wf['title']}")
        lines.append("```")
        for step in wf["steps"]:
            lines.append(step)
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def ledger_catalog(mcp_key: str | None = None, configured_only: bool = False) -> str:
    servers = _health.load_mcp_servers()

    if mcp_key:
        # Also check skills catalog
        if mcp_key == "skills":
            lines = [f"Skills catalog ({len(_rules.SKILLS_CATALOG)} skills):\n"]
            for s in _rules.SKILLS_CATALOG:
                lines.append(f"  {s['skill']}")
                lines.append(f"    trigger: {s['trigger']}")
                lines.append(f"    invoke:  {s['invoke']}")
                lines.append(f"    note:    {s['note']}")
                lines.append("")
            return "\n".join(lines)

        tools = _catalog.TOOL_CATALOG.get(mcp_key)
        if tools is None:
            known = list(_catalog.TOOL_CATALOG.keys()) + ["skills"]
            return f"No catalog entry for '{mcp_key}'.\nKnown: {', '.join(known)}"
        lines = [f"Tools for {mcp_key} ({len(tools)} tools):\n"]
        for tname, params, when in tools:
            lines.append(f"  {tname}({params})")
            lines.append(f"    → {when}")
            lines.append("")
        return "\n".join(lines)

    keys = list(_catalog.TOOL_CATALOG.keys())
    if configured_only:
        keys = [k for k in keys if k in servers]

    lines = [f"Tool catalog ({len(keys)} servers):\n"]
    for key in keys:
        tools = _catalog.TOOL_CATALOG[key]
        status = "✓" if key in servers else "○"
        lines.append(f"{status} {key} ({len(tools)} tools)")
        for tname, params, _ in tools:
            lines.append(f"  {tname}({params})")
        lines.append("")

    # Skills section
    lines += [
        "── Skills (Skill tool) ──",
        "",
    ]
    for s in _rules.SKILLS_CATALOG:
        lines.append(f"  {s['skill']:15}  {s['description']}")
    lines.append("")
    lines.append("Use ledger_catalog('skills') for full skills detail.")

    return "\n".join(lines)


_CHANGE_TYPE_BOOST: dict[str, set[str]] = {
    "add_dependency": {"constraint", "invariant"},
    "remove_feature": {"contract", "goal"},
    "change_interface": {"contract"},
    "refactor": {"invariant", "constraint"},
}


def ledger_preflight(change: str, files: list[str] | None = None,
                     change_type: str | None = None) -> str:
    """Pre-change impact synthesis across all cognitive tools.

    Reads .claude/ stores and returns a unified report:
    - CHARTER: conflict scoring against normative entries
    - MIND: nodes referencing affected files, open assumptions
    - WITNESS: exception history for affected files/functions
    - RETINA: baselines referencing affected URLs/labels
    - VERDICT: CLEAR / CAUTION / BLOCKED
    """
    import re
    files = files or []
    lines = [f"PREFLIGHT: {change}", ""]

    blockers = []
    warnings = []

    boost_types = _CHANGE_TYPE_BOOST.get(change_type or "", set())

    # ── CHARTER ──
    charter_data = _health._read_json_safe(_health._claude_dir() / "charter.json")
    if charter_data:
        entries = charter_data.get("entries", [])
        normative = [
            e for e in entries
            if e.get("type") in ("invariant", "constraint", "contract")
            and e.get("status") == "active"
        ]
        if normative:
            change_tokens = set(re.findall(r"[a-z0-9_]+", change.lower()))
            charter_conflicts = []
            prohibition_words = {"never", "not", "no", "without", "avoid", "forbidden"}
            for e in normative:
                entry_tokens = set(re.findall(r"[a-z0-9_]+", e["content"].lower()))
                if not entry_tokens:
                    continue
                overlap = change_tokens & entry_tokens
                score = len(overlap) / len(entry_tokens)
                # Apply change_type boost
                if boost_types and e.get("type") in boost_types:
                    score = min(score * 2.0, 1.0)
                # Check prohibition
                is_prohib = any(w in e["content"].lower() for w in prohibition_words)
                if is_prohib and score > 0:
                    score = min(score * 1.5, 1.0)
                if score >= 0.25:
                    charter_conflicts.append((score, e))
                elif score >= 0.10:
                    warnings.append(f"charter [{e['id']}]: {e['content']} (overlap {score:.0%})")

            if charter_conflicts:
                lines.append(f"CHARTER — {len(charter_conflicts)} CONFLICT(S):")
                for score, e in sorted(charter_conflicts, key=lambda x: -x[0]):
                    prohib = " ⛔" if any(w in e["content"].lower() for w in prohibition_words) else ""
                    lines.append(f"  [{e['id']}] {e['type'].upper()}{prohib}: {e['content']}  ({score:.0%})")
                    blockers.append(f"charter conflict: {e['content'][:50]}")
                lines.append("")
            else:
                lines.append(f"CHARTER — clear ({len(normative)} entries checked)")
                lines.append("")
    else:
        lines.append("CHARTER — no charter.json found")
        lines.append("")

    # ── MIND ──
    mind_data = _health._read_json_safe(_health._claude_dir() / "mind.json")
    if mind_data and mind_data.get("investigation"):
        nodes = mind_data.get("nodes", [])
        # Find nodes whose files overlap with affected files
        related_nodes = []
        if files:
            for n in nodes:
                node_files = n.get("files", [])
                for nf in node_files:
                    if any(f in nf or nf in f for f in files):
                        related_nodes.append(n)
                        break

        open_assumptions = [
            n for n in nodes
            if n["type"] == "assumption" and n["status"] == "open"
        ]

        mind_items = []
        if related_nodes:
            mind_items.append(f"{len(related_nodes)} node(s) reference affected files")
            for n in related_nodes[:3]:
                mind_items.append(f"  [{n['id']}] {n['type']}: {n['content']}")
        if open_assumptions:
            risky = [n for n in open_assumptions if any(
                any(f in nf or nf in f for f in files)
                for nf in n.get("files", [])
            )] if files else open_assumptions
            if risky:
                warnings.append(f"{len(risky)} open assumption(s) about affected files")
                mind_items.append(f"⚠ {len(risky)} open assumption(s) about these files")
                for n in risky[:2]:
                    mind_items.append(f"  [{n['id']}] {n['content']}")

        if mind_items:
            inv_title = mind_data["investigation"].get("title", "?")
            lines.append(f"MIND — investigation '{inv_title}':")
            lines.extend(f"  {item}" for item in mind_items)
        else:
            lines.append("MIND — no related nodes")
        lines.append("")
    else:
        lines.append("MIND — no active investigation")
        lines.append("")

    # ── WITNESS ──
    witness_state = _health.witness_active_state()
    if witness_state:
        witness_items = []
        if witness_state.get("recent_failures"):
            warnings.append(f"{witness_state['recent_failures']} recent test failures")
            witness_items.append(f"⚠ {witness_state['recent_failures']} recent failures")

        # Check if affected files have exception history
        witness_dir = _health._claude_dir() / "witness"
        if witness_dir.exists() and files:
            run_files = sorted(witness_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            exc_in_files = set()
            for rf in run_files[:3]:
                rd = _health._read_json_safe(rf)
                if rd:
                    for exc in rd.get("exceptions", []):
                        exc_file = exc.get("file", "")
                        if any(f in exc_file or exc_file.endswith(f) for f in files):
                            exc_in_files.add(f"{exc.get('type', '?')} in {exc_file}")
            if exc_in_files:
                warnings.append(f"exceptions in affected files: {', '.join(list(exc_in_files)[:3])}")
                witness_items.append(f"Recent exceptions in affected files:")
                for ex in list(exc_in_files)[:3]:
                    witness_items.append(f"  {ex}")

        if witness_items:
            lines.append(f"WITNESS — {witness_state['recent_runs']} recent runs:")
            lines.extend(f"  {item}" for item in witness_items)
        else:
            lines.append(f"WITNESS — {witness_state['recent_runs']} runs, no issues in affected files")
        lines.append("")
    else:
        lines.append("WITNESS — no runs found")
        lines.append("")

    # ── RETINA ──
    retina_state = _health.retina_active_state()
    if retina_state and (retina_state.get("captures") or retina_state.get("baselines")):
        lines.append(f"RETINA — {retina_state['captures']} captures, {retina_state['baselines']} baselines")
        if retina_state.get("baseline_names"):
            lines.append(f"  active baselines: {', '.join(retina_state['baseline_names'][:5])}")
        lines.append("")
    else:
        lines.append("RETINA — no captures or baselines")
        lines.append("")

    # ── VERDICT ──
    if blockers:
        verdict = "BLOCKED"
        lines.append(f"VERDICT: ⛔ {verdict}")
        lines.append("  Resolve charter conflicts before proceeding:")
        for b in blockers:
            lines.append(f"  - {b}")
    elif warnings:
        verdict = "CAUTION"
        lines.append(f"VERDICT: ⚠ {verdict}")
        for w in warnings:
            lines.append(f"  - {w}")
    else:
        verdict = "CLEAR"
        lines.append(f"VERDICT: ✓ {verdict}")
        lines.append("  No conflicts, no open risks in affected files.")

    return "\n".join(lines)


def ledger_correlate(query: str, scope: str | None = None) -> str:
    """Unified cross-tool search — find everything known about a topic."""
    import re
    query_tokens = set(re.findall(r"[a-z0-9_]+", query.lower()))
    if not query_tokens:
        return "Empty query. Provide search terms."

    results: dict[str, list[str]] = {}

    # ── MIND ──
    if scope in (None, "mind"):
        mind_data = _health._read_json_safe(_health._claude_dir() / "mind.json")
        if mind_data:
            mind_hits = []
            # Current nodes
            for n in mind_data.get("nodes", []):
                text = f"{n.get('content', '')} {n.get('notes', '')} {' '.join(n.get('files', []))}".lower()
                text_tokens = set(re.findall(r"[a-z0-9_]+", text))
                if query_tokens & text_tokens:
                    status = f" ({n['status']})" if n.get("status", "open") != "open" else ""
                    mind_hits.append(f"[{n['id']}] {n['type'].upper()}{status}: {n['content']}")
            # Archived
            for entry in mind_data.get("history", []):
                inv = entry.get("investigation", {})
                inv_text = f"{inv.get('title', '')} {inv.get('conclusion', '')}".lower()
                inv_tokens = set(re.findall(r"[a-z0-9_]+", inv_text))
                if query_tokens & inv_tokens:
                    resolved = inv.get("resolved_at", "")[:10] if inv.get("resolved_at") else "?"
                    mind_hits.append(f"[archived] {inv.get('title', '?')} ({resolved}): {inv.get('conclusion', '?')}")
                for n in entry.get("nodes", []):
                    text = f"{n.get('content', '')} {n.get('notes', '')}".lower()
                    text_tokens = set(re.findall(r"[a-z0-9_]+", text))
                    if query_tokens & text_tokens:
                        mind_hits.append(f"  [{n['id']}] {n['type']}: {n['content'][:60]}")
                        if len(mind_hits) > 15:
                            break
                if len(mind_hits) > 15:
                    break
            if mind_hits:
                results["MIND"] = mind_hits[:10]

    # ── CHARTER ──
    if scope in (None, "charter"):
        charter_data = _health._read_json_safe(_health._claude_dir() / "charter.json")
        if charter_data:
            charter_hits = []
            for e in charter_data.get("entries", []):
                text = f"{e.get('content', '')} {e.get('notes', '')}".lower()
                text_tokens = set(re.findall(r"[a-z0-9_]+", text))
                if query_tokens & text_tokens:
                    status = f" [{e['status']}]" if e.get("status") != "active" else ""
                    charter_hits.append(f"[{e['id']}] {e['type'].upper()}{status}: {e['content']}")
            if charter_hits:
                results["CHARTER"] = charter_hits[:10]

    # ── WITNESS ──
    if scope in (None, "witness"):
        witness_dir = _health._claude_dir() / "witness"
        if witness_dir.exists():
            witness_hits = []
            run_files = sorted(witness_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for rf in run_files[:3]:
                rd = _health._read_json_safe(rf)
                if not rd:
                    continue
                rid = rd.get("run_id", "?")
                for call in rd.get("calls", []):
                    fn_lower = call.get("fn", "").lower()
                    if any(t in fn_lower for t in query_tokens):
                        exc = " [exception]" if call.get("exception") else ""
                        witness_hits.append(f"[{rid}] {call['fn']}  {call.get('file', '?')}:{call.get('line', '?')}{exc}")
                        if len(witness_hits) >= 8:
                            break
                if len(witness_hits) >= 8:
                    break
            if witness_hits:
                results["WITNESS"] = witness_hits[:8]

    # ── RETINA ──
    if scope in (None, "retina"):
        retina_data = _health._read_json_safe(Path(_health._claude_dir() / "retina" / "retina.json"))
        if retina_data:
            retina_hits = []
            for cap in retina_data.get("captures", []):
                text = f"{cap.get('url', '')} {cap.get('label', '')}".lower()
                if any(t in text for t in query_tokens):
                    retina_hits.append(f"[{cap.get('type', '?')}] {cap.get('url', '?')}  label:{cap.get('label', '-')}")
            for name, bl in retina_data.get("baselines", {}).items():
                if any(t in name.lower() for t in query_tokens):
                    retina_hits.append(f"[baseline] {name}: {bl.get('url', '?')}")
            if retina_hits:
                results["RETINA"] = retina_hits[:5]

    if not results:
        return f"No results for '{query}' across cognitive tools."

    lines = [f"CORRELATE: '{query}'", ""]
    for tool_name, hits in results.items():
        lines.append(f"{tool_name} ({len(hits)} match{'es' if len(hits) != 1 else ''}):")
        for h in hits:
            lines.append(f"  {h}")
        lines.append("")

    return "\n".join(lines).rstrip()


# ─────────────────────────────────────────────────────────────────────────────
# MCP protocol
# ─────────────────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "ledger_context",
        "description": (
            "PRIMARY SESSION-START TOOL. Call this first every session. "
            "Returns: (1) HOW to use tools — anti-patterns and substitutions, "
            "(2) MANDATORY GATES — what to call before each action type, "
            "(3) ACTIVE STATE — open investigations, test failures, retina state, "
            "(4) RECOMMENDED NEXT — what to do based on current project state. "
            "Eliminates the need for human reminders about tool use."
        ),
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "ledger_query",
        "description": (
            "Get the concrete call sequence for any task. "
            "Returns the PRIORITY CHAIN (which tools to call, in what order, in parallel where safe) "
            "plus MCP server recommendations with relevance scores. "
            "Use this before starting any non-trivial work."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Free-text task description (e.g. 'debug failing auth test', 'refactor the parser').",
                },
                "healthy_only": {
                    "type": "boolean",
                    "description": "Only recommend currently healthy tools.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "ledger_rules",
        "description": (
            "Operational rules: anti-patterns (what NOT to do + what to do instead), "
            "mandatory gates, priority chains per task type, token efficiency rules, "
            "skills catalog, and built-in tool guidance. "
            "Filter by section: substitutions | gates | chains | tokens | skills | builtins | all"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "description": "Section to return: substitutions | gates | chains | tokens | skills | builtins | all",
                },
            },
            "required": [],
        },
    },
    {
        "name": "ledger_available",
        "description": "List all configured MCP tools grouped by layer with real-time health status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layer": {"type": "integer", "description": "Filter to a specific layer (0-6)."},
                "healthy_only": {"type": "boolean", "description": "Show only healthy tools."},
            },
            "required": [],
        },
    },
    {
        "name": "ledger_health",
        "description": "Real-time health check for all or one configured tool (rechecks now, not cached).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool": {"type": "string", "description": "MCP key to check. Omit for all."},
            },
            "required": [],
        },
    },
    {
        "name": "ledger_workflows",
        "description": "Canonical workflow patterns: session-start, debugging, investigation, agent-spawn, visual-ui, etc.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Filter by tag: debug, visual, agent, session, refactor, etc."},
            },
            "required": [],
        },
    },
    {
        "name": "ledger_catalog",
        "description": "Full tool signatures for one or all MCP servers. Use mcp_key='skills' for the skills catalog.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mcp_key": {"type": "string", "description": "Server key or 'skills'. Omit for all."},
                "configured_only": {"type": "boolean", "description": "Show only configured servers."},
            },
            "required": [],
        },
    },
    {
        "name": "ledger_diagnose",
        "description": (
            "Full prerequisite diagnosis for one or all configured tools. "
            "Checks binaries, hooks in settings.json, required files, env vars, and "
            "config drift (e.g. Serena language mismatch). Returns root cause + exact "
            "fix steps for every issue. Call this whenever a tool is degraded or "
            "behaving unexpectedly — never just accept a degraded tool."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "MCP key to diagnose (e.g. 'claude-session'). Omit to diagnose all configured tools.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "ledger_fix",
        "description": (
            "Apply all auto-fixable prerequisite fixes for a tool. "
            "Writes hooks to ~/.claude/settings.json, env vars to .mcp.json, "
            "or languages to .serena/project.yml. Reports exactly what was changed. "
            "Non-auto-fixable issues are listed with manual instructions. "
            "Always call ledger_diagnose first to see what will be changed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "description": "MCP key to fix (e.g. 'claude-session', 'serena').",
                },
            },
            "required": ["tool"],
        },
    },
    {
        "name": "ledger_mode",
        "description": (
            "Get or set the token priority mode. "
            "economy: minimal token spend, single best path, no exploration. "
            "balanced: default, good capability/cost ratio. "
            "performance: comprehensive, invest tokens in thorough tool activation. "
            "Mode persists in .claude/ledger-mode.json and applies to all subsequent "
            "ledger_context() and ledger_query() calls automatically."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "description": "economy | balanced | performance. Omit to read current mode.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "ledger_preflight",
        "description": (
            "Pre-change impact synthesis. Checks charter conflicts, mind assumptions about "
            "affected files, witness exception history, and retina baselines. "
            "Returns CLEAR / CAUTION / BLOCKED verdict. "
            "Use BEFORE structural changes — subsumes standalone charter_check. "
            "Pass change_type for 2x boost on relevant charter entry types."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "change": {
                    "type": "string",
                    "description": "Plain-language description of the proposed change.",
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths affected by the change.",
                },
                "change_type": {
                    "type": "string",
                    "enum": ["add_dependency", "remove_feature", "change_interface", "refactor", "general"],
                    "description": "Type of change — boosts relevant charter entry types 2x for sharper conflict detection.",
                },
            },
            "required": ["change"],
        },
    },
    {
        "name": "ledger_correlate",
        "description": (
            "Unified cross-tool search. Finds everything known about a topic across "
            "mind (nodes + archived investigations), charter (entries), witness (function calls), "
            "and retina (captures/baselines). Use when you need the full picture on a topic."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms to match across all cognitive tools.",
                },
                "scope": {
                    "type": "string",
                    "enum": ["mind", "charter", "witness", "retina"],
                    "description": "Limit search to a single tool. Omit for all.",
                },
            },
            "required": ["query"],
        },
    },
]


def dispatch(method: str, params: dict) -> str:
    if method == "ledger_context":
        return ledger_context()
    if method == "ledger_query":
        return ledger_query(params["task"], healthy_only=params.get("healthy_only", False))
    if method == "ledger_rules":
        return ledger_rules(section=params.get("section"))
    if method == "ledger_available":
        return ledger_available(layer=params.get("layer"), healthy_only=params.get("healthy_only", False))
    if method == "ledger_health":
        return ledger_health(tool=params.get("tool"))
    if method == "ledger_workflows":
        return ledger_workflows(tag=params.get("tag"))
    if method == "ledger_catalog":
        return ledger_catalog(mcp_key=params.get("mcp_key"), configured_only=params.get("configured_only", False))
    if method == "ledger_diagnose":
        return ledger_diagnose(tool=params.get("tool"))
    if method == "ledger_fix":
        return ledger_fix(tool=params["tool"])
    if method == "ledger_mode":
        return ledger_mode(mode=params.get("mode"))
    if method == "ledger_preflight":
        return ledger_preflight(params["change"], files=params.get("files"),
                                change_type=params.get("change_type"))
    if method == "ledger_correlate":
        return ledger_correlate(params["query"], scope=params.get("scope"))
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
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "claude-ledger", "version": VERSION},
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
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": result_text}], "isError": False},
            })
        except Exception as exc:
            send({
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True},
            })
        return

    if req_id is not None:
        send({"jsonrpc": "2.0", "id": req_id,
              "error": {"code": -32601, "message": f"Method not found: {method}"}})


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
