"""
image_cache.py

Centralized image caching service to eliminate disk I/O and resampling overhead during resets.
"""

from PIL import Image
import customtkinter as ctk
from core import abspath


class ButtonCache:
    """Stores pre-scaled PIL & CTkImage objects in RAM for instant UI rendering."""
    
    _cache: dict[str, ctk.CTkImage] = {}

    @classmethod
    def get(cls, imgpath: str, size: int = 40) -> ctk.CTkImage:
        """
        Retrieves a pre-scaled CTkImage from RAM cache, or loads and caches it on first call.
        """
        cache_key = f"{imgpath}"

        if cache_key not in cls._cache:
            # Load and resize ONCE
            pil_img = Image.open(abspath(imgpath)).resize((size, size), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(size, size))
            
            # Store in RAM permanently
            cls._cache[cache_key] = ctk_img
            
        return cls._cache[cache_key]