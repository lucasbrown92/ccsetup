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
        "use_instead": "fallback_rg(pattern) [dual-graph] or search_for_pattern(pattern) [serena]",
        "why": "Graph and serena tools have project context. Bash grep runs blind. fallback_rg respects the per-turn cap enforced by graph_continue.",
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
        "why": "graph_read(file::symbol) uses O(1) symbol-index lookup — 5-20x cheaper than full file reads. A 400-line file has ~380 lines you don't need.",
        "exception": "Non-code files (config, markdown, JSON), or files under ~50 lines.",
    },
    {
        "avoid": "Calling graph_retrieve directly",
        "use_instead": "graph_continue(query) — always",
        "why": "graph_continue has the memory-first routing layer on top of graph_retrieve. Calling graph_retrieve directly skips action-graph memory and reuse-gate logic, defeating the whole dual-graph system.",
        "exception": "None — graph_retrieve is an internal backend call. Always use graph_continue.",
    },
    {
        "avoid": "Exploring files without calling graph_continue first",
        "use_instead": "graph_continue(query) → read recommended_files via graph_read — one call per file",
        "why": "graph_continue returns pre-ranked recommended_files and enforces per-turn read budgets. Skipping it causes duplicate work and blows the token budget.",
        "exception": "graph_continue returns skip=true (project < 5 files).",
    },
    {
        "avoid": "Using training knowledge for external library APIs",
        "use_instead": "context7: resolve-library-id('name') then get-library-docs(id, topic='specific topic')",
        "why": "Training knowledge is stale and may describe old API versions. context7 fetches the actual current docs. The topic= param is critical — be specific.",
        "exception": "Library is not indexed in context7 (fallback to training with a caveat).",
    },
    {
        "avoid": "Internal reasoning only for multi-turn debugging",
        "use_instead": "mind_open + mind_add(type, content) to externalize hypotheses, facts, assumptions, next steps",
        "why": "Context compaction destroys internal reasoning silently. mind_summary() recovers full state in ≤15 lines. Use 'assumption' for things you're already building on (high risk), 'hypothesis' for what you're testing.",
        "exception": "Single-turn tasks where continuity across compaction doesn't matter.",
    },
    {
        "avoid": "Reading source code to start debugging a failure",
        "use_instead": "witness_runs() + witness_hotspots() first — see what actually ran, then read targeted code",
        "why": "Source tells you what should happen; witness tells you what did happen. Execution memory shows exact call stack, args, and locals. Source reading without it is hypothesis without evidence.",
        "exception": "No witness runs exist yet — run: pytest --witness to capture first.",
    },
    {
        "avoid": "Making structural changes without calling charter_check",
        "use_instead": "charter_check('one-sentence description of change') before touching code",
        "why": "charter.json holds invariants the project has declared. One call surfaces conflicts before they cause damage. CONFLICT returns specific entry IDs to surface to user.",
        "exception": "No .claude/charter.json yet — seed it first with charter_add.",
    },
    {
        "avoid": "Skipping graph_register_edit after editing files",
        "use_instead": "graph_register_edit(files=['path/to/file'], summary='what changed and why') after every edit",
        "why": "Without graph_register_edit, the retrieval cache stays stale and memory-first routing won't fire on subsequent turns. Also anchors symbol hashes for staleness detection.",
        "exception": "None — always call graph_register_edit after any file edit or code change.",
    },
    {
        "avoid": "Spawning Agent tool with an ad-hoc system prompt",
        "use_instead": "afe_compile(task) first, then inject spec's system_prompt_fragment when spawning Agent",
        "why": "Ad-hoc prompts produce inconsistent agents. afe_compile compiles posture from your actual state (mind/charter/witness).",
        "exception": "Trivially simple agent tasks with a single clear action.",
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
    {
        "avoid": "Using find_symbol with include_body=True immediately on a class",
        "use_instead": "find_symbol(name, depth=1, include_body=False) to see class structure, then include_body=True on specific methods only",
        "why": "depth=1 + include_body=False returns all method names and signatures without bodies — cheap. Only read bodies of methods you actually need.",
        "exception": "Small classes under ~30 lines where structure is obvious.",
    },
    {
        "avoid": "context7: vague topic= queries like 'how to use'",
        "use_instead": "context7: get-library-docs(id, topic='specific feature name, e.g. middleware configuration')",
        "why": "Vague topics return poorly targeted docs. Specific topic strings match the library's own documentation sections.",
        "exception": "You want the full library overview — omit topic= entirely.",
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
        "returns": "recommended_files: list of {file, access_type}; confidence: high/medium/low; max_supplementary_greps; max_supplementary_files. needs_project=true if graph not yet built.",
        "then": "If needs_project=true → graph_scan(project_root=pwd) — use pwd directly, do NOT ask user. Then graph_continue again. Read recommended_files via graph_read (parallel, one call per file). Stop at confidence=high — do NOT grep.",
        "skip_if": "graph_continue returns skip=true (project < 5 files) — ask user what to work on or read specific named files",
    },
    {
        "before": "Any file edit, code change, or write operation",
        "call": "graph_register_edit(files=['path'], summary='what changed and why')",
        "returns": "Acknowledgement; invalidates retrieval cache; updates action graph memory",
        "then": "Proceed. On next turn, graph_continue will route via memory-first (confidence=high, 0 greps needed).",
        "skip_if": "Never skip — stale cache breaks memory-first routing on subsequent turns.",
    },
    {
        "before": "Any structural change: rename, refactor, delete, move, change interface/contract",
        "call": "charter_check('one-sentence description of the change', change_type='refactor|add_dependency|remove_feature|change_interface')",
        "returns": "CLEAR or CONFLICT with specific entry IDs",
        "then": "CLEAR → proceed. CONFLICT → surface specific entry IDs to user before touching code. change_type boosts relevant entry types 2x — always pass it for sharper detection.",
        "skip_if": ".claude/charter.json does not exist yet — seed it first with charter_add",
    },
    {
        "before": "Starting to debug a test failure or runtime exception",
        "call": "witness_runs(limit=5) + witness_hotspots()",
        "returns": "Recent run IDs, pass/fail status, timestamps; hotspots = most-failing functions",
        "then": "witness_traces('fn_name', status='exception') → witness_exception('ErrorType') → witness_coverage_gaps('file.py')",
        "skip_if": "No witness runs exist — run: pytest --witness to capture first",
    },
    {
        "before": "Spawning the Agent tool for any complex task",
        "call": "afe_compile(task='description of what the agent should do')",
        "returns": "Compiled spec with system_prompt_fragment ready to inject",
        "then": "Use spec.system_prompt_fragment as the agent's system prompt.",
        "skip_if": "Task is a single trivial action (e.g., 'list files')",
    },
    {
        "before": "Structural changes (when mind + witness state exists)",
        "call": "ledger_preflight(change, files)",
        "returns": "CLEAR / CAUTION / BLOCKED with charter conflicts, mind assumptions, witness exceptions",
        "then": "CLEAR → proceed. CAUTION → review warnings. BLOCKED → resolve charter conflicts first.",
        "skip_if": "No .claude/ stores exist yet — fall back to charter_check alone",
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
            "1. graph_continue(query)                              → get recommended_files first (MANDATORY)",
            "2. graph_read(file::symbol)                          → cheapest: O(1) symbol-index lookup",
            "3. get_symbols_overview(relative_path)               → file structure before reading bodies",
            "4. find_symbol('ClassName/method', depth=1,          → class members without bodies",
            "              include_body=False)                     (name_path: 'Class/method' or 'fn_name')",
            "5. find_symbol('ClassName/method', include_body=True) → body of specific method only",
            "6. find_referencing_symbols(name, relative_path)     → callers/usages when needed",
        ],
        "avoid": "Read(full_file) — reads entire file when you need 1 function. find_symbol with include_body=True on a class before checking structure.",
        "parallel_tip": "Steps 2+3+4 can run in parallel if you know the file. graph_read reads in parallel for all recommended_files.",
    },
    "file_context": {
        "goal": "Find relevant files for a task without knowing where to look",
        "trigger_words": ["explore", "understand", "codebase", "context", "relevant", "related", "what files", "where is"],
        "chain": [
            "1. graph_continue(query)                              → MANDATORY — recommended_files: [{file, access_type}] + confidence",
            "   access_type='write' = previously edited; 'read' = previously read; 'new' = first time",
            "2. graph_read(entry['file']) for each recommended_file → parallel, one call per file",
            "3. fallback_rg(pattern) ONLY if confidence < high    → capped by max_supplementary_greps (hard limit)",
            "4. graph_read(additional_files) up to max_supplementary_files → then stop — never exceed caps",
        ],
        "avoid": "Reading files without graph_continue — wastes tokens on wrong files. Calling graph_retrieve directly (skips memory-first layer). Exceeding max_supplementary_greps or max_supplementary_files caps.",
        "parallel_tip": "All graph_read calls from recommended_files can run in parallel",
    },
    "debugging": {
        "goal": "Understand a test failure or runtime error",
        "trigger_words": ["debug", "failing", "fail", "error", "exception", "crash", "broken", "wrong", "test", "pytest", "traceback", "runtime"],
        "chain": [
            "1. witness_runs(limit=5)                             → recent run history (run pytest --witness first if none)",
            "2. witness_hotspots(run_count=5)                     → functions with most exceptions — prioritize here",
            "3. witness_traces('fn_name', status='exception')     → exact calls that raised",
            "4. witness_exception('ErrorType')                    → locals at crash site",
            "5. witness_coverage_gaps('file.py')                  → if coverage is the gap",
            "6. mind_open('title') + mind_add('assumption', ...) → externalize reasoning for multi-turn",
            "7. mind_import_witness('fn_name')                    → import execution data as FACT node",
        ],
        "avoid": "Reading source code before checking execution evidence. Scanning all runs manually instead of witness_hotspots first.",
        "parallel_tip": "Steps 1+2 can run in parallel (independent). Steps 3+4 can run in parallel if you know both the fn_name and error type.",
    },
    "after_edit": {
        "goal": "Maintain graph memory integrity after any file edit",
        "trigger_words": ["edit", "wrote", "changed", "modified", "saved", "updated", "fixed", "refactored"],
        "chain": [
            "1. graph_register_edit(['file.py'], summary='what changed and why') → MANDATORY after every edit",
            "   Use file::symbol notation when edit targets a specific function:   → e.g. 'src/auth.py::login'",
            "   If graph_state='primed' returned: first-ever edit, memory routing now active from here",
            "2. On next turn: graph_continue will route via memory-first           → confidence=high, 0 greps needed",
        ],
        "avoid": "Skipping graph_register_edit — leaves retrieval cache stale, breaks memory-first routing on all subsequent turns. Also: graph_scan wipes all state (action graph, cache, turns) — only call on new projects.",
        "parallel_tip": "N/A — call immediately after each edit",
    },
    "investigation": {
        "goal": "Track multi-turn debugging or research across compaction",
        "trigger_words": ["investigate", "track", "hypothesis", "theory", "session", "multi-session", "remember", "resume"],
        "chain": [
            "0. mind_recall('keywords from the issue')        → check if similar issue was solved before",
            "1. mind_summary()                                    → if session continues (resume state) — FIRST call",
            "   OR mind_open('title')                             → if starting fresh",
            "2. mind_add('assumption', '...')                     → externalize unverified beliefs first (highest risk)",
            "3. mind_add('hypothesis', '...', confidence=0.7)    → candidate explanations to test",
            "4. mind_add('next_step', '...')                     → queue concrete actions",
            "5. mind_update(node_id, 'confirmed/refuted', notes) → after evidence from witness/test",
            "6. mind_import_witness('fn_name')                   → import execution data as FACT node",
            "7. mind_resolve('conclusion', node_ids=[...])       → close investigation",
        ],
        "avoid": "Internal reasoning for anything that spans turns — compaction will destroy it. Confusing assumption (what you're building on) with hypothesis (what you're testing).",
        "parallel_tip": "mind_summary + charter_summary + graph_continue can run in parallel at session start",
    },
    "structural_change": {
        "goal": "Refactor, rename, delete, move, or change an interface",
        "trigger_words": ["refactor", "rename", "delete", "remove", "move", "change", "restructure", "redesign"],
        "chain": [
            "1. ledger_preflight('description', files=['...'])  → MANDATORY gate — BLOCKED returns charter conflicts + risks",
            "   OR: charter_check('description', change_type='refactor|add_dependency|remove_feature|change_interface')",
            "   change_type boosts relevant entry types 2x — always pass it for sharper conflict detection",
            "2. If CLEAR → proceed with implementation",
            "3. rename_symbol(name_path, relative_path, new_name) [serena] → renames all references safely",
            "4. replace_symbol_body(name_path, relative_path, body) [serena] → full function rewrites",
            "5. graph_register_edit(files, summary=...)          → MANDATORY after edit",
            "6. mind_add('decision', 'change made because...') if investigation active",
        ],
        "avoid": "Making changes before charter_check — surfaces invariant violations early. Skipping graph_register_edit after edits. Calling charter_check without change_type — misses 2x score boost.",
        "parallel_tip": "None — charter_check must complete before any edits",
    },
    "library_api": {
        "goal": "Use an external library or framework correctly",
        "trigger_words": ["library", "docs", "documentation", "api", "framework", "how to use", "package", "import", "sdk"],
        "chain": [
            "1. resolve-library-id('library-name')               → context7: get the stable library ID",
            "2. get-library-docs(id, topic='specific topic')     → context7: fetch actual current docs",
            "   topic= must be specific: 'middleware setup' not 'how to use'",
        ],
        "avoid": "Training knowledge for library APIs — stale, may describe wrong version. Vague topic= strings that return unfocused docs.",
        "parallel_tip": "N/A — step 2 requires step 1's output (unless you already know the library ID format: /org/repo)",
    },
    "agent_spawn": {
        "goal": "Spawn an Agent tool for complex multi-step work",
        "trigger_words": ["agent", "spawn", "subagent", "delegate", "complex", "multi-step", "orchestrate"],
        "chain": [
            "1. afe_context()                                    → read current mind/charter/witness state",
            "2. afe_compile(task='description')                  → compile agent spec",
            "3. afe_validate(spec_id)                            → check against charter constraints",
            "4. Agent(subagent_type=..., prompt=spec.system_prompt_fragment + task details)",
        ],
        "avoid": "Agent tool with ad-hoc prompt — produces inconsistent cognitive posture",
        "parallel_tip": "N/A — sequence is linear",
    },
    "visual_ui": {
        "goal": "Verify or debug a rendered UI",
        "trigger_words": ["screenshot", "visual", "ui", "browser", "render", "looks", "css", "layout", "regression", "baseline", "click", "interact"],
        "chain": [
            "1. retina_capture(url)                              → screenshot → returns PNG file path",
            "2. Read(file_path=capture.file)                     → view the PNG (required — capture returns path, not image)",
            "3. retina_inspect(url)                              → accessibility/ARIA tree for structure",
            "4. retina_console(url)                              → JS errors during load",
            "5. <make changes>",
            "6. graph_register_edit(files, summary=...)          → update graph after UI changes",
            "7. retina_diff(id_before, id_after)                 → verify change was correct",
        ],
        "avoid": "Inferring appearance from HTML/CSS source — Claude cannot see rendered output. Forgetting to Read() the PNG path returned by retina_capture.",
        "parallel_tip": "Steps 1+3+4 can run in parallel (all read the same URL independently)",
    },
    "visual_regression": {
        "goal": "Guard against visual regressions with saved baselines",
        "trigger_words": ["baseline", "regression", "pixel", "visual test", "retina_baseline", "retina_regress"],
        "chain": [
            "1. retina_baseline('name', url)                     → save baseline BEFORE making changes",
            "2. <implement changes>",
            "3. retina_regress('name')                           → PASS/FAIL + diff image path",
            "4. If FAIL: Read(diff_file)                         → inspect changed regions (red-highlighted)",
        ],
        "avoid": "Calling retina_capture before retina_baseline — baseline must exist before making changes.",
        "parallel_tip": "N/A — baseline must precede changes",
    },
    "code_graph": {
        "goal": "Trace call chains, find callers/callees, or analyze change impact across files",
        "trigger_words": ["callers", "callees", "call graph", "impact", "who calls", "dependency", "call chain", "dead code"],
        "chain": [
            "1. get_repository_status() [codegraphcontext]       → confirm index is current",
            "   If not indexed: index_codebase(path='.') first   → may take time for large repos",
            "2. get_callers('fn_name')                           → who calls this function",
            "3. get_callees('fn_name')                           → what this function calls",
            "4. get_impact('symbol_or_file')                     → downstream dependencies before a change",
            "   OR: find_referencing_symbols [serena]            → faster for single-hop LSP-backed usages",
        ],
        "avoid": "Assuming find_referencing_symbols (Serena) covers deep call chains — it's single-hop LSP. Use codegraphcontext for multi-hop graph traversal.",
        "parallel_tip": "get_callers + get_callees can run in parallel (independent queries)",
    },
    "semantic_search": {
        "goal": "Find code by concept or meaning when you don't know the symbol name",
        "trigger_words": ["semantic", "meaning", "concept", "similar", "like", "kind of", "sort of", "find code that"],
        "chain": [
            "1. leann_search('what you're looking for conceptually') → ranked code chunks by meaning",
            "   If no results: leann_index() first               → rebuild index (needed after large changes)",
            "2. graph_read(file::symbol) on top results          → read the relevant symbols",
        ],
        "avoid": "Keyword grep when you don't know the exact function name — LEANN finds by meaning.",
        "parallel_tip": "N/A — step 2 uses step 1's results",
    },
    "git_commit": {
        "goal": "Commit code changes",
        "trigger_words": ["commit", "git commit", "save changes", "check in"],
        "chain": [
            "1. Skill(skill='commit')                            → /commit handles everything correctly",
            "   (stages files, conventional message, pre-commit hooks, co-author line)",
        ],
        "avoid": "bash git commit — /commit handles edge cases that raw git misses",
        "parallel_tip": "N/A",
    },
    "pr_review": {
        "goal": "Review a pull request",
        "trigger_words": ["review", "pr", "pull request", "diff", "changes"],
        "chain": [
            "1. Skill(skill='review-pr', args='PR_NUMBER')       → /review-pr fetches and reviews",
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
    "graph_read(file::symbol) reads only that function — 5-20x cheaper than Read(full_file) via O(1) symbol-index lookup",
    "get_symbols_overview before any Read — understand structure, then read only the methods you need",
    "graph_continue recommended_files are pre-ranked — trust the ranking, read them in parallel",
    "Stop at confidence=high from graph_continue — do NOT grep further, caps are hard limits",
    "graph_register_edit after every edit — without it, memory-first routing fails on the next turn",
    "find_symbol(name, depth=1, include_body=False) → class structure without bodies; only request include_body=True for specific methods",
    "mind_summary() recovers full investigation state in ≤15 lines after compaction — call it FIRST",
    "charter_check(change, change_type='refactor|add_dependency|...') — change_type boosts relevant entry types 2x; omitting it halves conflict detection sensitivity",
    "charter_summary() in 1 call — do not read charter entries one by one",
    "witness_hotspots() prioritizes where to look — don't scan all runs manually",
    "Batch independent tool calls in parallel in a single response — halves round-trips",
    "count_tokens(text=...) before reading any file you suspect is large — exact count via API",
    "ledger_query('task description') → get concrete call sequence before starting any work",
    "context7: topic= must be specific ('middleware configuration' not 'how to use') — saves one round-trip",
    "leann_search over keyword grep when you don't know the symbol name — finds by meaning",
    "ledger_mode('economy') → set before token-sensitive sessions; ledger_mode('performance') for Max-plan thoroughness",
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
        "best_for": "Non-code files (config, markdown, JSON, .env); small files < 50 lines; viewing PNG files from retina_capture",
        "prefer_mcp": "graph_read(file::symbol) for any code file in the project — 5-20x cheaper",
        "tip": "Use offset+limit to read only a section. Always Read before Write on existing files. After retina_capture, you MUST Read the returned PNG path to see it.",
    },
    {
        "tool": "Edit",
        "best_for": "Targeted string replacement in existing files (a few lines within a large function)",
        "prefer_mcp": "replace_symbol_body(name_path, relative_path, body) [serena] for full function/class rewrites — more precise and safe",
        "tip": "Edit requires unique old_string. For symbol-level edits, serena is more reliable. Use for small intra-symbol changes where replace_symbol_body would be overkill.",
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
        "prefer_mcp": "fallback_rg [dual-graph] (respects turn budget) or search_for_pattern [serena] for project code",
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
        "best_for": "Shell commands with no dedicated tool: git, npm, python, build tools, pytest",
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


def match_chain(task: str, mode: str = "balanced") -> list[tuple[str, dict]]:
    """Find PRIORITY_CHAINS whose trigger_words match the task description.

    Returns list of (chain_key, chain_dict) sorted by match count descending.
    Applies MODE_PROFILES[mode] limits: chain_limit and chain_truncate.
    """
    profile = MODE_PROFILES.get(mode, MODE_PROFILES["balanced"])
    task_lower = task.lower()
    task_tokens = set(task_lower.split())
    scored: list[tuple[int, str, dict]] = []

    for key, chain in PRIORITY_CHAINS.items():
        triggers = chain.get("trigger_words", [])
        score = sum(1 for t in triggers if t in task_lower or t in task_tokens)
        if score > 0:
            scored.append((score, key, chain))

    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    chain_truncate = profile.get("chain_truncate")
    for _, key, chain in scored[: profile["chain_limit"]]:
        if chain_truncate is not None:
            chain = dict(chain)
            chain["chain"] = chain["chain"][:chain_truncate]
        results.append((key, chain))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# MODE PROFILES
# Token priority modes — set via ledger_mode(mode)
# ─────────────────────────────────────────────────────────────────────────────

MODE_PROFILES: dict[str, dict] = {
    "economy": {
        "description": "Minimal token spend — single best tool path, no exploration",
        "label": "ECONOMY",
        "chain_limit": 1,
        "chain_truncate": 4,
        "route_min_score": 0.15,
        "route_max": 2,
        "route_weight_mul": 0.80,
        "anti_penalty_mul": 1.5,
        "show_parallel_tips": False,
        "show_alt_chains": False,
        "show_skills": False,
        "show_not_configured": False,
        "context_rec_limit": 2,
    },
    "balanced": {
        "description": "Default — balanced capability and token cost",
        "label": "BALANCED",
        "chain_limit": 2,
        "chain_truncate": None,
        "route_min_score": 0.10,
        "route_max": 4,
        "route_weight_mul": 1.0,
        "anti_penalty_mul": 1.0,
        "show_parallel_tips": True,
        "show_alt_chains": True,
        "show_skills": True,
        "show_not_configured": True,
        "context_rec_limit": 4,
    },
    "performance": {
        "description": "Comprehensive — invest tokens in thorough tool activation",
        "label": "PERFORMANCE",
        "chain_limit": 3,
        "chain_truncate": None,
        "route_min_score": 0.08,
        "route_max": 6,
        "route_weight_mul": 1.20,
        "anti_penalty_mul": 0.5,
        "show_parallel_tips": True,
        "show_alt_chains": True,
        "show_skills": True,
        "show_not_configured": True,
        "context_rec_limit": 6,
    },
}
