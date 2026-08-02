from web_render.config import Config
from web_render.renderer import render


def render_with_skin(skin: str) -> str:
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        css=skin,
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
    )
    return render(config)


def test_win11_light_skin_is_inlined(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    html = render_with_skin("win11-light.css")

    assert "#F3F3F3" in html
    assert "#0078D4" in html


def test_win11_dark_skin_is_inlined(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    html = render_with_skin("win11-dark.css")

    assert "#202020" in html
    assert "#0091F8" in html


def test_custom_skin_is_inlined_after_base_style(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    html = render_with_skin("win11-light.css")

    base_marker = html.index("#f4f1f8")
    skin_marker = html.index("#F3F3F3")
    assert skin_marker > base_marker, "custom skin must come after base style.css to win the cascade"


def test_bundled_selawik_font_is_referenced(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    html = render_with_skin(None)

    assert "selawk.woff2" in html
    assert "font-family: 'Segoe UI'" in html


def test_render_emits_standards_mode_doctype(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    html = render_with_skin(None)

    assert html.lstrip().lower().startswith("<!doctype html>")
