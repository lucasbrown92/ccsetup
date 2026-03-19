#!/usr/bin/env python3
"""claude-afe: Agentic Field Engine — cognitive compiler for Claude Code.

MCP server (stdlib only, stdio transport). Compiles task descriptions into
agent specifications using the AFE operator matrix (9 coins, 8 functions,
4 animals, 3 regimes).

7 tools:
  afe_compile    — core compiler: task → agent spec
  afe_templates  — browse/search template registry
  afe_inspect    — show full detail of a spec or template
  afe_validate   — check spec against charter + coherence
  afe_ecology    — multi-agent orchestration: task → agent chain
  afe_context    — pull context from mind/charter/witness
  afe_history    — list past compilations

Storage: .claude/afe.json (override: CLAUDE_AFE_DIR).
Cross-tool: reads mind.json, charter.json, witness/*.json for context.

Transport: stdio MCP (JSON-RPC 2.0). No third-party dependencies — stdlib only.
"""

VERSION = "0.0.1"

import json
import sys
from pathlib import Path

# Make sibling modules importable when server.py is invoked from any CWD
sys.path.insert(0, str(Path(__file__).parent))

import schema as _schema
import store as _store
import templates as _templates
import compiler as _compiler


# ── Tool handlers ─────────────────────────────────────────────────────────────

def afe_compile(task, regime=None, template=None, domain=None,
                locus=None, modality=None):
    """Core compiler: task → agent spec."""
    spec = _compiler.compile_spec(
        task=task,
        regime=regime,
        template_id=template,
        domain=domain,
        locus=locus,
        modality=modality,
    )
    # Persist
    data = _store.load()
    data["specs"].append(spec)
    _store.save(data)

    brief = _schema.format_spec_brief(spec)
    funcs = _schema.format_function_bundle(spec["functions"])
    animals = " → ".join(spec["animal_order"])

    return (
        f"Compiled: {brief}\n\n"
        f"Functions: {funcs}\n"
        f"Animals: {animals}\n"
        f"Modality: {spec['modality']}\n"
        f"Locus: {spec.get('locus', '?')} | Domain: {spec.get('domain', '?')}\n\n"
        f"Use afe_inspect('{spec['id']}') for full spec with system prompt fragment.\n"
        f"Use afe_validate('{spec['id']}') to check against charter constraints."
    )


def afe_templates(regime=None, domain=None, filter_text=None):
    """Browse/search template registry."""
    results = _templates.list_templates(regime=regime, domain=domain)

    if filter_text:
        fl = filter_text.lower()
        results = [t for t in results if (
            fl in t["name"].lower() or
            fl in t["description"].lower() or
            fl in t["id"]
        )]

    if not results:
        return "No templates matching the given criteria."

    lines = [f"Templates ({len(results)}):\n"]
    for t in results:
        funcs = _schema.format_function_bundle(t["functions"])
        animals = " → ".join(t["animal_order"])
        lines.append(f"  [{t['id']}] {t['name']} ({t['regime']})")
        lines.append(f"    {t['description']}")
        lines.append(f"    {funcs} | {animals} | {t['modality']}")
        lines.append("")

    return "\n".join(lines)


def afe_inspect(item_id):
    """Show full detail of a compiled spec or template."""
    # Check templates first
    template = _templates.get_template(item_id)
    if template:
        funcs = _schema.format_function_bundle(template["functions"])
        animals = " → ".join(template["animal_order"])
        guards = template.get("distortion_guards", {})

        lines = [
            f"═══ TEMPLATE: {template['name']} [{template['id']}] ═══",
            f"Regime: {template['regime']}",
            f"Description: {template['description']}",
            f"Domain affinity: {', '.join(template.get('domain_affinity', []))}",
            f"Locus affinity: {template.get('locus_affinity', '?')}",
            "",
            f"Functions: {funcs}",
            f"Animal order: {animals}",
            f"Modality: {template['modality']}",
            "",
            "OPERATOR DEFINITION:",
            f"  Attend to: {template.get('selection_function', '')}",
            f"  Optimize for: {template.get('valuation_function', '')}",
            f"  Scope: {template.get('compression_strategy', '')}",
            f"  First action: {template.get('action_bias', '')}",
            "",
            f"SUCCESS: {template.get('success_criteria', '')}",
            f"HANDOFF: {template.get('handoff_spec', '')}",
        ]
        if any(guards.values()):
            lines.append("")
            lines.append("DISTORTION GUARDS:")
            if guards.get("ahrimanic"):
                lines.append(f"  Over-compression: {guards['ahrimanic']}")
            if guards.get("luciferic"):
                lines.append(f"  Over-expansion: {guards['luciferic']}")
        lines.append("")
        lines.append(f"Keywords: {', '.join(template.get('keywords', []))}")
        return "\n".join(lines)

    # Check stored specs and ecologies
    data = _store.load()
    item = _store.find_any(data, item_id)
    if not item:
        return f"No spec, ecology, or template found with id '{item_id}'."

    # Ecology
    if "specs" in item and "phase_count" in item:
        lines = [
            f"═══ ECOLOGY [{item['id']}] ═══",
            f"Task: {item['task']}",
            f"Phases: {item['phase_count']}",
            f"Created: {item['created_at'][:10]}",
            "",
        ]
        for spec in item["specs"]:
            phase = spec.get("phase", "?")
            name = spec.get("phase_name", "?")
            funcs = _schema.format_function_bundle(spec["functions"])
            lines.append(f"  Phase {phase}: {name}")
            lines.append(f"    {funcs} | {' → '.join(spec['animal_order'])}")
            lines.append(f"    Handoff: {spec.get('handoff_spec', 'none')}")
            lines.append("")
        return "\n".join(lines)

    # Single spec
    return _schema.format_spec_full(item)


def afe_validate(spec_id):
    """Check spec against charter constraints + internal coherence."""
    data = _store.load()
    spec = _store.find_spec(data, spec_id)
    if not spec:
        return f"No active spec with id '{spec_id}'. Use afe_history to search archives."

    issues = []
    warnings = []

    # Internal coherence checks
    functions = spec.get("functions", [])
    if len(functions) > 4:
        issues.append("Function bundle exceeds 4 — may cause unfocused behavior")
    if not spec.get("distortion_guards", {}).get("ahrimanic"):
        warnings.append("No ahrimanic guard — over-compression risk is unmitigated")
    if not spec.get("distortion_guards", {}).get("luciferic"):
        warnings.append("No luciferic guard — over-expansion risk is unmitigated")
    if not spec.get("success_criteria"):
        warnings.append("No success criteria — agent may not know when to stop")

    # Regime-specific checks
    if spec["regime"] == "canonical" and len(functions) > 2:
        warnings.append("Canonical regime typically uses 2 functions — consider synthetic")
    if spec["regime"] == "synthetic" and len(functions) < 3:
        warnings.append("Synthetic regime typically uses 3-4 functions — may underperform")

    # Charter constraint check
    charter_ctx = _compiler.load_charter_context()
    charter_conflicts = []
    if charter_ctx:
        task_lower = spec["task"].lower()
        for prohibition in charter_ctx.get("prohibitions", []):
            if any(word in task_lower for word in prohibition.lower().split()[:3]):
                charter_conflicts.append(f"⛔ Charter prohibition overlap: {prohibition}")
        for invariant in charter_ctx.get("invariants", []):
            # Flag if spec might violate invariants
            inv_lower = invariant.lower()
            if spec.get("regime") == "orchestration" and "single" in inv_lower:
                charter_conflicts.append(f"⚠ Invariant concern: {invariant}")
    else:
        warnings.append("No charter data found — cannot validate against project constraints")

    # Build report
    lines = [f"Validation: [{spec_id}] {spec['task'][:50]}\n"]

    if not issues and not charter_conflicts:
        lines.append("✓ No conflicts detected.")
    else:
        if charter_conflicts:
            lines.append(f"CHARTER CONFLICTS ({len(charter_conflicts)}):")
            for c in charter_conflicts:
                lines.append(f"  {c}")
            lines.append("")
        if issues:
            lines.append(f"COHERENCE ISSUES ({len(issues)}):")
            for i in issues:
                lines.append(f"  ✗ {i}")
            lines.append("")

    if warnings:
        lines.append(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            lines.append(f"  △ {w}")

    # Spec summary
    lines.append("")
    lines.append(f"Regime: {spec['regime']} | Template: {spec.get('template_id', 'custom')}")
    lines.append(f"Functions: {_schema.format_function_bundle(functions)}")
    lines.append(f"Modality: {spec['modality']} | Animals: {' → '.join(spec['animal_order'])}")

    return "\n".join(lines)


def afe_ecology(task, phases=None):
    """Multi-agent orchestration: task → sequenced agent chain."""
    ecology = _compiler.compile_ecology(task, phases)

    # Persist
    data = _store.load()
    data["ecologies"].append(ecology)
    _store.save(data)

    lines = [
        f"Ecology compiled: [{ecology['id']}]",
        f"Task: {task}",
        f"Phases: {ecology['phase_count']}",
        "",
    ]
    for spec in ecology["specs"]:
        phase = spec.get("phase", "?")
        name = spec.get("phase_name", "?")
        funcs = _schema.format_function_bundle(spec["functions"])
        animals = " → ".join(spec["animal_order"])
        lines.append(f"  Phase {phase}: {name}")
        lines.append(f"    [{spec['id']}] {funcs} | {animals} | {spec['modality']}")
        lines.append(f"    Handoff: {spec.get('handoff_spec', 'none')}")
        lines.append("")

    lines.append(f"Use afe_inspect('{ecology['id']}') for full ecology detail.")
    lines.append("Execute phases sequentially, using each spec's system_prompt_fragment.")

    return "\n".join(lines)


def afe_context(include=None):
    """Pull compilation context from mind/charter/witness."""
    include = include or ["mind", "charter", "witness"]
    contexts = _compiler.load_all_context(include)

    if not contexts:
        return "No context available from mind/charter/witness stores."

    lines = ["Cross-tool context for AFE compilation:\n"]

    for ctx in contexts:
        source = ctx["source"]
        if source == "mind":
            lines.append("MIND (active investigation):")
            lines.append(f"  Title: {ctx['title']}")
            lines.append(f"  Open: {ctx['open_hypotheses']} hypotheses, "
                         f"{ctx['open_assumptions']} assumptions, "
                         f"{ctx['open_next_steps']} next steps")
            if ctx.get("assumption_contents"):
                lines.append("  ⚠ Assumptions:")
                for a in ctx["assumption_contents"]:
                    lines.append(f"    - {a}")
            lines.append("")

        elif source == "charter":
            lines.append("CHARTER (normative constraints):")
            lines.append(f"  {ctx['invariant_count']} invariants, "
                         f"{ctx['constraint_count']} constraints, "
                         f"{ctx['prohibition_count']} prohibitions")
            if ctx.get("prohibitions"):
                lines.append("  ⛔ Prohibitions:")
                for p in ctx["prohibitions"]:
                    lines.append(f"    - {p}")
            lines.append("")

        elif source == "witness":
            status_icon = "✓" if ctx["status"] == "passing" else "✗"
            lines.append("WITNESS (execution evidence):")
            lines.append(f"  Latest run: {ctx['run_id']}")
            lines.append(f"  Status: {status_icon} {ctx['status']} "
                         f"({ctx['test_count']} tests, {ctx['exception_count']} exceptions)")
            lines.append("")

    return "\n".join(lines)


def afe_history(limit=20, filter_text=None):
    """List past compilations."""
    data = _store.load()

    # Combine active specs + history
    all_items = []
    for s in data.get("specs", []):
        s["_source"] = "active"
        all_items.append(s)
    for h in data.get("history", []):
        h["_source"] = "archived"
        all_items.append(h)

    # Filter
    if filter_text:
        fl = filter_text.lower()
        all_items = [item for item in all_items if (
            fl in item.get("task", "").lower() or
            fl in item.get("regime", "").lower() or
            fl in item.get("template_id", "").lower() or
            fl in item.get("locus", "").lower() or
            fl in item.get("domain", "").lower()
        )]

    # Most recent first
    all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    all_items = all_items[:limit]

    if not all_items:
        return "No compilation history found."

    lines = [f"AFE History ({len(all_items)} shown):\n"]
    for item in all_items:
        source = item.get("_source", "?")
        tag = "" if source == "active" else " [archived]"
        lines.append(f"  {_schema.format_spec_brief(item)}{tag}")

    # Clean up temp key
    for item in all_items:
        item.pop("_source", None)

    return "\n".join(lines)


# ── MCP transport (JSON-RPC 2.0 over stdio) ──────────────────────────────────

TOOLS = [
    {
        "name": "afe_compile",
        "description": (
            "Core cognitive compiler. Takes a task description and produces a complete "
            "agent specification with function bundle, animal workflow, modality, "
            "distortion guards, and system prompt fragment. "
            "Consults mind/charter/witness for cross-tool context. "
            "Use before spawning any Agent tool for complex tasks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "Task description — what the agent needs to accomplish.",
                },
                "regime": {
                    "type": "string",
                    "enum": _schema.REGIMES,
                    "description": "Agent regime: canonical (human-natural), synthetic (engineered), orchestration (meta). Auto-detected if omitted.",
                },
                "template": {
                    "type": "string",
                    "description": "Template ID to use (e.g. 'planner', 'module_writer'). Auto-matched if omitted.",
                },
                "domain": {
                    "type": "string",
                    "enum": _schema.DOMAINS,
                    "description": "Task domain. Auto-detected if omitted.",
                },
                "locus": {
                    "type": "string",
                    "enum": _schema.LOCI,
                    "description": "ADAP locus: Awareness/Intention/Capability/Energy. Auto-detected if omitted.",
                },
                "modality": {
                    "type": "string",
                    "enum": _schema.MODALITY_PROFILES,
                    "description": "Modality profile: MM/MF/FM/FF. Auto-detected if omitted.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "afe_templates",
        "description": (
            "Browse and search the template registry. Shows all available agent templates "
            "with their function bundles, animal orders, and use cases. "
            "Filter by regime (canonical/synthetic/orchestration), domain, or free text."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "regime": {
                    "type": "string",
                    "enum": _schema.REGIMES,
                    "description": "Filter by regime.",
                },
                "domain": {
                    "type": "string",
                    "enum": _schema.DOMAINS,
                    "description": "Filter by domain affinity.",
                },
                "filter": {
                    "type": "string",
                    "description": "Free text search in template names and descriptions.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "afe_inspect",
        "description": (
            "Show full detail of a compiled spec, ecology, or template by ID. "
            "For specs, includes the complete system_prompt_fragment ready for Agent tool injection."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "Spec ID, ecology ID, or template ID.",
                },
            },
            "required": ["id"],
        },
    },
    {
        "name": "afe_validate",
        "description": (
            "Validate a compiled spec against charter constraints and internal coherence. "
            "Checks for charter prohibition conflicts, function bundle coherence, "
            "missing distortion guards, and regime-specific issues."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "spec_id": {
                    "type": "string",
                    "description": "ID of the spec to validate.",
                },
            },
            "required": ["spec_id"],
        },
    },
    {
        "name": "afe_ecology",
        "description": (
            "Multi-agent orchestration compiler. Decomposes a complex task into a "
            "sequenced agent chain with explicit handoff artifacts between phases. "
            "Default: 4-phase (explore → plan → implement → review). "
            "Custom phases can be specified."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The complex task to decompose into an agent ecology.",
                },
                "phases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "task": {"type": "string"},
                            "template": {"type": "string"},
                            "locus": {"type": "string"},
                            "domain": {"type": "string"},
                            "modality": {"type": "string"},
                        },
                    },
                    "description": "Custom phase definitions. Each phase gets its own compiled spec.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "afe_context",
        "description": (
            "Pull compilation context from mind/charter/witness stores. "
            "Shows active investigation state, project constraints, and recent test results. "
            "Call before afe_compile to understand the cognitive field."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "include": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["mind", "charter", "witness"]},
                    "description": "Which stores to read. Default: all three.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "afe_history",
        "description": (
            "List past agent compilations. Shows active specs and archived history. "
            "Filter by task text, regime, template, locus, or domain."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max results to return. Default: 20.",
                    "default": 20,
                },
                "filter": {
                    "type": "string",
                    "description": "Free text search in task, regime, template, locus, domain.",
                },
            },
            "required": [],
        },
    },
]


# ── Dispatch ──────────────────────────────────────────────────────────────────

def dispatch(method, params):
    if method == "afe_compile":
        return afe_compile(
            task=params["task"],
            regime=params.get("regime"),
            template=params.get("template"),
            domain=params.get("domain"),
            locus=params.get("locus"),
            modality=params.get("modality"),
        )
    if method == "afe_templates":
        return afe_templates(
            regime=params.get("regime"),
            domain=params.get("domain"),
            filter_text=params.get("filter"),
        )
    if method == "afe_inspect":
        return afe_inspect(params["id"])
    if method == "afe_validate":
        return afe_validate(params["spec_id"])
    if method == "afe_ecology":
        return afe_ecology(
            task=params["task"],
            phases=params.get("phases"),
        )
    if method == "afe_context":
        return afe_context(include=params.get("include"))
    if method == "afe_history":
        return afe_history(
            limit=params.get("limit", 20),
            filter_text=params.get("filter"),
        )
    raise ValueError(f"Unknown method: {method}")


# ── MCP wire protocol ────────────────────────────────────────────────────────

def _log(msg):
    sys.stderr.write(f"[claude-afe] {msg}\n")
    sys.stderr.flush()


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def handle_request(req):
    req_id = req.get("id")
    method = req.get("method", "")
    params = req.get("params", {})

    # MCP lifecycle
    if method == "initialize":
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "claude-afe", "version": "1.0.0"},
            },
        })
        return

    if method in ("notifications/initialized", "notifications/cancelled"):
        return

    if method == "ping":
        send({"jsonrpc": "2.0", "id": req_id, "result": {}})
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
            _log(f"Tool error ({tool_name}): {exc}")
            send({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            })
        return

    # Unknown method
    if req_id is not None:
        send({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


def main():
    store_hint = _store.get_store_path().absolute()
    _log(f"claude-afe v1.0.0 starting  (store: {store_hint})")
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
