from pathlib import Path

from PIL import Image

from flow_render.config import Config
from flow_render.main import default_output_dir, main


def make_config() -> Config:
    return Config(
        keyword="pm",
        query="steam",
        icon="data:image/png;base64,x",
        results=[{"title": "Steam", "subtitle": "sub", "icon": "data:image/png;base64,y"}],
    )


def fake_screenshot(tmp_path: Path) -> Path:
    path = tmp_path / "raw.png"
    Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(path)
    return path


def test_main_does_not_create_build_or_output_dirs_in_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    screenshot = fake_screenshot(tmp_path)
    monkeypatch.setattr("flow_render.main.capture_screenshot", lambda html_path, width=None, height=None: screenshot)

    output_dir = tmp_path / "custom-output"
    main(make_config(), output_dir=output_dir)

    assert not (tmp_path / "build").exists()
    assert not (tmp_path / "output").exists()
    assert list(output_dir.glob("output_*.png"))


def test_main_defaults_to_default_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    screenshot = fake_screenshot(tmp_path)
    monkeypatch.setattr("flow_render.main.capture_screenshot", lambda html_path, width=None, height=None: screenshot)

    fake_default = tmp_path / "fake-default-output"
    monkeypatch.setattr("flow_render.main.default_output_dir", lambda: fake_default)

    main(make_config())

    assert list(fake_default.glob("output_*.png"))


def test_main_forwards_width_and_height_to_capture_screenshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    screenshot = fake_screenshot(tmp_path)
    captured = {}

    def fake_capture(html_path, width=None, height=None):
        captured['width'] = width
        captured['height'] = height
        return screenshot

    monkeypatch.setattr("flow_render.main.capture_screenshot", fake_capture)

    main(make_config(), output_dir=tmp_path / "custom-output", width=1600, height=900)

    assert captured['width'] == 1600
    assert captured['height'] == 900


def test_default_output_dir_is_outside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = default_output_dir()

    assert Path.cwd() not in result.parents
    assert "flow-render" in str(result)
