"""
menuscreen.py
GUI menu for selecting tracking type in PhysTrackX.

Author: Isam Balghari
"""

from tkinter import Tk, Widget
from .rigid.rigidapp import RigidApp
import webbrowser
import customtkinter as ctk
from PIL import Image, ImageSequence
import pygame


class AnimatedGIF(ctk.CTkLabel):
    """Plays a GIF animation once with background music, 
    and calls a callback at the end."""

    def __init__(self, master, gif_path: str, music_path: str = None, on_end=None,
                 *args, **kwargs):
        """
        Args:
            master: Parent widget.
            gif_path (str): Path to the GIF file.
            music_path (str, optional): Path to the music file to play.
            on_end (callable, optional): Function to call when animation ends.
        """
        # Load GIF frames
        self.sequence = [
            frame.copy() for frame in ImageSequence.Iterator(Image.open(gif_path))
        ]
        self.frames = [
            ctk.CTkImage(light_image=img, size=img.size) for img in self.sequence
        ]
        self.idx = 0
        self.on_end = on_end
        self.music_path = music_path

        # Init label with first frame
        super().__init__(master, image=self.frames[0], text="", *args, **kwargs)

        # Play music if given
        if self.music_path:
            pygame.mixer.init()
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.play(-1)  # Loop indefinitely

        # Start animation
        self.after(64, self._play_once)

    def _play_once(self):
        if self.idx < len(self.frames):
            self.configure(image=self.frames[self.idx])
            self.idx += 1
            self.after(64, self._play_once)
        else:
            # Stop music once animation ends
            if self.music_path:
                pygame.mixer.music.stop()
            if self.on_end:
                self.on_end()


class MenuScreen:
    """Main menu screen for selecting between rigid and non-rigid tracking modes."""

    def __init__(self, root: Tk) -> None:
        """
        Initialize the MenuScreen.

        Args:
            root (Tk): The main application root window.
        """
        self.root = root
        self.root.title("Select Tracking Type")

        # self._create_title_labels()
        # self._display_logo()
        # self._start_text_animation()
        self._create_icon_grid()

        # === Background animation ===
        self.animated_bg = AnimatedGIF(
            master=self.main_frame,
            gif_path=abspath("assets/logos/frontpage.gif"),
            music_path=abspath("assets/logos/startup.mp3"),
            on_end=self._show_start_button
        )

    def _create_icon_button(
        self,
        frame: Widget,
        img_path: str,
        command: callable,
        row: int,
        col: int,
        btn_size: int = 80
    ) -> None:
        """
        Create a button with an image and a command.

        Args:
            frame (Widget): Parent frame to hold the button.
            img_path (str): Path to the button icon.
            command (callable): Function to execute when clicked.
            row (int): Row index in grid.
            col (int): Column index in grid.
            btn_size (int, optional): Button size in pixels. Defaults to 80.
        """
        img = Image.open(abspath(img_path)).resize(
            (btn_size, btn_size), Image.Resampling.LANCZOS
        )
        img_ctk = ctk.CTkImage(dark_image=img, size=(btn_size, btn_size))
        button = ctk.CTkButton(
            frame,
            image=img_ctk,
            text="",
            width=btn_size,
            height=btn_size,
            compound="left",
            command=command
        )
        button.grid(row=row, column=col, padx=10, pady=10)

    def _display_logo(self) -> None:
        """Load and display the application logo."""
        img_path = abspath("assets/logo.png")
        img = Image.open(img_path)

        base_width = 700
        w_percent = base_width / float(img.size[0])
        h_size = int(float(img.size[1]) * w_percent)
        img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)

    def _show_donate_button(self):
        """Displays a donation button linking to donation section."""
        def open_donation():
            webbrowser.open("https://github.com/isamabdullah88/phystrackx?files=1#-support-this-project")

    # ================== Animation ================== #

    def _start_text_animation(self) -> None:
        """Start animating the welcome text."""
        self._animate_text()

    def _animate_text(self) -> None:
        """Append dots to the welcome text in a loop."""
        text = self.label.cget("text")
        if text.endswith("..."):
            self.label.configure(text="Welcome to PhysTrackX")
        else:
            self.label.configure(text=text + ".")
        self._tid = self.root.after(500, self._animate_text)

    # ================== Event Handlers ================== #

    def _rigid_mode(self) -> None:
        """Switch to the rigid tracking mode."""
        # self.root.after_cancel(self._tid)
        self.clear_screen()
        RigidApp(self.root)

    def _nonrigid_mode(self) -> None:
        """Switch to the non-rigid tracking mode."""
        # self.root.after_cancel(self._tid)
        NonRigid(self.root)

    # ================== Utility ================== #

    def clear_screen(self) -> None:
        """Remove all widgets from the root window."""
        for widget in self.root.winfo_children():
            widget.destroy()