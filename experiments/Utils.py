import numpy as np

def ptsellpise(ellipse, num_points=100):
    """Samples points from ellipses"""
    (cx, cy), (a, b), angle = ellipse
    theta = np.radians(angle)
    t = np.linspace(0, 2 * np.pi, num_points)
    
    x = cx + a/2 * np.cos(t) * np.cos(theta) - b/2 * np.sin(t) * np.sin(theta)
    y = cy + a/2 * np.cos(t) * np.sin(theta) + b/2 * np.sin(t) * np.cos(theta)

    return np.stack((y, x), axis=1)  # shape (N, 2)