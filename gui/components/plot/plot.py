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
    def __init__(self, parent, datamanager: DataManager, theme: str = 'ggplot') -> None:
        """
        Initializes the Plot component for visualizing data.

        Args:
            parent: The parent GUI container.
            datamanager (DataManager): The data manager with transformed coordinates.
            theme (str): Matplotlib theme style.
        """
        self.parent = parent
        self.datamanager = datamanager

        plt.style.use(theme)
        self.checkbox = Checkbox(self.parent, PlotType, text="Choose Plots", callback=self.showplots)

    @property
    def points(self):
        return self.datamanager.processed_points

    @property
    def timestamps(self):
        return self.datamanager.timestamps
    
    @property
    def xmin(self):
        return self.datamanager.xmin
    
    @property
    def xmax(self):
        return self.datamanager.xmax
    
    @property
    def ymin(self):
        return self.datamanager.ymin
    
    @property
    def ymax(self):
        return self.datamanager.ymax

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

    def plotx(self):
        for k, tpts in enumerate(self.points):
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$x$ vs $T$", fontname= "Segoe UI Emoji")
            plt.xlabel(r"$T(s)$")
            plt.ylabel(r"$x$")
            plt.xlim((0, self.timestamps[-1]))
            plt.ylim((self.xmin, self.xmax))
            plt.plot(self.timestamps, tpts[:, 0], '-m')

    def ploty(self):
        for k, tpts in enumerate(self.points):
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$y$ vs $T$", fontname= "Segoe UI Emoji")
            plt.xlabel(r"$T(s)$")
            plt.ylabel(r"$y$")
            plt.xlim((0, self.timestamps[-1]))
            plt.ylim((self.ymin, self.ymax))
            plt.plot(self.timestamps, tpts[:, 1], '-m')

    def plotxy(self):
        for k, tpts in enumerate(self.points):
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$y$ vs $x$", fontname= "Segoe UI Emoji")
            plt.xlabel(r"$x$")
            plt.ylabel(r"$y$")
            plt.xlim((self.xmin, self.xmax))
            plt.ylim((self.ymin, self.ymax))
            plt.plot(tpts[:, 0], tpts[:, 1], '-c')

    def plotdx(self):
        for k, tpts in enumerate(self.points):
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$\frac{dx}{dt}$", fontname= "Segoe UI Emoji")
            plt.xlabel(r"$T(s)$")
            plt.ylabel(r"$\frac{dx}{dt}$")
            plt.xlim((np.min(self.timestamps), np.max(self.timestamps)))
            xmin = min(self.xmin, np.min(dx_dt))
            xmax = max(self.xmax, np.max(dx_dt))
            plt.ylim((xmin, xmax))
            plt.plot(self.timestamps, dx_dt, '-g')

    def plotdy(self):
        for k, tpts in enumerate(self.points):
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$\frac{dy}{dt}$", fontname= "Segoe UI Emoji")
            plt.xlabel("Time (s)")
            plt.ylabel(r"$\frac{dy}{dt}$")
            plt.xlim((np.min(self.timestamps), np.max(self.timestamps)))
            ymin = min(self.ymin, np.min(dy_dt))
            ymax = max(self.ymax, np.max(dy_dt))
            plt.ylim((ymin, ymax))
            plt.plot(self.timestamps, dy_dt, '-g')

    def plotd2x(self):
        for k, tpts in enumerate(self.points):
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            d2x_dt2 = np.gradient(dx_dt, self.timestamps)
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$\frac{d^2x}{dt^2}$", fontname= "Segoe UI Emoji")
            plt.xlabel(r"$T(s)$")
            plt.ylabel(r"$\frac{d^2x}{dt^2}$")
            plt.xlim((0, self.timestamps[-1]))
            xmin = min(self.xmin, np.min(d2x_dt2))
            xmax = max(self.xmax, np.max(d2x_dt2))
            plt.ylim((xmin, xmax))
            plt.plot(self.timestamps, d2x_dt2, '-b')

    def plotd2y(self):
        for k, tpts in enumerate(self.points):
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            d2y_dt2 = np.gradient(dy_dt, self.timestamps)
            plt.figure()
            plt.title(f"[O-{k+1}] " + r"$\frac{d^2y}{dt^2}$", fontname= "Segoe UI Emoji")
            plt.xlabel(r"$T(s)$")
            plt.ylabel(r"$\frac{d^2y}{dt^2}$")
            plt.xlim((0, self.timestamps[-1]))
            ymin = min(self.ymin, np.min(d2y_dt2))
            ymax = max(self.ymax, np.max(d2y_dt2))
            plt.ylim((ymin, ymax))
            plt.plot(self.timestamps, d2y_dt2, '-b')


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
