"""
rigidapp.py

Main orchestrator interface for video-based tracking and visual instrumentation dashboards.
Includes hierarchical parent-handler session logging profiles.

Author: Isam Balghari
"""

import logging
import threading
from tkinter import messagebox
from gui.app import App

# Component imports
from gui.components.processanim import ProcessAnimation
from gui.components.spinner import Spinner
from gui.components.progressbar import ProgressBar
from gui.components.rect import Rect
from gui.components.tpoints import TPoints
from gui.components.ruler import ScaleRuler
from gui.components.titlebar import TitleBar
from gui.components.tooltip import ToolTip
from .videoapp import Video

# Sub-module managers
from gui.components.seekbar import SeekBar, SeekMode
from .plugins_manager import PluginManager
from .data_pipeline import DataPipelineManager


class RigidApp(App):
    """Main GUI application class for the PhysTrack Rigid tool."""
    
    def __init__(self, root) -> None:
        super().__init__(root)
        
        # Initialize component-specific logging namespace
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing high-level RigidApp workspace modules.")

        # 1. Instantiate Structural Sub-Managers
        self.plugin_mgr = PluginManager(self)
        self.pipeline_mgr = DataPipelineManager(self.videoview)
        self.seekbar = SeekBar(self.vidframe, self.vwidth, self.seekbarh, callback=self.updateframe)
        self.seekbar.set_trim_callback(self.trimvideo)

        # 2. Local Overlay Views
        self.trects = Rect(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.btnlist, self.plugin_mgr.btnlist.get('rectanglebd'))
        self.ocrrects = Rect(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.btnlist, self.plugin_mgr.btnlist.get('rectanglebd'), toggle=self.plugin_mgr.subtoolbar.toggle)
        self.tpoints = TPoints(self.videoview, self.vwidth, self.vheight)

        self.processanim = ProcessAnimation(self.videoview, self.plugin_mgr.crop)
        self.progressbar = ProgressBar(self.root, self.videoview, vwidth=self.vwidth, vheight=self.vheight)
        self.scruler = ScaleRuler(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.btnlist, self.plugin_mgr.btnlist.get("ruler"))

        # 3. Video Backend Thread Attachment
        self.videoapp = Video(self.videoview, self.vwidth, self.vheight, self.plugin_mgr.crop, self.plugin_mgr.filters, self.processanim)

        # Dynamic access alias configs
        self.btnlist = self.plugin_mgr.btnlist
        self.pluginsbtn = self.mkbutton("assets/plugin.png", self.plugins)
        ToolTip(self.pluginsbtn, "Plugins")
        
        self.logger.info("RigidApp UI system fully mapped and operational.")

    def _ensure_video_loaded(self) -> bool:
        """Internal interceptor safeguarding core functions from uninitialized states."""
        if self.videoapp.fcount < 10:
            self.logger.warning("User attempted context command block activation without verified video payload frames.")
            messagebox.showerror("Error", "Please upload a video file first!")
            return False
        return True

    def loadvideo(self, videopath: str) -> None:
        self.logger.info(f"Asynchronous load requested for source asset: {videopath}")
        self.title = TitleBar(self.videoview, self.vwidth, "Video View")
        self.spinner = Spinner(self.videoview, self.videoapp.imgview)
        
        threading.Thread(target=lambda: [
            self.videoapp.loadvideo(videopath),
            self.root.after(0, lambda: [
                self.spinner.destroy(), 
                self.loadcomponents(),
                self.logger.info("Video streaming channel successfully integrated on UI thread.")
            ])
        ], daemon=True).start()

    def trimvideo(self, startidx: int, endidx: int) -> None:
        self.logger.info(f"Targeted video clipping operation initialized. Frame coordinates range: [{startidx} -> {endidx}]")
        self.spinner = Spinner(self.videoview, self.videoapp.imgview, self.plugin_mgr.crop)
        
        threading.Thread(target=lambda: [
            self.videoapp.trimvideo(startidx, endidx),
            self.root.after(0, lambda: [
                self.videoapp.loadvideo(self.videoapp.trimpath, True),
                self.seekbar.set_mode(SeekMode.VIEW, self.videoapp.fcount),
                self.loadcomponents(),
                self.spinner.destroy(),
                self.logger.info("Asynchronous video trimming execution completed.")
            ])
        ], daemon=True).start()

    def loadcomponents(self) -> None:
        self.seekbar.set_mode(SeekMode.VIEW, self.videoapp.fcount)
        self.tpoints.addpoints(self.videoapp.trackpts, self.plugin_mgr.crop.crpx, self.plugin_mgr.crop.crpy)
        self.updateframe()

    def loadseek(self) -> None:
        if self._ensure_video_loaded():
            self.logger.info("Seeding timeline workspace frame navigation controls.")
            self.seekbar.set_mode(SeekMode.TRIM, self.videoapp.fcount)

    def updateframe(self) -> None:
        # Note: Avoid high-frequency logger.info operations inside live frame renders. 
        # Scrubbing the timeline would write 60+ logs/second, causing disk I/O bottlenecks and UI stutters.
        self.videoapp.showframe(self.seekbar.idx)
        self.tpoints.drawpoints(self.seekbar.idx)

    def scale(self) -> None:
        self.logger.info("Deploying coordinate scale rule overlay layer.")
        self.scruler.pack()

    def drawrect(self) -> None:
        if self._ensure_video_loaded():
            self.logger.info("Activating workspace item tracking validation boxes.")
            self.title = TitleBar(self.videoview, self.vwidth, "Mark Tool")
            self.trects.drawrect(self.plugin_mgr.crop.crpwidth, self.plugin_mgr.crop.crpheight, self.plugin_mgr.crop.crpx, self.plugin_mgr.crop.crpy)

    def appfilter(self) -> None:
        if self._ensure_video_loaded():
            self.logger.info("Opening dynamic filter modification matrix menu panel.")
            self.title = TitleBar(self.videoview, self.vwidth, "Filters Tool")
            self.plugin_mgr.filters.spawnfilter()
            self.plugin_mgr.toggle()

    def drawcrop(self) -> None:
        if self._ensure_video_loaded():
            self.logger.info("Initializing visual spatial geometric crop tool profiles.")
            self.title = TitleBar(self.videoview, self.vwidth, "Crop Tool")
            self.plugin_mgr.crop.drawrect()
            self.plugin_mgr.toggle()

    def drawocr(self) -> None:
        if self._ensure_video_loaded():
            self.logger.info("Mapping optical text zone character digit capture constraints.")
            self.title = TitleBar(self.videoview, self.vwidth, "OCR Tool")
            self.ocrrects.drawrect(self.plugin_mgr.crop.crpwidth, self.plugin_mgr.crop.crpheight, self.plugin_mgr.crop.crpx, self.plugin_mgr.crop.crpy)
            self.plugin_mgr.toggle()

    def dogeometry(self) -> None:
        self.logger.info("Launching trace physics kinematic geometry tracking instruments.")
        self.title = TitleBar(self.videoview, self.vwidth, "Geometry Tool")
        self.plugin_mgr.geometry.pack()
        self.plugin_mgr.toggle()

    def strack(self) -> None:
        if not self._ensure_video_loaded() or (not self.trects.rects and not self.ocrrects.rects):
            self.logger.warning("Tracking execution bypassed: no nodes or bounding layers found on canvas.")
            messagebox.showerror("Error", "No nodes mapped to track. Select regions first!")
            return

        self.logger.info("Kicking off optical flow and analytical tracking loops thread.")
        self.title = TitleBar(self.videoview, self.vwidth, "Tracking")
        self.axes.clear()
        self.trects.cleartkrects()
        self.ocrrects.cleartkrects()
        self.processanim.pack()
        self.progressbar.pack()

        threading.Thread(target=lambda: [
            self.videoapp.track(self.trects, self.ocrrects, self.progressbar.progress),
            self.root.after(0, lambda: [
                self.processanim.destroy(), 
                self.progressbar.destroy(), 
                self.loadcomponents(),
                self.logger.info("Background point tracking calculations wrapped cleanly.")
            ])
        ], daemon=True).start()
        self.progressbar.update()

    def clearcomponents(self) -> None:
        self.plugin_mgr.filters.clear()
        self.axes.clear()
        self.tpoints.clear()
        self.scruler.clear()
        self.pipeline_mgr.datamanager.clear()

    def reset(self) -> None:
        self.logger.info("Resetting application workspace tracking layers back to default profiles.")
        self.clearcomponents()
        self.videoapp.trackpts.clear()
        self.ocrrects.clear()
        self.trects.clear()
        self.plugin_mgr.crop.clear()
        self.seekbar.clear()
        if self.videopath:
            self.loadvideo(self.videopath)

    def plot(self) -> None:
        self.logger.info("Requesting analytical kinematics plot data visualizations compilation.")
        self.title = TitleBar(self.videoview, self.vwidth, "Data Visualization")
        self.pipeline_mgr.compile_and_run(self, "plot")

    def savedata(self) -> None:
        self.logger.info("Compiling active physical scalar tracking frames for spreadsheet generation.")
        self.title = TitleBar(self.videoview, self.vwidth, "Save Data")
        self.pipeline_mgr.compile_and_run(self, "save")

    def plugins(self) -> None:
        self.title = TitleBar(self.videoview, self.vwidth, "Plugins")
        self.plugin_mgr.toggle()
        self.plugin_mgr.geometry.set_scale(self.scruler.scale)
        self.logger.info("Extended dynamic components toolbox toggled.")