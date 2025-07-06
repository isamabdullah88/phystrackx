import customtkinter as ctk
from tkinter import ttk
from enum import Enum
from .Slider import Slider

class Radiobox(ctk.CTkToplevel):
    def __init__(self, canvas, vwidth, vheight, title="Select Option", options:Enum=None, callback=None, onselect=None):
        """soptions: Options where slider will spawn"""
        super().__init__(canvas)
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.title(title)
        self.geometry("480x320")
        self.resizable(False, False)
        self.grab_set()

        if options is None:
            options = []

        self.callback = callback
        # self.soptions = soptions
        self.onselect = onselect
        self.selected = ctk.StringVar(value=next(iter(options)).name)
        self.bcvalue = ctk.IntVar(value=0)

        # Title
        ctk.CTkLabel(self, text=title, font=("Segoe UI", 18, "bold")).pack(pady=(15, 5))
        self.slider = None

        # Grid for radio buttons
        self.grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(padx=20, pady=10)

        cols = 3
        for idx, option in enumerate(options):
            rb = ctk.CTkRadioButton(self.grid_frame, text=option.name, variable=self.selected, value=option.name, command=self.onselect)
            row = idx // cols
            col = idx % cols
            rb.grid(row=row, column=col, padx=15, pady=10, sticky="w")

        # Confirm button
        ctk.CTkButton(self, text="✓ Apply", command=lambda: self.callback(None), width=120).pack(pady=15)
        
    # def onselect(self):
    #     if self.slider:
    #         self.slider.destroy()
    #         self.slider = None
            
        
        # select = self.selected.get()
        # print('selected: ', select)
        # for option in self.soptions:
        #     if select == option:
                # self.slider = ttk.Scale(self, from_=1, to=100, orient='horizontal', variable=self.bcvalue, command=lambda event: self.callback(select))
                # self.slider.pack(side="bottom")
                
                # self.canvas.create_window(self.vwidth - 60, self.vheight - 20, window=self.slider)
        
        # if filter == FilterTypes.CONTRAST.name:
        #     self.slider = ttk.Scale(self.canvas, from_=1, to=10, orient='horizontal', variable=self.bcvalue, command=lambda: self.bcupdate(filter))
        #     self.canvas.create_window(self.vwidth - 60, self.vheight - 20, window=self.slider)

    # def onapply(self):
    #     if self.callback:
    #         self.callback(self.selected.get())
    #     self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("400x300")
        self.title("Main App")

        ctk.CTkButton(self, text="Choose Mode", command=self.open_popup).pack(pady=50)

    def open_popup(self):
        modes = ["Fast", "Balanced", "Accurate", "Experimental", "Legacy", "Disabled"]
        RadioBox(self, title="Select Processing Mode", options=modes, default="Balanced", callback=self.handle_choice)

    def handle_choice(self, selected_mode):
        print("Selected Mode:", selected_mode)

if __name__ == "__main__":
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    App().mainloop()
