from __future__ import annotations
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def render_collage(
    frontend_url: str,
    collage: dict,
    out_path: str | Path,
    scale: int = 1,
    timeout_ms: int = 60_000,
) -> Path:
    """Screenshot a collage exactly as the real frontend renders it.

    We inject the already-fetched collage JSON into the page (window.__EPHEMERA_COLLAGE__),
    so collage.js's headless hook renders it directly — no API round-trip from the browser,
    and pixel-identical to the live app because it's the same buildFragment().
    """
    out_path = Path(out_path)
    canvas = collage.get("canvas", {})
    width = int(canvas.get("width", 1600))
    height = int(canvas.get("height", 2200))

    init_script = "window.__EPHEMERA_COLLAGE__ = " + json.dumps(collage) + ";"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=scale,
        )
        page = context.new_page()
        page.add_init_script(init_script)  # runs before collage.js
        page.goto(f"{frontend_url}/", wait_until="load")
        # collage.js sets this true once every image has settled.
        page.wait_for_function("() => window.__EPHEMERA_RENDER_READY__ === true", timeout=timeout_ms)
        page.locator("#canvas").screenshot(path=str(out_path))
        browser.close()

    return out_path
