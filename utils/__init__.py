"""Utility modules for batch image processing."""

# Always export modules without external dependencies
from .sorting import natural_sort_key
from .file_utils import filter_files_by_patterns, get_pattern_for_preset
from .iteration_state import IterationState
from .queue_control import (
    HAS_SERVER,
    should_continue,
    stop_auto_queue,
    trigger_next_queue,
)

# Conditionally export image utilities (requires numpy, torch, PIL)
try:
    from .image_utils import load_image_as_tensor
    from .save_image_utils import (
        construct_filename,
        handle_existing_file,
        resolve_output_directory,
        save_with_format,
        tensor_to_pil,
    )

    __all__ = [
        "natural_sort_key",
        "filter_files_by_patterns",
        "get_pattern_for_preset",
        "IterationState",
        "trigger_next_queue",
        "stop_auto_queue",
        "should_continue",
        "HAS_SERVER",
        "load_image_as_tensor",
        "tensor_to_pil",
        "save_with_format",
        "construct_filename",
        "handle_existing_file",
        "resolve_output_directory",
    ]
except ImportError:
    # Allow import to succeed even without ComfyUI dependencies
    # This enables running tests for modules that don't need these dependencies
    __all__ = [
        "natural_sort_key",
        "filter_files_by_patterns",
        "get_pattern_for_preset",
        "IterationState",
        "trigger_next_queue",
        "stop_auto_queue",
        "should_continue",
        "HAS_SERVER",
    ]
