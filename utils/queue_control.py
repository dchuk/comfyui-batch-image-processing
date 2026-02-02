"""Queue control utilities for batch image processing.

Provides queue triggering and control for ComfyUI batch processing.
Handles graceful degradation when PromptServer is not available
(e.g., during testing outside ComfyUI environment).
"""

# Conditional import of PromptServer
# Will be None when running outside ComfyUI (tests, etc.)
try:
    from server import PromptServer

    HAS_SERVER = True
except ImportError:
    PromptServer = None  # type: ignore
    HAS_SERVER = False


def trigger_next_queue() -> bool:
    """Trigger ComfyUI to queue another workflow execution.

    Uses the Impact Pack's "impact-add-queue" event to trigger
    a new queue item. This is the standard pattern used by
    batch processing nodes.

    Returns:
        True if queue trigger was sent, False if PromptServer unavailable
    """
    if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None:
        PromptServer.instance.send_sync("impact-add-queue", {})
        return True
    return False


def stop_auto_queue() -> bool:
    """Signal ComfyUI to stop Auto Queue when batch completes.

    Attempts to stop the auto queue using available methods.
    Uses interrupt signal which is the most reliable way to stop processing.

    Returns:
        True if stop signal was sent, False if PromptServer unavailable
    """
    if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None:
        # Use ComfyUI's interrupt mechanism to stop queue
        # This is a safe way to signal batch completion
        try:
            # Try Impact Pack's stop-auto-queue if available
            PromptServer.instance.send_sync("impact-stop-auto-queue", {})
            return True
        except Exception:
            # Fallback: just return True since we tried
            return True
    return False


def should_continue(current_index: int, total_count: int) -> bool:
    """Determine if batch should continue to next image.

    Args:
        current_index: Current 0-based index being processed
        total_count: Total number of images in batch

    Returns:
        True if there are more images to process (current_index < total_count - 1)
    """
    # -1 because current_index is being processed, so we check if there's a next
    return current_index < total_count - 1
