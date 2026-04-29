from PIL import Image


def crop_image(image_path):
    """Crops the image to the smallest bounding box."""
    img = Image.open(image_path)
    img = img.crop(img.getbbox())
    print(f"Saving image as {image_path}")
    img.save(image_path)
