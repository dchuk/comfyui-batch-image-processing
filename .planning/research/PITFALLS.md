# Domain Pitfalls: ComfyUI Custom Nodes for Batch Processing

**Domain:** ComfyUI custom nodes with batch image processing, directory iteration, and graph-level looping
**Researched:** 2026-02-01
**Overall Confidence:** HIGH (verified against official docs and multiple community sources)

---

## Critical Pitfalls

Mistakes that cause rewrites, major rework, or fundamental architecture problems.

### Pitfall 1: Incorrect Node Registration Structure

**What goes wrong:** Node fails to appear in ComfyUI's "Add Node" menu, or appears but crashes on use. The node simply doesn't exist from ComfyUI's perspective.

**Why it happens:** Missing or malformed `NODE_CLASS_MAPPINGS` in `__init__.py`, or required class attributes (`INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, `CATEGORY`) are missing or incorrectly defined.

**Consequences:**
- Node silently fails to register (no error, just absent)
- "Import Failed" error in ComfyUI console
- Node appears but crashes when added to workflow

**Warning signs:**
- Node not appearing in Add Node menu after restart
- `Import Failed` messages in console logs
- Node disappears after ComfyUI restart

**Prevention:**
```python
# Required class attributes - ALL must be present
class MyNode:
    CATEGORY = "batch_processing"

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {...}}

    RETURN_TYPES = ("IMAGE",)  # Tuple with trailing comma
    RETURN_NAMES = ("images",)  # Must be tuple, not string
    FUNCTION = "execute"  # Name of method to call

    def execute(self, ...):
        return (result,)  # Must return tuple

# Registration in __init__.py
NODE_CLASS_MAPPINGS = {
    "BatchImageLoader": BatchImageLoader,
}
```

**Critical details:**
- `RETURN_NAMES = "seed"` (string) breaks silently; must be `RETURN_NAMES = ("seed",)` (tuple)
- Return statement `return result` breaks; must be `return (result,)` (tuple)
- `NODE_CLASS_MAPPINGS` must be a dictionary, not a list

**Phase to address:** Phase 1 (Foundation) - establish correct node structure from the start.

**Sources:** [ComfyUI Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough), [GitHub Issue #4629](https://github.com/comfyanonymous/ComfyUI/issues/4629)

---

### Pitfall 2: Image Tensor Format Mismatch (BHWC vs Squeezed)

**What goes wrong:** Image processing fails with tensor dimension errors, or produces corrupted/distorted output.

**Why it happens:** ComfyUI uses `[B,H,W,C]` format (Batch, Height, Width, Channels), but developers assume `[H,W,C]` or use squeezed tensors when batch size is 1.

**Consequences:**
- "Tensor size mismatch" errors at runtime
- Images rendered with wrong dimensions/colors
- Batch operations fail silently or produce garbage
- Downstream nodes crash

**Warning signs:**
- Error: "The size of tensor a (X) must match the size of tensor b (Y)"
- Images appear distorted or color-shifted
- Operations work for single images but fail for batches

**Prevention:**
```python
def process_images(self, images):
    # images is always [B, H, W, C] - even for single images
    batch_size, height, width, channels = images.shape

    # WRONG: Assuming single image
    # image = images  # May be [H,W,C] if squeezed by upstream node

    # RIGHT: Always handle as batch
    for i in range(batch_size):
        single_image = images[i]  # Now [H, W, C]
        # process...

    # WRONG: Return squeezed
    # return processed_image  # Missing batch dimension

    # RIGHT: Always return with batch dimension
    if processed_image.dim() == 3:
        processed_image = processed_image.unsqueeze(0)
    return (processed_image,)
```

**Critical details:**
- Always unsqueeze when receiving potentially squeezed input
- Always check and maintain batch dimension on output
- Use `.shape` to verify dimensions before operations
- RGB images have 3 channels; RGBA has 4 (handle alpha channel cases)

**Phase to address:** Phase 1 (Foundation) - define image handling utilities from the start.

**Sources:** [ComfyUI Tensor Docs](https://docs.comfy.org/custom-nodes/backend/tensors)

---

### Pitfall 3: Memory Accumulation in Batch/Loop Processing

**What goes wrong:** RAM/VRAM grows unbounded during long batch processing runs, eventually causing OOM crash or OS process termination.

**Why it happens:** Tensors/images held in memory across iterations without explicit cleanup. ComfyUI's execution caching can retain intermediate results.

**Consequences:**
- Process killed by OS after processing ~50-200 images
- ComfyUI becomes unresponsive
- "torch.OutOfMemoryError" or "CUDA out of memory"
- System-wide slowdown as swap is used

**Warning signs:**
- Memory usage grows linearly with processed images
- Processing speed decreases over time
- ComfyUI hangs after many iterations
- Memory not released after workflow completion

**Prevention:**
```python
import gc
import torch

def process_batch(self, images, ...):
    results = []

    for i, image in enumerate(images):
        result = self._process_single(image)
        results.append(result.cpu())  # Move to CPU immediately

        # Periodic cleanup
        if i % 10 == 0:
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

    # Don't accumulate in instance variables
    # self.history.append(result)  # WRONG - grows forever

    return (torch.stack(results),)

# For loop implementations: clear state between iterations
def on_iteration_complete(self):
    gc.collect()
    torch.cuda.empty_cache()
```

**Critical details:**
- Move results to CPU if VRAM is constrained
- Call `gc.collect()` and `torch.cuda.empty_cache()` periodically
- Never store accumulated results in instance variables
- Process in smaller sub-batches (e.g., 10-20 images at a time)
- Consider yielding results incrementally rather than accumulating

**Phase to address:** Phase 2 (Batch Processing) - must be designed into batch architecture.

**Sources:** [GitHub Issue #11301](https://github.com/Comfy-Org/ComfyUI/issues/11301), [Batch Processing Guide](https://apatero.com/blog/batch-process-1000-images-comfyui-guide-2025)

---

### Pitfall 4: Execution Model Misunderstanding (Loops/Iteration)

**What goes wrong:** Custom loops don't execute as expected, iterations skip or repeat incorrectly, state doesn't persist between iterations.

**Why it happens:** ComfyUI's execution model changed from back-to-front recursive to front-to-back topological sort. Loops work via tail-recursion/subgraph expansion, not traditional iteration. Execution order is non-deterministic.

**Consequences:**
- Loops execute wrong number of times or not at all
- State lost between iterations
- Inconsistent behavior across runs
- Resume capability breaks unexpectedly

**Warning signs:**
- Loop count differs from expected
- Variables reset unexpectedly between iterations
- Different results on re-execution with same inputs
- Workflow hangs or completes instantly

**Prevention:**
```python
# DON'T rely on execution order
# Execution order is non-deterministic and changes based on caching

# DO use explicit state management
class LoopController:
    # Class-level state for persistence across executions
    _loop_state = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "iteration_id": ("STRING",),  # Unique ID for this loop
                "total_iterations": ("INT", {"default": 10}),
            }
        }

    def execute(self, iteration_id, total_iterations):
        # Initialize or retrieve state
        if iteration_id not in self._loop_state:
            self._loop_state[iteration_id] = {"current": 0, "total": total_iterations}

        state = self._loop_state[iteration_id]
        current = state["current"]

        # Check if loop should continue
        should_continue = current < state["total"]

        if should_continue:
            state["current"] += 1

        return (current, should_continue)
```

**Critical details:**
- Execution order depends on node IDs AND caching state
- Use Queue Trigger pattern (like Impact Pack) for iteration
- Store loop state in class variables or external persistence
- Each "iteration" may be a separate prompt/queue execution
- Consider Auto Queue mechanism for loop continuation

**Phase to address:** Phase 3 (Looping) - requires careful design before implementation.

**Sources:** [Execution Model Inversion Guide](https://docs.comfy.org/development/comfyui-server/execution_model_inversion_guide), [ControlFlowUtils](https://github.com/VykosX/ControlFlowUtils)

---

### Pitfall 5: IS_CHANGED and Caching Misuse

**What goes wrong:** Nodes re-execute when they shouldn't (wasting time) or don't re-execute when they should (producing stale results).

**Why it happens:** Incorrect implementation of `IS_CHANGED` classmethod, or not understanding ComfyUI's caching behavior.

**Consequences:**
- Batch processing re-processes already-completed images
- Resume capability fails (always starts from beginning)
- Changed files not detected, producing stale output
- Massive slowdown from unnecessary re-execution

**Warning signs:**
- Same images processed multiple times
- File changes not reflected in output
- "Skipped" images that should have been processed
- Inconsistent caching behavior

**Prevention:**
```python
class DirectoryLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": ""}),
                "index": ("INT", {"default": 0}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    FUNCTION = "load_image"

    @classmethod
    def IS_CHANGED(cls, directory, index):
        # Return a value that changes when node should re-execute
        import os

        if not os.path.isdir(directory):
            return ""

        files = sorted(os.listdir(directory))
        if index >= len(files):
            return ""

        filepath = os.path.join(directory, files[index])

        # Use modification time and file size for change detection
        stat = os.stat(filepath)
        return f"{filepath}:{stat.st_mtime}:{stat.st_size}"

    def load_image(self, directory, index):
        # ... implementation
```

**Critical details:**
- `IS_CHANGED` receives the same arguments as your FUNCTION
- Return value is compared to previous return value (not True/False)
- Return stable hash/string for unchanged state
- Consider file modification time + size for file-based inputs
- Be careful with `--cache-none` flag which disables caching entirely

**Phase to address:** Phase 2 (Batch Processing) - essential for resume capability.

**Sources:** [Caching Issue #4631](https://github.com/comfyanonymous/ComfyUI/issues/4631), [Feature Request #3111](https://github.com/comfyanonymous/ComfyUI/issues/3111)

---

## Moderate Pitfalls

Mistakes that cause delays, debugging time, or technical debt.

### Pitfall 6: Inconsistent Batch Sizes Across Nodes

**What goes wrong:** Nodes in a workflow have different batch size expectations, causing dimension mismatches or silent data loss.

**Prevention:**
- Document expected batch behavior clearly
- Use `RebatchImages` node pattern for normalization
- Validate batch dimensions at node entry
- Handle both batched and single-image inputs gracefully

```python
def validate_batch_input(self, images):
    """Normalize input to consistent batch format."""
    if images is None:
        raise ValueError("No images provided")

    if images.dim() == 3:
        # Single image [H, W, C] -> batch [1, H, W, C]
        images = images.unsqueeze(0)

    if images.dim() != 4:
        raise ValueError(f"Expected 4D tensor, got {images.dim()}D")

    return images
```

**Phase to address:** Phase 1 (Foundation) - establish batch handling conventions.

---

### Pitfall 7: Directory Path Handling Issues

**What goes wrong:** Directory loading fails silently, returns wrong files, or breaks across platforms (Windows vs Unix paths).

**Prevention:**
```python
import os
from pathlib import Path

def get_image_files(self, directory):
    """Cross-platform directory scanning with proper error handling."""
    path = Path(directory).expanduser().resolve()

    if not path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Supported image extensions
    extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff'}

    files = sorted([
        f for f in path.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ], key=lambda f: f.name)  # Consistent sort order

    return files
```

**Critical details:**
- Always use `pathlib.Path` or `os.path.join` for cross-platform compatibility
- Sort files explicitly for deterministic order (don't rely on OS ordering)
- Handle symlinks and hidden files appropriately
- Validate directory exists before listing

**Phase to address:** Phase 2 (Batch Processing) - core to directory iteration.

---

### Pitfall 8: Frontend Extension Synchronization Issues

**What goes wrong:** JavaScript extensions don't load, load out of sync with backend, or break after ComfyUI updates.

**Prevention:**
- Keep frontend extensions minimal if possible
- Use `WEB_DIRECTORY` export in `__init__.py`:
```python
WEB_DIRECTORY = "./web/js"
```
- Test with `--disable-all-custom-nodes` to isolate issues
- Avoid deprecated APIs (`/scripts/ui.js` is deprecated)
- Don't rely on JS state persisting across batch iterations

**Warning signs:**
- "[DEPRECATION WARNING] Detected import of deprecated legacy API"
- UI elements not appearing or misaligned
- Progress indicators not updating
- Workflows not executing when UI shows ready

**Phase to address:** Phase 4 (Progress Tracking) - if UI updates are needed.

**Sources:** [Frontend Issues](https://comfyui-wiki.com/en/news/2025-05-13-comfyui-custom-nodes-issues)

---

### Pitfall 9: Optional Input Validation Changes

**What goes wrong:** Nodes that worked before suddenly fail validation after ComfyUI updates, particularly for optional inputs.

**Why it happens:** ComfyUI execution model inversion (PR #2666) changed how optional inputs are validated. Previously only required inputs were validated; now optional inputs connected in the graph are also validated.

**Prevention:**
```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "image": ("IMAGE",),
        },
        "optional": {
            "mask": ("MASK",),  # Now validated if connected
        }
    }

@classmethod
def VALIDATE_INPUTS(cls, input_types=None, **kwargs):
    """Override to handle optional input validation gracefully."""
    # Return True to skip default validation
    # Return string to report error
    if "mask" in kwargs and kwargs["mask"] is not None:
        # Validate mask if provided
        pass
    return True
```

**Critical details:**
- Don't use reserved parameters (`min`, `max`) on non-comparable types (dicts)
- Implement `VALIDATE_INPUTS` for custom validation logic
- Test with both connected and disconnected optional inputs

**Phase to address:** Phase 1 (Foundation) - affects all node input handling.

**Sources:** [Execution Model Guide](https://docs.comfy.org/development/comfyui-server/execution_model_inversion_guide)

---

### Pitfall 10: Type Matching and "Any" Type Workarounds

**What goes wrong:** Nodes that accept any input type (`"*"`) break with "Return type mismatch" errors.

**Why it happens:** The `"*"` type was never officially supported; it worked by accident. Recent ComfyUI versions enforce type matching more strictly.

**Prevention:**
```python
# DON'T use "*" as input type (will break)
# "input": ("*",)  # WRONG

# DO use specific types or the "any_typ" pattern
any_typ = tuple()  # Empty tuple trick

@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "any_input": (any_typ,),  # Workaround for any type
        }
    }
```

**Critical details:**
- Define explicit types when possible
- Use the `any_typ = tuple()` workaround if truly needed
- Consider using COMBO type for constrained options
- V3 nodes will have proper "any" type support

**Phase to address:** Phase 1 (Foundation) - affects type definitions.

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable without major rework.

### Pitfall 11: Missing Trailing Comma in Tuples

**What goes wrong:** `RETURN_TYPES = ("IMAGE")` is parsed as a string, not a tuple, causing registration failures.

**Prevention:**
```python
# WRONG - string, not tuple
RETURN_TYPES = ("IMAGE")
RETURN_NAMES = ("output")

# RIGHT - tuple with trailing comma
RETURN_TYPES = ("IMAGE",)
RETURN_NAMES = ("output",)
```

**Phase to address:** Phase 1 - catch with linting/code review.

---

### Pitfall 12: Dependency Version Conflicts

**What goes wrong:** Your node requires a specific library version that conflicts with other installed nodes.

**Prevention:**
- Use flexible version ranges in `requirements.txt`: `torch>=2.0.0` instead of `torch==2.4.1`
- Test with common node packs installed
- Document known conflicts
- Consider making problematic dependencies optional

**Phase to address:** Phase 5 (Release) - test in realistic environments.

---

### Pitfall 13: Forgetting to Handle Empty Directories

**What goes wrong:** Directory loader crashes or hangs when given an empty directory.

**Prevention:**
```python
def load_from_directory(self, directory, index):
    files = self.get_image_files(directory)

    if not files:
        # Return placeholder or raise clear error
        raise ValueError(f"No valid images found in: {directory}")

    if index >= len(files):
        raise ValueError(f"Index {index} exceeds available images ({len(files)})")
```

**Phase to address:** Phase 2 (Batch Processing) - edge case handling.

---

### Pitfall 14: Not Testing with ComfyUI Manager

**What goes wrong:** Your node works in development but fails when installed via ComfyUI Manager.

**Prevention:**
- Test installation via Manager in a clean environment
- Include proper `__init__.py` exports
- Verify `pyproject.toml` or `setup.py` is correct
- Test with portable/packaged ComfyUI distributions

**Phase to address:** Phase 5 (Release) - pre-release testing.

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| Phase 1: Foundation | Node registration (#1), Tensor format (#2), Optional validation (#9) | Use scaffold template, validate tensor shapes, implement VALIDATE_INPUTS |
| Phase 2: Batch Processing | Memory accumulation (#3), Directory handling (#7), IS_CHANGED (#5) | Design cleanup strategy upfront, use pathlib, implement IS_CHANGED from start |
| Phase 3: Looping | Execution model (#4), State persistence | Study Impact Pack/ControlFlowUtils patterns, use Queue Trigger approach |
| Phase 4: Progress & Resume | Frontend sync (#8), Caching (#5) | Minimize JS extensions, persist progress to disk |
| Phase 5: Release | Dependencies (#12), Manager testing (#14) | Test in clean environment with common node packs |

---

## Testing Difficulties Specific to ComfyUI Nodes

### Challenge 1: No Official Testing Framework

**Problem:** ComfyUI doesn't provide a standard unit testing framework for custom nodes.

**Mitigation:**
- Test node methods directly in isolation (they're just Python methods)
- Use pytest for unit tests of processing logic
- Create minimal test workflows for integration testing
- Use ComfyUI's `--disable-all-custom-nodes` to isolate issues

### Challenge 2: Execution Environment Complexity

**Problem:** Nodes depend on ComfyUI's execution environment (folder_paths, model loading, etc.)

**Mitigation:**
- Mock ComfyUI dependencies in unit tests
- Keep processing logic separate from ComfyUI integration code
- Test in actual ComfyUI instance for integration tests

### Challenge 3: Batch/Loop Testing at Scale

**Problem:** Memory issues may only appear after processing 100+ images.

**Mitigation:**
- Test with deliberately small memory limits
- Monitor memory growth over iterations
- Use memory profiling tools during development
- Create stress-test workflows with many iterations

---

## Sources

### Official Documentation
- [ComfyUI Custom Nodes Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough)
- [ComfyUI Tensor Documentation](https://docs.comfy.org/custom-nodes/backend/tensors)
- [Execution Model Inversion Guide](https://docs.comfy.org/development/comfyui-server/execution_model_inversion_guide)
- [Troubleshooting Custom Node Issues](https://docs.comfy.org/troubleshooting/custom-node-issues)

### GitHub Issues and Discussions
- [Memory Leak Issue #11301](https://github.com/Comfy-Org/ComfyUI/issues/11301)
- [RETURN_NAMES String Bug #4629](https://github.com/comfyanonymous/ComfyUI/issues/4629)
- [Caching Slowdown #4631](https://github.com/comfyanonymous/ComfyUI/issues/4631)
- [IS_CHANGED Feature Request #3111](https://github.com/comfyanonymous/ComfyUI/issues/3111)

### Reference Implementations
- [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) - Loop/iteration patterns
- [ControlFlowUtils](https://github.com/VykosX/ControlFlowUtils) - Advanced flow control
- [WAS Node Suite](https://github.com/WASasquatch/was-node-suite-comfyui) - Batch loading patterns (archived but reference)

### Community Guides
- [Custom Node Issues Update Notice (May 2025)](https://comfyui-wiki.com/en/news/2025-05-13-comfyui-custom-nodes-issues)
- [Batch Processing 1000+ Images Guide](https://apatero.com/blog/batch-process-1000-images-comfyui-guide-2025)
- [Custom Nodes Breaking After Updates](https://apatero.com/blog/custom-nodes-breaking-comfyui-updates-fix-guide-2025)
