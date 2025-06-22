import tkinter as tk

class ProgressBar:
    def __init__(self, canvas, vwidth=200, vheight=100, bheight=30, bg="#e2bcc5", fg="#5e0492"):
        # super().__init__(parent)
        # self.canvas = tk.Canvas(self, width=width, height=height, highlightthickness=10)
        # self.canvas.pack()
        self.canvas = canvas
        self.width = vwidth
        self.height = vheight
        self.bheight = bheight
        self.bg = bg
        self.fg = fg

        # Background bar
        self.bholder = self.canvas.create_rectangle(0, self.height-self.bheight, self.width, self.height, fill=bg, outline='black')

        # Foreground progress bar (initially 0)
        self.bar = self.canvas.create_rectangle(0, self.height-self.bheight, 10, self.height, fill=fg, outline='')

    def set(self, percent):
        """Set progress between 0 and 100."""
        percent = max(0, min(100, percent))  # Clamp to [0, 100]
        bar_width = (percent / 100) * self.width
        self.canvas.coords(self.bar, 0, self.height-self.bheight, bar_width, self.height)
        
    def destroy(self):
        self.canvas.delete(self.bholder)
        self.canvas.delete(self.bar)

# Example usage
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Custom Progress Bar")

    progress = ProgressBar(root, width=300, height=30)
    progress.pack(pady=20)

    # progress.set(65)  # Set to 65%

    root.mainloop()
