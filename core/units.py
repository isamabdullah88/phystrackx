"""
units.py

Reads a length typed for the scale ruler, such as "50 cm" or "2.5m". The number sets the
ruler's real-world length, and the unit (if any) is shown on the ruler, in the plots, and in
the labels.

Author: Isam Balghari
"""

import re

# A number, then an optional unit: letters and symbols such as µ, ^, / (no spaces, no digits first)
_LENGTH = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([^\s\d.+\-][^\s]*)?\s*")


def parse_length(text: str) -> tuple[float, str]:
    """
    Splits a typed length into its value and unit.

    Returns:
        (value, unit): "50 cm" -> (50.0, "cm"), "50" -> (50.0, "").

    Raises:
        ValueError: If there is no number, or the value is not above zero.
    """
    match = _LENGTH.fullmatch(text)
    if not match:
        raise ValueError(f"Not a length: {text!r}")
    value = float(match.group(1))
    if not value > 0:
        raise ValueError("The length must be above zero")
    return value, (match.group(2) or "")


def unit_suffix(unit: str) -> str:
    """' cm' for a unit, or '' when there is none, for labels that end with the unit."""
    return f" {unit}" if unit else ""
