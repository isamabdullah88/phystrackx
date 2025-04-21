from PIL import Image, ImageDraw

class Circle:
    """Basic circle unit class."""
    def __init__(self, **kwargs):
        self.cx = kwargs.get('cx', 0)
        self.cy = kwargs.get('cy', 0)
        self.rad = kwargs.get('rad', 0)


def circilize(width, height):
    """Create a fully transparent image (RGBA)"""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Define circle parameters
    circle_bounds = (0, 0, width, height)  # (left, top, right, bottom)
    circle_color = (255, 0, 0, 128)     # Red color with 50% opacity

    # Draw the circle (ellipse) on the transparent background
    draw.ellipse(circle_bounds, fill=circle_color)

    return image