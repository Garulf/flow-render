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
