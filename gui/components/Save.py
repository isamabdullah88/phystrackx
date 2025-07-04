

import csv
import customtkinter as ctk
from gui.Plot import Plot
from .Axes import Axes

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
            
            dt = 1 / self.pdata.fps
            ts = 0.0
            # Prep header
            header = ["T(s)"]
            for i,data in enumerate(datalist):
                header.extend([f"x{i+1}", f"y{i+1}"])
            print('header: ', header)
            writer.writerow(header)
            
            # Persist data into file
            for i in range(self.pdata.samplecount):
                row = [f"{ts:.06f}"]
                for tpoints in datalist:
                    cx, cy = tpoints[i,:]
                    row.extend([f"{cx:.02f}", f"{cy:.02f}"])
                
                ts += dt
                writer.writerow(row)
                # for i in range(self.pdata.samplecount):
                #     cx, cy = data[i]
                #     writer.writerow([i, f"{cx:.02f}", f"{cy:.02f}"])
                    
                    
                    
if __name__ == "__main__":
    import numpy as np
    data = data = [np.random.rand(100, 2) * 100, np.random.rand(100, 2) * 100]
    axes = Axes(ctk.CTk(), None, 200, 200)
    plot = Plot(data, axes, 200, 200, 200, 200)
    
    save = Save(plot, None)
    # save.askfilepath()
    save.filepath = "test.csv"
    save.savedata()
    