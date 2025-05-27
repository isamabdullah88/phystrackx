import numpy as np

def ptsellpise(ellipse, numpts=100):
    """Samples points from ellipse"""
    (cx, cy), (a, b), angle = ellipse
    theta = np.radians(angle)
    t = np.linspace(0, 2 * np.pi, numpts)
    
    x = cx + a/2 * np.cos(t) * np.cos(theta) - b/2 * np.sin(t) * np.sin(theta)
    y = cy + a/2 * np.cos(t) * np.sin(theta) + b/2 * np.sin(t) * np.cos(theta)

    return np.stack((y, x), axis=1)  # shape (N, 2)


def ptsline(line, numpts=100):
    """Samples points from line"""
    (x0, y0), (x1, y1) = line

    x = np.linspace(x0, x1, numpts)
    y = np.linspace(y0, y1, numpts)

    return np.stack((y, x), axis=1)