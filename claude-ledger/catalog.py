#!/usr/bin/env python3
"""claude-ledger catalog — embedded tool catalog for all ccsetup-managed MCP servers.

This is a copy of _TOOL_CATALOG from ccsetup.py, kept in sync at install time.
Includes entries for claude-retina and claude-ledger itself (10 tools).

Each entry: (tool_name, params_summary, when_to_use)
"""

# Full catalog: mcp_key -> list of (name, params, when_to_use)
TOOL_CATALOG: dict[str, list[tuple[str, str, str]]] = {
    "serena": [
        ("get_symbols_overview",      "relative_path, depth?",
         "Get file structure: all symbol names + kinds. Do this before reading bodies. depth=0 top-level only."),
        ("find_symbol",               "name_path_pattern, depth?, include_body?, relative_path?, substring_matching?",
         "Find a symbol by name. name_path='ClassName/method_name'. depth=1 shows children. include_body=False is cheap."),
        ("find_referencing_symbols",  "name_path, relative_path, include_kinds?",
         "Get callers/usages of a symbol — LSP-backed, single-hop. Pass both name_path and relative_path."),
        ("replace_symbol_body",       "name_path, relative_path, body",
         "Replace an entire function/method/class body. More reliable than Edit for full rewrites."),
        ("insert_after_symbol",       "name_path, relative_path, body",
         "Add code after an existing symbol (e.g., add a new method after the last method in a class)."),
        ("insert_before_symbol",      "name_path, relative_path, body",
         "Add code before an existing symbol (e.g., add a new import before the first function)."),
        ("rename_symbol",             "name_path, relative_path, new_name",
         "Rename a symbol across ALL references in the project — safe, LSP-backed."),
        ("search_for_pattern",        "substring_pattern, relative_path?, paths_include_glob?, context_lines_before?, context_lines_after?",
         "Regex search when symbol name is unknown. Restrict with relative_path= or paths_include_glob=."),
        ("list_dir",                  "relative_path, recursive?",
         "Directory listing within project. Use find_file for searching by filename."),
        ("find_file",                 "file_mask, relative_path?",
         "Search for file by name or glob mask. Faster than list_dir for file discovery."),
    ],
    "dual-graph": [
        ("graph_continue",       "query, top_files?, top_edges?, limit?",
         "MANDATORY first call every turn. Returns: recommended_files (list of {file, access_type}), confidence (high/medium/low), max_supplementary_greps, max_supplementary_files. needs_project=true → call graph_scan(pwd). skip=true → project < 5 files."),
        ("graph_read",           "file, max_chars?, query?, anchor?",
         "Read one file or file::symbol (e.g. 'src/auth.py::login'). O(1) symbol-index lookup — 5-20x cheaper. Returns stale=true if symbol changed since last scan. Respects per-turn read budget (18K chars)."),
        ("graph_scan",           "project_root",
         "Build/rebuild graph index from absolute path. Wipes all state (action graph, retrieval cache, turn state). Call when graph_continue returns needs_project=true — use pwd, do NOT ask user first."),
        ("graph_register_edit",  "files, summary?",
         "MANDATORY after every edit. Invalidates retrieval cache, records decision/edit_observation in context-store, increments edited_count. Use file::symbol notation when edit targets specific function. Returns graph_state='primed' on first-ever edit."),
        ("graph_retrieve",       "query, top_files?, top_edges?",
         "Raw backend retrieval — returns ranked graph_files list with scores. DO NOT call directly; graph_continue has memory-first routing layer on top. Only use for custom top_files/top_edges values."),
        ("graph_neighbors",      "file, limit?",
         "Get all graph edges touching a file. Returns neighbor files in the dependency graph."),
        ("graph_impact",         "changed_files",
         "Cross-file impact analysis — returns connected_files and untouched_connected_files affected by edits to changed_files list."),
        ("graph_action_summary", "query?, limit?",
         "Recent action graph summary: recent_actions, relevant_files, decisions log (last 20 edits), memories. Use for session recovery and debugging what was touched."),
        ("fallback_rg",          "pattern, max_hits?",
         "Controlled ripgrep fallback. Only call when confidence < high, up to max_supplementary_greps times per turn. Hard-blocked after FALLBACK_MAX_CALLS_PER_TURN (default 1). Returns hits[] with file/line/text."),
    ],
    "claude-mind": [
        ("mind_open",           "title",
         "Start or resume an investigation. Only one investigation is active at a time. Old ones archive automatically."),
        ("mind_add",            "type, content, confidence?, files?, evidence_ids?, depends_on?",
         "Add a reasoning node. type: assumption (high-risk, unverified), hypothesis (being tested), fact (confirmed), question, ruled_out, next_step. Add assumptions FIRST."),
        ("mind_update",         "node_id, status, notes?",
         "Confirm or refute a hypothesis/assumption after gathering evidence. status: confirmed, refuted, suspended, escalated."),
        ("mind_query",          "filter",
         "Query nodes by type (hypothesis, assumptions, facts), status (open, confirmed), or free text. Use 'all' for everything."),
        ("mind_summary",        "(none)",
         "FIRST call after context compaction. Recovers full investigation state in ≤15 lines. Never guess — always call this first."),
        ("mind_resolve",        "conclusion, node_ids?",
         "Close investigation with a conclusion. Optionally list node_ids that led to the conclusion."),
        ("mind_import_witness",  "fn_name, run_id?",
         "Import witness execution data as a FACT node. Links execution evidence directly into reasoning graph."),
        ("mind_graph",          "(none)",
         "Visualize the reasoning chain: nodes, dependencies, assumption→hypothesis→evidence chains."),
        ("mind_recall",         "query, limit?, node_types?",
         "Search archived investigations for similar past work. Use at investigation start to check if similar issue was solved before."),
        ("mind_sweep",          "(none)",
         "Risk detection: stale assumptions (>2h), high-risk (many dependents), overdue next steps (>1h). Run periodically."),
        ("mind_replay",         "investigation_id?",
         "Investigation strategy timeline — shows how reasoning progressed. Use to understand playbooks for similar problems."),
        ("mind_export_watch",   "assumption_ids?",
         "Generate structured watch list from assumptions/hypotheses to guide witness_traces calls after next test run."),
    ],
    "claude-charter": [
        ("charter_add",     "type, content, notes?, scope?, expires_at?, deadline?",
         "Record an invariant/constraint/non_goal/contract/goal. expires_at= for time-bounded entries (ISO datetime); deadline= to flag goal/contract when date passes."),
        ("charter_update",  "id, status?, content?, notes?",
         "Modify or archive an entry. status: active, archived. ID format: 'aaa00001'."),
        ("charter_query",   "filter",
         "Review entries by type, keyword, or 'all'. Returns entry IDs needed for charter_check responses."),
        ("charter_summary", "(none)",
         "Full project constitution overview. Call at session start to load project constraints."),
        ("charter_check",   "change_description, file_path?, change_type?",
         "MANDATORY before any structural change. change_type: add_dependency|remove_feature|change_interface|refactor|general — boosts relevant entry types 2x for sharper conflict detection. Returns CLEAR or CONFLICT."),
        ("charter_audit",   "(none)",
         "Charter health report: gaps, imbalances, prohibited patterns, and temporal section (expired entries + past-deadline goals). Run periodically."),
    ],
    "claude-witness": [
        ("witness_runs",          "limit?",
         "List recent test runs with pass/fail status and timestamps. First call in any debugging session."),
        ("witness_hotspots",      "limit?, run_count?",
         "Functions with the most exceptions across recent runs. Call BEFORE witness_traces — tells you where to focus."),
        ("witness_traces",        "fn_name, run_id?, status?",
         "All calls to a function in a run. status='exception' for only failing calls. Includes args and return values."),
        ("witness_exception",     "exc_type, run_id?",
         "Exception details with full local variable state at crash site. Most useful for understanding root cause."),
        ("witness_coverage_gaps", "file",
         "Find untested code paths in a file. Use when tests pass but behavior is wrong."),
        ("witness_diff",          "run_a, run_b",
         "Compare two test runs — what functions changed behavior between them."),
        ("witness_check_charter", "run_id?",
         "Cross-check execution against charter entries — did the run violate any declared invariants?"),
    ],
    "leann-server": [
        ("leann_search",   "query, limit?",
         "Semantic code search — find by meaning/concept when you don't know the symbol name. Returns ranked code chunks."),
        ("leann_index",    "directory?",
         "Build or refresh the local AST-aware search index. Required before first search and after large codebase changes."),
    ],
    "context7": [
        ("resolve-library-id", "libraryName",
         "Fuzzy-match library name to stable context7 ID ('/org/repo' format). Use when unsure of exact ID."),
        ("get-library-docs",   "context7CompatibleLibraryID, topic?",
         "Fetch live library documentation. topic= must be SPECIFIC ('middleware configuration', not 'how to use'). Skip resolve step if you know the ID."),
    ],
    "claude-session": [
        ("save_current_session",  "(none)",
         "Archive the active session (full conversation history, tool results, todos). Do before risky work."),
        ("clone_session",         "session_id?",
         "Duplicate current or specified session for parallel investigation branches."),
        ("restore_session",       "archive",
         "Import session from archive with a new session ID. Requires sessionCleanup.enabled=false in settings."),
        ("delete_session",        "session_id",
         "Remove session with safety confirmation. Native sessions require --force CLI flag."),
        ("move_session",          "session_id, project",
         "Relocate a session between projects."),
        ("session_lineage",       "session_id",
         "View ancestry and parent-child relationships of cloned/restored sessions."),
    ],
    "context-mode": [
        ("context_status", "(none)",
         "Check what's currently virtualized vs. in active context window."),
        ("context_search", "query",
         "Search across virtualized tool outputs (large file reads, fetched docs, search results)."),
    ],
    "seu-claude": [
        ("memory_store",       "key, value",          "Persist data across sessions by key."),
        ("memory_recall",      "key",                  "Retrieve persisted data by key."),
        ("task_create",        "title, description?",  "Create a tracked task surviving crashes."),
        ("task_list",          "status?",              "List tracked tasks, optionally filtered by status."),
        ("analyze_dependency",  "file",                "Find imports, exports, and circular dependencies for a file."),
        ("validate_code",       "file",                "Run ESLint + TypeScript checks before committing."),
        ("execute_sandbox",     "command",             "Run a command in an isolated sandbox environment."),
        ("orchestrate_agents",  "task, agents?",       "Multi-agent coordination (Coder, Reviewer, Tester roles)."),
    ],
    "codegraphcontext": [
        ("index_codebase",         "path, watch?",
         "Build the call-graph index. Required before other tools. watch=True enables live updates. Poll get_repository_status() for completion."),
        ("get_callers",            "function_name, limit?",
         "Find all callers of a function — multi-hop graph traversal (deeper than Serena find_referencing_symbols)."),
        ("get_callees",            "function_name, limit?",
         "Find all functions called by a function — full call tree."),
        ("get_impact",             "symbol_name",
         "Cross-file change impact: everything downstream of this symbol. Use before refactoring."),
        ("search_symbols",         "pattern, language?",
         "Find symbols by name pattern, optionally filtered by language."),
        ("get_repository_status",  "(none)",
         "Confirm index is current before making graph queries. Check if indexing job is complete."),
        ("analyze_complexity",     "threshold?",
         "Find high-complexity functions above threshold. Useful for refactor targeting."),
        ("find_dead_code",         "repository?",
         "Detect unreferenced functions and dead code across the repository."),
    ],
    "token-counter": [
        ("count_tokens",       "text?, messages?, system?, model?",
         "Exact token count via Anthropic API. Use 'text' for single string; 'messages' for full conversation. Call BEFORE reading large files."),
        ("get_session_stats",  "(none)",
         "Running session cost dashboard — cumulative input/output tokens and USD cost."),
        ("log_usage",          "input_tokens, output_tokens, cache_read_tokens?, cache_write_tokens?, description?, model?, project?",
         "Record actual API usage for cost tracking. input/output_tokens come from the API response usage object, not count_tokens."),
        ("estimate_cost",      "input_tokens, output_tokens, model?",
         "Estimate USD cost for a given token count without making an API call."),
        ("get_usage_history",  "(none)",
         "Retrieve historical usage records across sessions."),
        ("reset_session",      "(none)",
         "Reset the current session cost accumulator."),
    ],
    "claude-retina": [
        ("retina_capture",   "url, selector?, viewport?, scheme?, label?, wait_ms?",
         "Screenshot any URL. Returns PNG file path — must follow with Read(file_path=...) to view it. viewport: desktop|tablet|mobile|wide or WxH."),
        ("retina_diff",      "capture_a, capture_b, threshold?",
         "Pixel diff two screenshots — returns red-highlighted diff image + change percentage + changed regions."),
        ("retina_inspect",   "url, selector?, depth?, roles_only?",
         "Get accessibility/ARIA DOM tree. Use for structure understanding and a11y auditing."),
        ("retina_console",   "url, actions?, categories?, wait_ms?",
         "Capture JS console errors/warnings during page load or after interactions."),
        ("retina_interact",  "url, actions[], viewport?, label?",
         "Multi-step interaction: actions are dicts with type=click|type|scroll|navigate|wait|hover|press|clear|screenshot."),
        ("retina_baseline",  "name, url, selector?, viewport?, scheme?, notes?",
         "Save named visual baseline BEFORE making changes. Required for retina_regress."),
        ("retina_regress",   "name, url?, threshold?, pixel_threshold?",
         "Compare current UI against saved baseline — returns PASS/FAIL + diff image path."),
        ("retina_history",   "limit?, type?, url_filter?",
         "List recent captures, diffs, baselines, and interactions. type: capture|diff|baseline|interact."),
    ],
    "claude-ledger": [
        ("ledger_context",   "(none)",                       "Session-start briefing: mode + health + active state + recommended next steps. Call first every session."),
        ("ledger_query",     "task, healthy_only?",          "What tools to use for a given task — opinionated routing with call sequence and MCP scores."),
        ("ledger_mode",      "mode?",                        "Get or set token priority mode: economy | balanced | performance. Persists to .claude/ledger-mode.json."),
        ("ledger_diagnose",  "tool?",                        "Full prerequisite diagnosis — root cause + fix steps for degraded tools."),
        ("ledger_fix",       "tool",                         "Auto-apply fixable issues: hooks, env vars, Serena language drift."),
        ("ledger_available", "layer?, healthy_only?",        "List all configured tools by layer with health status."),
        ("ledger_health",    "tool?",                        "Real-time health check for all or one tool (rechecks now, not cached)."),
        ("ledger_workflows", "tag?",                         "Canonical workflow patterns: session-start, debugging, investigation, agent-spawn, visual-ui, etc."),
        ("ledger_catalog",   "mcp_key?, configured_only?",  "Full tool signatures for one or all MCP servers."),
        ("ledger_rules",     "section?",                     "Operational rules: anti-patterns, mandatory gates, priority chains, token habits, skills catalog."),
        ("ledger_preflight",  "change, files?, change_type?", "Pre-change impact synthesis: charter + mind + witness + retina. Returns CLEAR/CAUTION/BLOCKED. change_type boosts charter scoring 2x. Subsumes charter_check."),
        ("ledger_correlate",  "query, scope?",              "Unified cross-tool search — everything known about a topic across all cognitive tools."),
    ],
}

# Layer assignments for each mcp_key
LAYER_MAP: dict[str, int] = {
    "serena": 0,
    "dual-graph": 0,
    "leann-server": 1,
    "Claude Context": 1,
    "context7": 1,
    "claude-witness": 1,
    "claude-session": 2,
    "context-mode": 2,
    "claude-mind": 2,
    "claude-charter": 2,
    "ccusage": 4,
    "cclogviewer": 4,
    "claudio": 4,
    "cship": 4,
    "claude-retina": 4,
    "token-counter": 4,
    "seu-claude": 5,
    "claude-ledger": 5,
    "codegraphcontext": 6,
}

LAYER_NAMES: dict[int, str] = {
    0: "Foundation",
    1: "Context Intelligence",
    2: "Memory & Continuity",
    3: "Safety & Guardrails",
    4: "Observability",
    5: "Orchestration",
    6: "Workflow",
}

# Per-tool prerequisite specs used by ledger_diagnose / ledger_fix.
# Each "requires" entry has a type and fix instructions.
#
# Types:
#   binary       — PATH binary must exist
#   hook         — ~/.claude/settings.json must have a matching hook
#   file         — a file path must exist
#   env          — an env var must be set
#   auto_configure — a check function must pass (config drift detection)
#
# auto_fixable=True means ledger_fix can write the fix without user action.
TOOL_REQUIREMENTS: dict[str, dict] = {
    "claude-session": {
        "title": "Session MCP",
        "why": (
            "claude-session-mcp requires sessionCleanup.enabled=false in "
            "~/.claude/settings.json, otherwise Claude Code deletes session files "
            "after 30 days — making restore_session silently fail. Also requires "
            "the companion binary for session tracking hooks."
        ),
        "docs": "https://github.com/chrisguillory/claude-session-mcp",
        "requires": [
            {
                "type": "binary",
                "name": "claude-session-mcp",
                "fix": (
                    "Install: uv tool install git+https://github.com/chrisguillory/claude-session-mcp\n"
                    "  (check repo README for current install command)"
                ),
                "auto_fixable": False,
            },
            {
                "type": "hook",
                "event": "SessionStart",
                "match_command": "claude-workspace",
                "fix_description": (
                    "Add SessionStart hook to ~/.claude/settings.json so "
                    "claude-workspace registers the session on startup."
                ),
                "fix_hook_entry": {
                    "hooks": [{"type": "command", "command": "claude-workspace session start"}],
                },
                "auto_fixable": True,
            },
            {
                "type": "file",
                "path": "~/.claude-workspace/sessions.json",
                "fix": (
                    "After installing, run: claude-workspace session start\n"
                    "or start a new Claude session — the hook creates sessions.json automatically."
                ),
                "auto_fixable": False,
            },
        ],
    },
    "serena": {
        "title": "Serena LSP",
        "why": (
            "Serena starts language servers based on the languages list in "
            ".serena/project.yml. If the list doesn't match the actual project "
            "languages, symbol search silently misses entire file types. "
            "E.g., a Python+Bash project without 'bash' in languages will miss all shell scripts."
        ),
        "requires": [
            {
                "type": "auto_configure",
                "check": "serena_languages",
                "fix_description": (
                    "Add detected languages to .serena/project.yml so Serena "
                    "indexes all file types in the project."
                ),
                "auto_fixable": True,
            },
        ],
    },
    "leann-server": {
        "title": "LEANN Semantic Search",
        "why": "LEANN_INDEX_PATH tells LEANN where to store its AST index. Without it, the server crashes at startup.",
        "requires": [
            {
                "type": "env",
                "var": "LEANN_INDEX_PATH",
                "fix": (
                    "Add to the env section of leann-server in .mcp.json:\n"
                    "  \"LEANN_INDEX_PATH\": \".leann/index\""
                ),
                "auto_fixable": True,
            },
        ],
    },
    "claude-retina": {
        "title": "Claude Retina Visual",
        "why": "claude-retina drives Playwright for browser screenshots. Without Playwright installed, all retina_* tools fail.",
        "requires": [
            {
                "type": "binary",
                "name": "playwright",
                "fix": (
                    "pip install playwright && playwright install chromium\n"
                    "  (or: uv pip install playwright && playwright install chromium)"
                ),
                "auto_fixable": False,
            },
        ],
    },
    "codegraphcontext": {
        "title": "CodeGraphContext",
        "why": (
            "CodeGraphContext requires an initial index_codebase() call before any graph queries. "
            "Without it, get_callers/get_callees/get_impact return empty or stale results. "
            "Also requires 'cgc' binary in PATH after pip install."
        ),
        "requires": [
            {
                "type": "binary",
                "name": "cgc",
                "fix": (
                    "pip install codegraphcontext\n"
                    "  cgc mcp setup  # auto-configures MCP entry\n"
                    "  (Windows: may need PATH fix script after install)"
                ),
                "auto_fixable": False,
            },
        ],
    },
}
