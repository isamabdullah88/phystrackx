"""Simple smoothing filter. Maintains a window of values and smoothens current value by computing
mean of window."""
import numpy as np

class Smoothen:
    """
    Simple smoothing filter. Maintains a window of values and smoothens current value by 
    computing mean of window.
    """
    def __init__(self, winlen=20, tol=25.):
        self._winlen = winlen
        self._tol = tol

        self._winvals = []

    def smoothen(self, val: float) -> float:
        """Smoothens the value based on the window of values

        Args:
            val (float): current value

        Returns:
            float: smoothed value
        """
        if len(self._winvals) == 0:
            self._winvals.append(val)
            return val

        sval = np.mean(self._winvals)
        if abs(sval - val) < self._tol:
            self._winvals.append(val)
        else:
            self._winvals.append(self._winvals[-1])

        if len(self._winvals) > self._winlen:
            self._winvals.pop(0)

        sval = np.mean(self._winvals)
        return sval
