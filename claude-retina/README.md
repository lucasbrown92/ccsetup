# claude-retina

**Visual browser automation for Claude Code.** Gives Claude eyes on the running UI.

Claude can read HTML/CSS/JS source but cannot *see* what renders. claude-retina closes that gap: screenshot any URL, diff before/after, inspect accessibility trees, capture JS console errors, run click/type interaction sequences, and do visual regression testing against named baselines.

## Tools

| Tool | Params | Purpose |
|------|--------|---------|
| `retina_capture` | `url, selector?, viewport?, scheme?, label?, wait_ms?` | Screenshot a URL or CSS selector. Returns PNG path for `Read` tool. |
| `retina_diff` | `capture_a, capture_b, threshold?` | Pixel-level diff → red-highlight diff image + change % + changed regions |
| `retina_inspect` | `url, selector?, depth?, roles_only?` | Accessibility/semantic DOM tree (ARIA roles, labels, structure) |
| `retina_console` | `url, actions?, categories?, wait_ms?` | Capture JS console errors/warnings/logs and uncaught exceptions |
| `retina_interact` | `url, actions[], viewport?, label?` | Multi-step interaction sequence (click/type/scroll/etc.) with screenshots |
| `retina_baseline` | `name, url, selector?, viewport?, scheme?, notes?` | Save named baseline PNG for regression testing |
| `retina_regress` | `name, url?, threshold?, pixel_threshold?` | Compare current UI against saved baseline → PASS/FAIL + diff |
| `retina_history` | `limit?, type?, url_filter?` | List recent captures, diffs, baselines, interactions |

## Installation

```bash
# Install server (done by ccsetup / bash install.sh):
#   ~/.local/share/ccsetup/claude-retina/server.py

# Install browser deps:
pip install playwright Pillow
playwright install chromium
```

**Playwright** is required for all browser tools (retina_capture, retina_inspect, retina_console, retina_interact, retina_baseline, retina_regress).

**Pillow** is required for pixel-level diffs (retina_diff, retina_regress). Without it, retina_diff falls back to PNG header dimensions + file-size comparison.

If deps are missing, each tool returns a clear error with install instructions.

## Storage

```
.claude/retina/
├── retina.json           ← index of all captures, baselines, regressions
├── captures/             ← PNG screenshots and diff images
│   ├── a1b2c3d4.png
│   └── diff_a1b2c3d4_b2c3d4e5.png
└── baselines/            ← named baseline PNGs
    └── homepage-desktop.png
```

Override with `CLAUDE_RETINA_DIR` env var.

## Workflows

### See what the UI actually looks like
```
1. retina_capture("http://localhost:3000")
2. Read(file_path=".claude/retina/captures/<id>.png")
3. retina_inspect("http://localhost:3000")    → accessibility tree
4. retina_console("http://localhost:3000")    → JS errors
```

### Visual regression guard
```
1. retina_baseline("feature-x", "http://localhost:3000/feature")
2. <implement changes>
3. retina_regress("feature-x")               → PASS/FAIL + diff
4. If FAIL → Read(diff_file) to inspect
```

### Verify before/after a code change
```
1. retina_capture("http://localhost:3000")    → ID: before
2. <make code changes, reload server>
3. retina_capture("http://localhost:3000")    → ID: after
4. retina_diff("before_id", "after_id")       → change %
5. Read(diff_file) → see exactly what changed
```

### Interaction sequence (login flow)
```python
retina_interact("http://localhost:3000/login", actions=[
    {"type": "type",  "selector": "#email",    "text": "user@example.com"},
    {"type": "type",  "selector": "#password", "text": "secret"},
    {"type": "click", "selector": "#submit"},
    {"type": "wait",  "ms": 1000},
])
```

## Viewports

Named aliases: `desktop` (1280×800), `tablet` (768×1024), `mobile` (375×667), `wide` (1920×1080). Or use `WxH` directly.

## Action Types

`click {selector}`, `type {selector, text}`, `scroll {selector?, delta_y}`, `navigate {url}`, `wait {ms}`, `hover {selector}`, `press {key}`, `clear {selector}`, `screenshot`

## Configuration

`.mcp.json` entry (written by ccsetup):
```json
{
  "mcpServers": {
    "claude-retina": {
      "command": "python3",
      "args": ["~/.local/share/ccsetup/claude-retina/server.py"]
    }
  }
}
```
