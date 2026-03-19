#!/usr/bin/env python3
"""claude-ledger rules — prescriptive operational playbook for Claude Code.

These rules specify HOW Claude should operate, not just what tools exist.
Goal: Claude never needs to be reminded to use its tools — correct routing
is built into the system.

Sections:
  TOOL_SUBSTITUTIONS  — use X instead of Y (anti-pattern elimination)
  MANDATORY_GATES     — before action X, always call Y first
  PRIORITY_CHAINS     — for task type X, call tools in this order
  TOKEN_RULES         — maximize capability per token
  SKILLS_CATALOG      — Claude Code slash commands (Skill tool)
  BUILTIN_TOOLS       — Read/Edit/Write/Grep/Glob/Bash/Agent guidance
"""

# ─────────────────────────────────────────────────────────────────────────────
# TOOL SUBSTITUTIONS
# These are the most common "Claude forgets to use its tools" patterns.
# Each entry: what to avoid, what to use instead, why, and exceptions.
# ─────────────────────────────────────────────────────────────────────────────

TOOL_SUBSTITUTIONS: list[dict] = [
    {
        "avoid": "bash grep / rg",
        "use_instead": "fallback_rg(pattern, glob?) [dual-graph] or search_for_pattern(pattern) [serena]",
        "why": "Graph and serena tools have project context. Bash grep runs blind against the filesystem.",
        "exception": "Config files, non-indexed paths, or when both graph and serena are unavailable.",
    },
    {
        "avoid": "bash find / ls",
        "use_instead": "Glob(pattern) [built-in] or find_file(name) / list_dir() [serena]",
        "why": "Glob and serena understand the project. bash find produces unstructured noise.",
        "exception": "None — always prefer dedicated tools for file discovery.",
    },
    {
        "avoid": "Read(file_path) for an entire code file",
        "use_instead": "graph_read(file::symbol) for specific functions; get_symbols_overview + find_symbol for structure",
        "why": "A 400-line file has ~380 lines you don't need. Symbol-level reads are 5-20x cheaper per token.",
        "exception": "Non-code files (config, markdown, JSON), or files under ~50 lines.",
    },
    {
        "avoid": "Exploring files without calling graph_continue first",
        "use_instead": "graph_continue(query) → read recommended_files via graph_read — one call per file",
        "why": "graph_continue has pre-ranked every file by relevance to your query. Skipping it means duplicate work.",
        "exception": "graph_continue returns skip=true (project < 5 files).",
    },
    {
        "avoid": "Using training knowledge for external library APIs",
        "use_instead": "context7: resolve-library-id('name') then get-library-docs(id, topic?)",
        "why": "Training knowledge is stale and may describe old API versions. context7 fetches the actual current docs.",
        "exception": "Library is not indexed in context7 (fallback to training with a caveat).",
    },
    {
        "avoid": "Internal reasoning only for multi-turn debugging",
        "use_instead": "mind_open + mind_add to externalize hypotheses, facts, and next steps",
        "why": "Context compaction destroys internal reasoning silently. mind_summary() recovers full state in ≤15 lines.",
        "exception": "Single-turn tasks where continuity across compaction doesn't matter.",
    },
    {
        "avoid": "Spawning Agent tool with an ad-hoc system prompt",
        "use_instead": "afe_compile(task) first, then inject spec's system_prompt_fragment when spawning Agent",
        "why": "Ad-hoc prompts produce inconsistent agents. afe_compile compiles posture from your actual state (mind/charter/witness).",
        "exception": "Trivially simple agent tasks with a single clear action.",
    },
    {
        "avoid": "Making structural changes (rename/refactor/remove) without checking constraints",
        "use_instead": "charter_check('one-sentence description of change') before touching code",
        "why": "charter.json holds invariants the project has declared. One call surfaces conflicts before they cause damage.",
        "exception": "No .claude/charter.json yet (run charter_add to seed it).",
    },
    {
        "avoid": "Starting to debug a failure from reading source code",
        "use_instead": "witness_runs() + witness_hotspots() first — see what actually ran, then read targeted code",
        "why": "Execution memory shows the exact call stack and locals. Source reading without it is hypothesis without evidence.",
        "exception": "No witness runs exist yet (run: pytest --witness to capture first).",
    },
    {
        "avoid": "bash cat / head / tail on any file",
        "use_instead": "Read(file_path) built-in — or graph_read(file::symbol) for symbol-targeted reads",
        "why": "Read is the correct tool with proper permissions. graph_read is even better for indexed code.",
        "exception": "None — never use bash for file reading.",
    },
    {
        "avoid": "bash git commit",
        "use_instead": "Skill(skill='commit') — Claude Code /commit skill",
        "why": "/commit handles pre-commit hooks, conventional message format, co-author line, and staging correctly.",
        "exception": "User explicitly asks for raw git command.",
    },
    {
        "avoid": "Reading all recommended_files sequentially (one at a time in separate turns)",
        "use_instead": "Call multiple graph_read() in parallel in a single response — they are independent",
        "why": "Parallel tool calls in one response halve round-trips. graph_read is safe to parallelize.",
        "exception": "Second read depends on first read's result.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# MANDATORY GATES
# Before these actions, always make this call first.
# Non-negotiable. Each gate call takes ≤1 second and prevents costly mistakes.
# ─────────────────────────────────────────────────────────────────────────────

MANDATORY_GATES: list[dict] = [
    {
        "before": "Any non-trivial task or new session turn",
        "call": "graph_continue(query)",
        "returns": "recommended_files (ranked), confidence level, max_supplementary_greps cap",
        "then": "Read recommended_files via graph_read (parallel). Stop at confidence=high — do NOT grep further.",
        "skip_if": "graph_continue returns skip=true (project < 5 files)",
    },
    {
        "before": "Any structural change: rename, refactor, delete, move, change interface/contract",
        "call": "charter_check('one-sentence description of the change')",
        "returns": "CLEAR or CONFLICT with specific entry IDs",
        "then": "CLEAR → proceed. CONFLICT → surface to user before touching code.",
        "skip_if": ".claude/charter.json does not exist yet",
    },
    {
        "before": "Spawning the Agent tool for any complex task",
        "call": "afe_compile(task='description of what the agent should do')",
        "returns": "Compiled spec with system_prompt_fragment ready to inject",
        "then": "Use spec.system_prompt_fragment as the agent's system prompt.",
        "skip_if": "Task is a single trivial action (e.g., 'list files')",
    },
    {
        "before": "Starting to debug a test failure or runtime exception",
        "call": "witness_runs(limit=5)",
        "returns": "Recent run IDs, pass/fail status, timestamps",
        "then": "witness_hotspots() for chronic failures → witness_traces('fn') → witness_exception('Type')",
        "skip_if": "No witness runs exist — run: pytest --witness to capture first",
    },
    {
        "before": "Resuming after context compaction or long gap",
        "call": "mind_summary() [if investigation open] + ledger_context() or graph_continue(query)",
        "returns": "Full investigation state + project context",
        "then": "Recover full state before doing any work. Do not guess.",
        "skip_if": "Fresh session with no prior investigation state",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# PRIORITY CHAINS
# For each task type, call tools in this exact priority order.
# Stop when you have enough. Use ">" to mean "prefer over".
# ─────────────────────────────────────────────────────────────────────────────

PRIORITY_CHAINS: dict[str, dict] = {
    "code_navigation": {
        "goal": "Find a function, class, symbol, or understand code structure",
        "trigger_words": ["find", "locate", "where", "symbol", "function", "class", "method", "navigate", "definition", "callers", "usages", "who calls"],
        "chain": [
            "1. graph_continue(query)                            → get recommended_files first",
            "2. get_symbols_overview(relative_path)             → file structure before reading bodies",
            "3. find_symbol(name_path, depth=1)                 → serena: structure without body",
            "4. find_symbol(name_path, include_body=True)       → serena: read body only when needed",
            "5. graph_read(file::symbol)                        → or graph_read for body of specific fn",
            "6. find_referencing_symbols(name)                  → callers/usages when needed",
        ],
        "avoid": "Read(full_file) — reads entire file when you need 1 function",
        "parallel_tip": "Steps 2+3 can run in parallel if you know the file already",
    },
    "file_context": {
        "goal": "Find relevant files for a task without knowing where to look",
        "trigger_words": ["explore", "understand", "codebase", "context", "relevant", "related", "what files", "where is"],
        "chain": [
            "1. graph_continue(query)                            → MANDATORY — ranked recommended_files",
            "2. graph_read(file) for each recommended_file       → parallel, one call per file",
            "3. fallback_rg(pattern) ONLY if confidence < high  → capped by max_supplementary_greps",
        ],
        "avoid": "Reading files without graph_continue — wastes tokens on wrong files",
        "parallel_tip": "All graph_read calls from recommended_files can run in parallel",
    },
    "debugging": {
        "goal": "Understand a test failure or runtime error",
        "trigger_words": ["debug", "failing", "fail", "error", "exception", "crash", "broken", "wrong", "test", "pytest"],
        "chain": [
            "1. witness_runs(limit=5)                           → recent run history",
            "2. witness_hotspots(run_count=5)                   → chronic failure points",
            "3. witness_traces('fn_name', status='exception')   → calls that raised exceptions",
            "4. witness_exception('ErrorType')                  → locals at crash site",
            "5. witness_coverage_gaps('file.py')                → if coverage is the gap",
            "6. mind_add('hypothesis', '...')                   → externalize reasoning if multi-turn",
        ],
        "avoid": "Reading source code before checking execution evidence",
        "parallel_tip": "Steps 1+2 can run in parallel (independent)",
    },
    "investigation": {
        "goal": "Track multi-turn debugging or research across compaction",
        "trigger_words": ["investigate", "track", "hypothesis", "theory", "session", "multi-session", "remember", "resume"],
        "chain": [
            "1. mind_summary()                                  → if session continues (resume state)",
            "   OR mind_open('title')                           → if starting fresh",
            "2. mind_add('assumption/hypothesis/fact', '...')  → externalize each belief",
            "3. mind_update(node_id, 'confirmed/refuted')      → after evidence from witness/test",
            "4. mind_resolve('conclusion')                     → close investigation",
        ],
        "avoid": "Internal reasoning for anything that spans turns — compaction will destroy it",
        "parallel_tip": "mind_summary + charter_summary + graph_continue can run in parallel at session start",
    },
    "structural_change": {
        "goal": "Refactor, rename, delete, move, or change an interface",
        "trigger_words": ["refactor", "rename", "delete", "remove", "move", "change", "restructure", "redesign"],
        "chain": [
            "1. charter_check('one-sentence description')       → MANDATORY gate — check constraints first",
            "2. If CLEAR → proceed with implementation",
            "3. rename_symbol(old, new) [serena]                → for renames (updates all references)",
            "4. replace_symbol_body(symbol, new_body) [serena] → for full function rewrites",
            "5. charter_check + mind_add(after) to record the change",
        ],
        "avoid": "Making changes before charter_check — surfaces invariant violations early",
        "parallel_tip": "None — charter_check must complete before any edits",
    },
    "library_api": {
        "goal": "Use an external library or framework correctly",
        "trigger_words": ["library", "docs", "documentation", "api", "framework", "how to use", "package", "import"],
        "chain": [
            "1. resolve-library-id('library-name')             → context7: get the library ID",
            "2. get-library-docs(id, topic='specific topic')   → context7: fetch actual current docs",
        ],
        "avoid": "Training knowledge for library APIs — stale, may describe wrong version",
        "parallel_tip": "N/A — step 2 requires step 1's output",
    },
    "agent_spawn": {
        "goal": "Spawn an Agent tool for complex multi-step work",
        "trigger_words": ["agent", "spawn", "subagent", "delegate", "complex", "multi-step", "orchestrate"],
        "chain": [
            "1. afe_context()                                   → read current mind/charter/witness state",
            "2. afe_compile(task='description')                 → compile agent spec",
            "3. afe_validate(spec_id)                           → check against charter constraints",
            "4. Agent(subagent_type=..., prompt=spec.system_prompt_fragment + task details)",
        ],
        "avoid": "Agent tool with ad-hoc prompt — produces inconsistent cognitive posture",
        "parallel_tip": "N/A — sequence is linear",
    },
    "visual_ui": {
        "goal": "Verify or debug a rendered UI",
        "trigger_words": ["screenshot", "visual", "ui", "browser", "render", "looks", "css", "layout", "regression", "baseline"],
        "chain": [
            "1. retina_capture(url)                             → screenshot",
            "2. Read(file_path=capture.file)                   → view the PNG",
            "3. retina_inspect(url)                             → accessibility/ARIA tree",
            "4. retina_console(url)                             → JS errors during load",
            "5. <make changes>",
            "6. retina_diff(id_before, id_after)                → verify change was correct",
        ],
        "avoid": "Inferring appearance from HTML/CSS source — Claude cannot see rendered output",
        "parallel_tip": "Steps 1+3+4 can run in parallel (all read the same URL independently)",
    },
    "git_commit": {
        "goal": "Commit code changes",
        "trigger_words": ["commit", "git commit", "save changes", "check in"],
        "chain": [
            "1. Skill(skill='commit')                           → /commit handles everything correctly",
            "   (stages files, conventional message, pre-commit hooks, co-author line)",
        ],
        "avoid": "bash git commit — /commit handles edge cases that raw git misses",
        "parallel_tip": "N/A",
    },
    "pr_review": {
        "goal": "Review a pull request",
        "trigger_words": ["review", "pr", "pull request", "diff", "changes"],
        "chain": [
            "1. Skill(skill='review-pr', args='PR_NUMBER')      → /review-pr fetches and reviews",
        ],
        "avoid": "Manually fetching diff with bash — /review-pr does it structured",
        "parallel_tip": "N/A",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# TOKEN EFFICIENCY RULES
# Concrete habits that maximize capability per token spent.
# ─────────────────────────────────────────────────────────────────────────────

TOKEN_RULES: list[str] = [
    "graph_read(file::symbol) reads only that function — 5-20x cheaper than Read(full_file)",
    "get_symbols_overview before any Read — understand structure, then read only what you need",
    "graph_continue recommended_files are pre-ranked — trust the ranking, read them in parallel",
    "Stop at confidence=high from graph_continue — do NOT grep further, caps are hard limits",
    "mind_summary() recovers full investigation state in ≤15 lines after compaction",
    "charter_summary() in 1 call — do not read charter entries one by one",
    "witness_hotspots() prioritizes where to look — don't scan all runs manually",
    "Batch independent tool calls in parallel in a single response — halves round-trips",
    "find_symbol(name, depth=1, include_body=False) → class structure without reading bodies",
    "ledger_query('task description') → get concrete call sequence before starting any work",
    "After any edit: graph_register_edit(files) → keep graph memory current for next query",
]

# ─────────────────────────────────────────────────────────────────────────────
# SKILLS CATALOG
# Claude Code slash commands invoked via the Skill tool.
# These are NOT MCP servers — they are built-in command expansions.
# ─────────────────────────────────────────────────────────────────────────────

SKILLS_CATALOG: list[dict] = [
    {
        "skill": "commit",
        "trigger": "user asks to commit, create a git commit, or uses /commit",
        "description": "Git commit: stages files, writes conventional commit message, co-author line, handles pre-commit hooks.",
        "invoke": "Skill(skill='commit')",
        "note": "Always prefer this over bash git commit — handles edge cases, hook failures, signing correctly.",
    },
    {
        "skill": "review-pr",
        "trigger": "user asks to review a PR, /review-pr, or 'look at PR #N'",
        "description": "Fetches PR diff from GitHub and writes structured review feedback.",
        "invoke": "Skill(skill='review-pr', args='123')",
        "note": "Pass PR number as args. Uses gh CLI under the hood.",
    },
    {
        "skill": "simplify",
        "trigger": "after writing code, user asks to review quality, simplify, or check the diff",
        "description": "Reviews changed code for over-engineering, reuse opportunities, and efficiency. Fixes issues.",
        "invoke": "Skill(skill='simplify')",
        "note": "Run after significant code changes to catch premature abstractions and dead code.",
    },
    {
        "skill": "loop",
        "trigger": "user wants something to run repeatedly, on a schedule, or uses /loop",
        "description": "Runs a prompt or slash command on a recurring interval (default: 10m).",
        "invoke": "Skill(skill='loop', args='5m /my-command')",
        "note": "Use for polling, monitoring, or recurring workflows. Not for one-off tasks.",
    },
    {
        "skill": "claude-api",
        "trigger": "code imports anthropic / @anthropic-ai/sdk / claude_agent_sdk, or user asks to use Claude API",
        "description": "Build apps with the Claude API or Anthropic SDK. Provides API usage patterns.",
        "invoke": "Skill(skill='claude-api')",
        "note": "Trigger on import detection. Do NOT trigger for general AI/ML discussions.",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# BUILT-IN TOOL GUIDANCE
# Claude Code native tools — when to use each vs. the MCP alternatives
# ─────────────────────────────────────────────────────────────────────────────

BUILTIN_TOOLS: list[dict] = [
    {
        "tool": "Read",
        "best_for": "Non-code files (config, markdown, JSON, .env); small files < 50 lines",
        "prefer_mcp": "graph_read(file::symbol) for any code file in the project",
        "tip": "Use offset+limit to read only a section. Always Read before Write on existing files.",
    },
    {
        "tool": "Edit",
        "best_for": "Targeted string replacement in existing files",
        "prefer_mcp": "replace_symbol_body(symbol, new_body) [serena] for full function/class rewrites — more precise",
        "tip": "Edit requires unique old_string. For symbol-level edits, serena is more reliable.",
    },
    {
        "tool": "Write",
        "best_for": "Creating new files from scratch",
        "prefer_mcp": "N/A — Write is the right tool for new files",
        "tip": "Never use Write on existing files without Reading first — it overwrites silently.",
    },
    {
        "tool": "Grep",
        "best_for": "Content search when graph/serena tools are not sufficient",
        "prefer_mcp": "fallback_rg [dual-graph] or search_for_pattern [serena] for project code",
        "tip": "Use output_mode='files_with_matches' first to find candidates, then content for specific files.",
    },
    {
        "tool": "Glob",
        "best_for": "Finding files by name pattern",
        "prefer_mcp": "find_file(name) [serena] for project files; Glob for external path patterns",
        "tip": "More specific patterns are faster. Avoid /**/* without a suffix.",
    },
    {
        "tool": "Bash",
        "best_for": "Shell commands with no dedicated tool: git, npm, python, build tools",
        "prefer_mcp": "Everything else — Bash is last resort for file operations",
        "tip": "Never use bash for file reading, searching, or editing. Use dedicated tools.",
    },
    {
        "tool": "Agent",
        "best_for": "Long multi-step research that would pollute main context window",
        "prefer_mcp": "afe_compile first for complex agents; use subagent_type='Explore' for research",
        "tip": "Use isolation='worktree' for agents that write files. Background agents for parallel work.",
    },
]


def format_substitutions_brief() -> str:
    """Compact substitution table for ledger_context output."""
    lines = []
    for s in TOOL_SUBSTITUTIONS:
        lines.append(f"  ✗ {s['avoid']}")
        lines.append(f"  ✓ {s['use_instead']}")
        lines.append("")
    return "\n".join(lines)


def format_gates_brief() -> str:
    """Compact mandatory gates for ledger_context output."""
    lines = []
    for g in MANDATORY_GATES:
        lines.append(f"  before {g['before'].lower()}")
        lines.append(f"    → {g['call']}")
    return "\n".join(lines)


def match_chain(task: str) -> list[tuple[str, dict]]:
    """Find PRIORITY_CHAINS whose trigger_words match the task description.

    Returns list of (chain_key, chain_dict) sorted by match count descending.
    """
    task_lower = task.lower()
    task_tokens = set(task_lower.split())
    scored: list[tuple[int, str, dict]] = []

    for key, chain in PRIORITY_CHAINS.items():
        triggers = chain.get("trigger_words", [])
        score = sum(1 for t in triggers if t in task_lower or t in task_tokens)
        if score > 0:
            scored.append((score, key, chain))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [(key, chain) for _, key, chain in scored]
