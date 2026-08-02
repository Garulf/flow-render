from PIL import Image
from pathlib import Path


def crop_to_content(image_path, output_path=None) -> Path:
    """Crops the image to the smallest bounding box."""
    img = Image.open(image_path)
    img = img.crop(img.getbbox())
    destination = Path(output_path) if output_path else Path(image_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    img.save(destination)
    return destination
