from typing import Callable, Optional
import customtkinter as ctk
from .button import Button

class SubmitButton(Button):
    """
    A specialized button for submission actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/submit.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class BinButton(Button):
    """
    A specialized button for deletion actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/bin.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class PluginsButton(Button):
    """
    A specialized button for plugin actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plugins.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class VideoButton(Button):
    """
    A specialized button for video actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/video.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class SeekButton(Button):
    """
    A specialized button for seek actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/seek.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class AxisButton(Button):
    """
    A specialized button for axis actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/axis.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class RulerButton(Button):
    """
    A specialized button for ruler actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/ruler.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class RectangleButton(Button):
    """
    A specialized button for rectangle actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/rectangle.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)

class TrackButton(Button):
    """
    A specialized button for track actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/track.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class PlotButton(Button):
    """
    A specialized button for plot actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/plot.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class SaveButton(Button):
    """
    A specialized button for save actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/save.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs)


class ResetButton(Button):
    """
    A specialized button for reset actions, inheriting from the base Button class.
    """
    def __init__(self, master: ctk.CTkCanvas | ctk.CTkFrame, command: Callable[[], None],
                 size: int = 40, tooltip: Optional[str] = None,
                 fg_color: str = "#2b2b2b", hover_color: str = "#3a3a3a", **kwargs) -> None:
        super().__init__(master=master, imgpath="assets/reset.png", command=command,
                         size=size, tooltip=tooltip, fg_color=fg_color,
                         hover_color=hover_color, **kwargs) 

