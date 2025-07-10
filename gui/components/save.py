

import csv
import customtkinter as ctk
from gui.rigid import Plot
from experiments.components import OCRData

class Save:
    def __init__(self, pdata:Plot, ocrdata:OCRData):
        self.pdata = pdata
        self.ocrdata = ocrdata
        self.filepath = None
        
        self.samplecount = max(self.pdata.samplecount, self.ocrdata.samplecount)
        
    
    def askfilepath(self):
        self.filepath = ctk.filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not self.filepath:
            return
        
    def savedata(self):
        """Saves data onto file path"""
        datalist = self.pdata.data()
        with open(self.filepath, mode='w', newline='') as file:
            
            writer = csv.writer(file)
            
            dt = 1 / self.pdata.fps
            ts = 0.0
            # Prep header
            header = ["T(s)"]
            for i in range(self.pdata.datanum):
                header.extend([f"x{i+1}", f"y{i+1}"])
                
            for i in range(self.ocrdata.datanum):
                header.extend([f"text{i+1}"])

            writer.writerow(header)
            
            # Persist data into file
            for i in range(self.samplecount):
                row = [f"{ts:.06f}"]
                
                if i < self.pdata.samplecount:
                    for tpoints in datalist:
                        cx, cy = tpoints[i,:]
                        row.extend([f"{cx:.02f}", f"{cy:.02f}"])
                
                if i < self.ocrdata.samplecount:
                    for tocr in self.ocrdata.data:
                        txt = tocr[i]
                        row.extend([txt])
                
                ts += dt
                writer.writerow(row)
                    
                    
                    
if __name__ == "__main__":
    import numpy as np
    from .Axes import Axes
    data = [np.random.rand(100, 2) * 100, np.random.rand(100, 2) * 100]
    ocr = [["abc" for _ in range(100)]]
    axes = Axes(ctk.CTk(), None, 200, 200)
    plot = Plot(data, axes, 200, 200, 200, 200)
    
    save = Save(plot, ocr)
    # save.askfilepath()
    save.filepath = "test.csv"
    save.savedata()
    