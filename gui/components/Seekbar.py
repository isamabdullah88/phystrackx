from math import floor
import customtkinter as ctk
import tkinter as tk

class CutSeekBar:
    def __init__(self, master, width=200, height=40, fcount=100, ondrag=None, *args, **kwargs):
        # super().__init__(master, width=width, height=height, *args, **kwargs)
        # self.pack_propagate(False)
        # frame = ctk.CTkFrame(master, width=width, height=height)
        # frame.pack_propagate(False)

        self.canvas = tk.Canvas(master, width=width, height=height, bg="#4d535c")
        self.canvas.pack()

        self.fcount = fcount
        self.width = width
        self.height = height

        self.startidx = 1
        self.endidx = 98
        self.active_marker = None
        self.idx = self.startidx

        self._ondrag = ondrag

        self.draw()
        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)


    def setcount(self, fcount):
        self.fcount = fcount
        # self.startidx = floor(0.2*self.fcount)
        self.startidx = 1
        # self.endidx = floor(0.8*self.fcount)
        self.endidx = self.fcount-1
        self.idx = self.startidx
        self.draw()

    def frame_to_x(self, frame):
        return int(frame / self.fcount * self.width)

    def x_to_frame(self, x):
        return min(max(0, int(x / self.width * self.fcount)), self.fcount)

    def draw(self):
        self.canvas.delete("all")

        x1 = self.frame_to_x(self.startidx) + 5
        x2 = self.frame_to_x(self.endidx) - 5

        recth = floor(self.height/2)
        # print('recth: ', recth)
        # Draw background bar
        self.canvas.create_rectangle(5, recth - 3, self.width-5, recth + 3, fill="#e2bcc5")

        # Draw selected range (trim region)
        self.canvas.create_rectangle(x1, recth - 4, x2, recth + 4, fill="#e74ce0", outline="")

        # Draw draggable handles
        self.canvas.create_rectangle(x1-2, 10, x1+2, self.height-10, fill="#1eff00", outline="", tag="start")
        self.canvas.create_rectangle(x2-2, 10, x2+2, self.height-10, fill="#1eff00", outline="", tag="end")

        # Optional: display current range
        self.canvas.create_text(self.width//2, recth+10, fill="#ffffff",
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

        if (self._ondrag is not None) and (self.endidx < self.fcount):
            print('endidx: ', self.endidx)
            self._ondrag()

            self.draw()

    def get_trim_range(self):
        return self.startidx, self.endidx


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.videoview = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.videoview.pack(pady=30)

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
