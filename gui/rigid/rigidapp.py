
import threading
from tkinter import messagebox

from gui.app import App
from gui.components.processanim import ProcessAnimation
from gui.components.spinner import Spinner
from gui.components.seekbar import TrimSeekBar
from gui.components.seekbar import ViewSeekBar
from gui.components.ruler import ScaleRuler
from gui.components.progressbar import ProgressBar
from gui.components.rect import Rect
from gui.components.tpoints import TPoints
from gui.components.subtoolbar import SubToolbar
from gui.components.plot.save import Save
from gui.components.checkbox import Checkbox
from gui.components.label import Label
from gui.components.titlebar import TitleBar
from gui.components.tooltip import ToolTip
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry
from experiments.components.ocr import OCRData
from core import PlotType
from ..components.plot.plot import Plot
from .videoapp import Video

class RigidApp(App):
    def __init__(self, root):
        """
        ox, oy: Position of origin of coordinate axes specified by user in the video frame.
        fx, fy: Position of origin of image in the video frame.
        """
        super().__init__(root)
        
        # Plugins ---------------------------------------------------------------------------------
        self.subtoolbar = SubToolbar(self.videoview, width=self.twidth, btnsize=self.btnsize)
        
        # TODO: Use enum for these
        buttons = [
            ("assets/plugins/filters.png", self.appfilter, "Apply Filters to Video"),
            ("assets/plugins/crop.png", self.drawcrop, "Crop the Video"),
            ("assets/plugins/ocr.png", self.drawocr, "Draw to Apply OCR"),
            ("assets/plugins/geometry.png", self.dogeometry, "Geometry Tool")
        ]
        
        for imgpath, command, tooltip in buttons:
            self.btn = self.subtoolbar.mkbutton(imgpath, command)
            ToolTip(self.btn, tooltip)
            self.btnlist[imgpath.split('/')[-1][:-4]] = self.btn
        
        
        self.pluginsbtn = self.mkbutton("assets/plugin.png", self.plugins)
        ToolTip(self.pluginsbtn, "Plugins")
        
        self.filters = Filters(self.scrollframe, self.videoview, self.vwidth, self.vheight, self.updateframe, self.subtoolbar.toggle)
        
        self.crop = Crop(self.videoview, self.vwidth, self.vheight, self.updateframe, self.subtoolbar.toggle)
        
        self.geometry = Geometry(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['geometry'])
        
        # Main toolbar ----------------------------------------------------------------------------
        self.seekbar = TrimSeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
            
        self.trects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['rectanglebd'])
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['rectanglebd'], toggle=self.subtoolbar.toggle)
        
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)
        self.pdata = None
        
        self.processanim = ProcessAnimation(self.videoview, self.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth, vheight=self.vheight)
        
        # TODO: Restructure this to make more consistent
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist["ruler"])
        
        # TODO: Make this handle more gracefully
        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.crop, self.seekbar, self.filters, self.processanim)
        
        self.seekbar.settrim(trimvideo=self.trimvideo)

    def loadvideo(self, videopath:str, clear=True):
        """Loads a new video from user click."""
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        
        # self.videoapp.loadvideo(videopath)
        
        # self.loadcomponents()
        
        self.spinner = Spinner(self.videoview, self.crop)

        def load(spinner):
            print('spinner')
            self.videoapp.loadvideo(videopath)
            print('after ended')
            self.root.after(0, spinner.destroy())
            
            self.loadcomponents()

        threading.Thread(target=load, args=(self.spinner,)).start()
        
    def trimvideo(self, startidx, endidx):
        self.spinner = Spinner(self.videoview, self.crop)

        def trim(spinner):
            print('trim start')
            self.videoapp.trimvideo(startidx, endidx)
            print('trim ended')
            self.videoapp.loadvideo(self.videoapp.trimpath)
            self.loadcomponents()
            self.root.after(0, spinner.destroy())

        threading.Thread(target=trim, args=(self.spinner,)).start()
        
        
    def loadcomponents(self, trim=True):
        # Show frame count
        Label(self.videoview, text="Frame Count: " + str(self.videoapp.fcount)).place(x=10, y=80)
        
        # self.resize(self.videoapp.fwidth, self.videoapp.fheight)

        self.crop.set(self.videoapp.fwidth, self.videoapp.fheight)
        self.videoapp.setview()
        
        print('seekbar.disable: ', self.seekbar.disable)
        if self.seekbar.disable:
            self.seekbar = ViewSeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
            print('fcount: ', self.videoapp.fcount)
            self.seekbar.set(self.videoapp.fcount)
            self.seekbar.pack()
            print('packed')
        else:
            self.seekbar.set(self.videoapp.fcount)
        
        
        self.tpoints.addpoints(self.videoapp.trackpts, self.crop.crpx, self.crop.crpy)
        
        self.updateframe()
        
    def loadseek(self):
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.seekbar.pack()
        
        

    def updateframe(self):
        """Updates the frame displayed in the video view based on the slider position."""
        self.videoapp.showframe(self.seekbar.idx)
        
        # draw tracked points
        self.tpoints.drawpoints(self.seekbar.idx)

    def scale(self):
        self.scruler.pack()

    def drawrect(self):
        """Draws rectangle with simple lines"""
        self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
        
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.trects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
    
    
    def appfilter(self):
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
        self.filters.spawnfilter()
        self.subtoolbar.toggle()
    
    def drawcrop(self):
        """Crop for crop plugin. This crop the all frames of video"""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        self.crop.drawrect()
        self.subtoolbar.toggle()
        
    def drawocr(self):
        """Draws rectangle for OCR"""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
        self.ocrrects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
        self.subtoolbar.toggle()
        
    def dogeometry(self):
        """Starts geomtry plugin"""
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.geometry.pack()
        self.subtoolbar.toggle()

    def strack(self):
        """
        Detects and tracks radius for the main videoapp circle using classical techniques.
        """
        if (self.videoapp.fcount < 10) or ((len(self.trects.rects) == 0) and (len(self.ocrrects.rects) == 0)):
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        # Clear previous Axes, rectangles and OCRs
        self.axes.clear()
        self.trects.clearrects()
        self.ocrrects.clearrects()
        
        self.processanim.pack()
        self.progressbar.pack()

        def trackbg(processanim, progressbar):
            
            self.videoapp.track(self.trects, self.ocrrects, self.progressbar.progress)
            
            self.root.after(0, processanim.destroy())
            self.root.after(0, progressbar.destroy())

            # self.loadvideo(self.videoapp.trackpath, clear=False)
            # self.seekbar = ViewSeekBar(self.vidframe, self.cwidth-self.twidth, self.seekbarh, fcount=self.videoapp.fcount, callback=self.updateframe)
            self.loadcomponents(trim=False)

        threading.Thread(target=trackbg, args=(self.processanim,self.progressbar)).start()
        
        self.progressbar.update()
        
    # TODO: Clear implementation of clear/abort while processing
    def clearcomponents(self):
        """Clear components"""
        # self.crop.cleardata()
        self.filters.clear()
        self.axes.clear()
        self.tpoints.clear()
        self.scruler.clear()
        
    def reset(self):
        print('Clear')
        self.clearcomponents()
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        self.trects.clear()
        self.crop.clear()
        self.seekbar.clear()
        self.loadvideo(self.videopath)
    
    def plot(self):
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.texts) == 0):
            messagebox.showerror("Error", "No tracked and text data available. Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        # TODO: Remove points from plot data as well when user removed the point
        self.gen_plotdata()
        
        # Checkbox(self.videoview, PlotType, self.pdata.showplots)

    def savedata(self):
        """
        Saves the tracked data to a CSV file.
        """
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.texts) == 0):
            messagebox.showerror("Error", "No tracked and text data and available. Please start tracking first.")
            return
        
        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")
        
        Checkbox(self.videoview, PlotType, self.pdata.showplots)
        
        self.gen_plotdata()
        ocrdata = OCRData(self.videoapp.texts)
        
        save = Save(self.pdata, ocrdata)
        save.askfilepath()
        save.savedata()
        
        messagebox.showinfo("Success", "Tracked data saved successfully.")
        
    def plugins(self):
        """
        Opens a processanim to select a filter type and apply it to the video frame.
        """
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()
        
    
    def gen_plotdata(self):
        """Evolve raw data into plot data"""
        if self.pdata is None:    
            scale = 1
            if self.scruler is not None:
                scale = self.scruler.scalef
                
            self.pdata = Plot(self.videoapp.trackpts, self.axes, self.vwidth, self.vheight, self.fwidth,
                    self.fheight, scale=scale, fps=self.videoapp.fps)