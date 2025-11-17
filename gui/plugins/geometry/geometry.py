"""
Geometry plugin for PhysTrackX.

This module handles interactive geometry drawing and measurement,
including triangles, distances, angles, and canvas screenshots.
"""

from tkinter import messagebox
from PIL import ImageGrab
import tkinter as tk
import customtkinter as ctk

from ..utils import mkbutton
from .point import Point
from .triangle import Triangle
from ...components.togglebutton import ToggleButton


class Geometry:
    """Handles user interaction with geometric elements on a canvas."""

    def __init__(self, canvas: ctk.CTkCanvas, vwidth: int, vheight: int, btnlist, activebtn):
        self.canvas = canvas
        self.vwidth = vwidth
        self.vheight = vheight
        self.btnlist = btnlist
        self.activebtn = activebtn
        self.togglebtn : ToggleButton = ToggleButton(self.canvas, commandon=self.unhide, commandoff=self.hide)

        self.currpt = None
        self.lines = []
        self.sltlines = []
        self.sltdpoints: list[Point] = []
        self.triangles: list[Triangle] = []
        self.triangle = Triangle(canvas)

        self.tkline = None
        self.tkpt = None
        self.selected = False
        self.showbtn = True
        self.clicked = False

        self.sltcolor = "#d4f3db"
        self.unsltcolor = "#28a745"
        self.dragcolor = "#4fcfbe"

    def pack(self):
        """Initialize buttons and canvas bindings."""
        self.btnframe = ctk.CTkFrame(self.canvas, width=60, fg_color="teal")
        # self.btnframe.pack(side=tk.RIGHT, padx=10)
        # self.btncanvas = tk.Canvas(self.btnframe)
        self.anglebtn = mkbutton(self.btnframe, "assets/plugins/angle.png", self.compute_angle, 40)
        self.distancebtn = mkbutton(self.btnframe, "assets/plugins/distance.png", self.compute_dist, 40)
        self.delbtn = mkbutton(self.btnframe, "assets/bin.png", self.deltriangle, 40)
        self.applybtn = mkbutton(self.btnframe, "assets/plugins/exit.png", self.onexit, 60)
        self.screenshot = mkbutton(self.btnframe, "assets/plugins/screenshot.png", self.capturescreen, 40)

        self.canvas.bind("<Button-1>", self.onclick)
        self.canvas.bind("<Motion>", self.ondrag)
        self.canvas.config(cursor="crosshair")

        # Disable other buttons
        for k, btn in self.btnlist.items():
            if btn != self.activebtn:
                btn.configure(state="disabled")

    def disp_buttons(self):
        """Display floating action buttons."""
        if self.showbtn:
            self.btnframe.pack(side=tk.RIGHT, padx=10)
            self.anglebtn.pack(padx=10, pady=10)
            self.distancebtn.pack(padx=10, pady=10)
            self.delbtn.pack(padx=10, pady=10)
            self.screenshot.pack(padx=10, pady=10)
            self.applybtn.pack(padx=10, pady=10)
            self.showbtn = False

            self.togglebtn.pack(anchor=tk.N, pady=50)

    def onclick(self, event):
        """Handle left-click to add points or select triangles."""
        point = Point(event.x, event.y)

        if self.triangle.complete:
            self.triangles.append(self.triangle.copy())
            found, triangle = self.is_pt_ontriangle(point)
            if found:
                triangle.select()
                return
            self.triangle = Triangle(self.canvas)

        self.triangle.addpoint(point)

        if self.triangle.complete:
            self.disp_buttons()

    def ondrag(self, event):
        """Handle dragging a line to a new point."""
        self.triangle.ondrag(event)

    def is_pt_ontriangle(self, point: Point) -> tuple[bool, Triangle | None]:
        """Check if a point lies on any existing triangle."""
        if not self.triangle.complete:
            return False, None

        for triangle in self.triangles:
            if triangle.is_pt_ontriangle(point):
                return True, triangle
        return False, None

    # def clear_sltlines(self):
    #     """Deselect and reset selected lines."""
    #     for line in self.sltlines:
    #         line.selected = False
    #         self.canvas.itemconfigure(line.tkline, width=3, fill=self.unsltcolor)
    #     self.sltlines.clear()
    #     self.selected = False

    def compute_angle(self):
        """Compute and display angles for selected triangles."""
        selected_triangles = [t for t in self.triangles if t.selected]

        if not selected_triangles:
            messagebox.showerror("Error", "No triangles selected. Please select at least one triangle.")
            return

        for triangle in selected_triangles:
            triangle.draw_angles()
            triangle.select()

    def capturescreen(self):
        """Capture and save a screenshot of the canvas."""
        filepath = ctk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if not filepath:
            return

        self.canvas.update()
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        w = x + self.canvas.winfo_width()
        h = y + self.canvas.winfo_height()

        ImageGrab.grab().crop((x, y, w, h)).save(filepath)
        messagebox.showinfo("Success", "Screenshot saved successfully.")

    def compute_dist(self):
        """Compute and label the side lengths of selected triangles."""
        selected_triangles = [t for t in self.triangles if t.selected]

        if not selected_triangles:
            messagebox.showerror("Error", "No triangles selected. Please select at least one triangle.")
            return

        for triangle in selected_triangles:
            triangle.label_lengths()
            triangle.select()

    def deltriangle(self):
        """Delete selected triangles from canvas and internal list."""
        selected_triangles = [t for t in self.triangles if t.selected]

        if not selected_triangles:
            messagebox.showerror("Error", "No triangles selected. Please select at least one triangle.")
            return

        for triangle in selected_triangles:
            triangle.delete()
            self.triangles.remove(triangle)

    def hide(self):
        """Hides all triangles if they are hidden"""
        for triangle in self.triangles:
            triangle.hide()

        # Hide current triangle
        self.triangle.hide()

    def unhide(self):
        """Unhides all triangles if they are hidden"""
        for triangle in self.triangles:
            triangle.unhide()

        # Unhide current triangle
        self.triangle.unhide()
    
    def onexit(self):
        """Cleanup when exiting the geometry tool."""
        self.anglebtn.pack_forget()
        self.distancebtn.pack_forget()
        self.delbtn.pack_forget()
        self.applybtn.pack_forget()
        self.screenshot.pack_forget()
        self.togglebtn.pack_forget()
        self.btnframe.destroy()

        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

        for _,btn in self.btnlist.items():
            btn.configure(state="normal")
            
        self.canvas.config(cursor="arrow")

        self.showbtn = True
