import tkinter as tk
from tkinter import simpledialog
from math import floor

class ScaleRuler:
    def __init__(self, canvas, cwidth, cheight):
        self.canvas = canvas
        self.width = 50
        self.height = 30
        self.p1 = [floor(cwidth/2)-floor(self.width/2), floor(cheight/2)]
        self.p2 = [floor(cwidth/2)+floor(self.width/2), floor(cheight/2)]
        self.scalef = None
        self.dragging = None

        self.draw()
        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        self.canvas.bind("<ButtonRelease-1>", self.onrelease)
        self.canvas.bind("<Double-Button-1>", self.ondclick)

    def ondclick(self, event):
        self.askscale()

    def draw(self):
        self.canvas.delete("ruler")
        x1, y = self.p1
        x2, _ = self.p2

        # Main body
        self.canvas.create_rectangle(x1, y - self.height//2, x2, y + self.height//2, fill="#e0e0e0", outline="black", tags="ruler")

        # Tick marks
        for i in range(11):
            tx = x1 + i * (x2 - x1) / 10
            self.canvas.create_line(tx, y - 10, tx, y + 15, width=2, tags="ruler")
            if self.scalef and i % 2 == 0:
                val = self.scalef * (tx - x1)
                self.canvas.create_text(tx, y + 25, text=f"{val:.1f}", font=("Arial", 9), tags="ruler")

        # Label
        if self.scalef:
            length = abs(x2 - x1)
            self.canvas.create_text((x1 + x2) / 2, y - 25, text=f"{self.scalef * length:.2f} units", font=("Arial", 10, "bold"), fill="blue", tags="ruler")

        # Resize handles
        self.canvas.create_rectangle(x1 - 2, y - 10, x1 + 2, y + 10, fill="red", tags="ruler")
        self.canvas.create_rectangle(x2 - 2, y - 10, x2 + 2, y + 10, fill="red", tags="ruler")

    def askscale(self):
        pixels = abs(self.p2[0] - self.p1[0])
        real = simpledialog.askfloat("Scale", "Enter real-world length this ruler represents:")
        if real and pixels:
            self.scalef = real / pixels
            self.draw()

    def onclick(self, event):
        x, y = event.x, event.y
        if abs(x - self.p1[0]) < 10 and abs(y - self.p1[1]) < 10:
            self.dragging = "resize1"
        elif abs(x - self.p2[0]) < 10 and abs(y - self.p2[1]) < 10:
            self.dragging = "resize2"
        elif self.p1[0]+10 < x < self.p2[0]-10 and self.p1[1] - self.height < y < self.p1[1] + self.height:
            self.dragging = "move"
            self.offset = [x - self.p1[0], y - self.p1[1]]

    def ondrag(self, event):
        if self.dragging == "resize1":
            if abs(self.p2[0] - event.x) > self.width:
                self.p1[0] = event.x
        elif self.dragging == "resize2":
            if abs(self.p1[0] - event.x) > self.width:
                self.p2[0] = event.x
        elif self.dragging == "move":
            dx = event.x - self.p1[0] - self.offset[0]
            dy = event.y - self.p1[1] - self.offset[1]
            self.p1[0] += dx
            self.p2[0] += dx
            self.p1[1] += dy
            self.p2[1] += dy
        
        self.draw()

    def onrelease(self, event):
        self.dragging = None

if __name__ == "__main__":
        
    root = tk.Tk()
    root.geometry("900x600")
    canvas = tk.Canvas(root, width=900, height=600)
    canvas.pack()
    ScaleRuler(canvas, 900, 600)
    root.mainloop()
