from types import SimpleNamespace

from PIL import Image
from playwright.sync_api import Error as PlaywrightError

from web_render.screenshot import RENDER_SCALE, _launch_chromium, capture_screenshot


def test_launch_chromium_returns_browser_on_success():
    browser = object()
    chromium = SimpleNamespace(launch=lambda channel: browser)
    playwright = SimpleNamespace(chromium=chromium)

    assert _launch_chromium(playwright) is browser


def test_launch_chromium_installs_and_retries_when_executable_missing(monkeypatch):
    browser = object()
    calls = []

    def launch(channel):
        calls.append(channel)
        if len(calls) == 1:
            raise PlaywrightError("Executable doesn't exist at C:\\fake\\chrome.exe")
        return browser

    playwright = SimpleNamespace(chromium=SimpleNamespace(launch=launch))

    installed = []
    monkeypatch.setattr(
        "web_render.screenshot._install_chromium",
        lambda: installed.append(True),
    )

    assert _launch_chromium(playwright) is browser
    assert installed == [True]
    assert calls == ["chromium", "chromium"]


def test_launch_chromium_reraises_unrelated_errors(monkeypatch):
    def launch(channel):
        raise PlaywrightError("Some other failure")

    playwright = SimpleNamespace(chromium=SimpleNamespace(launch=launch))

    monkeypatch.setattr(
        "web_render.screenshot._install_chromium",
        lambda: (_ for _ in ()).throw(AssertionError("should not install for unrelated errors")),
    )

    try:
        _launch_chromium(playwright)
        assert False, "expected PlaywrightError"
    except PlaywrightError as error:
        assert "Some other failure" in str(error)


def test_capture_screenshot_uses_requested_viewport_size(tmp_path):
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body style='margin:0;background:red;width:100%;height:100%'></body></html>")

    image_path = capture_screenshot(str(html_path), width=400, height=300)

    with Image.open(image_path) as img:
        assert img.size == (400 * RENDER_SCALE, 300 * RENDER_SCALE)


def test_capture_screenshot_uses_default_viewport_when_no_size_given(tmp_path):
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body style='margin:0;background:red;width:100%;height:100%'></body></html>")

    image_path = capture_screenshot(str(html_path))

    with Image.open(image_path) as img:
        assert img.size == (1280 * RENDER_SCALE, 720 * RENDER_SCALE)
