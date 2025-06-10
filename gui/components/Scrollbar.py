
import customtkinter as ctk

class ScrollBar:
    def __init__(self, root, width=200, height=200, padx=10, pady=10):
        # toolbar = ctk.CTkFrame(root, width=width, height=height, fg_color="black")
        toolbar = ctk.CTkFrame(root, width=width)
        toolbar.pack(side=ctk.LEFT, fill=None, expand=False, padx=(padx, 0), pady=pady)
        
        # Scrollbar for the canvas
        scrollbar = ctk.CTkScrollbar(toolbar, orientation="vertical")
        scrollbar.pack(side=ctk.RIGHT, fill="y")
        
        # self.canvas = ctk.CTkCanvas(toolbar, width=width, height=height, bg="silver")
        self.canvas = ctk.CTkCanvas(toolbar, width=width, height=height)
        
        self.scrollframe = ctk.CTkFrame(self.canvas, width=width)
        self.canvas.create_window((0, 0), window=self.scrollframe, anchor="nw", width=width, height=height)
        
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.pack(side=ctk.LEFT, fill=None, expand=False, padx=(padx, 0), pady=pady)
        
        
        scrollbar.configure(command=self.canvas.yview)