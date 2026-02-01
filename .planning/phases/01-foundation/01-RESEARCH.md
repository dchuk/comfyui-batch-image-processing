# Phase 1: Foundation - Research

**Researched:** 2026-02-01
**Domain:** ComfyUI Custom Node Development - Image Loading
**Confidence:** HIGH

## Summary

This phase establishes the BatchImageLoader node infrastructure for ComfyUI. The research confirms ComfyUI has well-documented patterns for custom node development with clear requirements: nodes are Python classes registered via `NODE_CLASS_MAPPINGS`, must define `INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, and `CATEGORY`, and images use `[B,H,W,C]` tensor format with float32 values in [0.0, 1.0] range.

Key findings for Phase 1 specific decisions:
- **Browse button**: Use ComfyUI-FileBrowserAPI or implement minimal JS widget; STRING input with folder path is the simple approach
- **Natural sorting**: Implement inline using regex key function (no natsort dependency needed); `re.split('(\d+)', s)` pattern is standard
- **Filter presets**: Use dropdown COMBO input with preset patterns, custom pattern as STRING input
- **Validation on queue**: Implement `VALIDATE_INPUTS` classmethod for path validation

**Primary recommendation:** Build a minimal, dependency-free node following ComfyUI's LoadImage patterns with natural sort implemented inline.

## Standard Stack

The established libraries/tools for this domain:

### Core (ComfyUI-Provided)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| torch | 2.4+ | Image tensors, tensor operations | Required by ComfyUI, all images are torch.Tensor |
| Pillow (PIL) | Latest | Image file I/O | Used by ComfyUI's LoadImage, handles EXIF/formats |
| numpy | >=1.25.0 | Array conversion | Bridge between PIL and torch |
| folder_paths | ComfyUI module | Standard directory access | Provides input/output directory paths |

### Supporting (Built-in Python)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| os / pathlib | File system operations | Path handling, directory listing |
| re | Regular expressions | Natural sort key generation |
| fnmatch | Pattern matching | Glob pattern filtering |
| glob | File pattern matching | Alternative to fnmatch for simple cases |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline natural sort | natsort library | Adds dependency; inline is ~10 lines, sufficient for filenames |
| fnmatch | glob module | glob creates file lists; fnmatch filters existing lists (more flexible) |
| ComfyUI-FileBrowserAPI | Text input only | FileBrowserAPI adds UX but requires JS; text input works, can add later |

**Installation:** No additional dependencies needed - all required packages are provided by ComfyUI.

## Architecture Patterns

### Recommended Project Structure
```
comfyui_batch_image_processing/
├── __init__.py              # NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
├── nodes/
│   ├── __init__.py
│   └── batch_loader.py      # BatchImageLoader class
├── utils/
│   ├── __init__.py
│   ├── sorting.py           # Natural sort implementation
│   └── image_utils.py       # Image loading utilities
└── tests/
    ├── conftest.py          # pytest fixtures, ComfyUI mocks
    └── test_batch_loader.py
```

### Pattern 1: ComfyUI Node Class Structure
**What:** Standard node class with required attributes and methods
**When to use:** Every custom node
**Example:**
```python
# Source: https://docs.comfy.org/custom-nodes/walkthrough
class BatchImageLoader:
    """Load images from a directory with filtering and natural sort."""

    CATEGORY = "batch_processing"  # Menu location

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": "", "tooltip": "Directory path"}),
                "filter_preset": (["All Images", "PNG Only", "JPG Only", "Custom"],),
            },
            "optional": {
                "custom_pattern": ("STRING", {"default": "*.png,*.jpg,*.jpeg,*.webp"}),
            },
            "hidden": {
                "current_index": ("INT", {"default": 0}),  # For iteration control
            }
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = ("IMAGE", "TOTAL_COUNT", "CURRENT_INDEX", "FILENAME", "BASENAME")
    FUNCTION = "load_image"
    OUTPUT_NODE = False

    def load_image(self, directory, filter_preset, custom_pattern="", current_index=0):
        # Implementation
        return (image_tensor, total_count, current_index + 1, filename, basename)

    @classmethod
    def IS_CHANGED(cls, directory, filter_preset, **kwargs):
        # Return value that changes when re-execution needed
        return f"{directory}:{filter_preset}:{current_index}"

    @classmethod
    def VALIDATE_INPUTS(cls, directory, **kwargs):
        if not os.path.isdir(directory):
            return f"Directory does not exist: {directory}"
        return True
```

### Pattern 2: Image Loading from PIL to Tensor
**What:** Convert PIL Image to ComfyUI's [B,H,W,C] tensor format
**When to use:** Any image loading from disk
**Example:**
```python
# Source: https://docs.comfy.org/custom-nodes/backend/datatypes
# Pattern from ComfyUI's LoadImage node
from PIL import Image, ImageOps
import numpy as np
import torch

def load_image_as_tensor(filepath: str) -> torch.Tensor:
    """Load image file as ComfyUI-compatible tensor [1,H,W,C]."""
    img = Image.open(filepath)
    img = ImageOps.exif_transpose(img)  # Handle EXIF rotation

    # Handle special modes
    if img.mode == 'I':
        img = img.point(lambda i: i * (1 / 255))
    img = img.convert("RGB")

    # Convert to tensor: float32 in [0.0, 1.0], shape [1, H, W, C]
    array = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(array)[None,]  # Add batch dimension
    return tensor
```

### Pattern 3: Natural Sort Key Function
**What:** Sort filenames so img2 comes before img10
**When to use:** Sorting any list of filenames with embedded numbers
**Example:**
```python
# Source: https://rosettacode.org/wiki/Natural_sorting (verified pattern)
import re

def natural_sort_key(s: str) -> list:
    """Generate key for natural sorting (case-insensitive)."""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', s)]

# Usage
files = ['img10.png', 'img2.png', 'img1.png']
sorted_files = sorted(files, key=natural_sort_key)
# Result: ['img1.png', 'img2.png', 'img10.png']
```

### Pattern 4: Multi-Pattern File Filtering
**What:** Filter files matching multiple extensions
**When to use:** When user specifies patterns like `*.png,*.jpg`
**Example:**
```python
# Source: https://docs.python.org/3/library/glob.html
import os
from fnmatch import fnmatch

def filter_files_by_patterns(directory: str, pattern_string: str) -> list[str]:
    """Filter files matching comma-separated patterns."""
    patterns = [p.strip() for p in pattern_string.split(',')]
    files = []

    for f in os.listdir(directory):
        filepath = os.path.join(directory, f)
        if os.path.isfile(filepath):
            if any(fnmatch(f.lower(), p.lower()) for p in patterns):
                files.append(f)

    return files
```

### Anti-Patterns to Avoid
- **Loading all images at once:** Causes memory exhaustion. Load one image per execution.
- **Returning bare tensor:** Must return `(tensor,)` tuple, not `tensor`
- **RETURN_TYPES as string:** Must be tuple with trailing comma: `("IMAGE",)` not `("IMAGE")`
- **Relying on execution order:** Order is non-deterministic; use data dependencies
- **Storing state in instance variables:** Use class variables or external files for persistence

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| EXIF rotation handling | Manual rotation logic | `ImageOps.exif_transpose()` | Many edge cases (orientation values 1-8) |
| Image format detection | Check extension only | PIL's `Image.open()` auto-detection | Extension can mismatch actual format |
| Directory path resolution | Manual string manipulation | `pathlib.Path.resolve()` | Handles symlinks, ~, relative paths |
| Image tensor format | Custom array manipulation | NumPy/torch standard operations | Preserves precision, handles dtypes |

**Key insight:** PIL and NumPy handle image format edge cases. Use them for I/O, not manual byte manipulation.

## Common Pitfalls

### Pitfall 1: Missing Trailing Comma in Tuples
**What goes wrong:** `RETURN_TYPES = ("IMAGE")` is a string, not a tuple; node fails to register
**Why it happens:** Python parentheses are grouping, not tuple syntax without comma
**How to avoid:** Always use trailing comma: `RETURN_TYPES = ("IMAGE",)`
**Warning signs:** Node doesn't appear in menu, "Import Failed" errors

### Pitfall 2: Image Tensor Shape Mismatch
**What goes wrong:** Downstream nodes fail with dimension errors
**Why it happens:** Forgetting batch dimension [B,H,W,C], returning [H,W,C]
**How to avoid:** Always verify shape is 4D: `tensor = tensor[None,]` adds batch if needed
**Warning signs:** "Tensor size mismatch" errors, dimension 3 vs 4 errors

### Pitfall 3: Path Validation Timing
**What goes wrong:** User sees error during workflow construction, not queue time
**Why it happens:** Validation in INPUT_TYPES runs at node creation, not execution
**How to avoid:** Use `VALIDATE_INPUTS` classmethod for path validation (runs at queue)
**Warning signs:** Errors appear while building workflow, not when running

### Pitfall 4: Case-Sensitive Pattern Matching
**What goes wrong:** `*.PNG` doesn't match `image.png` on case-sensitive systems
**Why it happens:** fnmatch is case-sensitive by default
**How to avoid:** Lowercase both pattern and filename before matching
**Warning signs:** Files "missing" that clearly exist in directory

### Pitfall 5: Corrupted/Unsupported File Handling
**What goes wrong:** Single bad file crashes entire batch
**Why it happens:** No try/except around PIL.Image.open()
**How to avoid:** Catch exceptions, log warning, skip file
**Warning signs:** Random crashes on certain directories

## Code Examples

Verified patterns from official sources:

### Complete INPUT_TYPES with All Widget Types
```python
# Source: https://docs.comfy.org/custom-nodes/walkthrough
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            # Text input
            "directory": ("STRING", {
                "default": "",
                "multiline": False,
                "tooltip": "Path to image directory"
            }),
            # Dropdown/COMBO
            "filter_preset": (["All Images", "PNG Only", "JPG Only", "Custom"], {
                "default": "All Images"
            }),
            # Integer with constraints
            "start_index": ("INT", {
                "default": 0,
                "min": 0,
                "max": 99999,
                "step": 1
            }),
        },
        "optional": {
            "custom_pattern": ("STRING", {"default": "*.png,*.jpg"}),
        },
    }
```

### IS_CHANGED for File-Based Inputs
```python
# Source: https://docs.comfy.org/custom-nodes/backend/server_overview
@classmethod
def IS_CHANGED(cls, directory, current_index, **kwargs):
    """Return unique value when node should re-execute."""
    if not os.path.isdir(directory):
        return ""

    files = cls._get_sorted_files(directory)
    if current_index >= len(files):
        return "complete"

    filepath = os.path.join(directory, files[current_index])
    stat = os.stat(filepath)

    # Change detection: path + mtime + size + index
    return f"{filepath}:{stat.st_mtime}:{stat.st_size}:{current_index}"
```

### VALIDATE_INPUTS for Queue-Time Validation
```python
# Source: https://docs.comfy.org/custom-nodes/backend/server_overview
@classmethod
def VALIDATE_INPUTS(cls, directory, filter_preset, custom_pattern="", **kwargs):
    """Validate inputs before execution."""
    if not directory:
        return "Directory path is required"

    if not os.path.isdir(directory):
        return f"Directory does not exist: {directory}"

    # Check for matching files
    pattern = cls._get_pattern(filter_preset, custom_pattern)
    files = cls._filter_files(directory, pattern)

    if not files:
        return f"No images found matching pattern: {pattern}"

    return True
```

### Node Registration in __init__.py
```python
# Source: https://docs.comfy.org/custom-nodes/backend/lifecycle
from .nodes.batch_loader import BatchImageLoader

NODE_CLASS_MAPPINGS = {
    "BatchImageLoader": BatchImageLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchImageLoader": "Batch Image Loader",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `*` any type | `tuple()` workaround or specific types | 2025 | Must define explicit types |
| Back-to-front execution | Front-to-back topological | PR #2666 (2025) | Execution order non-deterministic |
| Optional inputs skip validation | All connected inputs validated | PR #2666 (2025) | Must handle optional validation |

**Deprecated/outdated:**
- WAS Node Suite: Archived June 2025, known sorting bugs
- `"*"` type: No longer works reliably, use specific types

## Open Questions

Things that couldn't be fully resolved:

1. **Browse button implementation**
   - What we know: ComfyUI-FileBrowserAPI provides JS-based folder picker
   - What's unclear: Whether minimal text input is acceptable for MVP
   - Recommendation: Start with STRING input, add browse button as enhancement later

2. **Default directory behavior**
   - What we know: `folder_paths.get_input_directory()` returns ComfyUI's input folder
   - What's unclear: Whether to show full path or relative path in UI
   - Recommendation: Use full resolved path for clarity, show in tooltip

## Sources

### Primary (HIGH confidence)
- [ComfyUI Custom Nodes Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough) - Node structure, INPUT_TYPES
- [ComfyUI Backend Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes) - IMAGE tensor format [B,H,W,C]
- [ComfyUI Server Overview](https://docs.comfy.org/custom-nodes/backend/server_overview) - IS_CHANGED, VALIDATE_INPUTS, OUTPUT_NODE
- [ComfyUI folder_paths.py](https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py) - Standard directory access
- [Python glob documentation](https://docs.python.org/3/library/glob.html) - Pattern matching
- [Rosetta Code Natural Sort](https://rosettacode.org/wiki/Natural_sorting) - Natural sort algorithm

### Secondary (MEDIUM confidence)
- [natsort GitHub](https://github.com/SethMMorton/natsort) - Natural sort reference implementation
- [ComfyUI-FileBrowserAPI](https://github.com/GalactusX31/ComfyUI-FileBrowserAPI) - Browse button pattern
- Existing research in `.planning/research/` - ARCHITECTURE.md, STACK.md, PITFALLS.md

### Tertiary (LOW confidence)
- Community patterns from WebSearch (verified where possible)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries are ComfyUI-provided, verified in official docs
- Architecture: HIGH - Node structure verified with official walkthrough
- Pitfalls: HIGH - Verified against official docs and existing research

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - ComfyUI patterns are stable)
