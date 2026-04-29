from pathlib import Path
from playwright.sync_api import sync_playwright


def grab_image(path: str):
    full_path = Path(path).resolve()
    with sync_playwright() as p:
        for browser_type in [p.chromium]:
            browser = browser_type.launch()
            page = browser.new_page()
            page.goto(rf"file://{full_path}")
            page.goto
            # select #WindowBorder id
            # element = page.query_selector('#WindowBorder')
            # take a screenshot of the element
            image_file = Path(path).with_suffix('.png')
            page.screenshot(
                path=image_file,
                omit_background=True,
                scale="css"
            )
            browser.close()
    return image_file
