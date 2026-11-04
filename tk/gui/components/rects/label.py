
import customtkinter as ctk
from ..buttons import ToggleButton
from core import PixelRect


class LabelItem(ctk.CTkFrame):
    """Modular single-row widget displaying a color badge and coordinate text."""
    def __init__(self, parent, text="Label", color="#1f77b4", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Color indicator badge
        self.colorbox = ctk.CTkLabel(self, text="", width=14, height=14, fg_color=color,
                                     corner_radius=3)
        self.colorbox.pack(side="left", padx=(5, 8), pady=2)

        # Coordinate details
        self.label = ctk.CTkLabel(self, text=text, font=("Segoe UI", 13), anchor="w")
        self.label.pack(side="left", fill="x", expand=True)



class Labels(ctk.CTkFrame):
    """Container frame holding the toggle button and the list of labels."""
    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", ("#ffffff", "#2b2b2b"))
        kwargs.setdefault("corner_radius", 6)
        super().__init__(parent, **kwargs)

        self._items: list[LabelItem] = []

        # --- Top Header with ToggleButton ---
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(side="top", fill="x", padx=6, pady=4)

        self.title = ctk.CTkLabel(self.header, text="Rectangles",
                                        font=("Segoe UI", 14, "bold"))
        self.title.pack(side="left", padx=4)

        # Toggle button wired to expand/collapse callbacks
        self.tbutton = ToggleButton(self.header, commandon=self.toggleon, commandoff=self.toggleoff)
        self.tbutton.pack(side="right", padx=4)

        # --- Content Frame for Label Items ---
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))


    def add_labels(self, prects: list[PixelRect], color: str = "#2b8a3e"):
        """Creates and packs a LabelItem for each rectangle."""
        self.clear()

        for i, rect in enumerate(prects):
            x, y, w, h = rect.totuple()
            text = f"Rect-{i+1}: ({x:.0f}, {y:.0f}) | {w:.0f}×{h:.0f}"

            item = LabelItem(self.content_frame, text=text, color=color)
            item.pack(side="top", fill="x", pady=2)
            self._items.append(item)

    def clear(self):
        """Destroys all child label widgets and clears memory."""
        for item in self._items:
            item.destroy()
        self._items.clear()

    def toggleon(self):
        """Shows the labels list when the toggle is enabled."""
        self.content_frame.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))

    def toggleoff(self):
        """Collapses the labels list while keeping the toggle header visible."""
        self.content_frame.pack_forget()

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)
