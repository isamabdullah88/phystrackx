import cv2
import numpy as np
from PIL import Image, ImageDraw

class Circle:
    """Basic circle unit class."""
    def __init__(self, **kwargs):
        self.cx = kwargs.get('cx', 0)
        self.cy = kwargs.get('cy', 0)
        self.rad = kwargs.get('rad', 0)


def circilize(width, height):
    """Create a fully transparent image (RGBA)"""
    if width < 5: width = 5
    if height < 5: height = 5

    image = Image.new("RGB", (width, height), (0, 0, 0, 0))

    # Create a drawing context
    draw = ImageDraw.Draw(image)

    # Define circle parameters
    circle_bounds = (0, 0, width, height)  # (left, top, right, bottom)
    circle_color = (255, 255, 255)     # Red color with 50% opacity

    # Draw the circle (ellipse) on the transparent background
    draw.ellipse(circle_bounds, fill=circle_color)

    matte = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    matte[matte < 150] = 0

    circle_color = (255, 0, 0)     # Red color with 50% opacity
    draw.ellipse(circle_bounds, fill=circle_color)

    return np.array(image), matte