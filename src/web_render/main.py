from pathlib import Path
import shutil
from datetime import datetime
from uuid import uuid4

from .config import Config
from .renderer import render_from_config
from .screenshot import capture_screenshot
from .image import crop_to_content

BUILD_DIR = Path('build')
OUTPUT_DIR = Path('output')


def main(config: Config):
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config.save_to_file(str(BUILD_DIR / 'config.json'))

    html_path = BUILD_DIR / 'output.html'
    render_from_config(config, str(html_path))

    raw_image = capture_screenshot(str(html_path))
    unique_suffix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex[:8]}"
    final_image = crop_to_content(raw_image, OUTPUT_DIR / f"output_{unique_suffix}.png")
    print(f"Saved {final_image}")
