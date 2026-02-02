"""Image saving utilities for ComfyUI batch processing."""

import os

# Graceful imports for testing without ComfyUI dependencies
try:
    import numpy as np
except ImportError:
    np = None

try:
    import torch
except ImportError:
    torch = None

try:
    from PIL import Image
except ImportError:
    Image = None


def tensor_to_pil(tensor):
    """
    Convert ComfyUI image tensor to PIL Image.

    Args:
        tensor: torch.Tensor with shape [1, H, W, C] or [H, W, C],
                float32 values in [0.0, 1.0] range

    Returns:
        PIL.Image in RGB mode

    Raises:
        ImportError: If torch, numpy, or PIL are not available
    """
    if torch is None or np is None or Image is None:
        raise ImportError("tensor_to_pil requires torch, numpy, and PIL")

    # Handle batch dimension
    if len(tensor.shape) == 4:
        tensor = tensor.squeeze(0)  # [1, H, W, C] -> [H, W, C]

    # Convert: multiply by 255, clip to valid range, convert to uint8
    array = (255.0 * tensor.cpu().numpy()).clip(0, 255).astype(np.uint8)
    return Image.fromarray(array)


def save_with_format(img, filepath: str, format: str, quality: int = 100):
    """
    Save PIL image with format-specific options.

    Args:
        img: PIL.Image to save
        filepath: Output path (should already have correct extension)
        format: "PNG", "JPG", "JPEG", or "WebP"
        quality: Quality for JPG/WebP (1-100). PNG ignores this.
    """
    if Image is None:
        raise ImportError("save_with_format requires PIL")

    format_upper = format.upper()

    if format_upper == "PNG":
        img.save(filepath, "PNG", compress_level=4)
    elif format_upper in ("JPG", "JPEG"):
        # JPEG doesn't support alpha
        if img.mode == "RGBA":
            img = img.convert("RGB")
        # PIL recommends quality <= 95
        img.save(filepath, "JPEG", quality=min(95, quality))
    elif format_upper == "WEBP":
        # quality=100 triggers lossless mode
        img.save(filepath, "WEBP", quality=quality, lossless=(quality == 100))
    else:
        # Default to PNG for unknown formats
        img.save(filepath, "PNG", compress_level=4)


def construct_filename(
    original_basename: str, prefix: str, suffix: str, extension: str
) -> str:
    """
    Construct output filename with prefix/suffix.

    Uses raw concatenation per user decision: {prefix}{original}{suffix}.{ext}
    User provides separators in prefix/suffix fields (e.g., prefix "upscaled_").

    Args:
        original_basename: Original filename without extension (e.g., "photo")
        prefix: Prefix string including any separators (e.g., "upscaled_")
        suffix: Suffix string including any separators (e.g., "_2x")
        extension: Output extension without dot (e.g., "png")

    Returns:
        Complete filename (e.g., "upscaled_photo_2x.png")
    """
    return f"{prefix}{original_basename}{suffix}.{extension}"


def handle_existing_file(filepath: str, mode: str) -> tuple:
    """
    Handle existing file according to overwrite mode.

    Args:
        filepath: Proposed output path
        mode: "Overwrite", "Skip", or "Rename"

    Returns:
        (final_path, should_save): Path to use and whether to proceed
    """
    if not os.path.exists(filepath):
        return (filepath, True)

    if mode == "Overwrite":
        return (filepath, True)

    if mode == "Skip":
        print(f"Skipped: {os.path.basename(filepath)}")
        return (filepath, False)

    if mode == "Rename":
        # Simple increment: photo_1.png, photo_2.png (not zero-padded)
        base, ext = os.path.splitext(filepath)
        counter = 1
        max_attempts = 10000
        while counter <= max_attempts:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return (new_path, True)
            counter += 1
        # If we exceed max attempts, just use the last tried path
        raise RuntimeError(
            f"Could not find unique filename after {max_attempts} attempts"
        )

    # Default: overwrite
    return (filepath, True)


def resolve_output_directory(
    output_dir: str, source_dir: str, default_output_func=None
) -> str:
    """
    Resolve output directory per user decision.

    Args:
        output_dir: User-specified output directory (empty = use default)
                    If relative path (e.g., "images"), prepends ComfyUI output dir.
                    If absolute path (e.g., "/path/to/output"), uses directly.
        source_dir: Source directory path (for subfolder naming)
        default_output_func: Callable that returns ComfyUI output directory
                            (e.g., lambda: folder_paths.get_output_directory())

    Returns:
        Resolved output directory path (created if needed)
    """
    if output_dir and output_dir.strip():
        stripped = output_dir.strip()
        # Check if it's a relative path (not absolute)
        # This handles cases where output_dir is wired from loader's input_directory_name
        # e.g., "images" should become "output/images"
        if not os.path.isabs(stripped):
            # Relative path: prepend ComfyUI output directory
            if default_output_func is not None:
                comfy_output = default_output_func()
                if comfy_output:
                    resolved = os.path.join(comfy_output, stripped)
                else:
                    resolved = stripped
            else:
                resolved = stripped
        else:
            # Absolute path: use directly
            resolved = stripped
    else:
        # No output specified: ComfyUI output + source folder name
        if default_output_func is not None:
            comfy_output = default_output_func()
        else:
            comfy_output = ""

        if source_dir:
            source_folder_name = os.path.basename(source_dir.rstrip(os.sep))
        else:
            source_folder_name = ""

        if comfy_output and source_folder_name:
            resolved = os.path.join(comfy_output, source_folder_name)
        elif comfy_output:
            resolved = comfy_output
        else:
            resolved = source_folder_name if source_folder_name else "."

    # Create directory if it doesn't exist (no warning per user decision)
    os.makedirs(resolved, exist_ok=True)

    return resolved
