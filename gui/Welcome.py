
import customtkinter as ctk
from PIL import ImageTk, Image
from core import abspath

class WelcomeScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Welcome")
        self.root.geometry("960x640")

        # Title label
        self.label = ctk.CTkLabel(root, text="Welcome to PhysTrackX", font=("Helvetica", 24))
        self.label.pack(pady=(20, 0))

        # Subtitle label
        subtlabel = ctk.CTkLabel(root, text="A Project By Dr. Sabieh, Isam", font=("Helvetica", 18))
        subtlabel.pack(pady=(10, 0))

        # Load and display the image
        self.displogo(root)

        self.texanim()

    def displogo(self, root):
        # Load the image
        img = Image.open(abspath("assets/logo.png"))
        photo = ImageTk.PhotoImage(img)

        # Create a label to display the image
        imglabel = ctk.CTkLabel(root, image=photo, text="")
        imglabel.image = photo  # Keep a reference, prevent GC
        imglabel.pack(pady=(10, 20))

    def texanim(self):
        text = self.label.cget("text")
        if text.endswith("..."):
            self.label.configure(text="Welcome to PhysTrackX")
        else:
            self.label.configure(text=text + ".")
        self.root.after(500, self.texanim)

