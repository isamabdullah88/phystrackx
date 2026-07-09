"""
plugins_manager.py

Encapsulates tool extensions setups and toolbar action mapping paths.
Integrates session logging tracking for component lifecycle monitoring.

Author: Isam Balghari
"""

import logging
from gui.components.subtoolbar import SubToolbar
from gui.components.tooltip import ToolTip
from gui.plugins.filters import Filters
from gui.plugins.crop import Crop
from gui.plugins.geometry.geometry import Geometry


class PluginManager:
    """Encapsulates tool extensions setups and toolbar action mapping paths."""
    
    def __init__(self, app) -> None:
        self.app = app
        
        # Initialize sub-module specific logger namespace (e.g., gui.rigid.plugins.manager)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing PluginManager sub-toolbar canvas interfaces.")
        
        self.subtoolbar = SubToolbar(app.videoview, width=app.twidth, btnsize=app.btnsize)
        self.btnlist = {}
        
        self._build_toolbar()
        self._load_plugins()
        self.logger.info("All workflow sub-toolbar action hooks and plugins instantiated successfully.")

    def _build_toolbar(self) -> None:
        buttons = [
            ("assets/plugins/filters.png", self.app.appfilter, "Apply Filters to Video"),
            ("assets/plugins/crop.png", self.app.drawcrop, "Crop the Video"),
            ("assets/plugins/ocr.png", self.app.drawocr, "Draw to Apply OCR"),
            ("assets/plugins/geometry.png", self.app.dogeometry, "Geometry Tool")
        ]
        
        for imgpath, command, tooltip in buttons:
            btn = self.subtoolbar.mkbutton(imgpath, command)
            ToolTip(btn, tooltip)
            btn_key = imgpath.split('/')[-1].replace('.png', '')
            self.btnlist[btn_key] = btn
            
        self.logger.info(f"Registered {len(buttons)} workflow buttons to the sub-toolbar array matrix.")

    def _load_plugins(self) -> None:
        self.logger.info("Mounting plugin tracking engines (Filters, Crop, Geometry) to active video view viewport bounds.")
        self.filters = Filters(self.app.scrollframe, self.app.videoview, self.app.vwidth, self.app.vheight,
                               self.app.updateframe, self.subtoolbar.toggle)
        self.crop = Crop(self.app.videoview, self.app.vwidth, self.app.vheight, self.app.updateframe,
                         self.subtoolbar.toggle)
        self.geometry = Geometry(self.app.videoview, self.app.vwidth, self.app.vheight, self.btnlist,
                                 self.btnlist.get('geometry'))

    def toggle(self) -> None:
        self.logger.info("Toggling sub-toolbar interactive menu visibility matrix panel display track.")
        self.subtoolbar.toggle()