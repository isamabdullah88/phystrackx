"""
Equations as pictures: matplotlib's LaTeX (mathtext) drawn to a PNG, for the fit table. Pure
matplotlib (no Qt), so the plot warm-up can draw them on its own thread, and a table then only loads
them. Each picture is drawn at twice the resolution, so it is sharp on a retina screen; the table
shows it at half size.
"""

import io
from functools import lru_cache

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

SCALE = 2           # Drawn at twice the size the table shows it (the table sets the pixel ratio)
DPI = 110 * SCALE   # 11 pt text at 110 dpi is about the table's own text size


@lru_cache(maxsize=None)
def equation_png(tex: str, colour: str = "#2a2a2a") -> bytes:
    """The mathtext `tex` (in $...$) as a transparent PNG, cropped to the text."""
    figure = Figure(dpi=DPI)
    FigureCanvasAgg(figure)
    figure.text(0, 0, tex, fontsize=11, color=colour)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", transparent=True, bbox_inches="tight", pad_inches=0.03)
    return buffer.getvalue()
