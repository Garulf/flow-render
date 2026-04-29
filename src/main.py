from pathlib import Path
import shutil
from datetime import datetime
from uuid import uuid4

from config import Config
from renderer import render_from_config
from screenshot import grab_image
from image import crop_image


def main(config: Config):
    build_dir = Path('build')
    output_dir = Path('output')

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    config_path = build_dir / 'config.json'
    config.save_to_file(str(config_path))

    html_path = build_dir / 'output.html'
    render_from_config(config, str(html_path))

    raw_image = grab_image(str(html_path))
    unique_suffix = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex[:8]}"
    final_image = output_dir / f"output_{unique_suffix}.png"
    crop_image(raw_image, final_image)
