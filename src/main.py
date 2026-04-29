from pathlib import Path
import sys
from typing import Dict, List, Optional

from config import Config
from renderer import render_from_config
from screenshot import grab_image
from image import crop_image


def main(config: Config):
    render_from_config(config)
    image_file = grab_image('output.html')
    crop_image(image_file)
