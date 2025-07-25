
import customtkinter as ctk
from PIL import Image
from core import abspath

def mkbutton(canvas, imgpath, command, btnsize=30):
    """
    Creates a button with an image and a command.
    """
    img = Image.open(abspath(imgpath)).resize((btnsize, btnsize), Image.Resampling.LANCZOS)
    
    img = ctk.CTkImage(light_image=img, dark_image=img, size=(btnsize, btnsize))
    button = ctk.CTkButton(canvas, text="", width=btnsize, height=btnsize,
                        image=img, command=command)
    
    button.image = img
    
    return button