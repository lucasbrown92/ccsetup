#!/usr/bin/env python3
"""claude-ledger router — keyword-based tool routing.

Pure Python, no external NLP. Each ROUTE_INDEX entry has:
  mcp_key, keywords[], intent_phrases[], anti_keywords[], weight, description

score_route() returns a float 0.0-1.0. Routes with score >= 0.10 are included.
"""

import re

# Route index: each entry maps a task description to a recommended MCP server
ROUTE_INDEX: list[dict] = [
    {
        "mcp_key": "claude-witness",
        "keywords": [
            "test", "failing", "exception", "crash", "runtime", "execution",
            "pytest", "debug", "assert", "traceback", "error", "failure",
            "coverage", "runs", "pass", "fail",
        ],
        "intent_phrases": [
            "what failed", "why did it crash", "test is failing",
            "runtime error", "check execution", "which tests",
        ],
        "anti_keywords": ["visual", "screenshot", "browser", "ui", "render", "css", "html"],
        "weight": 1.2,
        "description": "Execution memory — what actually ran, exceptions, coverage gaps",
    },
    {
        "mcp_key": "claude-mind",
        "keywords": [
            "debug", "investigate", "hypothesis", "investigation", "track",
            "session", "reasoning", "theory", "explore", "understand",
            "why", "cause", "root cause",
        ],
        "intent_phrases": [
            "investigate this", "track my investigation", "what's my hypothesis",
            "open investigation", "resume investigation",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Persistent reasoning board — hypotheses, facts, multi-session debugging",
    },
    {
        "mcp_key": "claude-charter",
        "keywords": [
            "change", "refactor", "add", "remove", "rename", "modify",
            "constraint", "safe", "allowed", "invariant", "rule", "policy",
            "check", "conflict", "break", "violate",
        ],
        "intent_phrases": [
            "is it safe to", "check constraints", "violates", "allowed to",
            "before I change", "project rules",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Project constitution — check changes against invariants and constraints",
    },
    {
        "mcp_key": "claude-retina",
        "keywords": [
            "screenshot", "visual", "ui", "browser", "render", "css", "html",
            "layout", "click", "interact", "see", "looks", "appearance",
            "regression", "baseline", "pixel", "design",
        ],
        "intent_phrases": [
            "what does it look like", "take a screenshot", "visual regression",
            "check the ui", "see the rendered", "browser interaction",
        ],
        "anti_keywords": ["test", "exception", "traceback", "pytest"],
        "weight": 1.2,
        "description": "Visual browser automation — screenshots, diffs, accessibility, interactions",
    },
    {
        "mcp_key": "claude-afe",
        "keywords": [
            "agent", "spawn", "compile", "spec", "orchestrate", "multi-agent",
            "complex", "task", "cognitive", "posture", "ecology",
        ],
        "intent_phrases": [
            "spawn an agent", "compile spec", "multi-agent", "agent ecology",
            "complex task", "before spawning",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Cognitive compiler — task → agent spec before spawning Agent tool",
    },
    {
        "mcp_key": "serena",
        "keywords": [
            "symbol", "function", "class", "navigate", "find", "usage",
            "definition", "callers", "rename", "refactor", "method",
            "import", "references",
        ],
        "intent_phrases": [
            "find the function", "who calls", "navigate to", "find usages",
            "symbol definition", "class structure",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Semantic codebase navigation — symbols, callers, definitions",
    },
    {
        "mcp_key": "dual-graph",
        "keywords": [
            "context", "files", "explore", "codebase", "navigate",
            "session start", "relevant", "related", "graph",
        ],
        "intent_phrases": [
            "session start", "explore the codebase", "what files are relevant",
            "find related files", "understand the project",
        ],
        "anti_keywords": [],
        "weight": 0.9,
        "description": "Graph-aware context retrieval — recommended files, session memory",
    },
    {
        "mcp_key": "leann-server",
        "keywords": [
            "search", "semantic", "meaning", "similar", "code",
            "understand", "find code", "similar code",
        ],
        "intent_phrases": [
            "search by meaning", "find similar code", "semantic search",
        ],
        "anti_keywords": [],
        "weight": 0.9,
        "description": "Semantic code search — find code by meaning, not exact text",
    },
    {
        "mcp_key": "context7",
        "keywords": [
            "library", "docs", "documentation", "api", "framework",
            "reference", "how to use",
        ],
        "intent_phrases": [
            "library documentation", "api reference", "how to use",
            "latest docs", "framework docs",
        ],
        "anti_keywords": [],
        "weight": 1.0,
        "description": "Live library documentation — accurate API docs for any framework",
    },
]


def score_route(task: str, route: dict) -> float:
    """Score how well a route matches the task description.

    Returns float 0.0-1.0.
    """
    tokens = set(re.findall(r"[a-z0-9]+", task.lower()))

    kw_matches = len(tokens & set(route["keywords"]))
    kw_score = kw_matches / max(len(route["keywords"]), 1)

    phrase_bonus = sum(
        0.2 for p in route.get("intent_phrases", [])
        if p in task.lower()
    )

    anti_penalty = len(tokens & set(route.get("anti_keywords", []))) * 0.15

    raw = (kw_score + phrase_bonus - anti_penalty) * route.get("weight", 1.0)
    return max(0.0, min(1.0, raw))


def route(task: str, available_keys: set[str] | None = None,
          min_score: float = 0.10, top_n: int = 5) -> list[dict]:
    """Return top routes for a task description.

    Args:
        task: Free-text task description
        available_keys: If given, only return routes for these mcp_keys
        min_score: Minimum score threshold (default: 0.10)
        top_n: Maximum routes to return (default: 5)

    Returns:
        List of dicts: {mcp_key, score, description}
    """
    scored = []
    for entry in ROUTE_INDEX:
        key = entry["mcp_key"]
        if available_keys is not None and key not in available_keys:
            continue
        s = score_route(task, entry)
        if s >= min_score:
            scored.append({
                "mcp_key": key,
                "score": round(s, 3),
                "description": entry["description"],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]
