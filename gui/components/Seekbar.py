import customtkinter as ctk
import tkinter as tk

class CutSeekBar(ctk.CTkFrame):
    def __init__(self, master, width=700, height=40, total_frames=100, *args, **kwargs):
        super().__init__(master, width=width, height=height, *args, **kwargs)
        self.pack_propagate(False)

        self.canvas = tk.Canvas(self, width=width, height=height, bg="#222222", highlightthickness=0)
        self.canvas.pack()

        self.total_frames = total_frames
        self.width = width
        self.height = height

        self.start_frame = 20
        self.end_frame = 80
        self.active_marker = None

        self.canvas.bind("<Button-1>", self.click)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.draw()

    def frame_to_x(self, frame):
        return int(frame / self.total_frames * self.width)

    def x_to_frame(self, x):
        return min(max(0, int(x / self.width * self.total_frames)), self.total_frames)

    def draw(self):
        self.canvas.delete("all")

        x1 = self.frame_to_x(self.start_frame)
        x2 = self.frame_to_x(self.end_frame)

        # Draw background bar
        self.canvas.create_rectangle(0, self.height//2 - 4, self.width, self.height//2 + 4, fill="#444")

        # Draw selected range (trim region)
        self.canvas.create_rectangle(x1, self.height//2 - 6, x2, self.height//2 + 6, fill="#3a89f4", outline="")

        # Draw draggable handles
        self.canvas.create_line(x1, 0, x1, self.height, fill="white", width=3, tag="start")
        self.canvas.create_line(x2, 0, x2, self.height, fill="white", width=3, tag="end")

        # Optional: display current range
        self.canvas.create_text(self.width//2, self.height - 8, fill="white",
                                text=f"Trim Range: {self.start_frame} - {self.end_frame}")

    def click(self, event):
        x = event.x
        x1 = self.frame_to_x(self.start_frame)
        x2 = self.frame_to_x(self.end_frame)
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
            self.start_frame = min(max(0, frame), self.end_frame - 1)
        elif self.active_marker == "end":
            self.end_frame = max(min(self.total_frames, frame), self.start_frame + 1)

        self.draw()

    def get_trim_range(self):
        return self.start_frame, self.end_frame


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("800x500")
        self.title("Video Editor Cut Range")

        self.video_view = ctk.CTkFrame(self, width=700, height=300, fg_color="#1a1a1a")
        self.video_view.pack(pady=30)

        self.seekbar = CutSeekBar(self, total_frames=200)
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
