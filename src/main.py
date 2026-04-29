from pathlib import Path
import sys
from typing import Dict, List, Optional

from config import Config
from renderer import render_from_config
from screenshot import grab_image
from image import crop_image


def main(config: Config):
    build_dir = Path('.build')
    build_dir.mkdir(parents=True, exist_ok=True)

    config_path = build_dir / 'config.json'
    config.save_to_file(str(config_path))

    html_path = build_dir / 'output.html'
    render_from_config(config, str(html_path))

    raw_image = grab_image(str(html_path))
    final_image = build_dir / Path(raw_image).name
    crop_image(raw_image, final_image)
