import numpy as np

def ptsellpise(ellipse, numpts=100):
    """Samples points from ellipse"""
    (cx, cy), (a, b), angle = ellipse
    theta = np.radians(angle)
    t = np.linspace(0, 2 * np.pi, numpts)
    
    x = cx + a/2 * np.cos(t) * np.cos(theta) - b/2 * np.sin(t) * np.sin(theta)
    y = cy + a/2 * np.cos(t) * np.sin(theta) + b/2 * np.sin(t) * np.cos(theta)

    return np.stack((y, x), axis=1)  # shape (N, 2)


def ptsline(lcoords, numpts=10, xoff=0, yoff=0):
    """Samples points from line"""
    linepts = []
    
    for i in range(len(lcoords)-1):
        x0, y0 = lcoords[i]
        x1, y1 = lcoords[i+1]

        x = np.linspace(x0, x1, numpts) - xoff
        y = np.linspace(y0, y1, numpts) - yoff
        
        l = np.stack((x, y), axis=1)
        linepts.append(l)
    
    return np.array(linepts).reshape(-1, 2)  # shape (N, 2)