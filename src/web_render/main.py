import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .config import Config
from .renderer import render_from_config
from .screenshot import capture_screenshot
from .image import crop_to_content

APP_NAME = 'web-render'


def default_output_dir() -> Path:
    if sys.platform == 'win32':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        return Path(base) / APP_NAME / 'output'
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / APP_NAME / 'output'
    base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / APP_NAME / 'output'


def main(config: Config, output_dir: Optional[Path] = None):
    output_dir = Path(output_dir) if output_dir else default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix='web-render-') as build_dir:
        build_path = Path(build_dir)
        config.save_to_file(str(build_path / 'config.json'))

        html_path = build_path / 'output.html'
        render_from_config(config, str(html_path))

        raw_image = capture_screenshot(str(html_path))
        unique_suffix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex[:8]}"
        final_image = crop_to_content(raw_image, output_dir / f"output_{unique_suffix}.png")

    print(f"Saved {final_image}")
