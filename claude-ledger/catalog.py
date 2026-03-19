#!/usr/bin/env python3
"""claude-ledger catalog — embedded tool catalog for all ccsetup-managed MCP servers.

This is a copy of _TOOL_CATALOG from ccsetup.py, kept in sync at install time.
Includes entries for claude-retina and claude-ledger itself.

Each entry: (tool_name, params_summary, when_to_use)
"""

# Full catalog: mcp_key -> list of (name, params, when_to_use)
TOOL_CATALOG: dict[str, list[tuple[str, str, str]]] = {
    "serena": [
        ("get_symbols_overview",      "relative_path",                       "Need file structure / symbol list"),
        ("find_symbol",               "name_path_pattern, depth?, include_body?", "Looking for a specific symbol by name"),
        ("find_referencing_symbols",  "name, relative_path?",                "Need callers / usages of a symbol"),
        ("replace_symbol_body",       "symbol, new_body",                    "Editing an entire function/method/class body"),
        ("insert_after_symbol",       "symbol, code",                        "Adding code after an existing symbol"),
        ("insert_before_symbol",      "symbol, code",                        "Adding code before an existing symbol"),
        ("rename_symbol",             "symbol, new_name",                    "Renaming across all references"),
        ("search_for_pattern",        "pattern, relative_path?",             "Regex search when symbol name is unknown"),
        ("list_dir",                  "relative_path?",                      "Directory listing within project"),
        ("find_file",                 "filename, relative_path?",            "Searching for file by name"),
    ],
    "claude-mind": [
        ("mind_open",           "title",                                           "Starting or resuming an investigation"),
        ("mind_add",            "type, content, confidence?, files?, evidence_ids?, depends_on?", "Recording hypothesis/fact/assumption/question/ruled_out/next_step"),
        ("mind_update",         "node_id, status, notes?",                         "Confirming/refuting hypothesis or assumption"),
        ("mind_query",          "filter",                                           "Reviewing nodes by type/status/text search"),
        ("mind_summary",        "(none)",                                           "Recovering full investigation state after compaction"),
        ("mind_resolve",        "conclusion, node_ids?",                            "Closing investigation with conclusion"),
        ("mind_import_witness", "fn_name, run_id?",                                "Importing witness execution data as a FACT node"),
        ("mind_graph",          "(none)",                                           "Visualize reasoning chains and dependency trees"),
    ],
    "claude-charter": [
        ("charter_add",     "type, content, notes?, scope?",    "Recording invariant/constraint/non_goal/contract/goal"),
        ("charter_update",  "id, status?, content?, notes?",    "Modifying or archiving an entry"),
        ("charter_query",   "filter",                            "Reviewing entries by type or text search"),
        ("charter_summary", "(none)",                            "Full project constitution overview"),
        ("charter_check",   "change_description, file_path?",   "Before any structural change — checks for conflicts"),
        ("charter_audit",   "(none)",                            "Charter health report: gaps, imbalances, prohibitions"),
    ],
    "claude-witness": [
        ("witness_runs",          "limit?",                      "Listing recent test runs with pass/fail"),
        ("witness_traces",        "fn_name, run_id?, status?",   "Investigating specific function call behavior"),
        ("witness_exception",     "exc_type, run_id?",           "Exception details with local variable state"),
        ("witness_coverage_gaps", "file",                         "Finding untested code paths"),
        ("witness_diff",          "run_a, run_b",                 "Comparing two test runs — what changed"),
        ("witness_check_charter", "run_id?",                      "Cross-checking execution against charter entries"),
        ("witness_hotspots",      "limit?, run_count?",           "Functions with most exceptions — prioritize debugging"),
    ],
    "leann-server": [
        ("leann_search",   "query, limit?",      "Semantic code search — find by meaning"),
        ("leann_index",    "directory?",           "Build/refresh the local search index"),
    ],
    "context7": [
        ("resolve-library-id", "libraryName",                          "Find library ID for docs lookup"),
        ("get-library-docs",   "context7CompatibleLibraryID, topic?",  "Fetch live library documentation"),
    ],
    "claude-session": [
        ("session_list",    "(none)",       "List available sessions"),
        ("session_clone",   "session_id",   "Fork a session for parallel investigation"),
        ("session_archive", "session_id",   "Archive a session snapshot"),
        ("session_restore", "session_id",   "Restore a previous session state"),
    ],
    "context-mode": [
        ("context_status", "(none)",  "Check what's virtualized vs. in context"),
        ("context_search", "query",   "Search across virtualized tool outputs"),
    ],
    "seu-claude": [
        ("memory_store",  "key, value",           "Persist data across sessions"),
        ("memory_recall",  "key",                  "Retrieve persisted data"),
        ("task_create",   "title, description?",   "Create task for orchestration"),
        ("task_list",     "status?",               "List tracked tasks"),
    ],
    "codegraphcontext": [
        ("get_callers",  "symbol, depth?",  "Find all callers of a function"),
        ("get_callees",  "symbol, depth?",  "Find all functions called by a symbol"),
        ("get_impact",   "file_or_symbol",  "Cross-file change impact analysis"),
    ],
    "token-counter": [
        ("count_tokens",      "text",                                       "Estimate token cost before reading large content"),
        ("get_session_stats", "(none)",                                      "Running session cost dashboard"),
        ("log_usage",         "input_tokens, output_tokens, description?",   "Record usage for cost tracking"),
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

# Layer assignments for each mcp_key
LAYER_MAP: dict[str, int] = {
    "serena": 0,
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
