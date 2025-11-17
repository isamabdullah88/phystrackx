"""
menu.py

Main menu screen for PhysTrackX.

This module defines the startup interface, including animated background,
and a custom transparent image-based start button that launches the Rigid Motion module.

Author: Isam Balghari
"""

import customtkinter as ctk
from PIL import Image, ImageSequence, ImageEnhance
from core import abspath
from .rigid.rigidapp import RigidApp
import webbrowser

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
        self.after(50, self._play_once)

    def _play_once(self):
        if self.idx < len(self.frames):
            self.configure(image=self.frames[self.idx])
            self.idx += 1
            self.after(50, self._play_once)
        else:
            # Stop music once animation ends
            if self.music_path:
                pygame.mixer.music.stop()
            if self.on_end:
                self.on_end()


class MenuScreen:
    """Main menu screen with animation and image button to launch PhysTrack Rigid."""

    def __init__(self):
        self.root = ctk.CTk()
        
        self.width = 1280
        self.height = 720
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.update_idletasks()
        
        self.width = self.root.winfo_width()
        self.height = self.root.winfo_height()
        
        # === Frame for layout ===
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True)
        

        # === Background animation ===
        self.animated_bg = AnimatedGIF(
            master=self.main_frame,
            gif_path=abspath("assets/logos/frontpage.gif"),
            music_path=abspath("assets/logos/startup.mp3"),
            on_end=self._show_start_button
        )
        self.animated_bg.place(x=0, y=0, relwidth=1, relheight=1)

    def _show_start_button(self):
        """Display the start button after the GIF ends."""
        self._load_start_images()

        self.img_label = ctk.CTkLabel(
            master=self.main_frame,
            text="",
            image=self.tk_img_normal,
            fg_color="transparent",
            cursor="hand2"
        )
        self.img_label.place(x=591, y=467)

        self.img_label.bind("<Button-1>", self._launch_rigid_app)
        self.img_label.bind("<Enter>", self._hover_in)
        self.img_label.bind("<Leave>", self._hover_out)

        self._show_donate_button()  # 👈 Add this line to show donation button

    def _show_donate_button(self):
        """Displays a donation button linking to donation section."""
        def open_donation():
            webbrowser.open("https://github.com/isamabdullah88/phystrackx?files=1#-support-this-project")

        imgpath = abspath("assets/logos/donation.png")  # Ensure this image exists
        img = Image.open(imgpath).convert("RGBA").resize((50, 50))
        dimg = ctk.CTkImage(light_image=img, dark_image=img, size=(50, 50))

        self.donate_button = ctk.CTkButton(
            self.root,
            image=dimg,
            command=open_donation,
            text="",
            width=50,
            height=50
        )
        self.donate_button.image = dimg  # Prevent GC
        self.donate_button.place(x=1200, y=15)  # Adjust position if needed


    def _load_start_images(self):
        """Load normal and hover images for the start button."""
        img_path = abspath("assets/start.png")
        base_img = Image.open(img_path).convert("RGBA").resize((170, 72))
        bright_img = ImageEnhance.Brightness(base_img).enhance(1.2)

        self.tk_img_normal = ctk.CTkImage(light_image=base_img, size=base_img.size)
        self.tk_img_hover = ctk.CTkImage(light_image=bright_img, size=bright_img.size)

    def _hover_in(self, _):
        self.img_label.configure(image=self.tk_img_hover)

    def _hover_out(self, _):
        self.img_label.configure(image=self.tk_img_normal)

    def _launch_rigid_app(self, _):
        self._clear_screen()
        RigidApp(self.root)

    def _clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    MenuScreen(root)
    root.mainloop()
