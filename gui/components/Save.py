

import csv
import customtkinter as ctk
from gui.Plot import Plot

class Save:
    def __init__(self, pdata:Plot, ocrdata):
        self.pdata = pdata
        self.ocrdata = ocrdata
        self.filepath = None
        
    
    def askfilepath(self):
        self.filepath = ctk.filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not self.filepath:
            return
        
    def savedata(self):
        """Saves data onto file path"""
        datalist = self.pdata.data()
        with open(self.filepath, mode='w', newline='') as file:
            writer = csv.writer(file)
            for data in datalist:
                writer.writerow(["Frame", "Centroid X (real units)", "Centroid Y (real units)"])
                for i in range(self.pdata.samplecount):
                    cx, cy = data[i]
                    writer.writerow([i, f"{cx:.02f}", f"{cy:.02f}"])