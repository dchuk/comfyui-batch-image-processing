"""BatchImageLoader node for ComfyUI batch image processing."""

import os

from ..utils.file_utils import filter_files_by_patterns, get_pattern_for_preset
from ..utils.image_utils import load_image_as_tensor
from ..utils.sorting import natural_sort_key


class BatchImageLoader:
    """
    Load images from a directory with filtering and natural sort order.

    This node loads images from a specified directory path, applying optional
    glob pattern filtering. Images are sorted using natural sort (img2 before img10)
    and output one at a time for batch processing workflows.
    """

    CATEGORY = "batch_processing"

    @classmethod
    def INPUT_TYPES(cls):
        """Define input parameters for the node."""
        return {
            "required": {
                "directory": (
                    "STRING",
                    {
                        "default": "",
                        "multiline": False,
                        "tooltip": "Path to directory containing images",
                    },
                ),
                "filter_preset": (
                    ["All Images", "PNG Only", "JPG Only", "Custom"],
                    {"default": "All Images"},
                ),
            },
            "optional": {
                "custom_pattern": (
                    "STRING",
                    {
                        "default": "*.png,*.jpg,*.jpeg,*.webp",
                        "tooltip": "Comma-separated glob patterns (used when filter_preset is Custom)",
                    },
                ),
            },
            "hidden": {
                "current_index": ("INT", {"default": 0}),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "TOTAL_COUNT", "CURRENT_INDEX", "FILENAME", "BASENAME")
    FUNCTION = "load_image"
    OUTPUT_NODE = False

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        directory: str,
        filter_preset: str,
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        current_index: int = 0,
    ):
        """
        Validate inputs before execution.

        ComfyUI calls this at queue time to catch errors early.
        Returns True if valid, or an error string if invalid.
        """
        if not directory or not directory.strip():
            return "Directory path is required"

        if not os.path.isdir(directory):
            return f"Directory does not exist: {directory}"

        pattern = get_pattern_for_preset(filter_preset, custom_pattern)
        files = filter_files_by_patterns(directory, pattern)

        if not files:
            return f"No images found matching pattern: {pattern}"

        return True

    @classmethod
    def IS_CHANGED(
        cls,
        directory: str,
        filter_preset: str,
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        current_index: int = 0,
    ):
        """
        Determine if node should re-execute.

        Returns a value that changes when inputs change.
        """
        return f"{directory}|{filter_preset}|{custom_pattern}|{current_index}"

    def load_image(
        self,
        directory: str,
        filter_preset: str,
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        current_index: int = 0,
    ):
        """
        Load the current image from the directory.

        Args:
            directory: Path to the image directory
            filter_preset: Preset filter option
            custom_pattern: Custom glob pattern(s) when filter_preset is "Custom"
            current_index: 0-based index of current image (for iteration)

        Returns:
            Tuple of (image_tensor, total_count, current_index_1based, filename, basename)
        """
        # Get pattern and filter files
        pattern = get_pattern_for_preset(filter_preset, custom_pattern)
        files = filter_files_by_patterns(directory, pattern)

        # Sort files using natural sort
        files = sorted(files, key=natural_sort_key)

        total_count = len(files)

        # Handle wraparound for iteration
        actual_index = current_index % total_count if total_count > 0 else 0

        # Try to load the image at the current index
        # If it fails, try subsequent files
        attempts = 0
        last_error = None

        while attempts < total_count:
            try_index = (actual_index + attempts) % total_count
            filename = files[try_index]
            filepath = os.path.join(directory, filename)

            try:
                image_tensor = load_image_as_tensor(filepath)
                # Success - extract basename (filename without extension)
                basename = os.path.splitext(filename)[0]

                # Return 1-based index for user display
                return (image_tensor, total_count, try_index + 1, filename, basename)

            except Exception as e:
                last_error = e
                attempts += 1

        # All files failed to load
        raise RuntimeError(
            f"Failed to load any images from directory. Last error: {last_error}"
        )
