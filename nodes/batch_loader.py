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
            "hidden": {
                "prompt": "PROMPT",  # Complete workflow for re-queueing
                "extra_pnginfo": "EXTRA_PNGINFO",  # PNG metadata (for future use)
                "unique_id": "UNIQUE_ID",  # This node's ID (for future use)
                "queue_nonce": "INT",  # Injected by queue_control to bust cache
            },
        }

    # Output order optimized to align with BatchImageSaver inputs (minimizes wire crossing)
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "INT", "INT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("IMAGE", "INPUT_DIRECTORY", "INPUT_BASE_NAME", "INPUT_FILE_TYPE", "FILENAME", "INDEX", "TOTAL_COUNT", "STATUS", "BATCH_COMPLETE")
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
        # Hidden inputs (ComfyUI passes these to all class methods)
        prompt: dict = None,
        extra_pnginfo: dict = None,
        unique_id: str = None,
        queue_nonce: int = 0,
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
        # Hidden inputs (ComfyUI passes these to all class methods)
        prompt: dict = None,
        extra_pnginfo: dict = None,
        unique_id: str = None,
        queue_nonce: int = 0,
    ):
        """
        Determine if node should re-execute.

        Returns a value that changes when inputs or internal state change.
        queue_nonce is injected by trigger_next_queue to bust ComfyUI's cache.
        """
        import time
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[BatchImageLoader] ===== IS_CHANGED called at {timestamp} =====")

        if not directory:
            print(f"[BatchImageLoader] IS_CHANGED: directory is empty, returning ''")
            return ""

        # Normalize directory to match load_image's normalization
        import os
        normalized_dir = os.path.normpath(directory)
        state = IterationState.get_state(normalized_dir)
        index = state.get('index', 0)
        total = state.get('total_count', 0)
        status = state.get('status', 'unknown')

        # queue_nonce changes each re-queue to bust ComfyUI's execution cache
        hash_value = f"{normalized_dir}|{filter_preset}|{index}|{iteration_mode}|{queue_nonce}"

        print(f"[BatchImageLoader] IS_CHANGED: dir={os.path.basename(normalized_dir)}, index={index}/{total}, status={status}")
        print(f"[BatchImageLoader] IS_CHANGED: hash={hash_value[:80]}...")
        print(f"[BatchImageLoader] IS_CHANGED: unique_id={unique_id}, queue_nonce={queue_nonce}")

        return hash_value

    def load_image(
        self,
        directory: str,
        filter_preset: str,
        iteration_mode: str = "Continue",
        error_handling: str = "Stop on error",
        custom_pattern: str = "*.png,*.jpg,*.jpeg,*.webp",
        start_index: int = 0,
        # Hidden inputs (populated automatically by ComfyUI at runtime)
        prompt: dict = None,
        extra_pnginfo: dict = None,
        unique_id: str = None,
        queue_nonce: int = 0,
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
            prompt: Complete workflow dict (hidden input for re-queueing)
            extra_pnginfo: PNG metadata (hidden input for future use)
            unique_id: This node's ID (hidden input for future use)

        Returns:
            Tuple of (image_tensor, total_count, index, filename, basename, input_directory_name, original_format, status, batch_complete)
        """
        import time
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[BatchImageLoader] ===== load_image called at {timestamp} =====")
        print(f"[BatchImageLoader] load_image: directory={directory}")
        print(f"[BatchImageLoader] load_image: iteration_mode={iteration_mode}, unique_id={unique_id}")
        print(f"[BatchImageLoader] load_image: prompt={'PRESENT (keys: ' + str(list(prompt.keys())[:5]) + '...)' if prompt else 'None'}")

        # Normalize directory path for consistent state lookup
        directory = os.path.normpath(directory)

        # Get pattern and filter files
        pattern = get_pattern_for_preset(filter_preset, custom_pattern)
        files = filter_files_by_patterns(directory, pattern)

        # Sort files using natural sort
        files = sorted(files, key=natural_sort_key)

        total_count = len(files)
        print(f"[BatchImageLoader] load_image: found {total_count} files matching pattern")

        # === STATE MANAGEMENT ===

        # Get or initialize state for this directory
        state = IterationState.get_state(directory)
        print(f"[BatchImageLoader] load_image: initial state = index={state.get('index', 0)}, status={state.get('status', 'unknown')}")

        # Check for directory change - if last_directory differs from current, reset
        # This detects when user switches to a different folder
        last_dir = IterationState.get_last_directory()
        if last_dir is not None:
            if IterationState.check_directory_change(directory, last_dir):
                # Switching to a different directory, reset its state
                print(f"[BatchImageLoader] load_image: directory changed from {last_dir} to {directory}, resetting state")
                IterationState.reset(directory)
                state = IterationState.get_state(directory)

        # Track current directory for next execution's change detection
        IterationState.set_last_directory(directory)

        # Handle iteration_mode
        if iteration_mode == "Reset":
            print(f"[BatchImageLoader] load_image: iteration_mode=Reset, resetting state")
            IterationState.reset(directory)
            state = IterationState.get_state(directory)

        # Handle start_index: If start_index > 0 and state.index == 0, use start_index
        if start_index > 0 and state["index"] == 0:
            print(f"[BatchImageLoader] load_image: applying start_index={start_index}")
            state["index"] = start_index

        # Set total count for this batch
        IterationState.set_total_count(directory, total_count)

        # Set status to processing at start
        IterationState.set_status(directory, "processing")

        # === PROCESSING FLOW ===

        # Get current index from state (0-based)
        current_index = state["index"]
        print(f"[BatchImageLoader] load_image: current_index={current_index} (before wraparound check)")

        # Handle wraparound (in case index > total_count from previous run with more files)
        if current_index >= total_count:
            print(f"[BatchImageLoader] load_image: index {current_index} >= total {total_count}, wrapping to 0")
            current_index = 0
            state["index"] = 0

        print(f"[BatchImageLoader] load_image: will process index={current_index}, file={files[current_index] if files else 'N/A'}")

        # Load image with error handling
        return self._load_with_error_handling(
            directory=directory,
            files=files,
            current_index=current_index,
            total_count=total_count,
            error_handling=error_handling,
            skip_count=0,
            prompt=prompt,
            unique_id=unique_id,
        )

    def _load_with_error_handling(
        self,
        directory: str,
        files: list,
        current_index: int,
        total_count: int,
        error_handling: str,
        skip_count: int,
        prompt: dict = None,
        unique_id: str = None,
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
            prompt: Complete workflow dict for re-queueing
            unique_id: Node ID for injecting queue_nonce

        Returns:
            Tuple of (image_tensor, total_count, index, filename, basename, input_directory_name, original_format, status, batch_complete)
        """
        import time
        print(f"\n[BatchImageLoader] ----- _load_with_error_handling -----")
        print(f"[BatchImageLoader] Processing: index={current_index}/{total_count}, skip_count={skip_count}")

        # Infinite loop protection
        if skip_count >= total_count:
            raise RuntimeError("Failed to load any images from directory - all files skipped or failed")

        filename = files[current_index]
        filepath = os.path.join(directory, filename)
        print(f"[BatchImageLoader] Loading: {filename}")

        try:
            image_tensor = load_image_as_tensor(filepath)
            print(f"[BatchImageLoader] Loaded successfully: shape={image_tensor.shape}")
        except Exception as e:
            print(f"[BatchImageLoader] ERROR loading {filename}: {e}")
            if error_handling == "Stop on error":
                raise RuntimeError(f"Failed to load image {filename}: {e}") from e
            else:
                # Skip on error: advance index and try next image
                print(f"[BatchImageLoader] Skipping failed image, advancing to next")
                IterationState.advance(directory)
                next_index = (current_index + 1) % total_count
                return self._load_with_error_handling(
                    directory=directory,
                    files=files,
                    current_index=next_index,
                    total_count=total_count,
                    error_handling=error_handling,
                    skip_count=skip_count + 1,
                    prompt=prompt,
                    unique_id=unique_id,
                )

        # Success - extract basename (filename without extension) and format
        basename, ext = os.path.splitext(filename)
        # Get original format without the dot (e.g., "png", "jpg")
        original_format = ext[1:].lower() if ext else "png"

        # Extract just the folder name from directory path
        input_directory_name = os.path.basename(directory.rstrip(os.sep))
        print(f"[BatchImageLoader] basename={basename}, format={original_format}, dir_name={input_directory_name}")

        # Determine if this is the last image
        batch_complete = current_index >= total_count - 1

        # Queue control based on batch_complete
        print(f"\n[BatchImageLoader] ===== QUEUE CONTROL =====")
        print(f"[BatchImageLoader] index={current_index}, total={total_count}, batch_complete={batch_complete}")

        if batch_complete:
            # Stop Auto Queue and reset for re-run
            print(f"[BatchImageLoader] BATCH COMPLETE - stopping auto queue")
            stop_auto_queue()
            IterationState.wrap_index(directory)
            status = "completed"
            IterationState.set_status(directory, "completed")
            print(f"[BatchImageLoader] Wrapped index to 0 for next batch run")
        else:
            status = "processing"
            # Advance index BEFORE triggering next queue to avoid race condition
            old_index = IterationState.get_state(directory).get('index', 0)
            IterationState.advance(directory)
            new_index = IterationState.get_state(directory).get('index', 0)
            print(f"[BatchImageLoader] Advanced index: {old_index} -> {new_index}")

            # Now trigger next queue with updated state
            print(f"[BatchImageLoader] Triggering next queue...")
            print(f"[BatchImageLoader] prompt is {'PRESENT' if prompt else 'None'}, unique_id={unique_id}")
            queue_result = trigger_next_queue(prompt, unique_id=unique_id)
            print(f"[BatchImageLoader] trigger_next_queue returned: {queue_result}")

        print(f"[BatchImageLoader] ===== RETURNING =====")
        print(f"[BatchImageLoader] status={status}, batch_complete={batch_complete}")
        print(f"[BatchImageLoader] Outputs: IMAGE={image_tensor.shape}, INPUT_DIRECTORY={input_directory_name}, INPUT_BASE_NAME={basename}, INPUT_FILE_TYPE={original_format}, FILENAME={filename}, INDEX={current_index}, TOTAL_COUNT={total_count}, STATUS={status}, BATCH_COMPLETE={batch_complete}")

        # Return order matches RETURN_NAMES for clean wiring to BatchImageSaver
        return (image_tensor, input_directory_name, basename, original_format, filename, current_index, total_count, status, batch_complete)
