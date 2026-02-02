"""BatchProgressFormatter node for ComfyUI batch image processing."""


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
    OUTPUT_NODE = False

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
        }

    def format_progress(self, index: int, total_count: int) -> tuple:
        """
        Format progress as human-readable string.

        Args:
            index: 0-based index from BatchImageLoader
            total_count: Total number of images in batch

        Returns:
            Tuple containing formatted progress string
        """
        # Convert 0-based index to 1-based for human display
        current = index + 1

        # Protect against divide-by-zero
        safe_total = max(1, total_count)

        # Calculate percentage (integer, no decimals - uses int() which truncates)
        percentage = int((current / safe_total) * 100)

        # Format: "3 of 10 (30%)"
        progress_text = f"{current} of {safe_total} ({percentage}%)"

        return (progress_text,)
