"""Queue control utilities for batch image processing.

Provides queue triggering and control for ComfyUI batch processing.
Uses native HTTP POST to /prompt endpoint - no external custom node dependencies.
Handles graceful degradation when PromptServer is not available
(e.g., during testing outside ComfyUI environment).
"""

import json
import uuid
import urllib.request
import urllib.error

# Conditional import of PromptServer
# Will be None when running outside ComfyUI (tests, etc.)
try:
    from server import PromptServer

    HAS_SERVER = True
except ImportError:
    PromptServer = None  # type: ignore
    HAS_SERVER = False


def get_server_address() -> tuple:
    """Get the ComfyUI server address and port.

    Returns:
        Tuple of (address, port). Defaults to ('127.0.0.1', 8188).
    """
    if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None:
        address = getattr(PromptServer.instance, "address", "127.0.0.1")
        port = getattr(PromptServer.instance, "port", 8188)
        # Handle 0.0.0.0 (listen on all interfaces) - use localhost for HTTP calls
        if address == "0.0.0.0":
            address = "127.0.0.1"
        return (address, port)
    return ("127.0.0.1", 8188)


def trigger_next_queue(prompt: dict = None) -> bool:
    """Trigger ComfyUI to queue another workflow execution.

    Uses native HTTP POST to /prompt endpoint. Does not require
    Impact Pack or any external custom nodes.

    Args:
        prompt: The complete workflow prompt dict (from hidden PROMPT input).
                If None or empty, returns False.

    Returns:
        True if queue trigger was sent, False if failed or unavailable
    """
    # Early return if no prompt to queue
    if not prompt:
        return False

    # Early return if running outside ComfyUI (tests, etc.)
    if not HAS_SERVER:
        return False

    # Early return if server not initialized
    if PromptServer is None or PromptServer.instance is None:
        return False

    address, port = get_server_address()

    payload = {
        "prompt": prompt,
        "client_id": str(uuid.uuid4()),
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://{address}:{port}/prompt",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except urllib.error.URLError:
        return False
    except urllib.error.HTTPError:
        return False
    except Exception:
        return False


def stop_auto_queue() -> bool:
    """Signal ComfyUI to stop Auto Queue when batch completes.

    With native queue control, stopping is implicit - we simply
    don't trigger the next queue. This function exists for API
    compatibility and always returns True.

    Note: This does NOT rely on ComfyUI's "Auto Queue" checkbox.
    Our batch iteration controls itself:
    - When batch continues: We POST to /prompt to queue next execution
    - When batch completes: We simply don't POST (no "stop" event needed)

    Returns:
        True (stopping = not queueing next, which always succeeds)
    """
    # Native approach: batch complete = don't queue next
    # No external event needed - the absence of a queue trigger IS the stop
    return True


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
