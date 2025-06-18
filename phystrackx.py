import tkinter as tk
import customtkinter 

from gui.Welcome import WelcomeScreen
from gui.Menu import MenuScreen

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

class GUI:
    def __init__(self):
        pass

    def welcome(self):

        root = customtkinter.CTk()
        root.geometry("960x640")
        welcome = WelcomeScreen(root)
        root.after(500, root.destroy)  # Close welcome screen after 5 seconds
        root.mainloop()

    def start(self):
        
        root = customtkinter.CTk()
        root.geometry("960x640")
        menu = MenuScreen(root)
        root.mainloop()

def main():
    program = GUI()
    # program.welcome()
    program.start()


if __name__ == "__main__":
    main()