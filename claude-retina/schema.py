#!/usr/bin/env python3
"""claude-retina schema: TOOLS definitions, viewport constants, action types, error messages."""

DEFAULT_VIEWPORT = "1280x800"
DEFAULT_SCHEME = "light"
DEFAULT_WAIT_MS = 500
DEFAULT_THRESHOLD = 10.0   # per-pixel diff threshold (0-255)
DEFAULT_CHANGE_PCT = 0.5   # percent change to flag regression as FAIL

VIEWPORT_ALIASES = {
    "desktop": "1280x800",
    "tablet": "768x1024",
    "mobile": "375x667",
    "wide": "1920x1080",
}

ACTION_TYPES = {
    "click", "type", "scroll", "navigate", "wait",
    "hover", "press", "clear", "screenshot",
}

ERR_NO_PLAYWRIGHT = (
    "playwright not installed.\n"
    "  pip install playwright\n"
    "  playwright install chromium"
)

ERR_NO_PILLOW = (
    "Pillow not installed — falling back to header-only diff (no pixel comparison).\n"
    "Install for pixel-level diffs: pip install Pillow"
)

TOOLS = [
    {
        "name": "retina_capture",
        "description": (
            "Take a screenshot of a URL or CSS selector using headless Chromium. "
            "Returns the file path to the PNG. Use the Read tool to view it. "
            "Supports viewport size, color scheme (light/dark), CSS selector, "
            "a label for identification, and wait_ms to let dynamic content settle. "
            "Requires: pip install playwright && playwright install chromium"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to capture (e.g. 'http://localhost:3000').",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to capture instead of full page.",
                },
                "viewport": {
                    "type": "string",
                    "description": (
                        "Viewport as 'WxH' or named alias "
                        "(desktop=1280x800, tablet=768x1024, mobile=375x667, wide=1920x1080). "
                        "Default: 1280x800."
                    ),
                },
                "scheme": {
                    "type": "string",
                    "description": "Color scheme: 'light' (default), 'dark', or 'no-preference'.",
                },
                "label": {
                    "type": "string",
                    "description": "Human-readable label for this capture (shown in retina_history).",
                },
                "wait_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait after page load before capturing (default: 500).",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "retina_diff",
        "description": (
            "Pixel-level diff between two captures. Returns change percentage, "
            "count of changed pixels, and bounding boxes of changed regions. "
            "Saves a red-highlight diff image. Use the Read tool to view it. "
            "Requires capture IDs from retina_capture or retina_history. "
            "Requires: pip install Pillow (stdlib fallback if not available)"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "capture_a": {
                    "type": "string",
                    "description": "First capture ID (baseline/before).",
                },
                "capture_b": {
                    "type": "string",
                    "description": "Second capture ID (comparison/after).",
                },
                "threshold": {
                    "type": "number",
                    "description": "Per-pixel difference threshold 0-255 to consider a pixel changed (default: 10).",
                },
            },
            "required": ["capture_a", "capture_b"],
        },
    },
    {
        "name": "retina_inspect",
        "description": (
            "Inspect the accessibility/semantic DOM tree of a rendered page using "
            "Playwright's accessibility snapshot. Returns roles, labels, and structure "
            "without reading raw HTML. Useful for verifying semantic markup and ARIA labels. "
            "Requires: pip install playwright && playwright install chromium"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to inspect.",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to restrict inspection to a subtree.",
                },
                "depth": {
                    "type": "integer",
                    "description": "Max depth to display in the tree (default: 4).",
                },
                "roles_only": {
                    "type": "boolean",
                    "description": "If true, show only nodes with ARIA roles (default: false).",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "retina_console",
        "description": (
            "Capture JavaScript console output (errors, warnings, logs) and uncaught "
            "exceptions during page load and optional interaction sequence. "
            "Use to diagnose JS errors without opening DevTools. "
            "Requires: pip install playwright && playwright install chromium"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to load and monitor.",
                },
                "actions": {
                    "type": "array",
                    "description": "Optional interaction sequence to run after page load (same action format as retina_interact).",
                    "items": {"type": "object"},
                },
                "categories": {
                    "type": "array",
                    "description": "Filter message types: ['error', 'warning', 'log', 'info', 'debug']. Default: all.",
                    "items": {"type": "string"},
                },
                "wait_ms": {
                    "type": "integer",
                    "description": "Milliseconds to wait after page load (default: 500).",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "retina_interact",
        "description": (
            "Run a multi-step browser interaction sequence with a screenshot after each step. "
            "Action types: click {selector}, type {selector, text}, scroll {selector?, delta_y}, "
            "navigate {url}, wait {ms}, hover {selector}, press {key}, clear {selector}, screenshot. "
            "Returns step-by-step screenshots. Use Read tool to view each PNG. "
            "Requires: pip install playwright && playwright install chromium"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Starting URL.",
                },
                "actions": {
                    "type": "array",
                    "description": "Sequence of actions. Each is an object with 'type' key plus action-specific fields.",
                    "items": {"type": "object"},
                },
                "viewport": {
                    "type": "string",
                    "description": "Viewport as 'WxH' or alias. Default: 1280x800.",
                },
                "label": {
                    "type": "string",
                    "description": "Label for this interaction sequence.",
                },
            },
            "required": ["url", "actions"],
        },
    },
    {
        "name": "retina_baseline",
        "description": (
            "Save a named baseline screenshot for visual regression testing. "
            "Stored in .claude/retina/baselines/. "
            "Use retina_regress() to compare future UI states against it. "
            "Best practice: save a baseline before implementing visual changes. "
            "Requires: pip install playwright && playwright install chromium"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Unique name for this baseline (e.g. 'homepage-desktop', 'login-dark').",
                },
                "url": {
                    "type": "string",
                    "description": "URL to capture as the baseline.",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to baseline instead of full page.",
                },
                "viewport": {
                    "type": "string",
                    "description": "Viewport as 'WxH' or alias. Default: 1280x800.",
                },
                "scheme": {
                    "type": "string",
                    "description": "Color scheme: 'light' (default), 'dark', or 'no-preference'.",
                },
                "notes": {
                    "type": "string",
                    "description": "Notes about what this baseline represents.",
                },
            },
            "required": ["name", "url"],
        },
    },
    {
        "name": "retina_regress",
        "description": (
            "Compare the current UI against a saved named baseline. "
            "Returns PASS/FAIL + change percentage. On FAIL, saves and returns a diff image. "
            "Use retina_baseline() first to establish the baseline. "
            "Requires: pip install playwright Pillow && playwright install chromium"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Baseline name to compare against.",
                },
                "url": {
                    "type": "string",
                    "description": "URL to capture for comparison. If omitted, uses the baseline's URL.",
                },
                "threshold": {
                    "type": "number",
                    "description": "Change percentage above which to FAIL (default: 0.5%).",
                },
                "pixel_threshold": {
                    "type": "number",
                    "description": "Per-pixel difference threshold 0-255 (default: 10).",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "retina_history",
        "description": (
            "List recent captures, diffs, baselines, and interaction sequences. "
            "Use to find capture IDs for retina_diff or retina_regress. "
            "Filter by type (capture/diff/interaction/baseline/regression) or URL substring."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max entries to return (default: 20).",
                },
                "type": {
                    "type": "string",
                    "description": "Filter by entry type: capture / diff / interaction / baseline / regression.",
                },
                "url_filter": {
                    "type": "string",
                    "description": "Filter to entries whose URL contains this string.",
                },
            },
            "required": [],
        },
    },
]
