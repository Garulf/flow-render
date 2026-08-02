from pathlib import Path
from playwright.sync_api import sync_playwright

RENDER_SCALE = 2


def capture_screenshot(html_path: str) -> Path:
    page_url = f"file://{Path(html_path).resolve()}"
    image_file = Path(html_path).with_suffix('.png')
    image_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(device_scale_factor=RENDER_SCALE)
        page.goto(page_url)
        page.screenshot(
            path=image_file,
            omit_background=True,
            scale="device"
        )
        browser.close()
    return image_file
