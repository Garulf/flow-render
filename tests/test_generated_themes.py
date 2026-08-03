from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from flow_render.config import Config
from flow_render.renderer import render

THEMES_DIR = Path(__file__).parent.parent / 'src' / 'flow_render' / 'static' / 'themes'


def generated(name: str) -> str:
    return (THEMES_DIR / name).read_text()


def test_dracula_golden_values():
    css = generated('dracula.css')

    assert 'background-color: #282a36;' in css
    assert 'color: #f8f8f2;' in css
    assert 'font-size: 26px;' in css


def test_win11_dark_golden_values():
    css = generated('win11light-dark.css')

    assert 'background-color: #202020;' in css
    assert '#0091F8' in css


def test_all_generated_themes_are_self_contained():
    css_files = list(THEMES_DIR.glob('*.css'))
    assert len(css_files) >= 20
    for css_file in css_files:
        assert '.item-text-container' in css_file.read_text(), css_file.name


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        yield page
        browser.close()


def test_generated_dracula_computed_styles(page):
    config = Config(
        keyword="pm", query="steam", icon="data:image/png;base64,x",
        css="themes/dracula.css",
        results=[
            {"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"},
            {"title": "Epic", "subtitle": "sub", "icon": "data:image/png;base64,y"},
        ],
    )
    page.set_content(render(config))

    selected_title = page.eval_on_selector(
        ".selecteditem .Title", "el => getComputedStyle(el).color")
    plain_title = page.eval_on_selector(
        ".item:not(.selecteditem) .Title", "el => getComputedStyle(el).color")
    assert selected_title == "rgb(255, 121, 198)"
    assert plain_title == "rgb(248, 248, 242)"
