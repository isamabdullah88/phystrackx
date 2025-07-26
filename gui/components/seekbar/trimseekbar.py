
from typing import Optional, Callable
from math import ceil
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from .seek import Seek
from .bar import Bar
from core import abspath


class TrimSeekBar:
    """
    Seekbar widget that allows trimming by using two draggable bars (left and right)
    and dynamically drawn seek regions.
    """

    def __init__(
        self,
        frame: tk.Frame,
        width: int,
        height: int,
        fcount: int = 100,
        callback: Optional[Callable] = None
    ) -> None:
        """
        Initialize the ViewSeekBar.

        Args:
            frame: Parent Tkinter frame.
            width: Width of the seekbar canvas.
            height: Height of the seekbar canvas.
            fcount: Total number of frames.
            callback: Callback function on bar movement.
        """
        self.canvas = tk.Canvas(frame, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.btnsize = 50
        self.mintrim = 50
        self.fcount = fcount
        self.startidx = self.idx = 0
        self.endidx = fcount
        self.padx = 10
        self.width = width - self.btnsize - 40
        self.height = height
        self.callback = callback

        self.fixedseek: Optional[Seek] = None
        self.varseek: Optional[Seek] = None
        self.leftbar: Optional[Bar] = None
        self.rightbar: Optional[Bar] = None

    def setparams(self) -> None:
        """Set internal layout parameters based on current frame count."""
        self.idx = ceil(0.01 * self.fcount)
        self.xstart = self.padx
        self.xend = self.width - self.padx

        if self.leftbar is not None:
            self.leftbar.setcount(self.fcount)
            
        if self.rightbar is not None:
            self.rightbar.setcount(self.fcount)

    def clear(self) -> None:
        """Clear bar from canvas."""
        if self.leftbar is not None:
            self.leftbar.clear()
            
        if self.fixedseek is not None:
            self.fixedseek.clear()
            
        if self.rightbar is not None:
            self.rightbar.clear()
            
        if self.varseek is not None:
            self.varseek.clear()

    def pack(self) -> None:
        """Render the seek and bar on the canvas."""
        self.clear()
        self.setparams()

        self.fixedseek = Seek(
            self.canvas,
            self.xstart,
            self.xend,
            self.height / 2,
            color="#9c97d6"
        )
        self.fixedseek.pack()
        
        self.varseek = Seek(
            self.canvas,
            self.xstart + self.padx,
            self.xend - self.padx,
            self.height / 2,
            color="#42f2c9"
        )
        self.varseek.pack()

        self.leftbar = Bar(
            self.canvas,
            self.xstart + self.padx,
            self.xstart,
            self.xend,
            self.height / 2,
            self.fcount,
            callback=self.callback
        )
        self.leftbar.pack()
        
        self.rightbar = Bar(
            self.canvas,
            self.xend - self.padx,
            self.xstart,
            self.xend,
            self.height / 2,
            self.fcount,
            callback=self.callback
        )
        self.rightbar.pack()
        
        self.canvas.tag_raise(self.varseek.tkrect, self.fixedseek.tkrect)

        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        
        self.applybtn = self.mkbutton("assets/apply.png", self.onapply, btnsize=self.btnsize)
        self.applybtn.place(
            x=self.width + 10,
            y=self.height / 2 - self.btnsize / 2 - 5
        )

    def set(self, fcount: int) -> None:
        """Update frame count and refresh internal parameters."""
        self.fcount = fcount
        self.setparams()
    
    def settrim(self, trimvideo, loadvideo) -> None:
        """Assign trimming and reload callback functions."""
        self.trimvideo = trimvideo
        self.loadvideo = loadvideo

    def onclick(self, event) -> None:
        """Handle click on left or right bar."""
        self.leftbar.onclick(event)
        self.rightbar.onclick(event)

        if self.leftbar.clicked or self.rightbar.clicked:
            self.callback()

    def ondrag(self, event) -> None:
        """Handle drag motion and update seek visuals."""
        self.startidx = self.leftbar.idx
        self.endidx = self.rightbar.idx

        self.fixedseek.draw(self.leftbar.xstart, self.leftbar.xend)
        self.varseek.draw(self.leftbar.x, self.rightbar.x)

        lfunc = lambda x, xlim: min(x, xlim - self.mintrim)
        self.leftbar.ondrag(event, lfunc, self.rightbar.x)

        rfunc = lambda x, xlim: max(x, xlim + self.mintrim)
        self.rightbar.ondrag(event, rfunc, self.leftbar.x)

        if self.leftbar.clicked:
            self.idx = self.startidx
        if self.rightbar.clicked:
            self.idx = self.endidx

    def onapply(self) -> None:
        """Apply the selected trim and optionally reload video."""
        self.applybtn.place_forget()

        if self.trimvideo is not None:
            self.trimvideo(self.startidx, self.endidx)

        if self.loadvideo is not None:
            self.set(self.endidx - self.startidx)
            self.loadvideo("")
            
        self.clear()
        
    def mkbutton(self, imgpath, command, btnsize=30):
        """
        Create an image button for the seekbar.

        Args:
            imgpath: Path to the image file.
            command: Function to execute on click.
            btnsize: Button width and height.
        """
        img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
        img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
        button = ctk.CTkButton(
            self.canvas,
            text="",
            width=btnsize,
            height=btnsize,
            image=img,
            command=command
        )
        button.image = img  # prevent garbage collection
        return button


# --- Optional minimal test app ---



class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = tk.Frame(self, width=700, height=300)
        self.frame.pack(fill="both", expand=True)

        self.seekbar = TrimSeekBar(self.frame, 700, 100, fcount=100, callback=self.callback)
        self.seekbar.pack()
        self.seekbar.settrim(self.trimvideo, self.loadvideo)

    def callback(self):
        print('callback called: ' + str(time.time()))
        
    def trimvideo(self, arg1, arg2):
        print("Trim")
        
    def loadvideo(self, arg1):
        print("Load")


if __name__ == "__main__":
    import time
    app = App()
    app.mainloop()
