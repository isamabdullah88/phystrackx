"""
save.py

Handles saving transformed coordinate and OCR data to CSV using user-defined options.

Author: Isam Balghari
"""

import csv
import math
import os

import customtkinter as ctk
from gui.components.plot.datamanager import DataManager
from tkinter import messagebox
from ..checkbox import Checkbox
from .savetype import SaveType


class Save:
    def __init__(self, parent) -> None:
        """
        Initializes the Save handler for exporting processed data.

        Args:
            parent: The parent GUI container.
            datamanager (DataManager): DataManager instance with processed tracking and OCR data.
        """
        self.parent = parent
        self.datamanager = None
        self.filepath = None
        self.default_dir: str | None = None  # Where the save dialog starts (last save, or project's)
        self.on_saved = None  # Optional callback(path) after a CSV is written

    def activate(self, datamanager: DataManager) -> None:
        """
        Activates the Save handler with a DataManager instance.
        """
        self.datamanager = datamanager
        self.checkbox = Checkbox(self.parent, SaveType, text="Choose Data", callback=self.savedata,
                                 defaults=list(SaveType))

    @property
    def datacount(self) -> int:
        return self.datamanager.datacount

    @property
    def samplecount(self) -> int:
        return self.datamanager.maxcount

    @property
    def ocrcount(self) -> int:
        return self.datamanager.ocrcount

    @property
    def points(self):
        return self.datamanager.processed_points

    @property
    def ocr(self):
        return self.datamanager.ocrdata

    def askfilepath(self) -> None:
        """Prompts user to select a file path for saving data, starting in the default folder."""
        options = {"defaultextension": ".csv",
                   "filetypes": [("CSV files", "*.csv"), ("All files", "*.*")]}
        if self.default_dir and os.path.isdir(self.default_dir):
            options["initialdir"] = self.default_dir
        self.filepath = ctk.filedialog.asksaveasfilename(**options)

    def prepheader(self, savetypes: list[str]) -> list[str]:
        """Prepares the CSV header based on selected save options."""
        header = []
        if SaveType.TIME.name in savetypes:
            header.append("T(s)")

        if SaveType.XY.name in savetypes:
            for i in range(self.datacount):
                header.extend([f"x{i+1}", f"y{i+1}", f"r{i+1}"])

        if SaveType.OCR.name in savetypes:
            for i in range(self.ocrcount):
                header.append(f"text{i+1}")

        return header

    def savedata(self, savetypes: list[str]) -> None:
        """Asks where to save, then writes the selected data to CSV."""
        self.askfilepath()
        print('Saving to:', self.filepath)
        if not self.filepath:
            return
        self.write(savetypes, self.filepath)
        self.default_dir = os.path.dirname(os.path.abspath(self.filepath))
        if self.on_saved is not None:
            self.on_saved(os.path.abspath(self.filepath))
        messagebox.showinfo("Success", "Tracked data saved successfully.")

    def write(self, savetypes: list[str], path: str) -> None:
        """Writes the selected data to a CSV file at path."""
        with open(path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if SaveType.HEADER.name in savetypes:
                writer.writerow(self.prepheader(savetypes))

            for i in range(self.samplecount):
                row = []

                if SaveType.TIME.name in savetypes:
                    ts = self.datamanager.timestamps[i]
                    row.append(repr(float(ts)))  # Full precision, no rounding

                if SaveType.XY.name in savetypes:
                    for j in range(self.datacount):
                        if i >= len(self.points[j]):
                            row.extend(["", "", ""])
                            continue

                        x, y = self.points[j][i, :]
                        r = math.hypot(x, y)  # Distance from the axes origin
                        row.extend([repr(float(x)), repr(float(y)), repr(float(r))])

                if SaveType.OCR.name in savetypes:
                    for o in self.ocr:
                        row.append(o[i])
                
                writer.writerow(row)


def main():
    """
    GUI-based test for Save functionality using DataManager and dummy data.
    """
    import numpy as np
    import customtkinter as ctk
    from gui.components.axes import Axes
    from gui.components.tpoints import FPoint
    from gui.components.plot.datamanager import DataManager
    from experiments.components.ocr import OCRData
    from gui.components.plot.save import Save
    from gui.components.plot.savetype import SaveType

    # Initialize GUI
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Save Data Test")
    root.geometry("800x600")

    # Dummy canvas and button for Axes object
    canvas = ctk.CTkCanvas(root, width=640, height=480)
    canvas.pack()
    dummy_btn = ctk.CTkButton(root, text="Dummy")
    btnlist = {"dummy": dummy_btn}
    axes = Axes(root, canvas, vwidth=640, vheight=480, btnlist=btnlist, activebtn=dummy_btn)

    # --- Dummy FPoint data ---
    frame_count = 100
    t = np.linspace(0, 2 * np.pi, frame_count)
    x = 100 + 50 * np.cos(t)
    y = 100 + 50 * np.sin(t)
    fpoints = [[FPoint(x[i], y[i], 0, 0) for i in range(frame_count)]]

    # --- Dummy OCR data ---
    ocr_text = [["OCR={:.2f}s".format(i / 24) for i in range(frame_count)]]
    ocrdata = OCRData(ocr_text)

    # --- DataManager ---
    datamanager = DataManager(
        tpoints=fpoints,
        ocrdata=ocrdata,
        axes=axes,
        vwidth=640,
        vheight=480,
        fwidth=640,
        fheight=480,
        fps=24,
        scale=1.0
    )
    datamanager.transform()

    # --- Save handler ---
    saver = Save(root, datamanager=datamanager)

    root.mainloop()


if __name__ == "__main__":
    main()
