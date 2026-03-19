#!/usr/bin/env python3
"""claude-retina capture — Playwright browser automation (sync API).

Each public function creates a fresh browser context per call (no shared state).
Playwright not installed → raises RuntimeError with install instructions.

Sync API only — MCP server loop is synchronous; mixing async causes event loop conflicts.
"""

import time
from pathlib import Path


def _require_playwright():
    """Import guard: raises RuntimeError with pip install instructions if unavailable."""
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except ImportError:
        raise RuntimeError(
            "playwright not installed.\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )


def _resolve_viewport(viewport_str: str) -> str:
    """Resolve named viewport aliases to 'WxH' strings."""
    aliases = {
        "desktop": "1280x800",
        "tablet": "768x1024",
        "mobile": "375x667",
        "wide": "1920x1080",
    }
    return aliases.get(viewport_str, viewport_str)


def _parse_viewport(viewport_str: str) -> dict:
    """Parse 'WxH' string to {width, height} dict."""
    vp = _resolve_viewport(viewport_str)
    try:
        w, h = map(int, vp.split("x"))
    except (ValueError, AttributeError):
        w, h = 1280, 800
    return {"width": w, "height": h}


def _with_browser(viewport_str: str, scheme: str, fn):
    """Run fn(page) in a new isolated browser context. Always closes browser."""
    sync_playwright = _require_playwright()
    vp = _parse_viewport(viewport_str)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=vp,
            color_scheme=scheme,
        )
        page = ctx.new_page()
        try:
            return fn(page)
        finally:
            ctx.close()
            browser.close()


def screenshot_url(
    url: str,
    out_path: Path,
    selector: str | None = None,
    viewport: str = "1280x800",
    scheme: str = "light",
    wait_ms: int = 500,
) -> None:
    """Capture screenshot of URL (or selector) into out_path (PNG)."""

    def _capture(page):
        page.goto(url, wait_until="networkidle", timeout=30000)
        if wait_ms > 0:
            time.sleep(wait_ms / 1000)
        if selector:
            elem = page.query_selector(selector)
            if elem is None:
                raise ValueError(f"Selector not found: {selector!r}")
            elem.screenshot(path=str(out_path))
        else:
            page.screenshot(path=str(out_path), full_page=False)

    _with_browser(viewport, scheme, _capture)


def accessibility_snapshot(
    url: str,
    selector: str | None = None,
    viewport: str = "1280x800",
) -> dict | None:
    """Return Playwright accessibility snapshot dict for the page or a subtree."""

    def _snap(page):
        page.goto(url, wait_until="networkidle", timeout=30000)
        if selector:
            root = page.query_selector(selector)
            if root is None:
                raise ValueError(f"Selector not found: {selector!r}")
            return page.accessibility.snapshot(root=root)
        return page.accessibility.snapshot()

    return _with_browser(viewport, "light", _snap)


def capture_console(
    url: str,
    actions: list | None = None,
    wait_ms: int = 500,
    viewport: str = "1280x800",
) -> list[dict]:
    """Return list of console message dicts captured during load + optional actions."""
    messages: list[dict] = []

    def _run(page):
        def _on_msg(msg):
            loc = msg.location or {}
            messages.append({
                "type": msg.type,
                "text": msg.text,
                "location": f"{loc.get('url', '')}:{loc.get('lineNumber', '')}",
            })

        def _on_exc(exc):
            messages.append({
                "type": "uncaught_exception",
                "text": str(exc),
                "location": "",
            })

        page.on("console", _on_msg)
        page.on("pageerror", _on_exc)

        page.goto(url, wait_until="networkidle", timeout=30000)
        if wait_ms > 0:
            time.sleep(wait_ms / 1000)

        if actions:
            for action in actions:
                _execute_action(page, action)

    _with_browser(viewport, "light", _run)
    return messages


def run_interaction(
    url: str,
    actions: list,
    out_dir: Path,
    seq_id: str,
    viewport: str = "1280x800",
) -> list[dict]:
    """Execute a multi-step action sequence, screenshotting after each step.

    Returns list of step result dicts:
      {step, action, file, success, error}
    """
    results: list[dict] = []

    def _run(page):
        page.goto(url, wait_until="networkidle", timeout=30000)
        for i, action in enumerate(actions, start=1):
            step_file = out_dir / f"{seq_id}_step{i}.png"
            success = True
            error_msg = None
            try:
                _execute_action(page, action)
                page.screenshot(path=str(step_file))
            except Exception as exc:
                success = False
                error_msg = str(exc)
                # Best-effort screenshot even on error
                try:
                    page.screenshot(path=str(step_file))
                except Exception:
                    step_file = None
            results.append({
                "step": i,
                "action": action,
                "file": str(step_file) if step_file and step_file.exists() else None,
                "success": success,
                "error": error_msg,
            })

    _with_browser(viewport, "light", _run)
    return results


def _execute_action(page, action: dict) -> None:
    """Execute one action dict on the Playwright page."""
    atype = action.get("type", "").lower()

    if atype == "click":
        page.click(action["selector"], timeout=10000)

    elif atype == "type":
        page.fill(action["selector"], action.get("text", ""), timeout=10000)

    elif atype == "scroll":
        sel = action.get("selector")
        delta_y = action.get("delta_y", 300)
        if sel:
            page.evaluate(
                f"document.querySelector({sel!r}).scrollTop += {delta_y}"
            )
        else:
            page.evaluate(f"window.scrollBy(0, {delta_y})")

    elif atype == "navigate":
        page.goto(action["url"], wait_until="networkidle", timeout=30000)

    elif atype == "wait":
        time.sleep(action.get("ms", 1000) / 1000)

    elif atype == "hover":
        page.hover(action["selector"], timeout=10000)

    elif atype == "press":
        page.keyboard.press(action.get("key", "Enter"))

    elif atype == "clear":
        page.fill(action["selector"], "", timeout=10000)

    elif atype == "screenshot":
        pass  # caller handles screenshot step

    else:
        raise ValueError(
            f"Unknown action type: {atype!r}. "
            "Valid: click, type, scroll, navigate, wait, hover, press, clear, screenshot"
        )
