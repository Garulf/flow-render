import os

from web_render.config import Config
from web_render.renderer import render_from_config


def test_render_works_from_any_working_directory(tmp_path, monkeypatch):
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
    )
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "out.html"

    render_from_config(config, str(output))

    html = output.read_text()
    assert "Steam" in html


def test_render_inlines_multiple_stylesheets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "one.css").write_text("body { color: red; }")
    (tmp_path / "two.css").write_text("body { color: blue; }")
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
        css=["one.css", "two.css"],
    )
    output = tmp_path / "out.html"

    render_from_config(config, str(output))

    html = output.read_text()
    assert "color: red" in html
    assert "color: blue" in html


def make_config(result_count, max_results):
    return Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        max_results=max_results,
        results=[
            {"title": f"r{i}", "subtitle": "sub", "icon": "data:image/png;base64,y"}
            for i in range(result_count)
        ],
    )


def test_render_shows_scrollbar_when_results_exceed_max_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "out.html"

    render_from_config(make_config(5, max_results=3), str(output))

    assert '<div id="ResultsScrollbar">' in output.read_text()


def test_render_hides_scrollbar_when_results_are_at_capacity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "out.html"

    render_from_config(make_config(3, max_results=3), str(output))

    assert '<div id="ResultsScrollbar">' not in output.read_text()


def test_render_hides_scrollbar_when_results_are_under_capacity(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "out.html"

    render_from_config(make_config(2, max_results=3), str(output))

    assert '<div id="ResultsScrollbar">' not in output.read_text()


def test_render_truncates_results_to_max_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output = tmp_path / "out.html"

    render_from_config(make_config(5, max_results=3), str(output))

    html = output.read_text()
    assert '<div class="Title">r0</div>' in html
    assert '<div class="Title">r1</div>' in html
    assert '<div class="Title">r2</div>' in html
    assert '<div class="Title">r3</div>' not in html
    assert '<div class="Title">r4</div>' not in html


def test_render_exposes_plugin_fields_to_css_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo.css").write_text("/* {{ plugin.Name }} */")
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        plugin={"Name": "Steam Search"},
        css="promo.css",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
    )
    output = tmp_path / "out.html"

    render_from_config(config, str(output))

    assert "Steam Search" in output.read_text()


def test_render_leaves_plugin_reference_blank_when_no_plugin(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "promo.css").write_text("/* [{{ plugin.Name }}] */")
    config = Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        css="promo.css",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
    )
    output = tmp_path / "out.html"

    render_from_config(config, str(output))

    assert "[]" in output.read_text()
