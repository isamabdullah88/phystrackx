"""
Beautiful Custom Tkinter Dialog Box Example
Author: Isam Balghari 
Date: December 5, 2025

Description:
This script defines a custom Toplevel dialog box with input validation. 
It now requires an 'expected_type' argument (e.g., int, float, str) and 
will prevent the dialog from closing if the input doesn't match the required type.
"""

import tkinter as tk
from tkinter import ttk, font
from typing import Type

class DialogBox(tk.Toplevel):
    # Added 'expected_type' argument, defaulted to str
    def __init__(self, parent, title="Input Required", message="Please enter a value:", expected_type: Type = str): 
        
        super().__init__(parent)
        self.title(title)
        self.parent = parent
        self.result = None
        self.expected_type = expected_type # Store the required type
        
        # Make the dialog modal
        self.transient(parent)
        self.grab_set()
        
        # --- Visual Enhancement & Styling ---
        style = ttk.Style(self)
        
        DIALOG_BG = "#c4c3c3"
        TEXT_COLOR = "#ffffff"
        BUTTON_COLOR = "#337ab7"
        HOVER_COLOR = "#23527c"
        ERROR_COLOR = "#dc3545" # Red for error messages
        
        style.configure('TFrame', background=DIALOG_BG)
        style.configure('Accent.TButton', foreground='white', background=BUTTON_COLOR, font=('Arial', 12, 'bold'), padding=8)
        style.map('Accent.TButton', background=[('active', HOVER_COLOR)], foreground=[('active', 'white')])
        style.configure('TButton', font=('Arial', 12))

        # --- Create Main UI Components ---
        
        main_frame = ttk.Frame(self, padding="30 25 30 25")
        main_frame.pack(expand=True, fill='both')

        message_font = font.Font(family="Arial", size=16, weight="bold") 
        
        # Message Label
        message_label = ttk.Label(
            main_frame, 
            text=message, 
            font=message_font,
            foreground=TEXT_COLOR,
            background=DIALOG_BG
        )
        message_label.pack(fill='x', pady=(0, 10))

        # Expected Type Hint Label
        type_str = expected_type.__name__.capitalize()
        ttk.Label(
            main_frame,
            text=f"(Expected Input: {type_str})",
            foreground="#6c757d", # Grey hint text
            background=DIALOG_BG,
            font=('Arial', 10)
        ).pack(fill='x', pady=(0, 10))


        # Input Entry Field
        self.entry = ttk.Entry(
            main_frame, 
            width=50, 
            font=('Consolas', 14)
        )
        self.entry.pack(fill='x', padx=5, pady=5)
        self.entry.focus_set()
        
        # Error Message Label (Hidden initially)
        self.error_label = ttk.Label(
            main_frame,
            text="",
            foreground=ERROR_COLOR,
            background=DIALOG_BG,
            font=('Arial', 10, 'bold')
        )
        self.error_label.pack(fill='x', pady=(5, 0))


        # Separator 
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=15)

        # --- Button Section ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(0, 0))
        
        button_frame.columnconfigure(0, weight=1) 
        
        # OK Button (Confirm)
        ttk.Button(button_frame, 
                   text="Confirm", 
                   command=self.on_ok, 
                   style='Accent.TButton').grid(row=0, column=2, padx=(15, 0), sticky='e')

        # Cancel Button
        ttk.Button(button_frame, 
                   text="Cancel", 
                   command=self.on_cancel).grid(row=0, column=1, sticky='e')

        # --- Final setup ---
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind('<Return>', lambda e: self.on_ok())
        self.bind('<Escape>', lambda e: self.on_cancel())
        
        self.update_idletasks()
        self.center_window()
        
        self.wait_window(self)

    def center_window(self):
        """Calculates the necessary position to center the dialog on the screen."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        self.update_idletasks() 
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        self.geometry(f'+{x}+{y}')

    def on_ok(self):
        """Called when OK is pressed. Validates the input type before closing."""
        user_input_str = self.entry.get().strip()
        
        if not user_input_str:
            self.error_label.config(text="Input cannot be empty.")
            return

        try:
            # Attempt to convert the string input to the expected type
            validated_input = self.expected_type(user_input_str)
            
            # If successful, store the converted value and close
            self.result = validated_input
            self.destroy()
            
        except ValueError:
            # If conversion fails (e.g., str->int on non-numeric text)
            type_name = self.expected_type.__name__.capitalize()
            self.error_label.config(text=f"Invalid input. Please enter a valid {type_name} value.")
            self.entry.focus_set() # Keep focus on the entry field
        except Exception as e:
            # Catch other potential errors
            self.error_label.config(text=f"An unexpected error occurred: {e}")


    def on_cancel(self):
        """Called when Cancel or the window close button is hit."""
        self.result = None
        self.destroy()

# --- Main Application ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Main Application")
    
    def open_dialogs():
        
        # 1. Example requiring an INTEGER
        dialog_int = DialogBox(
            root, 
            title="Age Check", 
            message="Please enter your age:", 
            expected_type=int # <-- Expects an integer
        )
        if dialog_int.result is not None:
            print(f"Age entered (Type: {type(dialog_int.result).__name__}): {dialog_int.result}")
        else:
            print("Dialog 1 cancelled.")

        # 2. Example requiring a FLOAT
        dialog_float = DialogBox(
            root,
            title="Measurement",
            message="Enter the precise width in cm:",
            expected_type=float # <-- Expects a float
        )
        if dialog_float.result is not None:
            print(f"Width entered (Type: {type(dialog_float.result).__name__}): {dialog_float.result}")
        else:
            print("Dialog 2 cancelled.")

        # 3. Example requiring a STRING (default behavior)
        dialog_str = DialogBox(
            root,
            title="Name Input",
            message="Enter your full name:",
            expected_type=str # <-- Expects a string
        )
        if dialog_str.result is not None:
            print(f"Name entered (Type: {type(dialog_str.result).__name__}): {dialog_str.result}")
        else:
            print("Dialog 3 cancelled.")


    # Button to open the dialog
    ttk.Button(root, text="Open Type-Validated Dialogs", command=open_dialogs).pack(padx=50, pady=50)
    
    root.mainloop()