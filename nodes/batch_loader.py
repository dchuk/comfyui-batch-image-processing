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
        # Normalize directory path for consistent state lookup
        directory = os.path.normpath(directory)

        # Get pattern and filter files
        pattern = get_pattern_for_preset(filter_preset, custom_pattern)
        files = filter_files_by_patterns(directory, pattern)

        # Sort files using natural sort
        files = sorted(files, key=natural_sort_key)

        total_count = len(files)

        # === STATE MANAGEMENT ===

        # Get or initialize state for this directory
        state = IterationState.get_state(directory)

        # Check for directory change - if last_directory differs from current, reset
        # This detects when user switches to a different folder
        last_dir = IterationState.get_last_directory()
        if last_dir is not None:
            if IterationState.check_directory_change(directory, last_dir):
                # Switching to a different directory, reset its state
                IterationState.reset(directory)
                state = IterationState.get_state(directory)

        # Track current directory for next execution's change detection
        IterationState.set_last_directory(directory)

        # Handle iteration_mode
        if iteration_mode == "Reset":
            IterationState.reset(directory)
            state = IterationState.get_state(directory)

        # Handle start_index: If start_index > 0 and state.index == 0, use start_index
        if start_index > 0 and state["index"] == 0:
            state["index"] = start_index

        # Set total count for this batch
        IterationState.set_total_count(directory, total_count)

        # Set status to processing at start
        IterationState.set_status(directory, "processing")

        # === PROCESSING FLOW ===

        # Get current index from state (0-based)
        current_index = state["index"]

        # Handle wraparound (in case index > total_count from previous run with more files)
        if current_index >= total_count:
            current_index = 0
            state["index"] = 0

        # Load image with error handling
        return self._load_with_error_handling(
            directory=directory,
            files=files,
            current_index=current_index,
            total_count=total_count,
            error_handling=error_handling,
            skip_count=0,
        )

    def _load_with_error_handling(
        self,
        directory: str,
        files: list,
        current_index: int,
        total_count: int,
        error_handling: str,
        skip_count: int,
    ):
        """
        Load image at current index with error handling.

        Args:
            directory: Path to the image directory
            files: Sorted list of filenames
            current_index: Current 0-based index
            total_count: Total number of files
            error_handling: "Stop on error" or "Skip on error"
            skip_count: Number of files skipped so far (for infinite loop protection)

        Returns:
            Tuple of (image_tensor, total_count, index, filename, basename, status, batch_complete)
        """
        # Infinite loop protection
        if skip_count >= total_count:
            raise RuntimeError("Failed to load any images from directory - all files skipped or failed")

        filename = files[current_index]
        filepath = os.path.join(directory, filename)

        try:
            image_tensor = load_image_as_tensor(filepath)
        except Exception as e:
            if error_handling == "Stop on error":
                raise RuntimeError(f"Failed to load image {filename}: {e}") from e
            else:
                # Skip on error: advance index and try next image
                IterationState.advance(directory)
                next_index = (current_index + 1) % total_count
                return self._load_with_error_handling(
                    directory=directory,
                    files=files,
                    current_index=next_index,
                    total_count=total_count,
                    error_handling=error_handling,
                    skip_count=skip_count + 1,
                )

        # Success - extract basename (filename without extension)
        basename = os.path.splitext(filename)[0]

        # Determine if this is the last image
        batch_complete = current_index >= total_count - 1

        # Queue control based on batch_complete
        if batch_complete:
            # Stop Auto Queue and reset for re-run
            stop_auto_queue()
            IterationState.wrap_index(directory)
            status = "completed"
            IterationState.set_status(directory, "completed")
            # Don't advance - we've already wrapped to 0 for next run
        else:
            # Trigger next queue item
            trigger_next_queue()
            status = "processing"
            # Advance index AFTER successful load
            # This means interrupt during load leaves index unchanged (Continue mode resumes here)
            IterationState.advance(directory)

        # Return 0-based index
        return (image_tensor, total_count, current_index, filename, basename, status, batch_complete)
