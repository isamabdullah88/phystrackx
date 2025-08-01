import customtkinter

from gui.menu import MenuScreen
from core import setup_logging

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

class GUI:
    def __init__(self):
        self.width = 1280
        self.hegiht = 720

    def start(self):

        root = customtkinter.CTk()
        root.geometry(f"{self.width}x{self.hegiht}")
        menu = MenuScreen(root)
        root.mainloop()

def main():
    program = GUI()
    program.start()


if __name__ == "__main__":
    
    setup_logging()
    main()