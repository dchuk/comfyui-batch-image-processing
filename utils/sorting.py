"""Natural sorting utilities for filename ordering."""

import re


def natural_sort_key(s: str) -> list:
    """
    Generate key for natural sorting (case-insensitive).

    Natural sort orders numbers by their numeric value:
    ['img10', 'img2', 'img1'] -> ['img1', 'img2', 'img10']

    Args:
        s: String to generate sort key for

    Returns:
        List of string and integer parts for comparison
    """
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", s)
    ]
