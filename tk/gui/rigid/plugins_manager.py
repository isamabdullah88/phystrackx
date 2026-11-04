"""
plugins_manager.py

Encapsulates tool extensions setups and toolbar action mapping paths.
Integrates session logging tracking for component lifecycle monitoring.

Author: Isam Balghari
"""

import logging
from gui.components.subtoolbar import SubToolbar
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry
from gui.components.buttons import FiltersButton, CropButton, GeometryButton, OCRButton


class PluginManager:
    """Encapsulates tool extensions setups and toolbar action mapping paths."""
    
    def __init__(self, app) -> None:
        self.app = app
        
        # Initialize sub-module specific logger namespace (e.g., gui.rigid.plugins.manager)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing PluginManager sub-toolbar canvas interfaces.")
        
        self.subtoolbar = SubToolbar(app.videoview, width=app.twidth)
        self.btnlist = {}
        
        self._build_toolbar()
        self._load_plugins()
        self.logger.info("All workflow sub-toolbar action hooks and plugins instantiated successfully.")

    def _build_toolbar(self) -> None:
        self.btnlist = {
            "filters": FiltersButton(self.subtoolbar.frame, command=self.app.apply_filter, size=self.app.btnsize,
                                     tooltip="Apply Filters to Video"),
            "crop": CropButton(self.subtoolbar.frame, command=self.app.drawcrop, size=self.app.btnsize,
                               tooltip="Crop the Video"),
            "ocr": OCRButton(self.subtoolbar.frame, command=self.app.drawocr, size=self.app.btnsize,
                             tooltip="Draw to Apply OCR"),
            "geometry": GeometryButton(self.subtoolbar.frame, command=self.app.dogeometry, size=self.app.btnsize,
                                       tooltip="Geometry Tool")
        }

        for button in self.btnlist.values():
            button.pack(padx=self.app.padx/4, pady=self.app.pady/4)
            
        self.logger.info(f"Registered {len(self.btnlist)} workflow buttons to the sub-toolbar array matrix.")

    def _load_plugins(self) -> None:
        self.logger.info("Mounting plugin tracking engines (Filters, Crop, Geometry) to active video view viewport bounds.")
        self.filters = Filters(self.app.scrollframe, self.app.videoview, self.app.vwidth, self.app.vheight,
                               self.app.updateframe, self.subtoolbar.toggle)
        self.crop = Crop(self.app.videoview, self.app.vwidth, self.app.vheight, self.app.updateframe)
        self.geometry = Geometry(self.app.videoview, self.app.vwidth, self.app.vheight, self.btnlist,
                                 self.btnlist.get('geometry'))

    def toggle(self) -> None:
        self.logger.info("Toggling sub-toolbar interactive menu visibility matrix panel display track.")
        self.subtoolbar.toggle()