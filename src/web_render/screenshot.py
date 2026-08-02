import subprocess
import sys
from pathlib import Path

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


def capture_screenshot(html_path: str) -> Path:
    page_url = f"file://{Path(html_path).resolve()}"
    image_file = Path(html_path).with_suffix('.png')
    image_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = _launch_chromium(playwright)
        page = browser.new_page(device_scale_factor=RENDER_SCALE)
        page.goto(page_url)
        page.screenshot(
            path=image_file,
            omit_background=True,
            scale="device"
        )
        browser.close()
    return image_file
