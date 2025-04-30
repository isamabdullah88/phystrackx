import math
import customtkinter as ctk
import tkinter as tk

class CutSeekBar(ctk.CTkFrame):
    def __init__(self, master, width=700, height=40, fcount=100, ondrag=None, *args, **kwargs):
        super().__init__(master, width=width, height=height, *args, **kwargs)
        self.pack_propagate(False)

        self.canvas = tk.Canvas(self, width=width, height=height, bg="#222222", highlightthickness=0)
        self.canvas.pack()

        self.fcount = fcount
        self.width = width
        self.height = height

        self.startidx = 20
        self.endidx = 80
        self.active_marker = None
        self.idx = self.startidx

        self._ondrag = ondrag

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.draw()


    def setcount(self, fcount):
        self.fcount = fcount
        self.startidx = math.floor(0.2*self.fcount)
        self.endidx = math.floor(0.8*self.fcount)
        self.idx = self.startidx
        self.draw()

    def frame_to_x(self, frame):
        return int(frame / self.fcount * self.width)

    def x_to_frame(self, x):
        return min(max(0, int(x / self.width * self.fcount)), self.fcount)

    def draw(self):
        self.canvas.delete("all")

        x1 = self.frame_to_x(self.startidx)
        x2 = self.frame_to_x(self.endidx)

        # Draw background bar
        self.canvas.create_rectangle(0, self.height//2 - 4, self.width, self.height//2 + 4, fill="#444")

        # Draw selected range (trim region)
        self.canvas.create_rectangle(x1, self.height//2 - 6, x2, self.height//2 + 6, fill="#3a89f4", outline="")

        # Draw draggable handles
        self.canvas.create_line(x1, 0, x1, self.height, fill="white", width=3, tag="start")
        self.canvas.create_line(x2, 0, x2, self.height, fill="white", width=3, tag="end")

        # Optional: display current range
        self.canvas.create_text(self.width//2, self.height - 8, fill="white",
                                text=f"Trim Range: {self.startidx} - {self.endidx}")

    def click(self, event):
        x = event.x
        x1 = self.frame_to_x(self.startidx)
        x2 = self.frame_to_x(self.endidx)
        if abs(x - x1) < 10:
            self.active_marker = "start"
        elif abs(x - x2) < 10:
            self.active_marker = "end"
        else:
            self.active_marker = None

    def drag(self, event):
        x = event.x
        frame = self.x_to_frame(x)

        if self.active_marker == "start":
            self.startidx = min(max(0, frame), self.endidx - 1)
            self.idx = self.startidx
        elif self.active_marker == "end":
            self.endidx = max(min(self.fcount, frame), self.startidx + 1)
            self.idx = self.endidx

        self._ondrag()

        self.draw()

    def get_trim_range(self):
        return self.startidx, self.endidx


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.video_view = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.video_view.pack(pady=30)

        self.seekbar = CutSeekBar(self, fcount=200)
        self.seekbar.pack(pady=20)

        self.print_button = ctk.CTkButton(self, text="Print Cut Range", command=self.print_range)
        self.print_button.pack()

    def print_range(self):
        start, end = self.seekbar.get_trim_range()
        print(f"Selected trim range: Frame {start} to {end}")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()
