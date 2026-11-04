"""A project keeps its saved CSV: written, remembered in the project file, reloaded to plot, and
the next save starts in the same folder (no window needed)."""

import os
import tempfile

import numpy as np

from tests import harness as h
h.setup_env()

import customtkinter as ctk  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from core.project import read_project, write_project  # noqa: E402
from gui.components.plot import save as save_mod  # noqa: E402
from gui.components.plot.csvdata import load_csv  # noqa: E402
from gui.components.plot.plot import Plot  # noqa: E402
from gui.components.plot.save import Save  # noqa: E402
from gui.components.plot.savetype import SaveType  # noqa: E402


class _Data:
    """Stands in for the DataManager of a tracked run."""
    datacount = 1
    ocrcount = 0
    ocrdata = []

    def __init__(self, n=200):
        t = np.arange(n) / 30
        self.timestamps = t
        self.maxcount = n
        self.x = 0.3 * t + 0.5 * np.exp(-0.2 * t) * np.cos(2 * np.pi * t)
        self.y = 2.0 + 0.4 * np.exp(-0.1 * t) * np.sin(2 * np.pi * t)
        self.processed_points = [np.column_stack([self.x, self.y])]


def test_csv_round_trip_and_gap():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    path = os.path.join(folder, "run.csv")
    data = _Data()
    save = Save.__new__(Save)
    save.datamanager = data
    types = [SaveType.HEADER.name, SaveType.TIME.name, SaveType.XY.name]
    save.write(types, path)
    back = load_csv(path)
    h.check("CSV time column comes back exactly", np.array_equal(back.timestamps, data.timestamps))
    h.check("CSV x and y come back exactly", np.array_equal(back.processed_points[0],
                                                             data.processed_points[0]))

    # A shorter object leaves blank cells, which load as NaN rather than breaking the file
    data.processed_points = [data.processed_points[0], data.processed_points[0][:150]]
    data.datacount = 2
    save.write(types, path)
    back = load_csv(path)
    h.check("missing samples load as NaN", len(back.processed_points) == 2 and
            np.isnan(back.processed_points[1][-1]).all())


def test_dialog_starts_in_the_saved_folder():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    seen = {}
    real = ctk.filedialog.asksaveasfilename
    ctk.filedialog.asksaveasfilename = lambda **kw: seen.setdefault("kw", kw) and ""
    try:
        save = Save.__new__(Save)
        save.default_dir = folder
        save.askfilepath()
        h.check("save dialog starts in the saved folder", seen["kw"].get("initialdir") == folder,
                str(seen.get("kw")))
    finally:
        ctk.filedialog.asksaveasfilename = real


def test_saving_remembers_the_folder_and_notifies():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    path = os.path.join(folder, "run.csv")
    got = []
    save = Save.__new__(Save)
    save.datamanager = _Data()
    save.default_dir = None
    save.on_saved = got.append
    save.filepath = path
    real_ask, real_info = save.askfilepath, save_mod.messagebox.showinfo
    save.askfilepath = lambda: None
    save_mod.messagebox.showinfo = lambda *a, **k: None
    try:
        save.savedata([SaveType.HEADER.name, SaveType.XY.name])
    finally:
        save.askfilepath = real_ask
        save_mod.messagebox.showinfo = real_info
    h.check("saving remembers the folder", save.default_dir == folder, str(save.default_dir))
    h.check("saving tells the app the file", got == [os.path.abspath(path)], str(got))


def test_project_file_keeps_the_saved_data_entry():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    proj = os.path.join(folder, "p.phystrack")
    state = {"video": "/v.mp4", "canvas": [1, 1], "trim": None, "crop": None, "axes": None,
             "scale": None, "rects": {"track": [], "track_shapes": [], "ocr": []},
             "data": {"dir": folder, "files": [os.path.join(folder, "run.csv")]}}
    write_project(proj, state)
    h.check("project file keeps the data folder and file",
            read_project(proj)["data"] == state["data"])


def test_plot_works_from_the_loaded_csv():
    folder = tempfile.mkdtemp(dir=h.WORK_DIR)
    path = os.path.join(folder, "run.csv")
    save = Save.__new__(Save)
    save.datamanager = _Data()
    save.write([SaveType.HEADER.name, SaveType.TIME.name, SaveType.XY.name], path)
    loaded = load_csv(path)
    plot = Plot.__new__(Plot)
    plot.datamanager = loaded
    plot._widgets = []
    plot.ploty()
    texts = [tx for a in plt.gcf().axes for tx in a.texts]  # The results panel is beside the plot
    h.check("plot from the saved CSV draws its fit", any("T fit" in tx.get_text() or
                                                         "T peaks" in tx.get_text()
                                                         for tx in texts))
    plt.close("all")


if __name__ == "__main__":
    h.run_tests([test_csv_round_trip_and_gap, test_dialog_starts_in_the_saved_folder,
                 test_saving_remembers_the_folder_and_notifies,
                 test_project_file_keeps_the_saved_data_entry, test_plot_works_from_the_loaded_csv])
