"""Utility modules for batch image processing."""

# Always export modules without external dependencies
from .sorting import natural_sort_key
from .file_utils import filter_files_by_patterns, get_pattern_for_preset

# Conditionally export load_image_as_tensor (requires numpy, torch, PIL)
try:
    from .image_utils import load_image_as_tensor

    __all__ = [
        "natural_sort_key",
        "filter_files_by_patterns",
        "get_pattern_for_preset",
        "load_image_as_tensor",
    ]
except ImportError:
    # Allow import to succeed even without ComfyUI dependencies
    # This enables running tests for modules that don't need these dependencies
    __all__ = ["natural_sort_key", "filter_files_by_patterns", "get_pattern_for_preset"]
