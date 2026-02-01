"""ComfyUI Batch Image Processing Nodes.

A set of custom nodes for batch processing images through ComfyUI pipelines.
"""

from .nodes.batch_loader import BatchImageLoader

NODE_CLASS_MAPPINGS = {
    "BatchImageLoader": BatchImageLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchImageLoader": "Batch Image Loader",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
