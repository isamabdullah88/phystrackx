import customtkinter 

from gui.Menu import MenuScreen

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

class GUI:
    def __init__(self):
        self.width = 1200
        self.hegiht = 800

    def start(self):

        root = customtkinter.CTk()
        root.geometry(f"{self.width}x{self.hegiht}")
        menu = MenuScreen(root)
        root.mainloop()

def main():
    program = GUI()
    program.start()


if __name__ == "__main__":
    main()