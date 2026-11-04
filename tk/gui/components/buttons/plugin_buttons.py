from typing import Callable, Optional
import customtkinter as ctk
from .button import Button


class AngleButton(Button):
    """
    A specialized button for angle-related actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/angle.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class DistanceButton(Button):
    """
    A specialized button for distance-related actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/distance.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class ExitButton(Button):
    """
    A specialized button for exit actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/exit.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)



class ScreenshotButton(Button):
    """
    A specialized button for screenshot actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/screenshot.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)
    

class FiltersButton(Button):
    """
    A specialized button for filter actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/filters.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class CropButton(Button):
    """
    A specialized button for crop actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/crop.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class GeometryButton(Button):
    """
    A specialized button for geometry actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/geometry.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class OCRButton(Button):
    """
    A specialized button for OCR actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins/ocr.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)