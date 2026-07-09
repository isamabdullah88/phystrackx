"""
seekbar.py

A unified controller that orchestrates trim and view seekbars, exposing a clean, 
single-point-of-contact API for the main application.
"""

from enum import Enum, auto
from typing import Callable
import tkinter as tk

class SeekMode(Enum):
    UNINITIALIZED = auto()
    TRIM = auto()
    VIEW = auto()


class SeekBar:
    def __init__(self, frame: tk.Frame, width: int, height: int, callback: Callable[[], None]) -> None:
        """
        Initializes the playback controller shell with underlying seekbar components.
        """
        from .trimseekbar import TrimSeekBar
        from .viewseekbar import ViewSeekBar

        self.frame = frame
        self.width = width
        self.height = height
        self.callback = callback

        # Initialize both sub-components under the same parent container
        self.trim_seekbar = TrimSeekBar(frame, width, height, callback=callback)
        self.view_seekbar = ViewSeekBar(frame, width, height, callback=callback)

        # Default internal state configurations
        self._mode = SeekMode.UNINITIALIZED
        self._frame_count = 0

    @property
    def mode(self) -> SeekMode:
        return self._mode

    @property
    def idx(self) -> int:
        """
        Exposes a unified current frame index property. 
        The main application doesn't need to know which seekbar is active.
        """
        if self._mode == SeekMode.VIEW:
            return self.view_seekbar.idx
        return self.trim_seekbar.idx

    def set_mode(self, mode: SeekMode, frame_count: int) -> None:
        """
        Handles the structural layout shuffling and resets safely when modes change.
        """
        self._mode = mode
        self._frame_count = frame_count

        # Unpack everything first to ensure a clean visual sweep
        self.trim_seekbar.clear()
        self.view_seekbar.clear()

        # Display the appropriate component based on application state
        self.pack(self._frame_count)

    def set_trim_callback(self, action: Callable[[int, int], None]) -> None:
        """Hooks the downstream execution routine directly to the trim bar."""
        self.trim_seekbar.settrim(trimvideo=action)

    def pack(self, frame_count: int) -> None:
        """Exposes a unified pack method for the main application."""
        if self._mode == SeekMode.VIEW:
            self.view_seekbar.set(frame_count)
            self.view_seekbar.pack()
        elif self._mode == SeekMode.TRIM:
            self.trim_seekbar.set(frame_count)
            self.trim_seekbar.pack()

    def clear(self) -> None:
        """Cleans and unpacks all controlled UI elements."""
        self.trim_seekbar.clear()
        self.view_seekbar.clear()
        self._mode = SeekMode.UNINITIALIZED
        self._frame_count = 0