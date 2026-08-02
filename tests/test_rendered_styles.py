import pytest
from playwright.sync_api import sync_playwright

from web_render.config import Config
from web_render.renderer import render


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        yield page
        browser.close()


def render_page(page, skin):
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        css=skin,
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}],
    )
    page.set_content(render(config))


def computed(page, selector, prop):
    return page.eval_on_selector(
        selector, f"el => getComputedStyle(el).{prop}"
    )


def test_win11_dark_selected_title_is_white(page):
    render_page(page, "win11-dark.css")

    assert computed(page, ".selecteditem .Title", "color") == "rgb(255, 255, 255)"


def test_win11_dark_selected_subtitle_is_light_gray(page):
    render_page(page, "win11-dark.css")

    assert computed(page, ".selecteditem .SubTitle", "color") == "rgb(160, 160, 160)"


def test_base_query_icon_is_pinned_to_the_right(page):
    render_page(page, None)

    assert computed(page, "#GlassIcon", "position") == "absolute"
    icon_x = page.eval_on_selector("#GlassIcon", "el => el.getBoundingClientRect().x")
    window_x = page.eval_on_selector("#WindowBorder", "el => el.getBoundingClientRect().x")
    assert icon_x - window_x > 400, "query icon should sit at the right edge of the window"


def test_base_result_icon_is_positioned(page):
    render_page(page, None)

    assert computed(page, ".item .icon", "position") == "absolute"


def test_base_query_area_keeps_its_margins(page):
    render_page(page, None)

    assert computed(page, "#QueryBoxArea", "marginLeft") == "18px"


def test_win11_dark_hotkey_pill_lifts_on_selected_row(page):
    render_page(page, "win11-dark.css")

    assert computed(page, ".selecteditem .Hotkey", "backgroundColor") == "rgb(59, 59, 59)"


def test_win11_hotkey_pill_hugs_its_text(page):
    for skin in ("win11-light.css", "win11-dark.css"):
        render_page(page, skin)
        width = page.eval_on_selector(".selecteditem .Hotkey", "el => el.getBoundingClientRect().width")
        assert width < 45, f"{skin}: hotkey pill is {width}px wide; reference is ~31px"
