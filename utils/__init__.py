"""Utility modules for batch image processing."""

# Always export natural_sort_key (no external dependencies)
from .sorting import natural_sort_key

# Conditionally export load_image_as_tensor (requires numpy, torch, PIL)
try:
    from .image_utils import load_image_as_tensor

    __all__ = ["natural_sort_key", "load_image_as_tensor"]
except ImportError:
    # Allow import to succeed even without ComfyUI dependencies
    # This enables running tests for modules that don't need these dependencies
    __all__ = ["natural_sort_key"]
