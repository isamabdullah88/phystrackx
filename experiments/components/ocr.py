"""
ocr.py

Handles preprocessing and storage of OCR-derived textual data for numerical analysis.

Author: Isam Balghari
"""

import re
from typing import List


class OCRData:
    def __init__(self, data: List[List[str]]) -> None:
        """
        Initializes OCRData with a list of lists of strings.

        Args:
            data (List[List[str]]): OCR text data arranged by channels and samples.
        """
        self.data: List[List[str]] = data
        self.datacount: int = len(data)
        self.samplecount: int = len(data[0]) if self.datacount > 0 and data[0] else 0
        self.clean()

    def __len__(self) -> int:
        return self.datacount

    def clean(self) -> None:
        """
        Cleans OCR data by removing all non-numeric characters except decimal points.
        Updates self.data in-place with cleaned strings.
        """
        cleaned_data: List[List[str]] = []

        for text_series in self.data:
            cleaned_series = [re.sub(r"[^\d.]", "", entry) for entry in text_series]
            cleaned_data.append(cleaned_series)

        self.data = cleaned_data
