"""Image loading utilities for ComfyUI tensor conversion."""

import numpy as np
import torch
from PIL import Image, ImageOps


def load_image_as_tensor(filepath: str) -> torch.Tensor:
    """
    Load image file as ComfyUI-compatible tensor.

    Handles EXIF rotation, 16-bit grayscale (mode 'I'), and converts
    to RGB format. Returns tensor in ComfyUI's expected format:
    [B, H, W, C] with float32 values in [0.0, 1.0] range.

    Args:
        filepath: Path to the image file

    Returns:
        torch.Tensor with shape [1, H, W, C] (batch dimension included)

    Raises:
        FileNotFoundError: If the image file doesn't exist
        PIL.UnidentifiedImageError: If the file is not a valid image
    """
    img = Image.open(filepath)
    img = ImageOps.exif_transpose(img)  # Handle EXIF rotation

    # Handle 16-bit grayscale images (mode 'I')
    if img.mode == "I":
        img = img.point(lambda i: i * (1 / 255))

    # Convert to RGB (handles RGBA, L, P, etc.)
    img = img.convert("RGB")

    # Convert to tensor: float32 in [0.0, 1.0], shape [1, H, W, C]
    array = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(array)[None,]  # Add batch dimension

    return tensor
