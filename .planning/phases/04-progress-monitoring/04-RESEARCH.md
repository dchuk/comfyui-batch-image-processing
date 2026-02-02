# Phase 4: Progress & Monitoring - Research

**Researched:** 2026-02-02
**Domain:** ComfyUI Custom Node Output Extensions and Progress Formatting
**Confidence:** HIGH

## Summary

This phase extends existing nodes with new outputs and adds one helper node for progress text formatting. The research focused on three areas: (1) how to add return types to an existing OUTPUT_NODE like BatchImageSaver, (2) patterns for image passthrough from save nodes, and (3) creating simple utility nodes for string formatting.

The key insight is that BatchImageSaver currently has `RETURN_TYPES = ()` and `OUTPUT_NODE = True`, meaning it terminates the pipeline. To support image passthrough for preview wiring, we need to add `RETURN_TYPES` with IMAGE and STRING outputs while keeping `OUTPUT_NODE = True` (which is still valid when outputs exist). ComfyUI's standard PreviewImage also uses this pattern - OUTPUT_NODE just means the node produces visible output, not that it cannot have outputs.

The progress formatter is a simple utility node that takes two INT inputs (INDEX and TOTAL_COUNT) and outputs a formatted string like "3 of 10 (30%)". This follows established patterns from string utility node packs.

**Primary recommendation:** Extend BatchImageSaver with three new outputs (OUTPUT_IMAGE, SAVED_FILENAME, SAVED_PATH) and create a new BatchProgressFormatter node. Use defensive programming with max(1, total_count) for divide-by-zero protection.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Codebase)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python builtins | 3.10+ | String formatting, math | f-strings and basic arithmetic for progress calculation |
| os.path | Python stdlib | Path manipulation | Extract filename from full path |
| ComfyUI node pattern | N/A | RETURN_TYPES, RETURN_NAMES | Established pattern for node outputs |

### Supporting (Already Available)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| torch tensors | Image passthrough | Returning IMAGE type unchanged |
| typing | Type hints | Clean method signatures |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Formatted string output | Separate INT for percentage | User decision: keep it simple with formatted string |
| Custom preview node | ComfyUI PreviewImage | User decision: use existing PreviewImage, just wire OUTPUT_IMAGE to it |

**Installation:** No new dependencies required.

## Architecture Patterns

### Recommended Project Structure
```
comfyui_batch_image_processing/
├── nodes/
│   ├── batch_loader.py        # No changes needed (already has outputs)
│   ├── batch_saver.py         # MODIFY: Add RETURN_TYPES and new outputs
│   └── progress_formatter.py  # NEW: Simple progress text formatter
├── __init__.py                # MODIFY: Register new node
└── tests/
    └── test_progress_formatter.py  # NEW: Tests for formatter
```

### Pattern 1: Adding Outputs to OUTPUT_NODE
**What:** OUTPUT_NODE = True nodes CAN have RETURN_TYPES; they just also produce UI-visible results
**When to use:** When a terminal node (like save) should also pass data downstream
**Example:**
```python
# Source: ComfyUI nodes.py analysis + existing BatchImageSaver structure
class BatchImageSaver:
    CATEGORY = "batch_processing"
    # Changed from RETURN_TYPES = () to:
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("OUTPUT_IMAGE", "SAVED_FILENAME", "SAVED_PATH")
    FUNCTION = "save_image"
    OUTPUT_NODE = True  # Still true - produces UI preview

    def save_image(self, image, quality, overwrite_mode, ...):
        # ... existing save logic ...

        # Extract just the filename from the final path
        saved_filename = os.path.basename(final_path)
        saved_path = final_path

        # Return tuple matching RETURN_TYPES, plus ui dict
        return {
            "ui": {"images": [...]},  # UI preview data (existing)
            "result": (image, saved_filename, saved_path)  # New outputs
        }
```

### Pattern 2: Image Passthrough (Zero-Copy)
**What:** Return the input image tensor unchanged to allow downstream nodes (like PreviewImage) to consume it
**When to use:** When save node should enable preview wiring without re-loading
**Example:**
```python
# Source: Tensor operations are references, not copies by default
def save_image(self, image, ...):
    # ... save the image to disk ...

    # Return the SAME tensor (no copy, no re-encoding)
    # This is efficient - just passes the reference
    return {
        "ui": {...},
        "result": (image, ...)  # image is the input tensor, unchanged
    }
```

### Pattern 3: Simple Progress Formatter Node
**What:** Utility node that takes INDEX and TOTAL_COUNT, outputs formatted progress string
**When to use:** When user wants human-readable progress in their workflow
**Example:**
```python
# Source: Pattern from ComfyUI string utility nodes
class BatchProgressFormatter:
    """Format batch progress as human-readable string."""

    CATEGORY = "batch_processing"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("PROGRESS_TEXT",)
    FUNCTION = "format_progress"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "index": ("INT", {"default": 0, "min": 0, "forceInput": True}),
                "total_count": ("INT", {"default": 1, "min": 0, "forceInput": True}),
            },
        }

    def format_progress(self, index: int, total_count: int) -> tuple:
        # Convert 0-based index to 1-based for display
        current = index + 1
        # Protect against divide-by-zero
        safe_total = max(1, total_count)
        percentage = int((current / safe_total) * 100)

        progress_text = f"{current} of {safe_total} ({percentage}%)"
        return (progress_text,)
```

### Pattern 4: Node Registration in __init__.py
**What:** Adding new node to ComfyUI's node mappings
**When to use:** When creating new node class
**Example:**
```python
# Source: Existing __init__.py pattern in this codebase
from .nodes.batch_loader import BatchImageLoader
from .nodes.batch_saver import BatchImageSaver
from .nodes.progress_formatter import BatchProgressFormatter  # NEW

NODE_CLASS_MAPPINGS = {
    "BatchImageLoader": BatchImageLoader,
    "BatchImageSaver": BatchImageSaver,
    "BatchProgressFormatter": BatchProgressFormatter,  # NEW
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchImageLoader": "Batch Image Loader",
    "BatchImageSaver": "Batch Image Saver",
    "BatchProgressFormatter": "Batch Progress Formatter",  # NEW
}
```

### Anti-Patterns to Avoid
- **Re-encoding image for passthrough:** Just return the input tensor reference. Don't save, load, or convert.
- **Making OUTPUT_NODE = False on saver:** Keep it True so ComfyUI shows the preview in the node.
- **Complex state in formatter:** The formatter should be stateless - just takes inputs and produces output.
- **1-based INDEX assumption:** BatchImageLoader outputs 0-based INDEX. Formatter must convert for display.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image preview | Custom preview widget | Standard PreviewImage node | User decision; wire OUTPUT_IMAGE to PreviewImage |
| Progress bar UI | HTML/JS widget | Text output to any text display | Simpler, uses existing nodes |
| Percentage calculation | Complex rounding | `int((current / total) * 100)` | Simple integer percentage is sufficient |

**Key insight:** This phase intentionally keeps things simple - outputs that can be wired to existing nodes rather than building custom UI elements.

## Common Pitfalls

### Pitfall 1: Returning Wrong Structure from OUTPUT_NODE
**What goes wrong:** Node errors or UI preview doesn't work
**Why it happens:** OUTPUT_NODE nodes with RETURN_TYPES need special return format
**How to avoid:** Return `{"ui": {...}, "result": (tuple_of_outputs)}`
**Warning signs:** "TypeError" or missing preview images

### Pitfall 2: Divide by Zero in Percentage
**What goes wrong:** ZeroDivisionError crashes workflow
**Why it happens:** TOTAL_COUNT could be 0 if directory is empty (though validator should catch this)
**How to avoid:** Use `max(1, total_count)` before division
**Warning signs:** Workflow crashes on empty directories or at batch start

### Pitfall 3: Off-by-One in Progress Display
**What goes wrong:** Progress shows "0 of 10" or "10 of 10" twice
**Why it happens:** Mixing 0-based INDEX with 1-based display
**How to avoid:** Always convert: `current = index + 1` for display
**Warning signs:** Confusing progress output to users

### Pitfall 4: forceInput Not Set
**What goes wrong:** User can type in INDEX/TOTAL_COUNT instead of wiring
**Why it happens:** Without `forceInput: True`, inputs show as editable widgets
**How to avoid:** Add `"forceInput": True` to INPUT_TYPES for formatter inputs
**Warning signs:** Users typing values instead of connecting from BatchImageLoader

### Pitfall 5: Image Tensor Modified
**What goes wrong:** Downstream preview shows wrong image
**Why it happens:** Accidentally modifying the tensor before returning
**How to avoid:** Return the input tensor directly: `return {..., "result": (image, ...)}`
**Warning signs:** Preview image doesn't match saved image

## Code Examples

Verified patterns from official sources:

### BatchImageSaver Extended Return Structure
```python
# Source: ComfyUI nodes.py SaveImage pattern + this codebase
class BatchImageSaver:
    CATEGORY = "batch_processing"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("OUTPUT_IMAGE", "SAVED_FILENAME", "SAVED_PATH")
    FUNCTION = "save_image"
    OUTPUT_NODE = True

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
        # ... existing save logic produces final_path ...

        # Extract filename and path
        saved_filename = os.path.basename(final_path)
        saved_path = final_path

        # Return both UI preview and downstream outputs
        return {
            "ui": {
                "images": [
                    {
                        "filename": saved_filename,
                        "subfolder": subfolder,
                        "type": "output",
                    }
                ]
            },
            "result": (image, saved_filename, saved_path)
        }
```

### Complete BatchProgressFormatter Implementation
```python
# Source: Pattern from ComfyUI string utility nodes
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

        # Calculate percentage (integer, no decimals)
        percentage = int((current / safe_total) * 100)

        # Format: "3 of 10 (30%)"
        progress_text = f"{current} of {safe_total} ({percentage}%)"

        return (progress_text,)
```

### Node Registration Pattern
```python
# Source: This codebase __init__.py
"""ComfyUI Batch Image Processing Nodes."""

try:
    from .nodes.batch_loader import BatchImageLoader
    from .nodes.batch_saver import BatchImageSaver
    from .nodes.progress_formatter import BatchProgressFormatter

    NODE_CLASS_MAPPINGS = {
        "BatchImageLoader": BatchImageLoader,
        "BatchImageSaver": BatchImageSaver,
        "BatchProgressFormatter": BatchProgressFormatter,
    }

    NODE_DISPLAY_NAME_MAPPINGS = {
        "BatchImageLoader": "Batch Image Loader",
        "BatchImageSaver": "Batch Image Saver",
        "BatchProgressFormatter": "Batch Progress Formatter",
    }

    __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

except ImportError:
    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
    __all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Terminal save nodes (no output) | Save nodes with passthrough | Recent pattern | Enables preview wiring downstream |
| Custom progress UI widgets | String outputs to text displays | Simplicity trend | Works with any text display node |

**Deprecated/outdated:**
- Building custom preview widgets when PreviewImage exists
- Creating complex state management for simple formatting

## Open Questions

Things that couldn't be fully resolved:

1. **Return format for OUTPUT_NODE with outputs**
   - What we know: The pattern `{"ui": {...}, "result": (...)}` is used by some nodes
   - What's unclear: Whether all ComfyUI versions support this mixed format
   - Recommendation: Test thoroughly; this is the documented pattern

2. **forceInput behavior**
   - What we know: `forceInput: True` hides the widget and requires wiring
   - What's unclear: Exact behavior if user doesn't wire anything
   - Recommendation: Add validation or sensible defaults (0 for index, 1 for total_count)

## Sources

### Primary (HIGH confidence)
- [ComfyUI nodes.py](https://github.com/comfyanonymous/ComfyUI/blob/master/nodes.py) - SaveImage/PreviewImage implementation showing OUTPUT_NODE pattern
- [ComfyUI Docs - Properties](https://docs.comfy.org/custom-nodes/backend/server_overview) - RETURN_TYPES and return value patterns
- [ComfyUI example_node.py](https://github.com/comfyanonymous/ComfyUI/blob/master/custom_nodes/example_node.py.example) - Basic node structure

### Secondary (MEDIUM confidence)
- [comfyui-et_stringutils](https://github.com/exectails/comfyui-et_stringutils) - String formatting node patterns
- [CR Text Concatenate](https://www.runcomfy.com/comfyui-nodes/ComfyUI_Comfyroll_CustomNodes/CR-Text-Concatenate) - Text utility node pattern

### Tertiary (LOW confidence)
- [ComfyUI GitHub Discussion #2945](https://github.com/comfyanonymous/ComfyUI/discussions/2945) - Discussion on save with passthrough

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using only existing patterns and Python builtins
- Architecture: HIGH - Simple extensions to existing node structure
- Pitfalls: MEDIUM - Return format for OUTPUT_NODE with outputs needs validation

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days - node patterns are stable)
