"""File filtering utilities for batch image processing."""

import fnmatch
import os


def get_pattern_for_preset(preset: str, custom_pattern: str = "") -> str:
    """
    Get glob pattern string for a given filter preset.

    Args:
        preset: One of "All Images", "PNG Only", "JPG Only", or "Custom"
        custom_pattern: Custom pattern to use when preset is "Custom"

    Returns:
        Comma-separated glob patterns string
    """
    default_pattern = "*.png,*.jpg,*.jpeg,*.webp"

    presets = {
        "All Images": "*.png,*.jpg,*.jpeg,*.webp",
        "PNG Only": "*.png",
        "JPG Only": "*.jpg,*.jpeg",
    }

    if preset == "Custom":
        return custom_pattern.strip() if custom_pattern.strip() else default_pattern

    return presets.get(preset, default_pattern)


def filter_files_by_patterns(directory: str, pattern_string: str) -> list[str]:
    """
    Filter files in a directory by comma-separated glob patterns.

    Files are filtered using case-insensitive matching. Only regular files
    in the top level of the directory are included (no recursion into subdirectories).

    Args:
        directory: Path to the directory to search
        pattern_string: Comma-separated glob patterns (e.g., "*.png,*.jpg")

    Returns:
        List of filenames (not full paths) that match any of the patterns
    """
    if not os.path.isdir(directory):
        return []

    # Parse comma-separated patterns and strip whitespace
    patterns = [p.strip().lower() for p in pattern_string.split(",") if p.strip()]

    if not patterns:
        return []

    matching_files = []

    for entry in os.listdir(directory):
        # Skip directories, only include regular files
        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue

        # Case-insensitive matching
        entry_lower = entry.lower()
        for pattern in patterns:
            if fnmatch.fnmatch(entry_lower, pattern):
                matching_files.append(entry)
                break  # Don't add same file multiple times

    return matching_files
