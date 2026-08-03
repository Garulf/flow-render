import json
import threading
import urllib.request
from pathlib import Path

import pytest

from web_render import edit_server
from web_render.config import Config


def make_test_config():
    return Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        plugin={"Name": "Steam Search"},
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
    )


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(edit_server, "STATIC_DIR", tmp_path / "static")
    (tmp_path / "static").mkdir()
    srv = edit_server.build_server(make_test_config(), base_css_files=[])
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.session.cleanup()
    srv.server_close()


def request(server, method, path, body=None):
    url = f"http://{server.server_address[0]}:{server.server_address[1]}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as response:
        return response.status, response.read()


def test_get_root_serves_editor_shell(server):
    status, body = request(server, "GET", "/")

    assert status == 200
    assert b"<!doctype" in body.lower() or b"<html" in body.lower()


def test_get_preview_renders_current_config(server):
    status, body = request(server, "GET", "/preview")

    assert status == 200
    assert b"Steam" in body


def test_get_state_reflects_a_prior_update(server):
    request(server, "POST", "/update", {
        "type": "canvas",
        "canvas": {"angle": 90, "stops": [{"color": "#000000", "position": 0},
                                          {"color": "#ffffff", "position": 100}]},
    })

    status, body = request(server, "GET", "/state")

    assert status == 200
    state = json.loads(body)
    assert state["canvas"]["angle"] == 90


def test_update_element_transform_is_reflected_in_preview(server):
    request(server, "POST", "/update", {
        "type": "element",
        "selector": "#WindowBorder",
        "transform": {"translate_x": 10, "translate_y": 0, "translate_z": 0,
                      "rotate_x": 0, "rotate_y": 0, "rotate_z": 0},
    })

    status, body = request(server, "GET", "/preview")

    assert status == 200
    assert b"translate3d(10px" in body


def test_save_writes_css_file_with_live_jinja_template(server, tmp_path):
    request(server, "POST", "/update", {
        "type": "layer",
        "slot": 0,
        "layer": {"active": True, "template": "{{ plugin.Name }}", "font_size": 40,
                  "color": "#fff", "weight": "bold",
                  "transform": {"translate_x": 0, "translate_y": 0, "translate_z": 0,
                                "rotate_x": 0, "rotate_y": 0, "rotate_z": 0}},
    })

    status, body = request(server, "POST", "/save", {"filename": "my-promo"})

    assert status == 200
    result = json.loads(body)
    saved_path = Path(result["path"])
    assert saved_path.exists()
    assert saved_path == tmp_path / "static" / "my-promo.css"
    assert "{{ plugin.Name }}" in saved_path.read_text()


def test_preview_does_not_duplicate_base_css_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(edit_server, "STATIC_DIR", tmp_path / "static")
    (tmp_path / "static").mkdir()
    srv = edit_server.build_server(make_test_config(), base_css_files=["hero.css"])
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = request(srv, "GET", "/preview")
    finally:
        srv.shutdown()
        srv.session.cleanup()
        srv.server_close()

    assert status == 200
    assert body.count(b"preserve-3d") == 1


def test_save_sanitizes_filename_to_its_stem(server, tmp_path):
    status, body = request(server, "POST", "/save", {"filename": "../../etc/passwd"})

    result = json.loads(body)
    saved_path = Path(result["path"])
    assert saved_path == tmp_path / "static" / "passwd.css"
