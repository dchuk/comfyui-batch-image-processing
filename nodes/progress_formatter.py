"""BatchProgressFormatter node for ComfyUI batch image processing."""

# Graceful import for PromptServer (ComfyUI module for live UI updates)
try:
    from server import PromptServer
    HAS_SERVER = True
except ImportError:
    PromptServer = None
    HAS_SERVER = False


class BatchProgressFormatter:
    """
    Format batch progress as human-readable string.

    Takes INDEX (0-based) and TOTAL_COUNT from BatchImageLoader
    and outputs a formatted string like "3 of 10 (30%)".
    """

    CATEGORY = "batch_processing"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("PROGRESS_TEXT",)
    FUNCTION = "format_progress"
    OUTPUT_NODE = True  # Required for UI updates to display

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "index": (
                    "INT",
                    {
                        "default": 0,
                        "min": 0,
                        "forceInput": True,
                        "tooltip": "Wire from BatchImageLoader INDEX output",
                    },
                ),
                "total_count": (
                    "INT",
                    {
                        "default": 1,
                        "min": 0,
                        "forceInput": True,
                        "tooltip": "Wire from BatchImageLoader TOTAL_COUNT output",
                    },
                ),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    def format_progress(self, index: int, total_count: int, unique_id=None) -> dict:
        """
        Format progress as human-readable string.

        Args:
            index: 0-based index from BatchImageLoader
            total_count: Total number of images in batch
            unique_id: Node ID for UI broadcasts (hidden input)

        Returns:
            Dict with "ui" and "result" keys for OUTPUT_NODE pattern
        """
        # Convert 0-based index to 1-based for human display
        current = index + 1

        # Protect against divide-by-zero
        safe_total = max(1, total_count)

        # Calculate percentage (integer, no decimals - uses int() which truncates)
        percentage = int((current / safe_total) * 100)

        # Format: "3 of 10 (30%)"
        progress_text = f"{current} of {safe_total} ({percentage}%)"

        # Broadcast progress update to ALL connected clients
        if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None and unique_id is not None:
            PromptServer.instance.send_sync(
                "executed",
                {
                    "node": unique_id,
                    "output": {"text": [progress_text]},
                },
                sid=None  # Broadcast to ALL clients
            )

        return {"ui": {"text": [progress_text]}, "result": (progress_text,)}
