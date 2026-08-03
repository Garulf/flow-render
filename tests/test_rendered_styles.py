import pytest
from playwright.sync_api import sync_playwright

from flow_render.config import Config
from flow_render.renderer import render


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


def test_layer_slots_are_hidden_by_default(page):
    render_page(page, None)

    for i in range(1, 5):
        assert computed(page, f"#Layer{i}", "display") == "none"


def test_window_border_is_a_positioning_context(page):
    render_page(page, None)

    assert computed(page, "#WindowBorder", "position") == "relative"


def test_layer_activated_by_saved_theme_shows_plugin_driven_text(page, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo.css").write_text(
        "#Layer1 { display: block; transform: translate3d(10px, 0px, 0px); }\n"
        "#Layer1::before { content: \"{{ plugin.Name }}\"; }\n"
    )
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        plugin={"Name": "Steam Search"},
        css="promo.css",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}],
    )
    page.set_content(render(config))

    assert computed(page, "#Layer1", "display") == "block"
    content = page.eval_on_selector("#Layer1", "el => getComputedStyle(el, '::before').content")
    assert content == '"Steam Search"'


def test_layer_does_not_rotate_with_window_border(page, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo.css").write_text(
        "#WindowBorder { transform: perspective(2000px) rotateX(45deg) rotateY(-45deg); }\n"
        "#Layer1 { display: block; }\n"
        "#Layer1::before { content: \"Headline\"; }\n"
    )
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        css="promo.css",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}],
    )
    page.set_content(render(config))

    window_transform = computed(page, "#WindowBorder", "transform")
    layer_transform = computed(page, "#Layer1", "transform")
    assert window_transform != "none"
    assert layer_transform == "none"


def test_layer_is_a_sibling_of_window_border_not_a_child(page):
    render_page(page, None)

    is_child = page.eval_on_selector(
        "#WindowBorder", "el => el.querySelector('#Layer1') !== null"
    )
    assert is_child is False


def test_caret_visible_by_default(page):
    render_page(page, "win11-dark.css")

    display = page.eval_on_selector(
        "#QueryBoxText", "el => getComputedStyle(el, '::after').display"
    )
    assert display != "none"


def test_caret_hidden_when_show_caret_is_false(page):
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        css="win11-dark.css",
        show_caret=False,
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}],
    )
    page.set_content(render(config))

    display = page.eval_on_selector(
        "#QueryBoxText", "el => getComputedStyle(el, '::after').display"
    )
    assert display == "none"
