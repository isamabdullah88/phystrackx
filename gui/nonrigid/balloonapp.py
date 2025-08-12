import threading
from tkinter import messagebox

from gui.app import App
from gui.components.processanim import ProcessAnimation
from gui.components.spinner import Spinner
from gui.components.seekbar import TrimSeekBar, ViewSeekBar
from gui.components.ruler import ScaleRuler
from gui.components.progressbar import ProgressBar
from gui.components.rect import Rect
from gui.components.tpoints import TPoints
from gui.components.subtoolbar import SubToolbar
from gui.components.plot import Save, Plot, DataManager
from gui.components.label import Label
from gui.components.titlebar import TitleBar
from gui.components.tooltip import ToolTip
from gui.components.circle import Circle
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry
from .videoapp import Video

class BalloonApp(App):
    def __init__(self, root):
        super().__init__(root)
        
        # img = Image.open(abspath("assets/ruler.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        # img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        # self.ruler = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
        #                               image=img, command=self.scale)
        # self.ruler.pack(padx=5, pady=5)
        # self.ruler.image = img

        # For drawing ellipse over tracking area
        # img = Image.open(abspath("assets/circlebd.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
        # img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
        # self.circlebd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
        #                               image=img, command=self.drawcircle)
        # self.circlebd.pack(pady=10)
        
        # For drawing rectangle over text area
    #     img = Image.open(abspath("assets/rectanglebd.png")).resize((self.btnsize, self.btnsize), Image.Resampling.LANCZOS)
    #     img = ctk.CTkImage(dark_image=img, size=(self.btnsize, self.btnsize))
    #     self.rectbd = ctk.CTkButton(self.scrollframe, text="", width=self.btnsize, height=self.btnsize,
    #                                   image=img, command=self.drawrect)
    #     self.rectbd.pack(pady=10)
        

    #     self.seekbar = TrimSeekBar(self.vidframe, width=self.cwidth-self.twidth, height=self.seekbarh, ondrag=self.updateframe)
        
    #     # self.scroll_toolbar.pack()
        
    #     self.scruler = None

    #     self.ccoords = (0, 0)

    #     # mask from user for tracking
    #     self._mask = None
    #     # rect for text detection
    #     self._rect = None

    #     tempdir = './temp'
    #     if not os.path.exists(tempdir):
    #         os.makedirs(tempdir)

    #     self._trackpath = os.path.join(tempdir, 'track-balloon.mp4')

    #     self.balloon = Balloon(trackpath=self._trackpath)



    # def loadvideo(self, videopath):
    #     self.balloon.addvideo(videopath)
        
    #     self.seekbar.setcount(self.balloon.fcount)

    #     frame1 = self.balloon.frame(0)
    #     self.dispframe(frame1)

    # def dispframe(self, frame):
    #     fwidth = self.balloon.fwidth
    #     fheight = self.balloon.fheight
    #     frame = self.resizeframe(frame, fwidth, fheight)
    #     self.fheight, self.fwidth = frame.shape[:2]

    #     img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
    #     self.photo = ImageTk.PhotoImage(image=img)
    #     self._frame = frame
        
    #     self.fx = floor(self.vwidth/2 - self.fwidth/2)
    #     self.fy = floor(self.vheight/2 - self.fheight/2)
        
    #     # Default coordinate system
    #     if self.ox is None:
    #         self.ox = self.fx
        
    #     if self.oy is None:
    #         self.oy = self.fy + self.fheight

    #     self.imgview = self.videoview.create_image(self.fx, self.fy, image=self.photo, anchor='nw')
        
    # def updateframe(self):
    #     """Updates the frame displayed in the video view based on the slider position."""
    #     frame = self.balloon.frame(index=self.seekbar.idx)
    #     fwidth = self.balloon.fwidth
    #     fheight = self.balloon.fheight

    #     frame = self.resizeframe(frame, fwidth, fheight)

    #     img = Image.fromarray(cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2RGB))
    #     self.photo = ImageTk.PhotoImage(image=img)
    #     self._frame = frame

    #     self.videoview.itemconfig(self.imgview, image=self.photo)

    # def scale(self):
    #     self.scruler = ScaleRuler(self.videoview, cwidth=self.cwidth, cheight=self.cheight)

        self.subtoolbar = SubToolbar(self.videoview, width=self.twidth, btnsize=self.btnsize)

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

        self.seekbar = TrimSeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
        self.trects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['rectanglebd'])
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist['rectanglebd'], toggle=self.subtoolbar.toggle)
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)
        self.pdata = None

        self.processanim = ProcessAnimation(self.videoview, self.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth, vheight=self.vheight)
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, self.btnlist, self.btnlist["ruler"])

        self.circle = Circle(self.videoview, self.vwidth, self.vheight)

        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.crop, self.seekbar, self.filters, self.processanim)
        self.seekbar.settrim(trimvideo=self.trimvideo)

        self.save = None
        self.plot = None
        self.datamanager = None

    def loadvideo(self, videopath: str):
        """Loads the video into the viewer and initializes related components."""
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        self.spinner = Spinner(self.videoview, self.videoapp.imgview)

        def load(spinner):
            self.videoapp.loadvideo(videopath)
            self.root.after(0, spinner.destroy())
            self.loadcomponents()

        threading.Thread(target=load, args=(self.spinner,)).start()

    def trimvideo(self, startidx, endidx):
        """Trims the video based on user-defined start and end indices."""
        self.spinner = Spinner(self.videoview, self.videoapp.imgview, self.crop)

        def trim(spinner):
            self.videoapp.trimvideo(startidx, endidx)
            self.videoapp.loadvideo(self.videoapp.trimpath)
            self.loadcomponents()
            self.root.after(0, spinner.destroy())

        threading.Thread(target=trim, args=(self.spinner,)).start()

    def loadcomponents(self):
        """Loads and updates components after video is loaded or modified."""
        Label(self.videoview, text="Frame Count: " + str(self.videoapp.fcount)).place(x=10, y=80)

        if self.seekbar.disable:
            self.seekbar = ViewSeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
            self.seekbar.set(self.videoapp.fcount)
            self.seekbar.pack()
        else:
            self.seekbar.set(self.videoapp.fcount)

        self.tpoints.addpoints(self.videoapp.trackpts, self.crop.crpx, self.crop.crpy)
        self.updateframe()

    def loadseek(self):
        """Displays seekbar if video has enough frames."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.seekbar.pack()

    def updateframe(self):
        """Updates canvas to show current frame and overlays points."""
        self.videoapp.showframe(self.seekbar.idx)
        self.tpoints.drawpoints(self.seekbar.idx)

    def scale(self):
        """Displays the scale ruler on canvas."""
        self.scruler.pack()

    def drawrect(self):
        """Enables rectangle drawing mode for object tracking."""
        self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.trects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)

    def appfilter(self):
        """Activates video filter UI for user input."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to apply filter. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
        self.filters.spawnfilter()
        self.subtoolbar.toggle()

    def drawcrop(self):
        """Activates the cropping tool to trim the video frame area."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
        self.crop.drawrect()
        self.subtoolbar.toggle()

    def drawocr(self):
        """Draws a region for OCR (optical character recognition)."""
        if self.videoapp.fcount < 10:
            messagebox.showerror("Error", "No video to do OCR. Please upload a video!")
            return
        self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
        self.ocrrects.drawrect(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)
        self.subtoolbar.toggle()

    def dogeometry(self):
        """Launches the geometry analysis plugin UI."""
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.geometry.pack()
        self.subtoolbar.toggle()

    def strack(self):
        """Performs point tracking across video frames and visualizes result."""
        if (self.videoapp.fcount < 10) or ((len(self.trects.rects) == 0) and (len(self.ocrrects.rects) == 0)):
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        self.axes.clear()
        self.trects.clearrects()
        self.ocrrects.clearrects()

        self.processanim.pack()
        self.progressbar.pack()

        def trackbg(processanim, progressbar):
            self.videoapp.track(self.trects, self.ocrrects, self.progressbar.progress)
            self.root.after(0, processanim.destroy())
            self.root.after(0, progressbar.destroy())
            self.loadcomponents()

        threading.Thread(target=trackbg, args=(self.processanim, self.progressbar)).start()
        self.progressbar.update()

    def clearcomponents(self):
        """Clears all active UI drawing elements and overlays."""
        self.filters.clear()
        self.axes.clear()
        self.tpoints.clear()
        self.scruler.clear()

    def reset(self):
        """Resets the video view and related tracking/overlay data."""
        print('Clear')
        self.clearcomponents()
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        self.trects.clear()
        self.crop.clear()
        self.seekbar.clear()
        self.loadvideo(self.videopath)

    def plot(self):
        """Creates plots from tracked data or OCR values."""
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.ocrdata) == 0):
            messagebox.showerror("Error", "No tracked and text data available. Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")

        if self.datamanager is not None:
            self.plot = Plot(self.videoview, self.datamanager)
        else:
            self.datamanager = DataManager(
                self.tpoints.tpts, self.videoapp.ocrdata, self.axes,
                self.vwidth, self.vheight, self.fwidth, self.fheight,
                self.videoapp.fps, self.scruler.scalef
            )
            self.datamanager.transform()
            self.plot = Plot(self.videoview, self.datamanager)

    def savedata(self):
        """Saves data from tracking or OCR to file (CSV or other format)."""
        if (len(self.videoapp.trackpts) == 0) and (len(self.videoapp.ocrdata) == 0):
            messagebox.showerror("Error", "No tracked and text data and available. Please start tracking first.")
            return

        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")

        if self.datamanager is not None:
            self.save = Save(self.videoview, self.datamanager)
        else:
            self.datamanager = DataManager(
                self.tpoints.tpts, self.videoapp.ocrdata, self.axes,
                self.vwidth, self.vheight, self.fwidth, self.fheight,
                self.videoapp.fps, self.scruler.scalef
            )
            self.datamanager.transform()
            self.save = Save(self.videoview, self.datamanager)

    def plugins(self):
        """Toggles the plugin selection toolbar interface."""
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.subtoolbar.toggle()

    def drawcircle(self):
        """Draws circle"""
        self.circle.drawcircle(self.crop.crpwidth, self.crop.crpheight, self.crop.crpx, self.crop.crpy)

    
    # def drawrect(self):
    #     """Draws rectangle with simple lines"""
    #     self.rbox = None
        
    #     def ondown(event):
    #         if self.rbox is not None:
    #             self.videoview.delete(self.rbox)
            
    #         self.rcoords = (event.x, event.y)
            
    #         self.rbox = self.videoview.create_rectangle(event.x, event.y, event.x, event.y, outline="red")
            
    #     def inrect(event):
    #         sx, sy = self.rcoords
    #         ex, ey = (event.x, event.y)
            
    #         self.videoview.coords(self.rbox, sx, sy, event.x, event.y)

    #         self._rect = PixelRect(sx-self.fx, sy-self.fy, ex-sx, ey-sy).pix2norm(self.fwidth, self.fheight)

    #     self.videoview.bind("<Button-1>", ondown)
    #     self.videoview.bind("<B1-Motion>", inrect)


    def strack(self):
        """
        Detects and tracks radius for the main balloon circle using classical techniques.
        """
        if self.balloon.fcount < 10:
            messagebox.showerror("Error", "No task to track, upload video and mark points first!")
            return

        self.popup = Spinner(self.videoview, self.vwidth, self.vheight)

        def trackbg(popup):
            startidx = self.seekbar.startidx
            endidx = self.seekbar.endidx
            self.balloon.track(self._mask, self._rect, startidx, endidx)
            
            self.root.after(0, popup.destroy())

            self.loadvideo(self._trackpath)

        threading.Thread(target=trackbg, args=(self.popup,)).start()



    # def clear(self):
    #     """Clears almost everything"""
    #     super().clear()
        
    #     del self.balloon
    #     self.balloon = Balloon(trackpath=self._trackpath)
        
    #     self.scruler = None
    #     self._rcoords = None
    #     self._rects = []
        
    #     self.seekbar.setcount(100)


    # def plot_distances(self):
    #     if len(self.balloon.trackpts) < 1:
    #         messagebox.showerror("Error", "No tracked points available. Please start tracking first.")
    #         return

    #     num_tracks = len(self.balloon.trackpts)
    #     _, axes = plt.subplots(num_tracks+1, 2, figsize=(6, 5))

    #     for i in range(num_tracks):
    #         trackpts = self.balloon.trackpts[i]
    #         xcoords = trackpts[0, :] - self.fx
    #         ycoords = trackpts[1, :] - self.fy

    #         axes[i][0].plot(xcoords)
    #         axes[i][0].set_title("x coordinates")
    #         axes[i][1].plot(ycoords)
    #         axes[i][1].set_title("y coordinates")

    #     plt.tight_layout()
    #     plt.show()