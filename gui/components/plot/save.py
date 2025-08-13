"""
save.py

Handles saving transformed coordinate and OCR data to CSV using user-defined options.

Author: Isam Balghari
"""

import csv
import customtkinter as ctk
from gui.components.plot.datamanager import DataManager
from tkinter import messagebox
from ..checkbox import Checkbox
from .savetype import SaveType


class Save:
    def __init__(self, parent, datamanager: DataManager) -> None:
        """
        Initializes the Save handler for exporting processed data.

        Args:
            parent: The parent GUI container.
            datamanager (DataManager): DataManager instance with processed tracking and OCR data.
        """
        self.parent = parent
        self.datamanager = datamanager
        self.filepath = None

        self.checkbox = Checkbox(self.parent, SaveType, self.savedata)

    @property
    def datacount(self) -> int:
        return self.datamanager.datacount

    @property
    def samplecount(self) -> int:
        return self.datamanager.samplecount

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
        """Prompts user to select a file path for saving data."""
        self.filepath = ctk.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

    def prepheader(self, savetypes: list[str]) -> list[str]:
        """Prepares the CSV header based on selected save options."""
        header = []
        if SaveType.TIME.name in savetypes:
            header.append("T(s)")

        if SaveType.XY.name in savetypes:
            for i in range(self.datacount):
                header.extend([f"x{i+1}", f"y{i+1}"])

        if SaveType.OCR.name in savetypes:
            for i in range(self.ocrcount):
                header.append(f"text{i+1}")

        return header

    def savedata(self, savetypes: list[str]) -> None:
        """Saves selected data to CSV based on save type options."""
        self.askfilepath()
        if not self.filepath:
            return

        with open(self.filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            if SaveType.HEADER.name in savetypes:
                writer.writerow(self.prepheader(savetypes))

            for i in range(self.samplecount):
                row = []

                if SaveType.TIME.name in savetypes:
                    ts = self.datamanager.timestamps[i]
                    row.append(f"{ts:.06f}")

                if SaveType.XY.name in savetypes:
                    for j in range(self.datacount):
                        x, y = self.points[j][i, :]
                        row.extend([f"{x:.02f}", f"{y:.02f}"])

                if SaveType.OCR.name in savetypes:
                    for o in self.ocr:
                        row.append(o[i])

                writer.writerow(row)
        
        messagebox.showinfo("Success", "Tracked data saved successfully.")


def main():
    """
    GUI-based test for Save functionality using DataManager and dummy data.
    """
    import numpy as np
    import customtkinter as ctk
    from gui.components.axes import Axes
    from gui.components.tpoints import TrackPoint
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

    # --- Dummy TrackPoint data ---
    frame_count = 100
    t = np.linspace(0, 2 * np.pi, frame_count)
    x = 100 + 50 * np.cos(t)
    y = 100 + 50 * np.sin(t)
    fpoints = [[TrackPoint(x[i], y[i], 0, 0) for i in range(frame_count)]]

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
