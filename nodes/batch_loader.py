"""BatchImageLoader node for ComfyUI batch image processing."""

import os

from ..utils.file_utils import filter_files_by_patterns, get_pattern_for_preset
from ..utils.image_utils import load_image_as_tensor
from ..utils.iteration_state import IterationState
from ..utils.queue_control import stop_auto_queue, trigger_next_queue
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
                "iteration_mode": (
                    ["Continue", "Reset"],
                    {
                        "default": "Continue",
                        "tooltip": "Continue = resume from current position, Reset = start fresh",
                    },
                ),
                "error_handling": (
                    ["Stop on error", "Skip on error"],
                    {
                        "default": "Stop on error",
                        "tooltip": "How to handle images that fail to load",
                    },
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
                "start_index": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "max": 99999,
                        "tooltip": "Starting index for batch processing (0-based)",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("IMAGE", "TOTAL_COUNT", "INDEX", "FILENAME", "BASENAME", "STATUS", "BATCH_COMPLETE")
    FUNCTION = "load_image"
    OUTPUT_NODE = False

    @classmethod
    def VALIDATE_INPUTS(
        cls,
        directory: str,
        filter_preset: str,
        iteration_mode: str = "Continue",
        error_handling: str = "Stop on error",
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        start_index: int = 0,
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
        iteration_mode: str = "Continue",
        error_handling: str = "Stop on error",
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        start_index: int = 0,
    ):
        """
        Determine if node should re-execute.

        Returns a value that changes when inputs or internal state change.
        Includes current index to force re-execution each iteration.
        """
        if not directory:
            return ""
        state = IterationState.get_state(directory)
        return f"{directory}|{filter_preset}|{state.get('index', 0)}|{iteration_mode}"

    def load_image(
        self,
        directory: str,
        filter_preset: str,
        iteration_mode: str = "Continue",
        error_handling: str = "Stop on error",
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        start_index: int = 0,
    ):
        """
        Load the current image from the directory.

        Args:
            directory: Path to the image directory
            filter_preset: Preset filter option
            iteration_mode: "Continue" to resume from current position, "Reset" to start fresh
            error_handling: "Stop on error" or "Skip on error"
            custom_pattern: Custom glob pattern(s) when filter_preset is "Custom"
            start_index: Starting index for batch processing (0-based)

        Returns:
            Tuple of (image_tensor, total_count, index, filename, basename, status, batch_complete)
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
