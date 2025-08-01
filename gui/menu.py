import customtkinter as ctk
from PIL import Image, ImageSequence, ImageEnhance
from core import abspath
from .rigid.rigidapp import RigidApp

class AnimatedGIF(ctk.CTkLabel):
    def __init__(self, master, gif_path, on_end=None, *args, **kwargs):
        self.sequence = [
            frame.copy().convert("RGBA").resize((1280, 720))
            for frame in ImageSequence.Iterator(Image.open(gif_path))
        ]
        self.frames = [ctk.CTkImage(light_image=img, size=img.size) for img in self.sequence]
        self.idx = 0
        self.on_end = on_end  # Callback to run after last frame
        super().__init__(master, image=self.frames[0], text="", *args, **kwargs)
        self.after(25, self.play)

    def play(self):
        if self.idx < len(self.frames):
            self.configure(image=self.frames[self.idx])
            self.idx += 1
            self.after(25, self.play)
        else:
            if self.on_end:
                self.on_end()  # Call the callback when done


class MenuScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("PhysTrack Front Page")
        self.root.geometry("1280x720")

        # Container frame
        self.main_frame = ctk.CTkFrame(self.root, width=1280, height=720)
        self.main_frame.pack(fill="both", expand=True)
        self.canvas = ctk.CTkCanvas(self.main_frame)
        self.canvas.pack(fill="both", expand=True)

        # Animated GIF background
        # Play animation, then call self.show_start_button
        self.animated_bg = AnimatedGIF(
            self.root,
            abspath("assets/logos/frontpage.gif"),
            on_end=self.show_start_button
        )
        self.animated_bg.place(x=0, y=0, relwidth=1, relheight=1)


    def show_start_button(self):
        # Load original and hover images
        self.img_original = Image.open(abspath("assets/start.png")).convert("RGBA").resize((170, 72))
        enhancer = ImageEnhance.Brightness(self.img_original)
        self.img_hovered = enhancer.enhance(1.2)  # Brighter version

        self.tk_img_normal = ctk.CTkImage(light_image=self.img_original, size=self.img_original.size)
        self.tk_img_hover = ctk.CTkImage(light_image=self.img_hovered, size=self.img_hovered.size)

        # Create transparent label as image button
        self.img_label = ctk.CTkLabel(
            self.root,
            text="",
            image=self.tk_img_normal,
            fg_color="transparent",
            cursor="hand2"  # Change cursor to hand
        )
        self.img_label.place(x=591, y=467)

        # Bind events
        self.img_label.bind("<Button-1>", self.rigid)
        self.img_label.bind("<Enter>", self.on_enter)
        self.img_label.bind("<Leave>", self.on_leave)

    def on_click(self, event):
        print("Image button clicked!")

    def on_enter(self, event):
        self.img_label.configure(image=self.tk_img_hover)

    def on_leave(self, event):
        self.img_label.configure(image=self.tk_img_normal)

    # def _mkbutton(self, imgpath: str, command: callable, width, height) -> ctk.CTkButton:
    #     """Creates a CTkButton with an image and command."""
    #     img = Image.open(abspath(imgpath)).resize(
    #         (width, height), Image.Resampling.LANCZOS
    #     )
    #     ctkimg = ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))
    #     button = ctk.CTkButton(
    #         self.canvas, text="", width=0, height=0, corner_radius=50,
    #         command=command, image=ctkimg, border_spacing=0, border_width=0, fg_color="transparent", bg_color="black"
    #     )
    #     button.image = ctkimg
    #     return button

    def rigid(self, event):
        self.clear_screen()
        
        rigid = RigidApp(self.root)
        
    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    MenuScreen(root)
    root.mainloop()
