# Architecture Patterns: ComfyUI Batch Processing Nodes

**Domain:** ComfyUI Custom Nodes for Batch Image Processing
**Researched:** 2026-02-01
**Overall Confidence:** HIGH (Context7 + Official Docs verified)

## Executive Summary

ComfyUI uses a directed acyclic graph (DAG) execution model where nodes are Python classes that define inputs, outputs, and processing logic. The execution engine performs topological sorting and intelligent caching, only re-executing nodes whose inputs have changed. For batch/loop processing, there are two primary patterns: **queue-per-image** (using Auto Queue to re-execute the entire workflow) and **in-graph looping** (using execution blocking with Open/Close node pairs). This project should implement queue-per-image for simplicity and immediate saves, while using persistent state files for resume capability.

---

## Recommended Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ComfyUI Workflow (DAG)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐    ┌─────────────────┐    ┌────────────────┐ │
│  │  BatchLoader     │───▶│  Image Pipeline │───▶│  BatchSaver    │ │
│  │  (Load + Index)  │    │  (User's nodes) │    │  (Save + Log)  │ │
│  └──────────────────┘    └─────────────────┘    └────────────────┘ │
│         │                                               │          │
│         │              ┌──────────────────┐             │          │
│         └─────────────▶│  ProgressTracker │◀────────────┘          │
│                        │  (State File)    │                        │
│                        └──────────────────┘                        │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    Auto Queue Triggers Re-execution
                                │
                                ▼
                    Next iteration loads next image
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **BatchLoader** | Load images from directory, track current index, filter/sort files | ProgressTracker (read index), Pipeline (IMAGE output) |
| **ProgressTracker** | Persist state to JSON file, track completed items, enable resume | BatchLoader (current index), BatchSaver (completion log) |
| **BatchSaver** | Save processed image with naming, update progress state | ProgressTracker (mark complete), receives IMAGE from pipeline |
| **User Pipeline** | Any ComfyUI nodes (KSampler, upscaler, etc.) | Receives IMAGE from BatchLoader, outputs IMAGE to BatchSaver |

### Data Flow

```
[Filesystem]                    [ComfyUI Graph]                    [Filesystem]
     │                                │                                 │
     │  Directory of images           │                                 │
     ▼                                │                                 │
┌─────────────┐                       │                                 │
│ input/      │                       │                                 │
│ ├─001.jpg   │──────┐               │                                 │
│ ├─002.jpg   │      │               │                                 │
│ └─003.jpg   │      │               │                                 │
└─────────────┘      │               │                                 │
                     │               │                                 │
┌─────────────┐      │               │                                 │
│progress.json│◀─────┼───────────────┼─────────────────────────────────┤
│{            │      │               │                                 │
│ "index": 1, │      ▼               │                                 │
│ "done": [0] │  ┌─────────────┐     │                                 │
│}            │  │ BatchLoader │     │                                 │
└─────────────┘  │             │     │                                 │
     ▲           │ • Read dir  │     │                                 │
     │           │ • Sort files│     │                                 │
     │           │ • Get index │     │     ┌───────────────────┐       │
     │           │ • Load image│─────┼────▶│ torch.Tensor      │       │
     │           └─────────────┘     │     │ [B,H,W,C]         │       │
     │                               │     │ (Single image)    │       │
     │                               │     └─────────┬─────────┘       │
     │                               │               │                 │
     │                               │               ▼                 │
     │                               │     ┌───────────────────┐       │
     │                               │     │ User Pipeline     │       │
     │                               │     │ (KSampler, etc.)  │       │
     │                               │     └─────────┬─────────┘       │
     │                               │               │                 │
     │                               │               ▼                 │
     │                               │     ┌───────────────────┐       │
     │           ┌─────────────┐     │     │ torch.Tensor      │       │
     │           │ BatchSaver  │◀────┼─────│ [B,H,W,C]         │       │
     │           │             │     │     │ (Processed image) │       │
     └───────────│ • Save file │     │     └───────────────────┘       │
                 │ • Update log│     │                                 │
                 │ • Increment │     │                                 │
                 └──────┬──────┘     │                                 │
                        │            │                                 │
                        ▼            │                                 ▼
                 ┌─────────────┐     │                          ┌─────────────┐
                 │ output/     │     │                          │ output/     │
                 │ ├─001.png   │     │                          │ processed/  │
                 │ └─...       │     │                          └─────────────┘
                 └─────────────┘     │
```

---

## Patterns to Follow

### Pattern 1: Queue-Per-Image Execution Model

**What:** Each image is processed in a separate workflow execution. Auto Queue triggers the next execution automatically.

**When:** Default pattern for batch processing in ComfyUI.

**Why:**
- Immediate saves after each image (crash-safe)
- Simpler state management
- Natural resume points
- Works with any pipeline nodes (no special loop support needed)

**Example:**
```python
class BatchImageLoader:
    """Load one image per execution, incrementing through a directory."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": ""}),
                "reset_index": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT")
    RETURN_NAMES = ("image", "filename", "current_index", "total_count")
    FUNCTION = "load_next_image"
    OUTPUT_NODE = False

    def load_next_image(self, directory, reset_index):
        # Read state from progress file
        state = self._load_state(directory)
        if reset_index:
            state["index"] = 0

        # Get sorted file list
        files = self._get_sorted_files(directory)

        # Load current image
        current_index = state["index"]
        image = self._load_image(files[current_index])

        # Update state for next execution
        state["index"] = current_index + 1
        self._save_state(directory, state)

        return (image, files[current_index], current_index, len(files))
```

**References:**
- [ComfyUI Batch Processing Guide 2025](https://apatero.com/blog/batch-process-1000-images-comfyui-guide-2025)
- [ComfyUI Nodes Documentation](https://docs.comfy.org/development/core-concepts/nodes)

### Pattern 2: State File for Resume Capability

**What:** Persist processing state (current index, completed files, errors) to a JSON file alongside the input directory.

**When:** Any batch operation that should be resumable after interruption.

**Why:**
- Resume without reprocessing completed images
- Track which files failed for retry
- Simple file-based persistence (no database needed)

**Example:**
```python
# State file structure: .batch_progress.json
{
    "version": 1,
    "directory": "/path/to/input",
    "current_index": 5,
    "total_files": 100,
    "completed": [0, 1, 2, 3, 4],
    "failed": [],
    "started_at": "2026-02-01T10:00:00Z",
    "last_updated": "2026-02-01T10:05:00Z"
}
```

```python
def _load_state(self, directory):
    """Load or initialize progress state."""
    state_file = os.path.join(directory, ".batch_progress.json")
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    return {"version": 1, "index": 0, "completed": [], "failed": []}

def _save_state(self, directory, state):
    """Persist progress state atomically."""
    state_file = os.path.join(directory, ".batch_progress.json")
    temp_file = state_file + ".tmp"
    with open(temp_file, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, state_file)  # Atomic on most systems
```

### Pattern 3: IS_CHANGED for Index-Based Cache Busting

**What:** Use the `IS_CHANGED` class method to force re-execution based on the current file index.

**When:** Nodes that must re-execute each queue cycle (loaders, savers).

**Why:** ComfyUI's caching system would otherwise reuse previous outputs if inputs appear unchanged.

**Example:**
```python
class BatchImageLoader:
    @classmethod
    def IS_CHANGED(cls, directory, **kwargs):
        """Return unique value each time to prevent caching."""
        state = cls._load_state_static(directory)
        return str(state.get("index", 0))
```

**References:**
- [ComfyUI Custom Nodes - IS_CHANGED](https://docs.comfy.org/custom-nodes/backend/server_overview)

### Pattern 4: OUTPUT_NODE for Save Nodes

**What:** Mark saver nodes with `OUTPUT_NODE = True` to ensure they are always executed.

**When:** Any node that writes to filesystem or has side effects.

**Why:** ComfyUI only guarantees execution of output nodes and their dependencies.

**Example:**
```python
class BatchImageSaver:
    OUTPUT_NODE = True  # Critical: ensures this node always runs
    CATEGORY = "batch_processing"

    # ... rest of implementation
```

**References:**
- [ComfyUI Server Overview - OUTPUT_NODE](https://docs.comfy.org/custom-nodes/backend/server_overview)

### Pattern 5: IMAGE Tensor Format [B,H,W,C]

**What:** All images in ComfyUI are `torch.Tensor` with shape `[B, H, W, C]` (batch, height, width, channels).

**When:** Any image loading, processing, or saving.

**Why:** Consistency with ComfyUI's internal format; required for node compatibility.

**Example:**
```python
from PIL import Image, ImageOps
import numpy as np
import torch

def load_image(path: str) -> torch.Tensor:
    """Load image as ComfyUI-compatible tensor."""
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # Handle EXIF rotation
    if img.mode == 'I':
        img = img.point(lambda i: i * (1 / 255))
    img = img.convert("RGB")

    # Convert to tensor: [H, W, C] -> [1, H, W, C]
    array = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(array)[None,]  # Add batch dimension
    return tensor

def save_image(tensor: torch.Tensor, path: str):
    """Save ComfyUI tensor to file."""
    # tensor shape: [B, H, W, C], take first in batch
    img_array = 255.0 * tensor[0].cpu().numpy()
    img = Image.fromarray(np.clip(img_array, 0, 255).astype(np.uint8))
    img.save(path)
```

**References:**
- [ComfyUI IMAGE Datatype](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI Images and Masks](https://docs.comfy.org/custom-nodes/backend/images_and_masks)

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: In-Graph Looping for Simple Batch Operations

**What:** Using execution-blocking loop nodes (LoopOpen/LoopClose) for simple image batch processing.

**Why bad:**
- Complex implementation requiring multiple coordinating nodes
- State management is harder
- No immediate saves (must wait for loop completion)
- Harder to resume after interruption

**Instead:** Use queue-per-image with Auto Queue. Simpler, more robust, immediate saves.

### Anti-Pattern 2: Relying on Execution Order

**What:** Assuming nodes execute in a specific order (e.g., left-to-right).

**Why bad:**
> "The execution order is now considered non-deterministic and subject to change, influenced not only by the graph's structure but also by cached values. It is crucial not to rely on a specific execution order."

**Instead:** Use explicit data dependencies (connecting outputs to inputs) to control execution order.

**References:**
- [ComfyUI Execution Model Inversion Guide](https://github.com/comfy-org/docs/blob/main/development/comfyui-server/execution_model_inversion_guide.mdx)

### Anti-Pattern 3: Loading All Images at Once

**What:** Loading entire directory into memory before processing.

**Why bad:**
- Memory exhaustion with large batches
- No immediate progress visibility
- Complete restart needed on failure

**Instead:** Load one image per execution cycle.

### Anti-Pattern 4: External Node Dependencies

**What:** Depending on Impact Pack, Easy Use, or other third-party node packs for loop functionality.

**Why bad:**
- Installation complexity
- Version compatibility issues
- Maintenance burden
- Users must install additional packages

**Instead:** Use native ComfyUI patterns (Auto Queue + state files) that work with base ComfyUI.

---

## Component Specifications

### BatchImageLoader Node

**Purpose:** Load images sequentially from a directory, one per execution.

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `directory` | STRING | Path to input directory |
| `file_pattern` | STRING | Glob pattern (default: `*.{jpg,png,webp}`) |
| `sort_order` | ENUM | `name_asc`, `name_desc`, `date_asc`, `date_desc` |
| `reset_on_run` | BOOLEAN | Reset index to 0 when True |
| `skip_existing` | BOOLEAN | Skip files already processed |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| `IMAGE` | IMAGE | Current image as tensor [1,H,W,C] |
| `filename` | STRING | Current filename (without path) |
| `filepath` | STRING | Full path to current file |
| `index` | INT | Current 0-based index |
| `total` | INT | Total files in directory |
| `is_last` | BOOLEAN | True if this is the last image |

**Behavior:**
1. On first execution or reset: scan directory, sort files, initialize state
2. Load current index from state file
3. Load and return image at current index
4. Increment index in state file
5. If index >= total: signal completion (can trigger workflow stop)

### BatchImageSaver Node

**Purpose:** Save processed image with configurable naming, update progress.

**Inputs:**
| Name | Type | Description |
|------|------|-------------|
| `images` | IMAGE | Processed image tensor |
| `output_directory` | STRING | Where to save (default: ComfyUI output) |
| `filename_prefix` | STRING | Prefix for saved files |
| `naming_mode` | ENUM | `sequential`, `preserve_original`, `timestamp` |
| `original_filename` | STRING | Pass-through from loader (for preserve mode) |
| `format` | ENUM | `png`, `jpg`, `webp` |
| `quality` | INT | JPEG/WebP quality (1-100) |

**Outputs:**
| Name | Type | Description |
|------|------|-------------|
| `saved_path` | STRING | Full path to saved file |
| `success` | BOOLEAN | Whether save succeeded |

**Behavior:**
1. Construct output filename based on naming_mode
2. Convert tensor to PIL Image
3. Save with specified format/quality
4. Update progress state (mark current index as completed)
5. Return saved path

### ProgressTracker (Shared Module)

**Purpose:** Manage persistent state for batch operations.

**State File Format:**
```json
{
    "version": 1,
    "schema": "batch_progress_v1",
    "directory": "/path/to/input",
    "file_list": ["001.jpg", "002.jpg", "003.jpg"],
    "total_files": 3,
    "current_index": 1,
    "status": "in_progress",
    "completed": {
        "001.jpg": {
            "output_path": "/path/to/output/001.png",
            "completed_at": "2026-02-01T10:01:00Z"
        }
    },
    "failed": {},
    "started_at": "2026-02-01T10:00:00Z",
    "last_updated": "2026-02-01T10:01:00Z"
}
```

**Key Methods:**
- `load_or_create(directory)` - Load existing state or create new
- `get_next_index()` - Get next unprocessed index
- `mark_completed(filename, output_path)` - Record successful processing
- `mark_failed(filename, error)` - Record failure for retry
- `is_complete()` - Check if all files processed
- `get_progress()` - Return (completed, total, percentage)

---

## Build Order (Dependencies)

Based on component dependencies, implement in this order:

### Phase 1: Core Infrastructure
1. **ProgressTracker module** - State management (no dependencies)
   - JSON state file read/write
   - Atomic file operations
   - State schema validation

### Phase 2: Image I/O Nodes
2. **BatchImageLoader node** - Depends on ProgressTracker
   - Directory scanning
   - File filtering/sorting
   - Image loading (PIL -> torch.Tensor)
   - State integration

3. **BatchImageSaver node** - Depends on ProgressTracker
   - Image saving (torch.Tensor -> PIL)
   - Naming modes
   - Format/quality options
   - State updates

### Phase 3: Control & Monitoring
4. **BatchStopCondition node** (optional) - Conditional termination
   - Check if batch is complete
   - Signal ComfyUI to stop auto-queue

5. **BatchProgressDisplay node** (optional) - UI feedback
   - Show current/total progress
   - Estimated time remaining

### Phase 4: Polish
6. **Error handling** - Graceful failure recovery
7. **Testing** - Unit tests, integration tests
8. **Documentation** - Usage examples, workflow templates

---

## Key Technical Patterns to Implement

### 1. Directory Scanning with Sorting
```python
import os
import glob
from pathlib import Path

def scan_directory(directory: str, pattern: str = "*.{jpg,jpeg,png,webp}",
                   sort_order: str = "name_asc") -> list[str]:
    """Scan directory for images matching pattern, return sorted list."""
    # Expand glob patterns
    extensions = pattern.strip("*.{}").split(",")
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(directory, f"*.{ext}")))

    # Remove duplicates and get basenames
    files = list(set(files))

    # Sort based on order
    if sort_order == "name_asc":
        files.sort(key=lambda f: os.path.basename(f).lower())
    elif sort_order == "name_desc":
        files.sort(key=lambda f: os.path.basename(f).lower(), reverse=True)
    elif sort_order == "date_asc":
        files.sort(key=lambda f: os.path.getmtime(f))
    elif sort_order == "date_desc":
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

    return files
```

### 2. Atomic State File Writes
```python
import json
import os
import tempfile

def save_state_atomic(state: dict, filepath: str):
    """Save state file atomically to prevent corruption."""
    directory = os.path.dirname(filepath)

    # Write to temp file first
    fd, temp_path = tempfile.mkstemp(dir=directory, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=2)
        # Atomic rename
        os.replace(temp_path, filepath)
    except:
        # Clean up temp file on failure
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
```

### 3. Using folder_paths for ComfyUI Integration
```python
import folder_paths

def get_default_directories():
    """Get ComfyUI's standard directories."""
    return {
        "input": folder_paths.get_input_directory(),
        "output": folder_paths.get_output_directory(),
        "temp": folder_paths.get_temp_directory(),
    }

def get_save_path(filename_prefix: str, width: int, height: int):
    """Get path for saving output images."""
    return folder_paths.get_save_image_path(
        filename_prefix,
        folder_paths.get_output_directory(),
        width,
        height
    )
```

### 4. Node Registration Pattern
```python
# __init__.py for the custom node package

from .batch_loader import BatchImageLoader
from .batch_saver import BatchImageSaver

NODE_CLASS_MAPPINGS = {
    "BatchImageLoader": BatchImageLoader,
    "BatchImageSaver": BatchImageSaver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchImageLoader": "Batch Image Loader",
    "BatchImageSaver": "Batch Image Saver",
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
```

---

## Integration with ComfyUI Auto Queue

The batch processing system relies on ComfyUI's Auto Queue feature:

1. **User enables Auto Queue** in ComfyUI's "Extra Options"
2. **Workflow executes once** - BatchLoader loads first image
3. **Pipeline processes** - User's nodes transform the image
4. **BatchSaver saves** - Output written, state updated
5. **Execution completes** - Auto Queue triggers next execution
6. **Loop continues** until BatchLoader signals completion

### Signaling Completion

To stop Auto Queue when batch is complete:
```python
import comfy.model_management as model_management

def signal_batch_complete():
    """Signal ComfyUI to stop auto-queue."""
    # Option 1: Raise a special exception that ComfyUI handles gracefully
    # Option 2: Return a special value that downstream nodes can check
    # Option 3: Use interrupt mechanism
    model_management.interrupt_current_processing()
```

---

## Sources

### HIGH Confidence (Context7 / Official Documentation)
- [ComfyUI Nodes Documentation](https://docs.comfy.org/development/core-concepts/nodes) - Node structure and execution
- [ComfyUI Custom Nodes Server Overview](https://docs.comfy.org/custom-nodes/backend/server_overview) - INPUT_TYPES, OUTPUT_NODE, IS_CHANGED
- [ComfyUI IMAGE Datatype](https://docs.comfy.org/custom-nodes/backend/datatypes) - Tensor format [B,H,W,C]
- [ComfyUI Images and Masks](https://docs.comfy.org/custom-nodes/backend/images_and_masks) - Image loading/saving patterns
- [ComfyUI folder_paths.py](https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py) - Directory management
- [Execution Model Inversion Guide](https://github.com/comfy-org/docs/blob/main/development/comfyui-server/execution_model_inversion_guide.mdx) - Non-deterministic execution order

### MEDIUM Confidence (Verified Community Resources)
- [ComfyUI Batch Processing Guide 2025](https://apatero.com/blog/batch-process-1000-images-comfyui-guide-2025) - Queue-per-image pattern
- [ComfyUI-Loop-image Documentation](https://github.com/WainWong/ComfyUI-Loop-image) - Loop node architecture patterns
- [ControlFlowUtils LoopOpen](https://www.runcomfy.com/comfyui-nodes/ControlFlowUtils/LoopOpen) - Execution blocking patterns
- [Impact Pack Loop Tutorial](https://civitai.com/articles/3764/how-to-create-a-loop-in-comfyui-using-impact-pack) - Auto Queue integration

### Reference Implementations (For Pattern Study)
- [ComfyUI-Loop-image](https://github.com/WainWong/ComfyUI-Loop-image) - Flow control signal patterns
- [ComfyUI Impact Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack) - ImpactConditionalStopIteration
- [ControlFlowUtils](https://comfy.icu/extension/VykosX__ControlFlowUtils) - Persistent variables across executions
