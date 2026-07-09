"""
data_pipeline.py

Handles kinematic data compilations, transformations, plotting, and file exports.
Integrates parent-linked hierarchical warning and info logging hooks.

Author: Isam Balghari
"""

import logging
from tkinter import messagebox
from gui.components.plot import Save, Plot, DataManager


class DataPipelineManager:
    """Handles kinematic data compilations, transformations, plotting, and file exports."""
    
    def __init__(self, videoview) -> None:
        self.videoview = videoview
        
        # Instantiate sub-module logger namespace (e.g., gui.rigid.pipeline)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing core analytical DataPipelineManager engines.")
        
        self.saver = Save(videoview)
        self.plotter = Plot(videoview)
        self.datamanager = DataManager()

    def compile_and_run(self, app, action_type: str) -> None:
        """Centralized helper to check payload presence and fire analytical responses."""
        self.logger.info(f"Data compile request intercepted for action dispatcher pathway: [{action_type}]")
        
        # 1. State Guard Check
        if not app.videoapp.trackpts and not app.videoapp.ocrdata:
            self.logger.warning(
                f"Data compilation aborted for '{action_type}': Tracking point arrays and OCR registers are empty."
            )
            messagebox.showerror("Error", "No tracked variables or structural datasets available.")
            return

        # 2. Hand off parameters to DataManager contract
        self.logger.info("Staging active GUI configuration fields and mapping vectors for DataManager ingest.")
        success = self.datamanager.load_data(
            tpoints=app.tpoints.tpts, ocrdata=app.videoapp.ocrdata, axes=app.axes,
            vwidth=float(app.vwidth), vheight=float(app.vheight),
            fwidth=float(app.fwidth), fheight=float(app.fheight),
            fps=app.videoapp.fps, scale=app.scruler.scale
        )
        
        # 3. Process Execution Matrix
        if success:
            self.logger.info("DataManager load completed safely. Beginning physical coordinate transformations.")
            self.datamanager.transform()
            
            if action_type == "plot":
                self.logger.info("Directing processed tracking frames to Matplotlib plotting engine.")
                self.plotter.activate(self.datamanager)
            elif action_type == "save":
                self.logger.info("Directing processed workspace arrays to File Export engine.")
                self.saver.activate(self.datamanager)
        else:
            self.logger.error(
                f"Data pipeline processing failed: DataManager rejected tracking arrays during load routine check."
            )