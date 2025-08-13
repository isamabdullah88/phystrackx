"""
plot.py

Responsible for plotting position and motion derivatives from processed data using matplotlib.

Author: Isam Balghari
"""

import matplotlib.pyplot as plt
import numpy as np
import customtkinter as ctk

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
        self.checkbox = Checkbox(self.parent, PlotType, self.showplots)

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

    def plotx(self):
        for tpts in self.points:
            plt.figure()
            plt.title("X vs Time")
            plt.xlabel("Time (s)")
            plt.ylabel("X")
            plt.plot(self.timestamps, tpts[:, 0], '-m')

    def ploty(self):
        for tpts in self.points:
            plt.figure()
            plt.title("Y vs Time")
            plt.xlabel("Time (s)")
            plt.ylabel("Y")
            plt.plot(self.timestamps, tpts[:, 1], '-m')

    def plotxy(self):
        for tpts in self.points:
            plt.figure()
            plt.title("Y vs X")
            plt.xlabel("X")
            plt.ylabel("Y")
            plt.plot(tpts[:, 0], tpts[:, 1], '-c')

    def plotdx(self):
        for tpts in self.points:
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            plt.figure()
            plt.title("dx/dt")
            plt.xlabel("Time (s)")
            plt.ylabel("dx/dt")
            plt.plot(self.timestamps, dx_dt, '-g')

    def plotdy(self):
        for tpts in self.points:
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            plt.figure()
            plt.title("dy/dt")
            plt.xlabel("Time (s)")
            plt.ylabel("dy/dt")
            plt.plot(self.timestamps, dy_dt, '-g')

    def plotd2x(self):
        for tpts in self.points:
            dx_dt = np.gradient(tpts[:, 0], self.timestamps)
            d2x_dt2 = np.gradient(dx_dt, self.timestamps)
            plt.figure()
            plt.title("d²x/dt²")
            plt.xlabel("Time (s)")
            plt.ylabel("d²x/dt²")
            plt.plot(self.timestamps, d2x_dt2, '-b')

    def plotd2y(self):
        for tpts in self.points:
            dy_dt = np.gradient(tpts[:, 1], self.timestamps)
            d2y_dt2 = np.gradient(dy_dt, self.timestamps)
            plt.figure()
            plt.title("d²y/dt²")
            plt.xlabel("Time (s)")
            plt.ylabel("d²y/dt²")
            plt.plot(self.timestamps, d2y_dt2, '-b')


def main():
    """
    GUI-based test for the Plot system using dummy circular motion data.
    """
    import numpy as np
    import customtkinter as ctk
    from gui.components.tpoints import TrackPoint
    from gui.components.axes import Axes
    from gui.components.plot.datamanager import DataManager
    from gui.components.plot.plot import Plot

    # --- Setup GUI ---
    ctk.set_appearance_mode("System")
    root = ctk.CTk()
    root.geometry("800x600")
    root.title("Plot and Axes Test")

    canvas = ctk.CTkCanvas(root, width=640, height=480, bg="white")
    canvas.pack(pady=10)

    btn_frame = ctk.CTkFrame(root)
    btn_frame.pack(pady=5)
    axes_btn = ctk.CTkButton(btn_frame, text="Set Axes")
    axes_btn.pack()

    btnlist = {"axes": axes_btn}
    axes = Axes(root, canvas, vwidth=640, vheight=480, btnlist=btnlist, activebtn=axes_btn)

    # --- Generate dummy data ---
    t = np.linspace(0, 2 * np.pi, 150)
    x = 50 + 30 * np.cos(t)
    y = 50 + 30 * np.sin(t)
    fpoints = [[TrackPoint(x[i], y[i], 0, 0) for i in range(len(x))]]

    # --- Create DataManager ---
    datamanager = DataManager(
        tpoints=fpoints,
        axes=axes,
        vwidth=640,
        vheight=480,
        fwidth=640,
        fheight=480,
        fps=30,
        scale=1.0
    )

    # --- Setup Axes and Plot after marking ---
    def on_axes_applied():
        datamanager.transform()
        Plot(parent=root, datamanager=datamanager, theme='ggplot')

    axes_btn.configure(command=lambda: [axes.markaxes(), root.after(3000, on_axes_applied)])
    root.mainloop()


if __name__ == "__main__":
    main()
