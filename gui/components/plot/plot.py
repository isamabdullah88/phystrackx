"""
plot.py

Responsible for plotting position and motion derivatives from processed data using matplotlib.

Author: Isam Balghari
"""

import matplotlib.pyplot as plt
import numpy as np

from gui.components.checkbox import Checkbox
from .plottype import PlotType
from .datamanager import DataManager


class Plot:
    def __init__(self, parent, theme: str = 'ggplot') -> None:
        """
        Initializes the Plot component shell.
        Data coupling is deferred until activate() is invoked.

        Args:
            parent: The parent GUI container.
            theme (str): Matplotlib theme style.
        """
        self.parent = parent
        self.datamanager: DataManager | None = None
        
        # Apply the visual plotting environment profile
        plt.style.use(theme)
        
    def activate(self, datamanager: DataManager, theme: str = 'ggplot') -> None:
    
        """
        Initializes the Plot component for visualizing data.

        Args:
            parent: The parent GUI container.
            datamanager (DataManager): The data manager with transformed coordinates.
            theme (str): Matplotlib theme style.
        """
        self.datamanager = datamanager
        
        self.checkbox = Checkbox(self.parent, PlotType, text="Choose Plots", callback=self.showplots)

    @property
    def points(self):
        return self.datamanager.processed_points

    @property
    def timestamps(self):
        return self.datamanager.timestamps

    def showplots(self, selected_plots: list[str]) -> None:
        """Displays all selected plots."""
        plot_map = {
            PlotType.X.name: self.plotx,
            PlotType.Y.name: self.ploty,
            PlotType.XY.name: self.plotxy,
            PlotType.DX.name: self.plotdx,
            PlotType.DY.name: self.plotdy,
            PlotType.D2X.name: self.plotd2x,
            PlotType.D2Y.name: self.plotd2y
        }

        for plot_type in selected_plots:
            plot_func = plot_map.get(plot_type)
            if plot_func:
                plot_func()

        plt.show(block=False)

    def _plot(self, xdata, ydata, xlabel, ylabel, title, color):
        plt.figure()
        plt.title(title, fontname="Segoe UI Emoji")
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)

        xmin, xmax = np.min(xdata), np.max(xdata)
        ymin, ymax = np.min(ydata), np.max(ydata)
        plt.xlim((xmin*0.90, xmax*1.10))  # Add a 10% margin for better visibility
        plt.ylim((ymin*0.90, ymax*1.10))  # Add a 10% margin for better visibility
        plt.plot(xdata, ydata, '.', color=color)

    def plotx(self):
        for k, tpts in enumerate(self.points):
            self._plot(self.timestamps, tpts[:, 0], xlabel=r"$T(s)$", ylabel=r"$x$",
                       title=f"[O-{k+1}] " + r"$x$ vs $T$", color='m')

    def ploty(self):
        for k, tpts in enumerate(self.points):
            self._plot(self.timestamps, tpts[:, 1], xlabel=r"$T(s)$", ylabel=r"$y$",
                       title=f"[O-{k+1}] " + r"$y$ vs $T$", color='m')

    def plotxy(self):
        for k, tpts in enumerate(self.points):
            self._plot(tpts[:, 0], tpts[:, 1], xlabel=r"$x$", ylabel=r"$y$",
                       title=f"[O-{k+1}] " + r"$y$ vs $x$", color='c')

    def plotdx(self):
        for k, tpts in enumerate(self.points):
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            self._plot(self.timestamps, dx_dt, xlabel=r"$T(s)$", ylabel=r"$\frac{dx}{dt}$",
                       title=f"[O-{k+1}] " + r"$\frac{dx}{dt}$", color='g')

    def plotdy(self):
        for k, tpts in enumerate(self.points):
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            self._plot(self.timestamps, dy_dt, xlabel=r"$T(s)$", ylabel=r"$\frac{dy}{dt}$",
                       title=f"[O-{k+1}] " + r"$\frac{dy}{dt}$", color='g')

    def plotd2x(self):
        for k, tpts in enumerate(self.points):
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            d2x_dt2 = np.gradient(dx_dt, self.timestamps)
            self._plot(self.timestamps, d2x_dt2, xlabel=r"$T(s)$", ylabel=r"$\frac{d^2x}{dt^2}$",
                       title=f"[O-{k+1}] " + r"$\frac{d^2x}{dt^2}$", color='b')

    def plotd2y(self):
        for k, tpts in enumerate(self.points):
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            d2y_dt2 = np.gradient(dy_dt, self.timestamps)
            self._plot(self.timestamps, d2y_dt2, xlabel=r"$T(s)$", ylabel=r"$\frac{d^2y}{dt^2}$",
                       title=f"[O-{k+1}] " + r"$\frac{d^2y}{dt^2}$", color='b')


def main():
    """
    GUI-based test for the Plot system using dummy circular motion data.
    """
    import numpy as np
    import customtkinter as ctk
    from gui.components.tpoints import FPoint
    from gui.components.axes import Axes
    from gui.components.plot.datamanager import DataManager
    from gui.components.plot.plot import Plot
    from experiments.components.ocr import OCRData

    # --- Setup GUI ---
    ctk.set_appearance_mode("System")
    root = ctk.CTk()
    root.geometry("900x800")
    root.title("Plot and Axes Test")

    canvas = ctk.CTkCanvas(root, width=600, height=500, bg="white")
    canvas.pack(pady=10)

    btn_frame = ctk.CTkFrame(root)
    btn_frame.pack(pady=5)
    axes_btn = ctk.CTkButton(btn_frame, text="Set Axes")
    axes_btn.pack()

    btnlist = {"axes": axes_btn}
    axes = Axes(root, canvas, vwidth=600, vheight=500, btnlist=btnlist, activebtn=axes_btn)

    # --- Generate dummy data ---
    t = np.linspace(0, 2*np.pi, 360)
    x = 100 + 200 + 200 * np.cos(t)
    y = 200 + 200 * np.sin(t)

    fpoints = [[FPoint(x[i], y[i], 0, 0) for i in range(len(x))], 
               [FPoint(x[i], y[i], 0, 0) for i in range(len(x))]]

    # --- Dummy OCR data ---
    ocr_text = [["OCR={:.2f}s".format(i / 24) for i in range(len(x))],
                ["OCR={:.2f}s".format(i / 24) for i in range(len(x))]]
    ocrdata = OCRData(ocr_text)

    # --- Create DataManager ---
    datamanager = DataManager(tpoints=fpoints, ocrdata=ocrdata, axes=axes, vwidth=600, vheight=500,
                              fwidth=600, fheight=500, fps=1, scale=1.0)

    # --- Setup Axes and Plot after marking ---
    def on_axes_applied():
        datamanager.transform()
        Plot(parent=root, datamanager=datamanager, theme='ggplot')

    axes_btn.configure(command=lambda: [axes.markaxes(), root.after(3000, on_axes_applied)])
    root.mainloop()


if __name__ == "__main__":
    main()
