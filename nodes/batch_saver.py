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
            # Optional inputs ordered to align with BatchImageLoader outputs (minimizes wire crossing)
            "optional": {
                "output_directory": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Wire from INPUT_DIRECTORY. Empty = ComfyUI output folder.",
                    },
                ),
                "output_base_name": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Wire from INPUT_BASE_NAME. Base filename without extension.",
                    },
                ),
                "output_file_type": (
                    "STRING",
                    {
                        "default": "png",
                        "tooltip": "Wire from INPUT_FILE_TYPE or type format (png/jpg/jpeg/webp).",
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
            },
        }

    def save_image(
        self,
        image,
        quality,
        overwrite_mode,
        output_directory="",
        output_base_name="",
        output_file_type="png",
        filename_prefix="",
        filename_suffix="",
    ):
        """
        Save the processed image with configured options.

        Args:
            image: Image tensor from processing pipeline [B, H, W, C]
            quality: Quality for lossy formats (1-100)
            overwrite_mode: "Overwrite", "Skip", or "Rename"
            output_directory: Custom output directory (empty = default)
            output_base_name: Base filename for output (without extension)
            output_file_type: Output file extension (png, jpg, jpeg, webp)
            filename_prefix: Prefix for filename (include separators)
            filename_suffix: Suffix for filename (include separators)

        Returns:
            Dict with UI images for ComfyUI preview
        """
        import time
        timestamp = time.strftime("%H:%M:%S")
        print(f"\n[BatchImageSaver] ===== save_image called at {timestamp} =====")
        print(f"[BatchImageSaver] Inputs:")
        print(f"[BatchImageSaver]   image shape: {image.shape if hasattr(image, 'shape') else 'unknown'}")
        print(f"[BatchImageSaver]   quality: {quality}")
        print(f"[BatchImageSaver]   overwrite_mode: '{overwrite_mode}'")
        print(f"[BatchImageSaver]   output_directory: '{output_directory}'")
        print(f"[BatchImageSaver]   output_base_name: '{output_base_name}'")
        print(f"[BatchImageSaver]   output_file_type: '{output_file_type}'")
        print(f"[BatchImageSaver]   filename_prefix: '{filename_prefix}'")
        print(f"[BatchImageSaver]   filename_suffix: '{filename_suffix}'")

        # 1. Determine output format
        extension = output_file_type.lower().strip() if output_file_type else "png"
        print(f"[BatchImageSaver] Using extension: '{extension}'")

        # 2. Determine base filename
        if output_base_name and output_base_name.strip():
            basename = output_base_name.strip()
        else:
            # Generate fallback filename with random suffix
            basename = f"output_{random.randint(1000, 9999)}"
            print(f"[BatchImageSaver] WARNING: No output_base_name provided, using fallback: '{basename}'")
        print(f"[BatchImageSaver] basename: '{basename}'")

        # 3. Construct output path
        def get_default_output():
            if folder_paths:
                default_dir = folder_paths.get_output_directory()
                print(f"[BatchImageSaver] folder_paths.get_output_directory() = '{default_dir}'")
                return default_dir
            print(f"[BatchImageSaver] WARNING: folder_paths not available")
            return ""

        output_dir = resolve_output_directory(
            output_directory, "", get_default_output
        )
        print(f"[BatchImageSaver] Resolved output_dir: '{output_dir}'")

        filename = construct_filename(basename, filename_prefix, filename_suffix, extension)
        filepath = os.path.join(output_dir, filename)
        print(f"[BatchImageSaver] Full filepath: '{filepath}'")

        # 4. Handle existing file
        final_path, should_save = handle_existing_file(filepath, overwrite_mode)
        print(f"[BatchImageSaver] handle_existing_file: final_path='{final_path}', should_save={should_save}")

        if not should_save:
            # Skip mode - file exists and user chose to skip
            print(f"[BatchImageSaver] SKIPPING save (file exists, skip mode)")
            return {"ui": {"images": []}}

        # 5. Convert and save
        print(f"[BatchImageSaver] Converting tensor to PIL image...")
        pil_img = tensor_to_pil(image)
        print(f"[BatchImageSaver] PIL image size: {pil_img.size}, mode: {pil_img.mode}")

        print(f"[BatchImageSaver] Saving with format '{extension.upper()}', quality={quality}...")
        save_with_format(pil_img, final_path, extension.upper(), quality)
        print(f"[BatchImageSaver] SAVED: {final_path}")

        # Verify file was created
        if os.path.exists(final_path):
            file_size = os.path.getsize(final_path)
            print(f"[BatchImageSaver] File verified: {file_size} bytes")
        else:
            print(f"[BatchImageSaver] ERROR: File was NOT created!")

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

        result = {
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
        print(f"[BatchImageSaver] Returning UI result: {result}")
        print(f"[BatchImageSaver] ===== save_image complete =====\n")

        return result
