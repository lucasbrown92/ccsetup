"""Enums, validation, spec construction, coin derivation, and formatting for claude-afe."""

import re
import uuid
from datetime import datetime, timezone


# ── Enums ─────────────────────────────────────────────────────────────────────

REGIMES = ["canonical", "synthetic", "orchestration"]

LOCI = ["Awareness", "Intention", "Capability", "Energy"]

DOMAINS = [
    "Infrastructure", "Data", "Integration", "CoreLogic", "Interface", "Meta",
]

CHANNELS = [
    "Survival", "Creation", "Aid", "Power", "Decision",
    "Identity", "Expression", "Discernment", "Authority",
]

FUNCTIONS = ["Se", "Si", "Ne", "Ni", "Te", "Ti", "Fe", "Fi"]

MODALITIES = ["M", "F"]  # per-function
MODALITY_PROFILES = ["MM", "MF", "FM", "FF"]  # composite

ANIMALS = ["Consume", "Blast", "Play", "Sleep"]

ROLES = ["primary", "secondary", "tertiary", "quaternary"]

OBSERVER_AXES = ["S", "N", "both", "none"]
DECIDER_AXES = ["T", "F", "both", "none"]
SAVIOR_ORIENTATIONS = ["tribe", "self", "balanced"]
LEAD_AXES = ["decider", "observer", "balanced"]


# ── Coin derivation ──────────────────────────────────────────────────────────

_OBSERVER_FUNCS = {"Se", "Si", "Ne", "Ni"}
_DECIDER_FUNCS = {"Te", "Ti", "Fe", "Fi"}
_S_FUNCS = {"Se", "Si"}
_N_FUNCS = {"Ne", "Ni"}
_T_FUNCS = {"Te", "Ti"}
_F_FUNCS = {"Fe", "Fi"}
_EXTROVERTED = {"Se", "Ne", "Te", "Fe"}
_INTROVERTED = {"Si", "Ni", "Ti", "Fi"}


def derive_coins(functions):
    """Derive coin values from a function bundle.

    Returns a dict with observer_axis, decider_axis, savior_orientation, lead_axis.
    """
    func_names = {f["function"] for f in functions}
    observers = func_names & _OBSERVER_FUNCS
    deciders = func_names & _DECIDER_FUNCS

    # Coin 1: S vs N
    has_s = bool(observers & _S_FUNCS)
    has_n = bool(observers & _N_FUNCS)
    if has_s and has_n:
        observer_axis = "both"
    elif has_s:
        observer_axis = "S"
    elif has_n:
        observer_axis = "N"
    else:
        observer_axis = "none"

    # Coin 2: T vs F
    has_t = bool(deciders & _T_FUNCS)
    has_f = bool(deciders & _F_FUNCS)
    if has_t and has_f:
        decider_axis = "both"
    elif has_t:
        decider_axis = "T"
    elif has_f:
        decider_axis = "F"
    else:
        decider_axis = "none"

    # Coin 3: tribe vs self (extroverted decider = tribe-facing)
    ext_deciders = deciders & _EXTROVERTED
    int_deciders = deciders & _INTROVERTED
    if ext_deciders and int_deciders:
        savior_orientation = "balanced"
    elif ext_deciders:
        savior_orientation = "tribe"
    elif int_deciders:
        savior_orientation = "self"
    else:
        savior_orientation = "balanced"

    # Coin 4: decider-lead vs observer-lead (from primary function)
    if functions:
        primary = functions[0]["function"]
        if primary in _DECIDER_FUNCS:
            lead_axis = "decider"
        elif primary in _OBSERVER_FUNCS:
            lead_axis = "observer"
        else:
            lead_axis = "balanced"
    else:
        lead_axis = "balanced"

    return {
        "observer_axis": observer_axis,
        "decider_axis": decider_axis,
        "savior_orientation": savior_orientation,
        "lead_axis": lead_axis,
    }


def derive_animal_types(animal_order):
    """Derive info_animal, energy_animal, dominant_pair from animal order."""
    info = next((a for a in animal_order if a in ("Consume", "Blast")), "Consume")
    energy = next((a for a in animal_order if a in ("Play", "Sleep")), "Sleep")

    # Dominant pair: whichever pair's member appears first
    first = animal_order[0] if animal_order else "Consume"
    if first in ("Consume", "Blast"):
        dominant = "info"
    else:
        dominant = "energy"

    return {
        "info_animal": info,
        "energy_animal": energy,
        "dominant_pair": dominant,
    }


# ── Validation ────────────────────────────────────────────────────────────────

def validate_function_entry(func):
    """Validate a single function dict. Raises ValueError."""
    if not isinstance(func, dict):
        raise ValueError("Each function must be a dict with 'function', 'modality', 'role'")
    fn = func.get("function", "")
    if fn not in FUNCTIONS:
        raise ValueError(f"Invalid function '{fn}'. Valid: {', '.join(FUNCTIONS)}")
    mod = func.get("modality", "")
    if mod not in MODALITIES:
        raise ValueError(f"Invalid modality '{mod}'. Valid: M, F")
    role = func.get("role", "")
    if role not in ROLES:
        raise ValueError(f"Invalid role '{role}'. Valid: {', '.join(ROLES)}")


def validate_animal_order(order):
    """Validate animal order list. Raises ValueError."""
    if not isinstance(order, list) or not order:
        raise ValueError("animal_order must be a non-empty list")
    for a in order:
        if a not in ANIMALS:
            raise ValueError(f"Invalid animal '{a}'. Valid: {', '.join(ANIMALS)}")


def validate_modality_profile(mp):
    """Validate composite modality profile. Raises ValueError."""
    if mp not in MODALITY_PROFILES:
        raise ValueError(f"Invalid modality '{mp}'. Valid: {', '.join(MODALITY_PROFILES)}")


# ── Spec construction ─────────────────────────────────────────────────────────

def make_spec(task, regime, functions, animal_order, modality,
              locus=None, domain=None, channel=None,
              selection_function=None, valuation_function=None,
              compression_strategy=None, action_bias=None,
              tools=None, context_load=None, success_criteria=None,
              handoff_spec=None, distortion_guards=None,
              template_id=None, evidence_ids=None):
    """Create a compiled agent spec dict. Validates all inputs."""
    if not task or not task.strip():
        raise ValueError("task must not be empty")
    if regime not in REGIMES:
        raise ValueError(f"Invalid regime '{regime}'. Valid: {', '.join(REGIMES)}")
    for f in functions:
        validate_function_entry(f)
    validate_animal_order(animal_order)
    validate_modality_profile(modality)

    if locus and locus not in LOCI:
        raise ValueError(f"Invalid locus '{locus}'. Valid: {', '.join(LOCI)}")
    if domain and domain not in DOMAINS:
        raise ValueError(f"Invalid domain '{domain}'. Valid: {', '.join(DOMAINS)}")

    coins = derive_coins(functions)
    animals = derive_animal_types(animal_order)

    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": uuid.uuid4().hex[:12],
        "task": task.strip(),
        "regime": regime,
        "template_id": template_id,

        # Coins
        "observer_axis": coins["observer_axis"],
        "decider_axis": coins["decider_axis"],
        "savior_orientation": coins["savior_orientation"],
        "lead_axis": coins["lead_axis"],

        # Functions
        "functions": functions,

        # Animals
        "info_animal": animals["info_animal"],
        "energy_animal": animals["energy_animal"],
        "dominant_pair": animals["dominant_pair"],
        "animal_order": animal_order,

        # Modality
        "modality": modality,

        # Task targeting
        "locus": locus,
        "domain": domain,
        "channel": channel,

        # Operator definition
        "selection_function": selection_function or "",
        "valuation_function": valuation_function or "",
        "compression_strategy": compression_strategy or "",
        "action_bias": action_bias or "",

        # Claude Code instantiation
        "system_prompt_fragment": "",  # populated by compiler
        "tools": tools or [],
        "context_load": context_load or [],
        "success_criteria": success_criteria or "",
        "handoff_spec": handoff_spec or "",

        # Distortion guards
        "distortion_guards": distortion_guards or {
            "ahrimanic": "",
            "luciferic": "",
            "scope_limit": "",
        },

        # Evidence
        "evidence_ids": evidence_ids or [],

        # Metadata
        "created_at": now,
    }


# ── Formatting ────────────────────────────────────────────────────────────────

def format_function_bundle(functions):
    """Format function bundle as compact string: Te-M, Ni-F, ..."""
    return ", ".join(f"{f['function']}-{f['modality']}" for f in functions)


def format_spec_brief(spec):
    """One-line brief for listing."""
    funcs = format_function_bundle(spec["functions"])
    regime = spec["regime"].upper()
    locus = spec.get("locus") or "?"
    return f"[{spec['id']}] {regime} | {funcs} | {locus} — {spec['task'][:60]}"


def format_spec_full(spec):
    """Full multi-line rendering of a compiled spec."""
    lines = [
        f"═══ AGENT SPEC [{spec['id']}] ═══",
        f"Task: {spec['task']}",
        f"Regime: {spec['regime']}",
    ]
    if spec.get("template_id"):
        lines.append(f"Template: {spec['template_id']}")

    lines.append("")
    lines.append("COIN COMPOSITION:")
    lines.append(f"  Observer: {spec['observer_axis']}  |  Decider: {spec['decider_axis']}")
    lines.append(f"  Orientation: {spec['savior_orientation']}  |  Lead: {spec['lead_axis']}")

    lines.append("")
    lines.append("FUNCTION BUNDLE:")
    for f in spec["functions"]:
        lines.append(f"  {f['role']}: {f['function']}-{f['modality']}")

    lines.append("")
    lines.append(f"ANIMAL ORDER: {' → '.join(spec['animal_order'])}")
    lines.append(f"  Info: {spec['info_animal']}  |  Energy: {spec['energy_animal']}  |  Dominant: {spec['dominant_pair']}")

    lines.append("")
    lines.append(f"MODALITY: {spec['modality']}")

    if spec.get("locus") or spec.get("domain"):
        lines.append("")
        lines.append("TASK TARGETING:")
        if spec.get("locus"):
            lines.append(f"  Locus: {spec['locus']}")
        if spec.get("domain"):
            lines.append(f"  Domain: {spec['domain']}")
        if spec.get("channel"):
            lines.append(f"  Channel: {spec['channel']}")

    if spec.get("selection_function") or spec.get("valuation_function"):
        lines.append("")
        lines.append("OPERATOR DEFINITION:")
        if spec.get("selection_function"):
            lines.append(f"  Attend to: {spec['selection_function']}")
        if spec.get("valuation_function"):
            lines.append(f"  Optimize for: {spec['valuation_function']}")
        if spec.get("compression_strategy"):
            lines.append(f"  Scope: {spec['compression_strategy']}")
        if spec.get("action_bias"):
            lines.append(f"  First action: {spec['action_bias']}")

    guards = spec.get("distortion_guards", {})
    if any(guards.values()):
        lines.append("")
        lines.append("DISTORTION GUARDS:")
        if guards.get("ahrimanic"):
            lines.append(f"  Over-compression: {guards['ahrimanic']}")
        if guards.get("luciferic"):
            lines.append(f"  Over-expansion: {guards['luciferic']}")
        if guards.get("scope_limit"):
            lines.append(f"  Scope limit: {guards['scope_limit']}")

    if spec.get("tools"):
        lines.append("")
        lines.append(f"TOOLS: {', '.join(spec['tools'])}")

    if spec.get("success_criteria"):
        lines.append("")
        lines.append(f"SUCCESS: {spec['success_criteria']}")

    if spec.get("handoff_spec"):
        lines.append(f"HANDOFF: {spec['handoff_spec']}")

    if spec.get("evidence_ids"):
        lines.append("")
        lines.append(f"EVIDENCE: {', '.join(spec['evidence_ids'])}")

    if spec.get("system_prompt_fragment"):
        lines.append("")
        lines.append("SYSTEM PROMPT FRAGMENT:")
        lines.append(spec["system_prompt_fragment"])

    return "\n".join(lines)
