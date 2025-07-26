from math import floor, ceil
from typing import Optional, Callable, override
import customtkinter as ctk
from PIL import Image
from core import abspath
from .bar import Bar
from .viewseekbar import ViewSeekBar
from .seek import Seek


class TrimSeekBar(ViewSeekBar):
    """
    Seekbar widget that allows trimming by using two draggable bars (left and right)
    and dynamically drawn seek regions.
    """

    def __init__(
        self,
        frame,
        width: int,
        height: int,
        fcount: int = 100,
        callback: Optional[Callable] = None
    ):
        super().__init__(frame, width, height, fcount, callback)

        self.startidx = ceil(0.01 * fcount)
        self.endidx = floor(0.99 * fcount)
        self.idx = self.startidx

        self.callback = callback

        self.rseek: Optional[Seek] = None
        self.rightbar: Optional[Bar] = None
        self.bardiff = 50
        self.btnsize = 50

    def set_trparams(self) -> None:
        """Set layout parameters specific to trim mode."""
        self.idx = ceil(0.01 * self.fcount)
        self.xstart = self.padx
        self.xend = self.width - self.padx - self.btnsize - 20

        if self.leftbar is not None:
            self.leftbar.setcount(self.fcount)

    def pack(self) -> None:
        """Draw both seekbars and the two bars for trim range."""
        super().pack()
        self.set_trparams()

        self.varseek = Seek(self.canvas, self.xstart, self.xend, self.height / 2, color="#42f2c9")
        self.varseek.pack()

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

        self.applybtn = self.mkbutton("assets/apply.png", self.onapply, btnsize=self.btnsize)
        self.applybtn.place(
            x=self.width - self.btnsize - 2 * self.padx - 5,
            y=self.height / 2 - self.btnsize / 2 - 5
        )

    def settrim(self, trimvideo, loadvideo) -> None:
        """Assign trimming and reload callback functions."""
        self.trimvideo = trimvideo
        self.loadvideo = loadvideo

    def clearright(self) -> None:
        """Clear the right bar from canvas and reset parameters."""
        if self.rightbar is not None:
            self.rightbar.clear()
            self.rightbar.x = self.xend
            self.bardiff = 0

        super().setparams()

    def clear(self) -> None:
        """Clear left and right bars."""
        super().clear()
        self.clearright()

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

    @override
    def onclick(self, event) -> None:
        """Handle click on left or right bar."""
        self.leftbar.onclick(event)
        self.rightbar.onclick(event)

        if self.leftbar.clicked or self.rightbar.clicked:
            self.callback()

    @override
    def ondrag(self, event) -> None:
        """Handle drag motion and update seek visuals."""
        self.startidx = self.leftbar.idx
        self.endidx = self.rightbar.idx

        self.fixedseek.draw(self.leftbar.xstart, self.leftbar.xend)
        self.varseek.draw(self.leftbar.x, self.rightbar.x)

        lfunc = lambda x, xlim: min(x, xlim - self.bardiff)
        self.leftbar.ondrag(event, lfunc, self.rightbar.x)

        rfunc = lambda x, xlim: max(x, xlim + self.bardiff)
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
            self.clearright()
            super().pack()
            self.loadvideo("")


# Optional test driver
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.frame = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.frame.pack(fill="both", expand=True)

        self.canvas = ctk.CTkCanvas(self.frame)
        self.canvas.pack(fill="both", expand=True)

        self.tseekbar = TrimSeekBar(self.frame, 600, 100, 2000, callback=self.callback)
        self.tseekbar.pack()

    def callback(self):
        print('callback triggered')


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
