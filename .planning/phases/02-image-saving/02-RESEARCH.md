# Phase 2: Image Saving - Research

**Researched:** 2026-02-01
**Domain:** ComfyUI Custom Node Development - Image Saving
**Confidence:** HIGH

## Summary

This phase implements a BatchImageSaver node that saves processed images with customizable output paths, filenames, formats, and overwrite behavior. Research confirms ComfyUI uses OUTPUT_NODE = True for save nodes, returns a `{"ui": {"images": [...]}}` dict for UI integration, and relies on `folder_paths.get_output_directory()` to detect the ComfyUI output folder.

Key findings for Phase 2 decisions:
- **Image tensor to PIL conversion**: Use `Image.fromarray(np.clip(255. * tensor.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))` pattern from ComfyUI's SaveImage
- **Format saving**: PIL supports PNG (compress_level), JPEG (quality 0-95), and WebP (quality 0-100 for lossy) with simple `Image.save()` calls
- **Directory detection**: Import `folder_paths` from ComfyUI and use `folder_paths.get_output_directory()` for default output location
- **OUTPUT_NODE pattern**: Set `OUTPUT_NODE = True`, `RETURN_TYPES = ()`, return `{"ui": {"images": [...]}}` for proper ComfyUI integration

**Primary recommendation:** Follow ComfyUI's SaveImage patterns for tensor conversion and UI returns, using PIL's native format support for PNG/JPG/WebP quality control.

## Standard Stack

The established libraries/tools for this domain:

### Core (ComfyUI-Provided)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| torch | 2.4+ | Image tensors | All ComfyUI images are torch.Tensor |
| Pillow (PIL) | Latest | Image saving with format support | Native PNG/JPEG/WebP support with quality control |
| numpy | >=1.25.0 | Tensor to array conversion | Bridge between torch and PIL |
| folder_paths | ComfyUI module | Output directory detection | Standard ComfyUI path management |

### Supporting (Built-in Python)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| os / pathlib | File system operations | Directory creation, path joining |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PIL Image.save() | cv2.imwrite() | PIL is already loaded in ComfyUI, simpler API for formats |
| folder_paths | Hardcoded paths | folder_paths handles CLI --output-directory flag properly |

**Installation:** No additional dependencies needed - all required packages are provided by ComfyUI.

## Architecture Patterns

### Recommended Project Structure
```
comfyui_batch_image_processing/
├── __init__.py              # NODE_CLASS_MAPPINGS (add BatchImageSaver)
├── nodes/
│   ├── __init__.py          # Export BatchImageSaver
│   ├── batch_loader.py      # Existing - Phase 1
│   └── batch_saver.py       # NEW - BatchImageSaver class
├── utils/
│   ├── __init__.py          # Export save utilities
│   ├── image_utils.py       # Existing - add save_tensor_as_image()
│   └── file_utils.py        # Existing - add overwrite handling utilities
└── tests/
    ├── conftest.py          # Add output dir fixtures
    └── test_batch_saver.py  # NEW - saver tests
```

### Pattern 1: ComfyUI Output Node Structure
**What:** Standard output node class with OUTPUT_NODE = True and UI return dict
**When to use:** Any node that saves files or produces final outputs
**Example:**
```python
# Source: https://github.com/comfyanonymous/ComfyUI/discussions/2734
import folder_paths

class BatchImageSaver:
    """Save processed images with customizable naming and format."""

    CATEGORY = "batch_processing"

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "output_format": (["Match original", "PNG", "JPG", "WebP"],),
                "quality": ("INT", {"default": 100, "min": 1, "max": 100, "step": 1}),
                "overwrite_mode": (["Overwrite", "Skip", "Rename"],),
            },
            "optional": {
                "output_directory": ("STRING", {"default": ""}),
                "filename_prefix": ("STRING", {"default": ""}),
                "filename_suffix": ("STRING", {"default": ""}),
                "original_filename": ("STRING", {"default": ""}),  # From BatchImageLoader
                "source_directory": ("STRING", {"default": ""}),   # For default subfolder naming
            },
        }

    RETURN_TYPES = ()  # Output nodes return empty tuple
    FUNCTION = "save_image"
    OUTPUT_NODE = True  # Marks as output node - always executes

    def save_image(self, image, output_format, quality, overwrite_mode, **kwargs):
        # Implementation
        # ...
        return {"ui": {"images": results}}
```

### Pattern 2: Image Tensor to File
**What:** Convert ComfyUI tensor [B,H,W,C] to PIL and save with format/quality
**When to use:** Any image saving operation
**Example:**
```python
# Source: https://github.com/comfyanonymous/ComfyUI/blob/master/nodes.py
import numpy as np
from PIL import Image

def save_tensor_as_image(tensor, filepath: str, format: str, quality: int = 100):
    """
    Save image tensor to file with format-specific options.

    Args:
        tensor: torch.Tensor with shape [1, H, W, C] or [H, W, C], float32 in [0, 1]
        filepath: Output path (extension may be replaced based on format)
        format: "PNG", "JPG", "WebP", or "Match original"
        quality: 1-100 for JPG/WebP (ignored for PNG)
    """
    # Handle batch dimension
    if len(tensor.shape) == 4:
        tensor = tensor.squeeze(0)  # [H, W, C]

    # Convert to PIL
    array = (255.0 * tensor.cpu().numpy()).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(array)

    # Save with format-specific options
    if format == "PNG":
        img.save(filepath, "PNG", compress_level=4)
    elif format == "JPG":
        # Convert RGBA to RGB if needed
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(filepath, "JPEG", quality=min(95, quality))  # PIL caps at 95
    elif format == "WebP":
        img.save(filepath, "WEBP", quality=quality, lossless=(quality == 100))
```

### Pattern 3: Filename Construction
**What:** Build output filename from original + prefix/suffix (user decision: raw concatenation)
**When to use:** Constructing output filenames
**Example:**
```python
# Pattern: {prefix}{original}{suffix}.{ext}
# User provides separators in prefix/suffix fields

def construct_filename(original_basename: str, prefix: str, suffix: str, extension: str) -> str:
    """
    Construct output filename with prefix/suffix.

    Args:
        original_basename: Original filename without extension (e.g., "photo")
        prefix: Prefix string including any separators (e.g., "upscaled_")
        suffix: Suffix string including any separators (e.g., "_2x")
        extension: Output extension without dot (e.g., "png")

    Returns:
        Complete filename (e.g., "upscaled_photo_2x.png")
    """
    return f"{prefix}{original_basename}{suffix}.{extension}"
```

### Pattern 4: Overwrite Handling
**What:** Handle existing files per user-selected mode
**When to use:** Before saving any file
**Example:**
```python
import os

def handle_existing_file(filepath: str, mode: str) -> tuple[str, bool]:
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
        while True:
            new_path = f"{base}_{counter}{ext}"
            if not os.path.exists(new_path):
                return (new_path, True)
            counter += 1

    return (filepath, True)  # Default: overwrite
```

### Pattern 5: Output Directory Resolution
**What:** Determine output directory per user decision
**When to use:** Resolving where to save images
**Example:**
```python
import os
import folder_paths

def resolve_output_directory(output_dir: str, source_dir: str) -> str:
    """
    Resolve output directory per user decision.

    Args:
        output_dir: User-specified output directory (empty = use default)
        source_dir: Source directory path (for subfolder naming)

    Returns:
        Resolved output directory path (created if needed)
    """
    if output_dir and output_dir.strip():
        # User specified directory: use directly
        resolved = output_dir.strip()
    else:
        # No output specified: ComfyUI output + source folder name
        comfy_output = folder_paths.get_output_directory()
        source_folder_name = os.path.basename(source_dir.rstrip(os.sep))
        resolved = os.path.join(comfy_output, source_folder_name)

    # Create directory if it doesn't exist (no warning per user decision)
    os.makedirs(resolved, exist_ok=True)

    return resolved
```

### Pattern 6: UI Return Format
**What:** Return dict for ComfyUI UI integration
**When to use:** OUTPUT_NODE save operations
**Example:**
```python
# Source: https://github.com/comfyanonymous/ComfyUI/discussions/2734

def save_image(self, image, ...):
    # ... save logic ...

    results = []
    for saved_file in saved_files:
        # Get subfolder relative to output directory
        subfolder = os.path.relpath(
            os.path.dirname(saved_file),
            folder_paths.get_output_directory()
        )
        results.append({
            "filename": os.path.basename(saved_file),
            "subfolder": subfolder if subfolder != "." else "",
            "type": "output"
        })

    return {"ui": {"images": results}}
```

### Anti-Patterns to Avoid
- **Hardcoding output paths:** Always use `folder_paths.get_output_directory()` to respect CLI flags
- **Ignoring batch dimension:** Tensor may be [1,H,W,C] or [H,W,C]; always handle both
- **JPEG quality > 95:** PIL documentation warns against values above 95
- **Returning tuple from OUTPUT_NODE:** Return dict with "ui" key, not tuple
- **Silent failures:** Always log skipped files to console per user decision

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image format detection | Manual extension parsing | PIL's `Image.open().format` | Handles format mismatches (e.g., .jpg that's actually PNG) |
| EXIF-aware saving | Manual metadata copying | PIL preserves EXIF automatically | Edge cases with rotation/orientation |
| WebP lossless mode | Manual compression tuning | PIL `lossless=True` parameter | Quality=100 should trigger lossless per user expectation |
| ComfyUI output path | Hardcode or env vars | `folder_paths.get_output_directory()` | Respects --output-directory CLI flag |

**Key insight:** PIL's `Image.save()` with format-specific parameters handles 95% of image saving needs. Don't build custom encoders.

## Common Pitfalls

### Pitfall 1: OUTPUT_NODE Return Format
**What goes wrong:** Node saves but UI doesn't update, or node errors with "cannot iterate"
**Why it happens:** OUTPUT_NODE expects dict with "ui" key, not tuple
**How to avoid:** Always return `{"ui": {"images": [...]}}`, never `(result,)`
**Warning signs:** UI shows no saved images, TypeError in console

### Pitfall 2: Tensor Shape Mismatch
**What goes wrong:** PIL raises "cannot determine image dimensions" or shape errors
**Why it happens:** Not handling batch dimension [1,H,W,C] vs [H,W,C]
**How to avoid:** Use `squeeze(0)` when batch dim exists; check `len(tensor.shape)`
**Warning signs:** ValueError about array dimensions

### Pitfall 3: JPEG Quality Range
**What goes wrong:** Unexpected file sizes or quality artifacts
**Why it happens:** PIL JPEG quality 0-95 recommended (100 disables optimizations)
**How to avoid:** Cap quality at 95 for JPEG: `quality=min(95, user_quality)`
**Warning signs:** JPEG files larger than PNG, quality artifacts despite high quality setting

### Pitfall 4: RGBA to JPEG
**What goes wrong:** "cannot write mode RGBA as JPEG" error
**Why it happens:** JPEG doesn't support alpha channel
**How to avoid:** Convert to RGB before JPEG save: `img.convert("RGB")`
**Warning signs:** Error when saving processed images with transparency

### Pitfall 5: Path Separators on Windows
**What goes wrong:** "File not found" or paths with mixed separators
**Why it happens:** Using hardcoded `/` instead of `os.sep` or `os.path.join()`
**How to avoid:** Always use `os.path.join()` and `pathlib.Path`
**Warning signs:** Works on Linux/Mac, fails on Windows

### Pitfall 6: Rename Counter Overflow
**What goes wrong:** Infinite loop or very slow execution
**Why it happens:** Counter checking millions of filenames when many exist
**How to avoid:** Set reasonable maximum (e.g., 10000) and error if exceeded
**Warning signs:** Node hangs during save operation

## Code Examples

Verified patterns from official sources:

### Complete BatchImageSaver Node
```python
# Source: Pattern derived from ComfyUI SaveImage + user decisions
import os
import numpy as np
from PIL import Image

try:
    import folder_paths
except ImportError:
    folder_paths = None  # For testing outside ComfyUI

class BatchImageSaver:
    """Save processed images with customizable output paths and filenames."""

    CATEGORY = "batch_processing"

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory() if folder_paths else ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "Image tensor from processing pipeline"}),
                "output_format": (
                    ["Match original", "PNG", "JPG", "WebP"],
                    {"default": "Match original"},
                ),
                "quality": (
                    "INT",
                    {"default": 100, "min": 1, "max": 100, "step": 1,
                     "tooltip": "Quality for JPG/WebP (1-100). PNG ignores this."},
                ),
                "overwrite_mode": (
                    ["Overwrite", "Skip", "Rename"],
                    {"default": "Overwrite"},
                ),
            },
            "optional": {
                "output_directory": (
                    "STRING",
                    {"default": "", "tooltip": "Output directory (empty = ComfyUI output + source folder name)"},
                ),
                "filename_prefix": (
                    "STRING",
                    {"default": "", "tooltip": "Prefix for output filename (include separators like 'upscaled_')"},
                ),
                "filename_suffix": (
                    "STRING",
                    {"default": "", "tooltip": "Suffix for output filename (include separators like '_2x')"},
                ),
                "original_filename": (
                    "STRING",
                    {"default": "", "tooltip": "Original filename from BatchImageLoader (BASENAME output)"},
                ),
                "source_directory": (
                    "STRING",
                    {"default": "", "tooltip": "Source directory from BatchImageLoader (for default subfolder naming)"},
                ),
                "original_format": (
                    "STRING",
                    {"default": "png", "tooltip": "Original file format (for 'Match original' mode)"},
                ),
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_image"
    OUTPUT_NODE = True

    def save_image(self, image, output_format, quality, overwrite_mode,
                   output_directory="", filename_prefix="", filename_suffix="",
                   original_filename="", source_directory="", original_format="png"):
        # Implementation here
        pass
```

### Tensor to PIL Conversion (Verified)
```python
# Source: ComfyUI nodes.py SaveImage implementation
def tensor_to_pil(tensor):
    """Convert ComfyUI image tensor to PIL Image."""
    # Handle batch dimension
    if len(tensor.shape) == 4:
        tensor = tensor.squeeze(0)  # [1,H,W,C] -> [H,W,C]

    # Convert: multiply by 255, clip to valid range, convert to uint8
    array = (255.0 * tensor.cpu().numpy()).clip(0, 255).astype(np.uint8)
    return Image.fromarray(array)
```

### Format-Specific Saving (Verified)
```python
# Source: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
def save_with_format(img: Image.Image, filepath: str, format: str, quality: int):
    """Save PIL image with format-specific options."""
    if format.upper() == "PNG":
        img.save(filepath, "PNG", compress_level=4)
    elif format.upper() in ("JPG", "JPEG"):
        # JPEG doesn't support alpha
        if img.mode == "RGBA":
            img = img.convert("RGB")
        # PIL recommends quality <= 95
        img.save(filepath, "JPEG", quality=min(95, quality))
    elif format.upper() == "WEBP":
        # quality=100 triggers lossless mode
        img.save(filepath, "WEBP", quality=quality, lossless=(quality == 100))
    else:
        # Default to PNG for unknown formats
        img.save(filepath, "PNG", compress_level=4)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom image encoders | PIL Image.save() | Always | PIL handles format quirks |
| Hardcoded output paths | folder_paths module | ComfyUI standard | Respects --output-directory |
| RETURN_TYPES tuple for save | {"ui": {...}} dict | ComfyUI pattern | Required for UI integration |

**Deprecated/outdated:**
- `quality=100` for JPEG: Values above 95 disable compression optimizations and increase file size without quality benefit
- Manual EXIF handling: PIL preserves metadata automatically when possible

## Open Questions

Things that couldn't be fully resolved:

1. **Original format detection for "Match original"**
   - What we know: PIL's `Image.open().format` returns format, but requires opening the original file
   - What's unclear: Should we pass original format from BatchImageLoader or re-detect it?
   - Recommendation: Add `original_format` output to BatchImageLoader (or detect from filename extension as fallback)

2. **UI preview integration**
   - What we know: ComfyUI SaveImage shows preview thumbnails via "ui" return
   - What's unclear: Whether the `subfolder` path calculation works for absolute paths outside ComfyUI output
   - Recommendation: For custom output directories, may need to return empty subfolder or handle separately

## Sources

### Primary (HIGH confidence)
- [Pillow Image File Formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html) - PNG/JPEG/WebP save parameters
- [ComfyUI SaveImage Discussion](https://github.com/comfyanonymous/ComfyUI/discussions/2734) - Custom save node patterns
- [ComfyUI folder_paths.py](https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py) - get_output_directory() API
- [ComfyUI Server Overview](https://docs.comfy.org/custom-nodes/backend/server_overview) - OUTPUT_NODE behavior

### Secondary (MEDIUM confidence)
- [Save Image Extended](https://github.com/thedyze/save-image-extended-comfyui) - Extended filename patterns
- [ComfyUI Wiki SaveImage](https://comfyui-wiki.com/en/comfyui-nodes/image/save-image) - Basic save node documentation

### Tertiary (LOW confidence)
- WebSearch results for ComfyUI custom node patterns (verified against official sources where possible)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PIL/NumPy/torch are ComfyUI-provided, verified in official docs
- Architecture: HIGH - OUTPUT_NODE pattern verified in ComfyUI source and documentation
- Pitfalls: HIGH - Verified against PIL docs and ComfyUI discussions
- Code examples: MEDIUM - Derived from verified patterns but not tested in this codebase

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - PIL and ComfyUI patterns are stable)
