
from tkinter import messagebox
from customtkinter import CTkCanvas
import math
from .Utils import plcbutton
from .Line import Line

class Geometry:
    def __init__(self, canvas:CTkCanvas, vwidth:int, vheight:int):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self.spoint = None
        self.lines = []
        
        self.tkline = None
        # self.tklines = []
        # self.slt_tklines = []
        self.sltlines = []
        
        # self.slt_lines = [] # selected point lines
        self.selected = False
        
        
    def pack(self):
        self.anglebtn = plcbutton(self.canvas, "assets/plugins/angle.png", self.cmpangle, 40)
        
        self.canvas.bind("<ButtonPress-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        self.canvas.bind("<ButtonRelease-1>", self.onrelease)
        
        
    def onclick(self, event):
        spoint = event.x, event.y
        
        clsline = self.pointonlines(spoint)
        if clsline:
            self.canvas.itemconfigure(clsline.tkline, width=4, fill="#d4f3db")
            self.sltlines.append(clsline)
            self.selected = True
        else:
            self.selected = False
            self.spoint = spoint
            self.tkline = self.canvas.create_line(event.x, event.y, event.x, event.y, fill="#4fcfbe", width=2)
        
    def ondrag(self, event):
        if self.tkline:
            self.canvas.coords(self.tkline, self.spoint[0], self.spoint[1], event.x, event.y)
            
            
    def onrelease(self, event):
        if self.selected:
            return
        
        self.epoint = event.x, event.y
        self.canvas.coords(self.tkline, self.spoint[0], self.spoint[1], event.x, event.y)
        self.canvas.itemconfigure(self.tkline, fill="#28a745", width=3)
        
        self.lines.append(Line(self.tkline, (self.spoint, self.epoint)))
        self.anglebtn.place(x=self.vwidth-80, y=self.vheight-60)
        
    def cmpangle(self):
        """Computes angle between two lines via dot product of vectors"""
        if len(self.sltlines) < 2:
            messagebox.showerror("Error", "No lines selected. Please select two lines.")
            return
            
        line1, line2 = self.sltlines
        
        a1, a2 = line1.line
        b1, b2 = line2.line

        v1 = (a2[0] - a1[0], a2[1] - a1[1])
        v2 = (b2[0] - b1[0], b2[1] - b1[1])

        dot = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.hypot(*v1)
        mag2 = math.hypot(*v2)

        if mag1 == 0 or mag2 == 0:
            angle_deg = 0
        else:
            cos_theta = dot / (mag1 * mag2)
            cos_theta = max(min(cos_theta, 1), -1)
            angle_rad = math.acos(cos_theta)
            angle_deg = math.degrees(angle_rad)

        # Draw angle text between the two lines
        mid_x = (a2[0] + b2[0]) // 2
        mid_y = (a2[1] + b2[1]) // 2
        self.canvas.create_text(mid_x, mid_y, text=f"{angle_deg:.2f}°", font=("Arial", 14), fill="red")
        
        # Clear
        self.canvas.itemconfigure(self.sltlines[0].tkline, width=3, fill="#28a745")
        self.canvas.itemconfigure(self.sltlines[1].tkline, width=3, fill="#28a745")
        self.sltlines.clear()
        self.selected = False
        
        
    def pointonlines(self, point):
        if (len(self.lines) < 2) or (len(self.sltlines) >= 2):
            return
        
        for cline in self.lines:
            # exclude already selected lines
            if cline in self.sltlines:
                continue
            
            ponline = self.pointonline(point, cline.line)
            if ponline:
                return cline
        
        return None
        
    def pointonline(self, point, line, threshold=6):
        """Check if point is near a line segment."""
        startl, endl = line
        x0, y0 = point
        x1, y1 = startl
        x2, y2 = endl

        dx = x2 - x1
        dy = y2 - y1
        if dx == dy == 0:
            return False

        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / float(dx*dx + dy*dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        dist = math.hypot(x0 - proj_x, y0 - proj_y)
        return dist <= threshold