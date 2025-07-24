
from copy import deepcopy
from tkinter import messagebox
from customtkinter import CTkCanvas
import math
from ..utils import plcbutton
from .line import Line
from .point import Point
from .triangle import Triangle

class Geometry:
    def __init__(self, canvas:CTkCanvas, vwidth:int, vheight:int, btnlist, activebtn):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        
        self.currpt = None
        self.lines = []
        self.sltdpoints: list[Point] = []
        self.triangles: list[Triangle] = []
        self.triangle = Triangle(canvas)
        
        self.tkline = None
        self.tkpt = None
        self.sltlines = []
        
        self.selected = False
        
        self.sltcolor = "#d4f3db"
        self.unsltcolor = "#28a745"
        self.dragcolor = "#4fcfbe"
        
        self.showbtn = True
        
        self.btnlist = btnlist
        self.activebtn = activebtn
        
        self.clicked = False
        
        
    def pack(self):
        self.anglebtn = plcbutton(self.canvas, "assets/plugins/angle.png", self.cmpangle, 40)
        self.distancebtn = plcbutton(self.canvas, "assets/plugins/distance.png", self.cmpdist, 40)
        self.delbtn = plcbutton(self.canvas, "assets/bin.png", self.delline, 40)
        
        self.applybtn = plcbutton(self.canvas, "assets/plugins/exit.png", self.onexit, 60)
        
        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<Motion>", self.ondrag)
        # self.canvas.bind("<ButtonRelease-1>", self.onrelease)
        
        # Disable other buttons
        for k,btn in self.btnlist.items():
            if btn != self.activebtn:
                btn.configure(state="disabled")
        
        
    def onclick(self, event):
        currpt = event.x, event.y

        print('before complete: ', self.triangle.complete)
        
        if self.triangle.complete:
            self.triangles.append(self.triangle.copy())
            meet, triangle = self.ptontriangles(Point(*currpt))
            print('meet: ', meet)
            if meet:
                triangle.select()
                print('Triangle selected')
                return
            
            self.triangle = Triangle(self.canvas)
            self.triangle.addpoint(Point(*currpt))
        # print('addpt: ', addpt)
        else:
            self.triangle.addpoint(Point(*currpt))
        print('after complete: ', self.triangle.complete)
        # if addpt['exist']:
        #     print('exists')
            # Check if a triangle is selected
            # if self.triangle.ptontriangle(Point(*currpt)):
            #     print('Triangle selected')
            # else:
            
            # self.triangle.addpoint(Point(*currpt))
        # if self.onpoint(Point(*currpt)):
        #     currpt = self.sltdpoints[0]
        #     lastpt = self.sltdpoints[-1]
        #     self.canvas.coords(self.tkline, currpt.x, currpt.y, lastpt.x, lastpt.y)
        #     self.canvas.tag_lower(self.tkline)
        #     self.currpt = None
            
        # clsline = self.pointonlines(currpt)
        # if clsline:
        #     self.selected = True
        #     if clsline.selected: # if already, selected, deselect
        #         self.canvas.itemconfigure(clsline.tkline, width=3, fill=self.unsltcolor)
        #         clsline.selected = False
        #         self.sltlines.remove(clsline)
        #     else:
        #         if len(self.sltlines) >= 2:
        #             return
                
        #         self.canvas.itemconfigure(clsline.tkline, width=4, fill=self.sltcolor)
        #         clsline.selected = True
        #         self.sltlines.append(clsline)
        # else:
        #     self.selected = False
        # self.clicked = True
        # else:
        #     self.sltdpoints.append(Point(*currpt))
        #     self.currpt = currpt
            
        #     self.tkpt = self.canvas.create_oval(event.x-5, event.y-5, event.x+5, event.y+5, fill="#d82995")
        #     self.tkline = self.canvas.create_line(event.x, event.y, event.x, event.y, fill=self.dragcolor, width=2)
        #     self.canvas.tag_lower(self.tkline)
        
    def ondrag(self, event):
        self.triangle.ondrag(event)
        
        return
        if self.currpt is None:
            return
        print('dragging')
        
        if self.tkline:
            self.canvas.coords(self.tkline, self.currpt[0], self.currpt[1], event.x, event.y)
        # if self.tkline and (not self.selected):
        #     self.canvas.coords(self.tkline, self.spoint[0], self.spoint[1], event.x, event.y)
            
            
    # def onrelease(self, event):
        return
        if self.selected:
            return
        
        llength = math.sqrt((self.spoint[0]-event.x)**2 + (self.spoint[1]-event.y)**2)
        if llength < 10:
            self.canvas.delete(self.tkline)
            return
        
        self.epoint = event.x, event.y
        self.canvas.coords(self.tkline, self.spoint[0], self.spoint[1], event.x, event.y)
        self.canvas.itemconfigure(self.tkline, fill=self.unsltcolor, width=3)
        
        self.lines.append(Line(self.tkline, (self.spoint, self.epoint)))
        
        # Show buttons
        if self.showbtn:
            self.showbtn = False
            self.anglebtn.place(x=self.vwidth-80, y=self.vheight-260)
            self.distancebtn.place(x=self.vwidth-80, y = self.vheight-200)
            self.delbtn.place(x=self.vwidth-80, y=self.vheight-140)
            self.applybtn.place(x=self.vwidth-90, y=self.vheight-80)
        
    def ptontriangles(self, point: Point) -> bool:
        """Check if point is near any triangle."""
        # Don't select if current triangle is not complete
        print('complete: ', self.triangle.complete)
        if not self.triangle.complete:
            return False, None
        
        print('triangles: ', len(self.triangles))
        for triangle in self.triangles:
            if triangle.ptontriangle(point):
                return True, triangle
        return False, None
    # def pointonlines(self, point):
    #     """Check if the point lies on any of the drawn line"""
    #     for cline in self.lines:
            
    #         ponline = self.pointonline(point, cline.line)
    #         if ponline:
    #             return cline
        
    #     return None
    
    # def onpoint(self, currpt):
    #     """Check if the point lies on first drawn point"""
    #     if len(self.sltdpoints) == 0:
    #         return False
        
    #     return currpt.meets(self.sltdpoints[0])
        
    # def pointonline(self, point, line, threshold=6):
    #     """Check if point is near a line segment."""
    #     startl, endl = line
    #     x0, y0 = point
    #     x1, y1 = startl
    #     x2, y2 = endl

    #     dx = x2 - x1
    #     dy = y2 - y1
    #     if dx == dy == 0:
    #         return False

    #     t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / float(dx*dx + dy*dy)))
    #     proj_x = x1 + t * dx
    #     proj_y = y1 + t * dy
    #     dist = math.hypot(x0 - proj_x, y0 - proj_y)
    #     return dist <= threshold
    
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
        
        tktext = self.canvas.create_text(mid_x, mid_y, text=f"{angle_deg:.2f}°", font=("Arial", 14), fill="#d4f3db")
        line1.tktext = tktext
        
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
        
        tktext = self.canvas.create_text(mid_x, mid_y, text=f"{dist:.2f}", font=("Arial", 14), fill="#d4f3db")
        self.sltlines[0].tktext = tktext
    
        # Clear
        self.clear_sltlines()
        
    def delline(self):
        """Deletes selected line"""
        if len(self.sltlines) == 0:
            messagebox.showerror("Error", "No line selected to delete.")
            return
        
        # Delete and disappear
        self.canvas.delete(self.sltlines[-1].tkline)
        # Delete text
        if self.sltlines[-1].tktext is not None:
            self.canvas.delete(self.sltlines[-1].tktext)
        line = self.sltlines.pop(-1)
        self.lines.remove(line)
        
        
    def onexit(self):
        self.anglebtn.place_forget()
        self.distancebtn.place_forget()
        self.delbtn.place_forget()
        self.applybtn.place_forget()
        
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")
        
        # Activate all buttons
        for k,btn in self.btnlist.items():
            btn.configure(state="normal")
            
        self.showbtn = True