"""
buttons.py

Custom styled button components for the PhysTrack GUI toolkit.
Integrates automatic image caching to ensure fast initialization during UI rebuilds.
"""

from typing import Callable, Optional
import customtkinter as ctk
from .button_cache import ButtonCache


class Button(ctk.CTkButton):
    """
    A unified, reusable icon button that automatically leverages memory caching 
    for image assets to prevent I/O bottlenecks.
    """

    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, imgpath: str,
                 command: Callable[[], None], size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        
        # 1. Fetch pre-scaled image from RAM cache (Instant 0 ms read)
        self.cached_img = ButtonCache.get(imgpath, size=size)

        # 2. Pass setup properties down to standard CTkButton
        super().__init__(master=master, text="", image=self.cached_img, command=command, 
                         width=size, height=size, fg_color=fg_color, hover_color=hover_color,
                         **kwargs)

        # 3. Optional ToolTip integration
        if tooltip:
            from gui.components.tooltip import ToolTip
            ToolTip(self, tooltip)