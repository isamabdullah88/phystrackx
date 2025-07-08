
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
        self.sltlines = []
        
        self.selected = False
        
        self.sltcolor = "#d4f3db"
        self.unsltcolor = "#28a745"
        self.dragcolor = "#4fcfbe"
        
        self.showbtn = False
        
        
    def pack(self):
        self.anglebtn = plcbutton(self.canvas, "assets/plugins/angle.png", self.cmpangle, 40)
        self.distancebtn = plcbutton(self.canvas, "assets/plugins/distance.png", self.cmpdist, 40)
        self.delbtn = plcbutton(self.canvas, "assets/bin.png", self.delline, 40)
        
        self.canvas.bind("<ButtonPress-1>", self.onclick)
        self.canvas.bind("<B1-Motion>", self.ondrag)
        self.canvas.bind("<ButtonRelease-1>", self.onrelease)
        
        
    def onclick(self, event):
        spoint = event.x, event.y
        
        clsline = self.pointonlines(spoint)
        if clsline:
            self.selected = True
            print('clsline selected: ', clsline.selected)
            if clsline.selected: # if already, selected, deselect
                self.canvas.itemconfigure(clsline.tkline, width=3, fill=self.unsltcolor)
                clsline.selected = False
                self.sltlines.remove(clsline)
                # self.selected = False
            else:
                print('selected')
                if len(self.sltlines) >= 2:
                    return
                
                self.canvas.itemconfigure(clsline.tkline, width=4, fill=self.sltcolor)
                clsline.selected = True
                self.sltlines.append(clsline)
                print('sltlines: ', self.sltlines)
                # self.selected = True
        else:
            print('draw')
            self.selected = False
            self.spoint = spoint
            self.tkline = self.canvas.create_line(event.x, event.y, event.x, event.y, fill=self.dragcolor, width=2)
        
    def ondrag(self, event):
        if self.tkline and (not self.selected):
            self.canvas.coords(self.tkline, self.spoint[0], self.spoint[1], event.x, event.y)
            
            
    def onrelease(self, event):
        if self.selected:
            return
        
        print('released')
        print('selected: ', self.selected)
        
        llength = math.sqrt((self.spoint[0]-event.x)**2 + (self.spoint[1]-event.y)**2)
        if llength < 10:
            self.canvas.delete(self.tkline)
            return
        
        print('Line formation')
        
        self.epoint = event.x, event.y
        self.canvas.coords(self.tkline, self.spoint[0], self.spoint[1], event.x, event.y)
        self.canvas.itemconfigure(self.tkline, fill=self.unsltcolor, width=3)
        
        self.lines.append(Line(self.tkline, (self.spoint, self.epoint)))
        
        # Show buttons
        if not self.showbtn:
            self.showbtn = True
            self.anglebtn.place(x=self.vwidth-80, y=self.vheight-180)
            self.distancebtn.place(x=self.vwidth-80, y = self.vheight-120)
            self.delbtn.place(x=self.vwidth-80, y=self.vheight-60)
        
    
    def pointonlines(self, point):
        # print('slc lines: ', self.sltlines)
        # if len(self.sltlines) > 2:
        #     return None
        
        print('lines: ', self.lines)
        for cline in self.lines:
            # exclude already selected lines
            # if cline in self.sltlines:
            #     continue
            
            ponline = self.pointonline(point, cline.line)
            if ponline:
                print('found line')
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
    
    def clear_sltlines(self):
        """Deselects and clears selected lines toggling selected flag of each"""
        for line in self.sltlines:
            line.selected = False
            self.canvas.itemconfigure(line.tkline, width=3, fill=self.unsltcolor)
            
        self.sltlines.clear()
        self.selected = False
        
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
        self.clear_sltlines()
        
        
    def cmpdist(self):
        """Computes distance of the selected line"""
        if len(self.sltlines) != 1:
            messagebox.showerror("Error", "Please select one line to get the distance.")
            return
        
        line = self.sltlines[0].line
        p1, p2 = line
        
        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        mid_x = (p1[0] + p2[0]) // 2
        mid_y = (p1[1] + p2[1]) // 2
        
        self.canvas.create_text(mid_x, mid_y, text=f"{dist:.2f}px", font=("Arial", 14), fill="green")
    
        # Clear
        self.clear_sltlines()
        
    def delline(self):
        """Deletes selected line"""
        if len(self.sltlines) == 0:
            messagebox.showerror("Error", "No line selected to delete.")
            return
        
        # Delete and disappear
        self.canvas.delete(self.sltlines[-1].tkline)
        self.sltlines.pop(-1)
        self.lines.pop(-1)