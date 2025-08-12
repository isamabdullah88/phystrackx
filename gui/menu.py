"""
menuscreen.py
GUI menu for selecting tracking type in PhysTrackX.

Author: Isam Balghari
"""

import customtkinter as ctk
from PIL import Image
from tkinter import Tk, Widget

from .rigid.rigidapp import RigidApp
from .nonrigid.nonrigid import NonRigid
from core import abspath


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

    # ================== UI Construction Methods ================== #

    # def _create_title_labels(self) -> None:
    #     """Create and place the main title and subtitle labels."""
    #     self.label = ctk.CTkLabel(
    #         self.root, text="Welcome to PhysTrackX", font=("Helvetica", 24)
    #     )
    #     self.label.pack(pady=(20, 0))

    #     subtlabel = ctk.CTkLabel(
    #         self.root, text="A Project By Dr. Sabieh, Isam", font=("Helvetica", 18)
    #     )
    #     subtlabel.pack(pady=(10, 0))

    def _create_icon_grid(self) -> None:
        """Create a centered frame with buttons for selecting tracking type."""
        center_frame = ctk.CTkFrame(self.root)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        self._create_icon_button(
            center_frame, "assets/rigid.png", self._rigid_mode, row=0, col=0
        )
        self._create_icon_button(
            center_frame, "assets/nonrigid.png", self._nonrigid_mode, row=0, col=1
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

        photo = ctk.CTkImage(dark_image=img, size=(base_width, h_size))
        image_label = ctk.CTkLabel(self.root, image=photo, text="")
        image_label.image = photo  # Prevent garbage collection
        image_label.pack(pady=(10, 0))

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