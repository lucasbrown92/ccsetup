#!/usr/bin/env python3
"""claude-ledger router — keyword-based tool routing.

Pure Python, no external NLP. Each ROUTE_INDEX entry has:
  mcp_key, keywords[], intent_phrases[], anti_keywords[], weight, description

score_route() returns a float 0.0-1.0. Routes with score >= 0.10 are included.
"""

import re

from rules import MODE_PROFILES

# Route index: each entry maps a task description to a recommended MCP server
ROUTE_INDEX: list[dict] = [
    {
        "mcp_key": "claude-witness",
        "keywords": [
            "test", "failing", "fail", "error", "exception", "crash", "runtime",
            "execution", "pytest", "debug", "assert", "traceback", "failure",
            "coverage", "runs", "pass", "hotspot", "trace", "locals", "stack",
            "vitest", "jest", "go test", "witness",
        ],
        "intent_phrases": [
            "what failed", "why did it crash", "test is failing",
            "runtime error", "check execution", "which tests",
            "what actually ran", "locals at crash", "coverage gaps",
        ],
        "anti_keywords": ["visual", "screenshot", "browser", "ui", "render", "css", "html"],
        "weight": 1.3,
        "description": "Execution memory — what actually ran, exceptions, coverage gaps, locals at crash",
    },
    {
        "mcp_key": "claude-mind",
        "keywords": [
            "investigate", "hypothesis", "investigation", "track", "session",
            "reasoning", "theory", "explore", "understand", "why", "cause",
            "root cause", "assumption", "fact", "compaction", "resume", "multi-session",
            "mind", "externalize", "node", "open", "resolve",
            "recall", "past", "history", "similar", "sweep", "stale", "replay", "watch",
        ],
        "intent_phrases": [
            "investigate this", "track my investigation", "what's my hypothesis",
            "open investigation", "resume investigation", "after compaction",
            "externalize reasoning", "assumptions I'm making",
            "have I seen this before", "similar issue", "past investigation",
            "stale assumptions", "risk detection",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Persistent reasoning board — hypotheses, assumptions, facts across context compaction",
    },
    {
        "mcp_key": "claude-charter",
        "keywords": [
            "change", "refactor", "add", "remove", "rename", "modify",
            "constraint", "safe", "allowed", "invariant", "rule", "policy",
            "check", "conflict", "break", "violate", "contract", "goal",
            "architecture", "principle", "non-goal", "constitution",
            "expires", "deadline", "temporal", "time-bound", "expiry",
        ],
        "intent_phrases": [
            "is it safe to", "check constraints", "violates", "allowed to",
            "before I change", "project rules", "architectural invariant",
            "check before refactoring", "add dependency constraint",
            "remove feature safely", "change interface",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Project constitution — check changes against invariants, constraints, contracts, and time-bounded entries",
    },
    {
        "mcp_key": "claude-retina",
        "keywords": [
            "screenshot", "visual", "ui", "browser", "render", "css", "html",
            "layout", "click", "interact", "see", "looks", "appearance",
            "regression", "baseline", "pixel", "design", "playwright",
            "accessibility", "aria", "console", "js error", "viewport",
        ],
        "intent_phrases": [
            "what does it look like", "take a screenshot", "visual regression",
            "check the ui", "see the rendered", "browser interaction",
            "save baseline", "check against baseline", "js errors",
        ],
        "anti_keywords": ["test", "exception", "traceback", "pytest"],
        "weight": 1.2,
        "description": "Visual browser automation — screenshots, diffs, accessibility, JS console, interactions",
    },
    {
        "mcp_key": "serena",
        "keywords": [
            "symbol", "function", "class", "navigate", "find", "usage",
            "definition", "callers", "rename", "refactor", "method",
            "import", "references", "name_path", "overview", "structure",
            "lsp", "body", "replace", "insert",
        ],
        "intent_phrases": [
            "find the function", "who calls", "navigate to", "find usages",
            "symbol definition", "class structure", "get symbols",
            "rename across all references",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Semantic codebase navigation — symbols, callers, definitions, safe renames",
    },
    {
        "mcp_key": "dual-graph",
        "keywords": [
            "context", "files", "relevant", "related", "graph", "continue",
            "recommended", "ranked", "scan", "register", "edit", "neighbors",
            "impact", "memory", "graph_read", "graph_continue", "graph_scan",
        ],
        "intent_phrases": [
            "get file context", "recommended files", "relevant files",
            "graph scan", "register edit", "impact analysis", "graph neighbors",
        ],
        "anti_keywords": [],
        "weight": 1.1,
        "description": "Dual-graph context — pre-ranked file recommendations, memory-first routing, impact analysis",
    },
    {
        "mcp_key": "leann-server",
        "keywords": [
            "semantic", "meaning", "similar", "concept", "roughly", "kind",
            "search", "find code", "natural", "language", "understanding",
            "leann", "index", "unknown", "vague",
        ],
        "intent_phrases": [
            "search by meaning", "find similar code", "semantic search",
            "don't know the function name", "find something that does",
            "find code that", "by concept", "roughly does",
        ],
        "anti_keywords": [],
        "weight": 0.9,
        "description": "Semantic code search — find code by meaning and concept, not exact text",
    },
    {
        "mcp_key": "context7",
        "keywords": [
            "library", "docs", "documentation", "api", "framework",
            "reference", "how to use", "package", "sdk", "npm", "pip",
            "react", "next", "django", "fastapi", "supabase", "stripe",
        ],
        "intent_phrases": [
            "library documentation", "api reference", "how to use",
            "latest docs", "framework docs", "current api",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Live library documentation — current API docs for any framework or package",
    },
    {
        "mcp_key": "codegraphcontext",
        "keywords": [
            "callers", "callees", "call graph", "impact", "dependency",
            "call chain", "dead code", "who calls", "call tree",
            "multi-hop", "downstream", "upstream", "graph traversal",
        ],
        "intent_phrases": [
            "who calls this function", "call chain", "change impact",
            "downstream dependencies", "dead code", "call graph traversal",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Explicit call graph — multi-hop callers/callees, change impact, dead code detection",
    },
    {
        "mcp_key": "token-counter",
        "keywords": [
            "tokens", "cost", "budget", "expensive", "large file",
            "how much", "usage", "session cost", "count", "estimate",
        ],
        "intent_phrases": [
            "how many tokens", "token cost", "session cost", "budget check",
            "before reading this file", "estimate cost",
        ],
        "anti_keywords": [],
        "weight": 0.8,
        "description": "Token counting and session cost — pre-flight checks before large reads",
    },
    {
        "mcp_key": "claude-session",
        "keywords": [
            "session", "save", "archive", "restore", "clone", "fork",
            "backup", "history", "crash", "recovery", "lineage",
        ],
        "intent_phrases": [
            "save session", "restore session", "clone session",
            "fork session", "session lineage", "crash recovery",
        ],
        "anti_keywords": [],
        "weight": 0.8,
        "description": "Lossless session archive — save, clone, restore full conversation history",
    },
    {
        "mcp_key": "claude-ledger",
        "keywords": [
            "preflight", "impact", "before change", "correlate", "evidence",
            "routing", "workflow", "diagnose", "fix", "health", "mode",
            "available", "catalog", "rules", "context",
        ],
        "intent_phrases": [
            "before I change", "impact analysis", "what do I know about",
            "cross-tool search", "preflight check", "is it safe",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Meta-orchestrator — routing, preflight impact analysis, cross-tool correlation, health diagnosis",
    },
]


def score_route(task: str, route: dict, mode: str = "balanced") -> float:
    """Score how well a route matches the task description.

    Returns float 0.0-1.0. Applies mode-specific weight and anti-penalty multipliers.
    """
    profile = MODE_PROFILES.get(mode, MODE_PROFILES["balanced"])
    tokens = set(re.findall(r"[a-z0-9]+", task.lower()))

    kw_matches = len(tokens & set(route["keywords"]))
    kw_score = kw_matches / max(len(route["keywords"]), 1)

    phrase_bonus = sum(
        0.2 for p in route.get("intent_phrases", [])
        if p in task.lower()
    )

    anti_hits = len(tokens & set(route.get("anti_keywords", [])))
    anti_penalty = anti_hits * 0.15 * profile["anti_penalty_mul"]

    raw = (kw_score + phrase_bonus - anti_penalty) * route.get("weight", 1.0) * profile["route_weight_mul"]
    return max(0.0, min(1.0, raw))


def _get_all_routes() -> list[dict]:
    """Return ROUTE_INDEX merged with dynamic extension routes."""
    import extensions as _ext
    ext_routes = _ext.get_extended_routes()
    if not ext_routes:
        return ROUTE_INDEX
    # Deduplicate: extensions override hardcoded entries with same mcp_key
    hardcoded_keys = {r["mcp_key"] for r in ROUTE_INDEX}
    merged = list(ROUTE_INDEX)
    for r in ext_routes:
        if r["mcp_key"] not in hardcoded_keys:
            merged.append(r)
    return merged


def route(task: str, available_keys: set[str] | None = None,
          min_score: float | None = None, top_n: int | None = None,
          mode: str = "balanced") -> list[dict]:
    """Return top routes for a task description.

    Args:
        task: Free-text task description
        available_keys: If given, only return routes for these mcp_keys
        min_score: Minimum score threshold (overrides mode profile if given)
        top_n: Maximum routes to return (overrides mode profile if given)
        mode: Token priority mode — economy | balanced | performance

    Returns:
        List of dicts: {mcp_key, score, description}
    """
    profile = MODE_PROFILES.get(mode, MODE_PROFILES["balanced"])
    effective_min = min_score if min_score is not None else profile["route_min_score"]
    effective_top = top_n if top_n is not None else profile["route_max"]

    all_routes = _get_all_routes()
    scored = []
    for entry in all_routes:
        key = entry["mcp_key"]
        if available_keys is not None and key not in available_keys:
            continue
        s = score_route(task, entry, mode=mode)
        if s >= effective_min:
            scored.append({
                "mcp_key": key,
                "score": round(s, 3),
                "description": entry["description"],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:effective_top]
