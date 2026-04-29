from html2image import Html2Image
from PIL import Image, ImageChops


def html_to_image(html: str, output: str):
    hti = Html2Image()
    hti.screenshot(html_file=html, save_as=output)
    return output


def auto_fit_crop(image: str):
    img = Image.open(image)
    img = img.crop()
    img.save(image)


def trim(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    # Bounding box given as a 4-tuple defining the left, upper, right, and lower pixel coordinates.
    # If the image is completely empty, this method returns None.
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


if __name__ == '__main__':
    html_to_image('index.html', 'index.png')
    img = Image.open('index.png')
    img = trim(img)
    img.save('index.png')
