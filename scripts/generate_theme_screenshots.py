"""Render example/config.json against every bundled theme, for the README gallery.

Usage: uv run python scripts/generate_theme_screenshots.py
"""
import tempfile
from pathlib import Path

from flow_render.config import Config
from flow_render.renderer import render_from_config, detect_canvas_size
from flow_render.screenshot import capture_screenshot
from flow_render.image import crop_to_content

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "example" / "themes"
THEMES_DIR = REPO_ROOT / "src" / "flow_render" / "static" / "themes"


def targets():
    generated = sorted(p.stem for p in THEMES_DIR.glob("*.css"))
    yield "default", None
    for name in ("win11-dark", "win11-light"):
        yield name, f"{name}.css"
    for name in generated:
        yield name, f"themes/{name}.css"


def render_one(name: str, css) -> None:
    config = Config.from_file(str(REPO_ROOT / "example" / "config.json"))
    config.css = css
    width, height = (None, None)
    if css:
        detected = detect_canvas_size(config.css_files)
        if detected:
            width, height = detected

    with tempfile.TemporaryDirectory(prefix="flow-render-themegen-") as build_dir:
        html_path = Path(build_dir) / "output.html"
        render_from_config(config, str(html_path))
        raw_image = capture_screenshot(str(html_path), width=width, height=height)
        final_image = crop_to_content(raw_image, OUT_DIR / f"{name}.png")
    print(f"{name}: {final_image}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, css in targets():
        render_one(name, css)


if __name__ == "__main__":
    main()
