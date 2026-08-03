import re
from pathlib import Path
from typing import Optional, Tuple

import jinja2

from .config import Config

DEFAULT_TEMPLATES = Path(__file__).parent / 'templates'
STATIC_DIR = Path(__file__).parent / 'static'
BASE_TEMPLATE = 'base.html'

CANVAS_SIZE_MARKER = re.compile(r'/\*\s*web-render-canvas:\s*(\d+)x(\d+)\s*\*/')


def render(render_data: Config) -> str:
    search_paths = [Path.cwd(), DEFAULT_TEMPLATES, STATIC_DIR]
    template_loader = jinja2.FileSystemLoader(searchpath=search_paths)
    template_env = jinja2.Environment(loader=template_loader)
    loaded_template = template_env.get_template(BASE_TEMPLATE)

    # Keep legacy templates working by exposing Config fields at top-level.
    return loaded_template.render(
        **render_data.as_dict(),
        render_data=render_data,
        static_url=STATIC_DIR.resolve().as_uri(),
    )


def detect_canvas_size(css_files) -> Optional[Tuple[int, int]]:
    """Look for a `/* web-render-canvas: WIDTHxHEIGHT */` marker in the given
    css_files (resolved the same way Jinja resolves `{% include %}`: cwd
    first, then the bundled templates/static dirs). Written by edit mode's
    Save when the canvas size differs from the default. Later files in the
    list win, matching the existing css_files cascade order."""
    search_paths = [Path.cwd(), DEFAULT_TEMPLATES, STATIC_DIR]
    result = None
    for name in css_files:
        for directory in search_paths:
            candidate = directory / name
            if candidate.is_file():
                match = CANVAS_SIZE_MARKER.search(candidate.read_text())
                if match:
                    result = (int(match.group(1)), int(match.group(2)))
                break
    return result


def save_rendered(rendered_template: str, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(rendered_template)


def render_from_config(config: Config, output_path: str = 'output.html'):
    save_rendered(render(config), output_path)
