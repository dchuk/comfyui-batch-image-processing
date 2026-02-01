"""BatchImageSaver node for ComfyUI batch image processing."""

import os
import random

from ..utils.save_image_utils import (
    construct_filename,
    handle_existing_file,
    resolve_output_directory,
    save_with_format,
    tensor_to_pil,
)

# Graceful import for folder_paths (ComfyUI module)
try:
    import folder_paths
except ImportError:
    folder_paths = None  # For testing outside ComfyUI


class BatchImageSaver:
    """
    Save processed images with customizable output paths and filenames.

    This node saves images from the processing pipeline with user-configured
    naming patterns, format options, and overwrite behavior. Designed to work
    with BatchImageLoader for batch processing workflows.
    """

    CATEGORY = "batch_processing"
    RETURN_TYPES = ()
    FUNCTION = "save_image"
    OUTPUT_NODE = True

    def __init__(self):
        """Initialize the saver with default output directory."""
        self.output_dir = folder_paths.get_output_directory() if folder_paths else ""

    @classmethod
    def INPUT_TYPES(cls):
        """Define input parameters for the node."""
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image tensor from processing pipeline"}),
                "output_format": (
                    ["Match original", "PNG", "JPG", "WebP"],
                    {"default": "Match original"},
                ),
                "quality": (
                    "INT",
                    {
                        "default": 100,
                        "min": 1,
                        "max": 100,
                        "step": 1,
                        "tooltip": "Quality for JPG/WebP (1-100). PNG ignores this.",
                    },
                ),
                "overwrite_mode": (
                    ["Overwrite", "Skip", "Rename"],
                    {"default": "Overwrite"},
                ),
            },
            "optional": {
                "output_directory": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Output directory (empty = ComfyUI output + source folder name)",
                    },
                ),
                "filename_prefix": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Prefix for output filename (include separators)",
                    },
                ),
                "filename_suffix": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Suffix for output filename (include separators)",
                    },
                ),
                "original_filename": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Original filename from BatchImageLoader (BASENAME output)",
                    },
                ),
                "source_directory": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Source directory for default subfolder naming",
                    },
                ),
                "original_format": (
                    "STRING",
                    {
                        "default": "png",
                        "tooltip": "Original format (for Match original mode)",
                    },
                ),
            },
        }

    def save_image(
        self,
        image,
        output_format,
        quality,
        overwrite_mode,
        output_directory="",
        filename_prefix="",
        filename_suffix="",
        original_filename="",
        source_directory="",
        original_format="png",
    ):
        """
        Save the processed image with configured options.

        Args:
            image: Image tensor from processing pipeline [B, H, W, C]
            output_format: "Match original", "PNG", "JPG", or "WebP"
            quality: Quality for lossy formats (1-100)
            overwrite_mode: "Overwrite", "Skip", or "Rename"
            output_directory: Custom output directory (empty = default)
            filename_prefix: Prefix for filename (include separators)
            filename_suffix: Suffix for filename (include separators)
            original_filename: Base filename from loader (without extension)
            source_directory: Source directory for subfolder naming
            original_format: Original file format for "Match original" mode

        Returns:
            Dict with UI images for ComfyUI preview
        """
        # 1. Determine output format
        if output_format == "Match original":
            extension = original_format.lower() if original_format else "png"
            # Normalize jpeg to jpg
            if extension == "jpeg":
                extension = "jpg"
        else:
            # Map display names to extensions
            format_map = {"PNG": "png", "JPG": "jpg", "WebP": "webp"}
            extension = format_map.get(output_format, "png")

        # 2. Determine base filename
        if original_filename and original_filename.strip():
            basename = original_filename.strip()
        else:
            # Generate fallback filename with random suffix
            basename = f"output_{random.randint(1000, 9999)}"

        # 3. Construct output path
        def get_default_output():
            if folder_paths:
                return folder_paths.get_output_directory()
            return ""

        output_dir = resolve_output_directory(
            output_directory, source_directory, get_default_output
        )

        filename = construct_filename(basename, filename_prefix, filename_suffix, extension)
        filepath = os.path.join(output_dir, filename)

        # 4. Handle existing file
        final_path, should_save = handle_existing_file(filepath, overwrite_mode)

        if not should_save:
            # Skip mode - file exists and user chose to skip
            return {"ui": {"images": []}}

        # 5. Convert and save
        pil_img = tensor_to_pil(image)
        save_with_format(pil_img, final_path, extension.upper(), quality)

        # 6. Return UI dict
        # Calculate subfolder relative to ComfyUI output directory
        if folder_paths:
            try:
                comfy_output = folder_paths.get_output_directory()
                subfolder = os.path.relpath(os.path.dirname(final_path), comfy_output)
                if subfolder == ".":
                    subfolder = ""
            except ValueError:
                # Happens on Windows if paths are on different drives
                subfolder = ""
        else:
            subfolder = ""

        return {
            "ui": {
                "images": [
                    {
                        "filename": os.path.basename(final_path),
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ]
            }
        }
