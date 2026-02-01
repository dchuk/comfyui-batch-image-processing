"""ComfyUI Batch Image Processing Nodes.

A set of custom nodes for batch processing images through ComfyUI pipelines.
"""

try:
    from .nodes.batch_loader import BatchImageLoader

    NODE_CLASS_MAPPINGS = {
        "BatchImageLoader": BatchImageLoader,
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "BatchImageLoader": "Batch Image Loader",
    }

    __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

except ImportError:
    # Allow import to succeed even without ComfyUI dependencies (torch, numpy, PIL)
    # This enables running tests for modules that don't need these dependencies
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
