"""Compiler pipeline for claude-afe: task → agent spec.

11 stages, each a pure function. The pipeline is a collaboration between
Claude's judgment (task interpretation, parameter overrides) and the server's
deterministic logic (template matching, constraint validation, prompt assembly).
"""

import json
import os
import re
from pathlib import Path

import schema as _schema
import templates as _templates


# ── Stage 1: Task Intake ──────────────────────────────────────────────────────

def tokenize_task(task):
    """Normalize task text into lowercase tokens."""
    return set(re.findall(r"[a-z0-9_]+", task.lower()))


# ── Stage 2: Context Read ─────────────────────────────────────────────────────

def _load_json_store(env_var, default_dir, filename):
    """Load a JSON store file, returning None on missing/corrupt."""
    store_dir = Path(os.environ.get(env_var, default_dir))
    path = store_dir / filename
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError, OSError):
        return None


def load_mind_context():
    """Load mind.json — returns investigation summary or None."""
    data = _load_json_store("CLAUDE_MIND_DIR", ".claude", "mind.json")
    if not data or not data.get("investigation"):
        return None
    inv = data["investigation"]
    nodes = data.get("nodes", [])
    assumptions = [n for n in nodes if n["type"] == "assumption" and n["status"] == "open"]
    hypotheses = [n for n in nodes if n["type"] == "hypothesis" and n["status"] == "open"]
    next_steps = [n for n in nodes if n["type"] == "next_step" and n["status"] == "open"]
    return {
        "source": "mind",
        "title": inv.get("title", ""),
        "open_hypotheses": len(hypotheses),
        "open_assumptions": len(assumptions),
        "open_next_steps": len(next_steps),
        "assumption_contents": [n["content"] for n in assumptions[:5]],
        "hypothesis_contents": [n["content"] for n in hypotheses[:5]],
    }


def load_charter_context():
    """Load charter.json — returns active constraints/invariants or None."""
    data = _load_json_store("CLAUDE_CHARTER_DIR", ".claude", "charter.json")
    if not data:
        return None
    entries = data.get("entries", [])
    active = [e for e in entries if e.get("status") == "active"]
    if not active:
        return None

    invariants = [e for e in active if e["type"] == "invariant"]
    constraints = [e for e in active if e["type"] == "constraint"]
    prohibitions = [e for e in active if _is_prohibition(e["content"])]

    return {
        "source": "charter",
        "invariant_count": len(invariants),
        "constraint_count": len(constraints),
        "prohibition_count": len(prohibitions),
        "invariants": [e["content"] for e in invariants[:5]],
        "constraints": [e["content"] for e in constraints[:5]],
        "prohibitions": [e["content"] for e in prohibitions[:5]],
    }


_PROHIBITION_WORDS = frozenset({
    "never", "not", "no", "must not", "shall not", "cannot", "without",
    "avoid", "don't", "doesn't", "forbidden", "prohibited", "disallowed",
})


def _is_prohibition(content):
    lower = content.lower()
    return any(w in lower for w in _PROHIBITION_WORDS)


def load_witness_context():
    """Load latest witness run — returns summary or None."""
    witness_dir = Path(os.environ.get("CLAUDE_WITNESS_DIR", ".claude/witness"))
    if not witness_dir.exists():
        return None
    files = sorted(witness_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        with open(files[0], "r", encoding="utf-8") as f:
            run = json.load(f)
    except (json.JSONDecodeError, ValueError, OSError):
        return None

    calls = run.get("calls", [])
    exceptions = [c for c in calls if c.get("exception")]
    return {
        "source": "witness",
        "run_id": run.get("run_id", "?"),
        "test_count": run.get("test_count", len(calls)),
        "exception_count": len(exceptions),
        "status": "failing" if exceptions else "passing",
    }


def load_all_context(include=None):
    """Load context from mind/charter/witness. Returns list of context dicts."""
    include = include or ["mind", "charter", "witness"]
    contexts = []
    if "mind" in include:
        ctx = load_mind_context()
        if ctx:
            contexts.append(ctx)
    if "charter" in include:
        ctx = load_charter_context()
        if ctx:
            contexts.append(ctx)
    if "witness" in include:
        ctx = load_witness_context()
        if ctx:
            contexts.append(ctx)
    return contexts


# ── Stage 3: Locus Identification ─────────────────────────────────────────────

_LOCUS_KEYWORDS = {
    "Awareness": {"why", "understand", "investigate", "debug", "analyze", "trace",
                   "diagnose", "inspect", "examine", "find", "search", "explore"},
    "Intention": {"design", "plan", "architect", "decide", "strategy", "propose",
                  "evaluate", "choose", "approach", "tradeoff"},
    "Capability": {"implement", "write", "build", "create", "module", "feature",
                   "code", "add", "develop", "construct", "make"},
    "Energy": {"review", "refactor", "clean", "test", "verify", "validate",
               "check", "audit", "simplify", "improve", "optimize"},
}


def identify_locus(task_tokens, explicit_locus=None):
    """Determine ADAP locus from task tokens. Explicit override takes precedence."""
    if explicit_locus and explicit_locus in _schema.LOCI:
        return explicit_locus
    scores = {}
    for locus, keywords in _LOCUS_KEYWORDS.items():
        scores[locus] = len(task_tokens & keywords)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Capability"  # default


# ── Stage 4: Domain × Channel ────────────────────────────────────────────────

_DOMAIN_KEYWORDS = {
    "Infrastructure": {"infrastructure", "docker", "ci", "cd", "deploy", "build",
                       "migration", "config", "environment", "setup", "install"},
    "Data": {"database", "data", "query", "schema", "model", "migration",
             "storage", "cache", "orm", "sql"},
    "Integration": {"api", "endpoint", "webhook", "auth", "oauth", "middleware",
                    "integration", "service", "client", "request"},
    "CoreLogic": {"logic", "algorithm", "module", "function", "class", "component",
                  "core", "business", "domain", "handler"},
    "Interface": {"ui", "ux", "frontend", "component", "layout", "style",
                  "dashboard", "page", "form", "button", "accessibility"},
    "Meta": {"document", "readme", "docs", "architecture", "design", "plan",
             "strategy", "process", "workflow", "review"},
}

_DEFAULT_CHANNELS = {
    "Infrastructure": "Survival",
    "Data": "Power",
    "Integration": "Decision",
    "CoreLogic": "Creation",
    "Interface": "Expression",
    "Meta": "Discernment",
}


def identify_domain(task_tokens, explicit_domain=None):
    """Determine domain from task tokens."""
    if explicit_domain and explicit_domain in _schema.DOMAINS:
        return explicit_domain
    scores = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        scores[domain] = len(task_tokens & keywords)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "CoreLogic"


def identify_channel(domain):
    """Default channel from domain."""
    return _DEFAULT_CHANNELS.get(domain, "Creation")


# ── Stage 5: Regime Selection ─────────────────────────────────────────────────

_ORCHESTRATION_KEYWORDS = {"orchestrate", "coordinate", "multi", "phases",
                           "sequence", "pipeline", "workflow", "ecology", "steps"}


def select_regime(task_tokens, explicit_regime=None, template_score=0.0):
    """Decision tree for regime selection."""
    if explicit_regime and explicit_regime in _schema.REGIMES:
        return explicit_regime
    if task_tokens & _ORCHESTRATION_KEYWORDS:
        return "orchestration"
    if template_score >= 0.5:
        return "synthetic"
    # Check if task is simple enough for canonical
    if template_score < 0.2:
        return "synthetic"  # no good match, build custom
    return "synthetic"  # default


# ── Stage 6: Function Bundle ─────────────────────────────────────────────────

def compose_function_bundle(template, regime):
    """Extract function bundle from template."""
    return list(template["functions"])


# ── Stage 7: Animal Order ────────────────────────────────────────────────────

_LOCUS_ANIMAL_ORDER = {
    "Awareness": ["Consume", "Sleep", "Blast"],
    "Intention": ["Sleep", "Consume", "Blast"],
    "Capability": ["Blast", "Play", "Sleep"],
    "Energy": ["Play", "Blast", "Sleep"],
}


def determine_animal_order(locus, template=None):
    """Animal order from locus, with template override."""
    if template and template.get("animal_order"):
        return list(template["animal_order"])
    return list(_LOCUS_ANIMAL_ORDER.get(locus, ["Consume", "Blast", "Sleep"]))


# ── Stage 8: Modality Assignment ─────────────────────────────────────────────

_MODALITY_KEYWORDS = {
    "MM": {"enforce", "standard", "compliance", "strict", "convention", "rigid"},
    "MF": {"implement", "convention", "match", "follow", "pattern", "consistent"},
    "FM": {"interface", "user", "api", "contract", "consumer", "usability"},
    "FF": {"explore", "ideate", "research", "discover", "brainstorm", "creative"},
}


def assign_modality(task_tokens, explicit_modality=None, template=None):
    """Determine modality profile."""
    if explicit_modality and explicit_modality in _schema.MODALITY_PROFILES:
        return explicit_modality
    if template and template.get("modality"):
        return template["modality"]
    scores = {}
    for mod, keywords in _MODALITY_KEYWORDS.items():
        scores[mod] = len(task_tokens & keywords)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "MF"  # default


# ── Stage 9: Distortion Guards ───────────────────────────────────────────────

def build_distortion_guards(template, charter_context=None):
    """Build distortion guard profile from template + charter prohibitions."""
    guards = dict(template.get("distortion_guards", {}))
    guards.setdefault("ahrimanic", "")
    guards.setdefault("luciferic", "")
    guards.setdefault("scope_limit", "")

    # Inject charter prohibitions as scope_limit additions
    if charter_context and charter_context.get("prohibitions"):
        prohibitions = charter_context["prohibitions"]
        existing = guards.get("scope_limit", "")
        charter_limits = "; ".join(f"[C] {p}" for p in prohibitions[:3])
        if existing:
            guards["scope_limit"] = f"{existing}; {charter_limits}"
        else:
            guards["scope_limit"] = charter_limits

    return guards


# ── Stage 10: System Prompt Fragment ─────────────────────────────────────────

_ANIMAL_TOOLS = {
    "Consume": ["Read", "Glob", "Grep"],
    "Blast": ["Read", "Write", "Edit"],
    "Play": ["Read", "Write", "Edit", "Bash"],
    "Sleep": ["Read"],
}


def generate_prompt_fragment(spec):
    """Assemble cognitive posture prompt from compiled spec."""
    name = spec.get("template_id", spec["id"])
    functions = spec["functions"]
    animal_order = spec["animal_order"]
    guards = spec.get("distortion_guards", {})

    lines = [f"=== AGENT: {name} ==="]

    # Cognitive posture
    lines.append("COGNITIVE POSTURE")
    if spec.get("selection_function"):
        lines.append(f"  Attend to: {spec['selection_function']}")
    if spec.get("valuation_function"):
        lines.append(f"  Optimize for: {spec['valuation_function']}")
    if spec.get("compression_strategy"):
        lines.append(f"  Scope: {spec['compression_strategy']}")
    if spec.get("action_bias"):
        lines.append(f"  First action: {spec['action_bias']}")

    # Function bundle
    lines.append("")
    lines.append(f"FUNCTIONS: {_schema.format_function_bundle(functions)}")

    # Workflow
    lines.append("")
    workflow_parts = []
    for animal in animal_order:
        tools = _ANIMAL_TOOLS.get(animal, [])
        workflow_parts.append(f"{animal} (tools: {', '.join(tools)})")
    lines.append(f"WORKFLOW: {' → '.join(workflow_parts)}")

    # Distortion guards
    if any(guards.values()):
        lines.append("")
        lines.append("DISTORTION GUARDS")
        if guards.get("ahrimanic"):
            lines.append(f"  Over-compression: {guards['ahrimanic']}")
        if guards.get("luciferic"):
            lines.append(f"  Over-expansion: {guards['luciferic']}")
        if guards.get("scope_limit"):
            lines.append(f"  Scope limit: {guards['scope_limit']}")

    # Success criteria
    if spec.get("success_criteria"):
        lines.append("")
        lines.append(f"SUCCESS: {spec['success_criteria']}")

    # Handoff
    if spec.get("handoff_spec"):
        lines.append(f"HANDOFF: {spec['handoff_spec']}")

    lines.append(f"=== END AGENT ===")
    return "\n".join(lines)


# ── Stage 11: Tool Scoping ───────────────────────────────────────────────────

def scope_tools(animal_order):
    """Determine available tools from animal order (union of all phases)."""
    tools = set()
    for animal in animal_order:
        tools.update(_ANIMAL_TOOLS.get(animal, []))
    return sorted(tools)


# ── Full Pipeline ─────────────────────────────────────────────────────────────

def compile_spec(task, regime=None, template_id=None, domain=None,
                 locus=None, modality=None):
    """Run the full compiler pipeline. Returns a spec dict."""
    # Stage 1: Task intake
    tokens = tokenize_task(task)

    # Stage 2: Context read
    contexts = load_all_context()
    charter_ctx = next((c for c in contexts if c["source"] == "charter"), None)
    mind_ctx = next((c for c in contexts if c["source"] == "mind"), None)
    witness_ctx = next((c for c in contexts if c["source"] == "witness"), None)

    # Stage 3: Locus
    resolved_locus = identify_locus(tokens, locus)

    # Stage 4: Domain
    resolved_domain = identify_domain(tokens, domain)
    channel = identify_channel(resolved_domain)

    # Template matching (needed for regime selection)
    matches = _templates.match_template(task, regime)
    top_score = matches[0][0] if matches else 0.0

    # Explicit template override
    if template_id:
        template = _templates.get_template(template_id)
        if not template:
            raise ValueError(f"Unknown template '{template_id}'. Use afe_templates to browse.")
    elif matches and top_score >= 0.15:
        template = matches[0][1]
    else:
        template = _templates.get_template("module_writer")  # safe default

    # Stage 5: Regime
    resolved_regime = select_regime(tokens, regime, top_score)

    # Stage 6: Function bundle
    functions = compose_function_bundle(template, resolved_regime)

    # Stage 7: Animal order
    animal_order = determine_animal_order(resolved_locus, template)

    # Stage 8: Modality
    resolved_modality = assign_modality(tokens, modality, template)

    # Stage 9: Distortion guards
    guards = build_distortion_guards(template, charter_ctx)

    # Build evidence IDs from cross-tool context
    evidence_ids = []
    if mind_ctx:
        evidence_ids.append(f"[M]mind:investigation:{mind_ctx['title'][:30]}")
    if charter_ctx:
        evidence_ids.append(f"[C]charter:active:{charter_ctx['invariant_count']}inv/{charter_ctx['constraint_count']}con")
    if witness_ctx:
        evidence_ids.append(f"[W]witness:{witness_ctx['run_id']}:{witness_ctx['status']}")

    # Assemble spec
    spec = _schema.make_spec(
        task=task,
        regime=resolved_regime,
        functions=functions,
        animal_order=animal_order,
        modality=resolved_modality,
        locus=resolved_locus,
        domain=resolved_domain,
        channel=channel,
        selection_function=template.get("selection_function", ""),
        valuation_function=template.get("valuation_function", ""),
        compression_strategy=template.get("compression_strategy", ""),
        action_bias=template.get("action_bias", ""),
        success_criteria=template.get("success_criteria", ""),
        handoff_spec=template.get("handoff_spec", ""),
        distortion_guards=guards,
        template_id=template["id"],
        evidence_ids=evidence_ids,
    )

    # Stage 10: System prompt fragment
    spec["system_prompt_fragment"] = generate_prompt_fragment(spec)

    # Stage 11: Tool scoping
    spec["tools"] = scope_tools(animal_order)

    return spec


# ── Ecology Compilation ──────────────────────────────────────────────────────

import uuid
from datetime import datetime, timezone


def compile_ecology(task, phases=None):
    """Compile a multi-agent ecology for a complex task.

    If phases is None, uses a standard 4-phase decomposition.
    Returns an ecology dict with sequenced specs.
    """
    if not phases:
        phases = [
            {"name": "explore", "task": f"Explore and map the territory for: {task}",
             "template": "canonical_explorer", "locus": "Awareness"},
            {"name": "plan", "task": f"Design the approach for: {task}",
             "template": "planner", "locus": "Intention"},
            {"name": "implement", "task": f"Implement: {task}",
             "template": "module_writer", "locus": "Capability"},
            {"name": "review", "task": f"Review and validate: {task}",
             "template": "systems_refactorer", "locus": "Energy"},
        ]

    specs = []
    for i, phase in enumerate(phases):
        spec = compile_spec(
            task=phase.get("task", task),
            template_id=phase.get("template"),
            locus=phase.get("locus"),
            domain=phase.get("domain"),
            modality=phase.get("modality"),
        )
        spec["phase"] = i + 1
        spec["phase_name"] = phase.get("name", f"phase_{i+1}")
        specs.append(spec)

    # Set handoff chain
    for i in range(len(specs) - 1):
        if not specs[i].get("handoff_spec"):
            specs[i]["handoff_spec"] = f"Output for phase {i+2}: {specs[i+1].get('phase_name', '')}"

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": uuid.uuid4().hex[:12],
        "task": task,
        "phase_count": len(specs),
        "specs": specs,
        "created_at": now,
    }
