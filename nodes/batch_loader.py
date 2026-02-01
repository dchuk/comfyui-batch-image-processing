"""BatchImageLoader node for ComfyUI batch image processing."""

import torch

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
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "TOTAL_COUNT", "CURRENT_INDEX", "FILENAME", "BASENAME")
    FUNCTION = "load_image"
    OUTPUT_NODE = False

    def load_image(
        self,
        directory: str,
        filter_preset: str,
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
    ):
        """
        Load the current image from the directory.

        This is a placeholder implementation that returns dummy values.
        The full implementation will be completed in Plan 02.

        Args:
            directory: Path to the image directory
            filter_preset: Preset filter option
            custom_pattern: Custom glob pattern(s) when filter_preset is "Custom"

        Returns:
            Tuple of (image_tensor, total_count, current_index, filename, basename)
        """
        # Placeholder implementation - returns dummy values
        # Full implementation in Plan 02
        dummy_image = torch.zeros((1, 64, 64, 3), dtype=torch.float32)
        total_count = 0
        current_index = 1
        filename = ""
        basename = ""

        return (dummy_image, total_count, current_index, filename, basename)
