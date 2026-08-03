import subprocess
import sys
from pathlib import Path
from typing import Optional

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

RENDER_SCALE = 2


def _install_chromium() -> None:
    print("Chromium not found; installing it now (this only happens once)...", file=sys.stderr)
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)


def _launch_chromium(playwright):
    try:
        return playwright.chromium.launch(channel="chromium")
    except PlaywrightError as error:
        if "Executable doesn't exist" not in str(error):
            raise
        _install_chromium()
        return playwright.chromium.launch(channel="chromium")


def capture_screenshot(html_path: str, width: Optional[int] = None, height: Optional[int] = None) -> Path:
    page_url = f"file://{Path(html_path).resolve()}"
    image_file = Path(html_path).with_suffix('.png')
    image_file.parent.mkdir(parents=True, exist_ok=True)
    # Playwright treats an explicit viewport=None as "disable the default
    # viewport" (not "use the default"), so only pass it when we actually
    # have both dimensions — omitting the kwarg keeps Playwright's own
    # 1280x720 default for existing callers that don't request a size.
    page_kwargs = {"device_scale_factor": RENDER_SCALE}
    if width and height:
        page_kwargs["viewport"] = {"width": width, "height": height}
    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        page = browser.new_page(**page_kwargs)
        page.goto(page_url)
        page.screenshot(
            path=image_file,
            omit_background=True,
            scale="device"
        )
        browser.close()
    return image_file
