
import customtkinter as ctk

class ScrollBar:
    def __init__(self, root, width=200, height=200, padx=10, pady=10):
        self.width = width - 20
        self.height = height
        self.padx = padx
        self.pady = pady
        toolbar = ctk.CTkFrame(root, width=width, height=height)
        toolbar.pack_propagate(False)
        toolbar.pack(side=ctk.LEFT)
        
        
        self.canvas = ctk.CTkCanvas(toolbar, width=self.width, height=height)
        
        # Scrollbar for the canvas
        self.scrollbar = ctk.CTkScrollbar(toolbar, width=20, orientation="vertical", height=height,
                                          command=self.canvas.yview)
        
        self.scrollframe = ctk.CTkFrame(self.canvas, width=self.width, bg_color="#899fbd", fg_color="#5bdada")
        
    def pack(self):
        self.canvas.create_window((0, 0), window=self.scrollframe, anchor="nw", width=self.width)
        self.canvas.update_idletasks()
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"), yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=ctk.LEFT)
        self.scrollbar.pack(side=ctk.RIGHT)