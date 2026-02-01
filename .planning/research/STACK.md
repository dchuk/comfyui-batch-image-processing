# Technology Stack: ComfyUI Batch Image Processing Custom Nodes

**Project:** ComfyUI Batch Image Processing
**Researched:** 2026-02-01
**Overall Confidence:** HIGH

## Executive Summary

ComfyUI custom node development follows a well-documented, standardized pattern. The framework provides a rich set of dependencies (PyTorch, PIL, NumPy) and a clear node registration system. For batch image processing with graph-level looping, the recommended approach uses **node expansion with GraphBuilder** - the same pattern that enables Impact Pack's loop functionality, but implemented independently without external node dependencies.

---

## Project Structure

**Confidence: HIGH** (Verified via [ComfyUI Official Documentation](https://docs.comfy.org/custom-nodes/walkthrough))

```
comfyui_batch_image_processing/
├── __init__.py                    # Node registration, exports NODE_CLASS_MAPPINGS
├── nodes/                         # Node implementations (modular)
│   ├── __init__.py
│   ├── batch_loader.py            # Directory image loading node
│   ├── batch_iterator.py          # Loop control node (node expansion)
│   ├── batch_saver.py             # Save with progress tracking
│   └── loop_utils.py              # ExecutionBlocker, loop state management
├── tests/                         # Unit tests
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures, mock ComfyUI context
│   ├── test_batch_loader.py
│   ├── test_batch_iterator.py
│   └── test_batch_saver.py
├── pyproject.toml                 # Package metadata, ComfyUI registry config
├── requirements.txt               # Additional dependencies (if any beyond ComfyUI)
└── README.md                      # User documentation
```

### Rationale

- **Flat `nodes/` directory**: Easier to navigate than deep nesting; each node type gets its own file
- **Separate `tests/`**: Standard Python testing convention; pytest auto-discovers tests
- **`pyproject.toml`**: Required for ComfyUI Registry publishing; standard Python packaging

---

## Required Boilerplate

### `__init__.py` (Root)

**Confidence: HIGH** (Verified via [ComfyUI Docs - Lifecycle](https://docs.comfy.org/custom-nodes/backend/lifecycle))

```python
from .nodes.batch_loader import BatchImageLoader
from .nodes.batch_iterator import BatchIteratorOpen, BatchIteratorClose
from .nodes.batch_saver import BatchImageSaver

NODE_CLASS_MAPPINGS = {
    "BatchImageLoader": BatchImageLoader,
    "BatchIteratorOpen": BatchIteratorOpen,
    "BatchIteratorClose": BatchIteratorClose,
    "BatchImageSaver": BatchImageSaver,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BatchImageLoader": "Batch Image Loader",
    "BatchIteratorOpen": "Batch Iterator (Open)",
    "BatchIteratorClose": "Batch Iterator (Close)",
    "BatchImageSaver": "Batch Image Saver",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

### Node Class Template

**Confidence: HIGH** (Verified via [ComfyUI Docs - Custom Nodes](https://docs.comfy.org/custom-nodes/walkthrough))

```python
class MyNode:
    """
    Node description for documentation.
    """

    # Required: Menu location in ComfyUI
    CATEGORY = "batch_processing"

    # Required: Input specification
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "value": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 100,
                    "step": 1,
                    "tooltip": "Description for users"
                }),
                "mode": (["option1", "option2"],),  # Dropdown
            },
            "optional": {
                "mask": ("MASK",),
            },
            "hidden": {
                "prompt": "PROMPT",           # Workflow metadata
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }

    # Required: Output types (tuple)
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("processed_image",)  # Optional: friendly names

    # Required: Method name to execute
    FUNCTION = "execute"

    # Optional attributes
    OUTPUT_NODE = False        # True for terminal nodes (SaveImage)
    OUTPUT_IS_LIST = (False,)  # True for list outputs
    INPUT_IS_LIST = False      # True to receive all inputs as lists

    def execute(self, image, value, mode, mask=None):
        # Process inputs
        # IMAGE is torch.Tensor with shape [B, H, W, C]
        result = image * value
        return (result,)  # Must return tuple

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Return unique value to force re-execution
        # Return float("NaN") to always re-execute
        return ""

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        # Return True or error message string
        return True
```

---

## ComfyUI-Provided Dependencies

**Confidence: HIGH** (Verified via [ComfyUI requirements.txt](https://github.com/comfyanonymous/ComfyUI/blob/master/requirements.txt))

| Dependency | Version | Purpose | Notes |
|------------|---------|---------|-------|
| **torch** | 2.4+ | Tensor operations, GPU compute | Core of all image processing |
| **torchvision** | Matches torch | Image transforms | Available but not often needed |
| **numpy** | >=1.25.0 | Array operations | For PIL conversion |
| **Pillow (PIL)** | Latest | Image I/O | Load/save images to disk |
| **scipy** | Latest | Scientific computing | Occasionally useful |
| **tqdm** | Latest | Progress bars | Available for long operations |
| **aiohttp** | >=3.11.8 | Async HTTP | For server communication |

### What You Do NOT Need in requirements.txt

These are already provided by ComfyUI:
- torch, torchvision, torchaudio
- numpy
- Pillow
- scipy
- tqdm
- safetensors
- transformers

### Image Data Format

**Confidence: HIGH** (Verified via [ComfyUI Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes))

```python
# IMAGE: torch.Tensor with shape [B, H, W, C]
# - B: Batch size (always >= 1)
# - H: Height
# - W: Width
# - C: Channels (3 for RGB)
# - Values: float32 in range [0.0, 1.0]

# Load from PIL to ComfyUI format:
from PIL import Image, ImageOps
import numpy as np
import torch

i = Image.open(image_path)
i = ImageOps.exif_transpose(i)  # Handle EXIF rotation
image = i.convert("RGB")
image = np.array(image).astype(np.float32) / 255.0
image = torch.from_numpy(image)[None,]  # Add batch dimension

# Save from ComfyUI format to PIL:
for batch_idx, img in enumerate(images):
    i = 255. * img.cpu().numpy()
    img_pil = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
    img_pil.save(filepath)
```

---

## Loop Implementation Strategy

**Confidence: HIGH** (Verified via [ComfyUI Node Expansion](https://docs.comfy.org/custom-nodes/backend/expansion))

### Why Node Expansion (Not Queue-Based)

| Approach | Pros | Cons |
|----------|------|------|
| **Node Expansion** | Self-contained, no external deps, proper caching | More complex implementation |
| Queue Trigger (Impact Pack pattern) | Simpler concept | Requires Auto Queue, external dependency |
| Batch all at once | Simplest | Memory issues with large batches |

**Recommendation: Node Expansion** - Implements loops via tail-recursion within the graph itself. Each iteration creates a subgraph, enabling proper caching and no dependency on ComfyUI Manager or Impact Pack.

### GraphBuilder Pattern

```python
from comfy_execution.graph_utils import GraphBuilder

class BatchIteratorOpen:
    """Opens a loop over images in a batch."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "current_index": ("INT", {"default": 0, "min": 0}),
            },
        }

    RETURN_TYPES = ("IMAGE", "INT", "INT", "BATCH_LOOP")  # current_image, index, total, loop_state
    FUNCTION = "iterate"
    CATEGORY = "batch_processing"

    def iterate(self, images, current_index):
        total = images.shape[0]
        if current_index >= total:
            # Loop complete - return ExecutionBlocker or final state
            from comfy_execution.graph_utils import ExecutionBlocker
            return (ExecutionBlocker(None), current_index, total, None)

        current_image = images[current_index:current_index+1]
        return (current_image, current_index, total, {"images": images, "index": current_index})

class BatchIteratorClose:
    """Closes loop, triggers next iteration via node expansion."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "processed_image": ("IMAGE",),
                "loop_state": ("BATCH_LOOP",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "close_loop"
    CATEGORY = "batch_processing"

    def close_loop(self, processed_image, loop_state):
        if loop_state is None:
            return (processed_image,)

        # Expand to next iteration
        graph = GraphBuilder()
        next_iter = graph.node(
            "BatchIteratorOpen",
            images=loop_state["images"],
            current_index=loop_state["index"] + 1
        )
        # ... continue building subgraph
        return {
            "result": (processed_image,),
            "expand": graph.finalize(),
        }
```

### Key Imports for Loop Implementation

```python
from comfy_execution.graph_utils import GraphBuilder
from comfy_execution.graph import ExecutionBlocker  # Stops execution branch
```

---

## Folder Paths API

**Confidence: HIGH** (Verified via [ComfyUI folder_paths.py](https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py))

```python
import folder_paths

# Get standard directories
input_dir = folder_paths.get_input_directory()    # ComfyUI/input/
output_dir = folder_paths.get_output_directory()  # ComfyUI/output/

# Get save path with counter
full_output_folder, filename, counter, subfolder, filename_prefix = \
    folder_paths.get_save_image_path(
        filename_prefix="batch_output",
        output_dir=output_dir,
        image_width=512,
        image_height=512
    )
```

---

## Progress Tracking & Server Communication

**Confidence: HIGH** (Verified via [ComfyUI Messages API](https://docs.comfy.org/development/comfyui-server/comms_messages))

```python
from server import PromptServer

class BatchImageSaver:
    # ... INPUT_TYPES, etc.

    def save_images(self, images, filename_prefix):
        total = images.shape[0]

        for i, image in enumerate(images):
            # Send progress to UI
            PromptServer.instance.send_sync(
                "progress",
                {"value": i + 1, "max": total}
            )

            # Save image...

        # Send completion message
        PromptServer.instance.send_sync(
            "batch.complete",
            {"message": f"Saved {total} images"}
        )

        return {"ui": {"images": saved_info}, "result": ()}
```

---

## Testing Framework

**Confidence: MEDIUM** (Pattern verified via [ComfyUI tests-unit](https://github.com/comfyanonymous/ComfyUI/tree/master/tests-unit), specific mocking patterns inferred)

### Setup

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-mock>=3.10",
    "pytest-cov>=4.0",
]
```

### Test Structure

```python
# tests/conftest.py
import pytest
import torch
import sys
from unittest.mock import MagicMock

@pytest.fixture
def mock_comfyui():
    """Mock ComfyUI modules that aren't available in test environment."""
    # Mock folder_paths
    folder_paths = MagicMock()
    folder_paths.get_input_directory.return_value = "/tmp/test_input"
    folder_paths.get_output_directory.return_value = "/tmp/test_output"
    sys.modules['folder_paths'] = folder_paths

    # Mock server
    server = MagicMock()
    server.PromptServer.instance = MagicMock()
    sys.modules['server'] = server

    yield {
        'folder_paths': folder_paths,
        'server': server,
    }

    # Cleanup
    del sys.modules['folder_paths']
    del sys.modules['server']

@pytest.fixture
def sample_image_tensor():
    """Create a sample IMAGE tensor in ComfyUI format [B,H,W,C]."""
    return torch.rand(1, 512, 512, 3, dtype=torch.float32)

@pytest.fixture
def sample_batch_tensor():
    """Create a batch of images for loop testing."""
    return torch.rand(5, 256, 256, 3, dtype=torch.float32)
```

### Test Example

```python
# tests/test_batch_loader.py
import pytest
import torch
from pathlib import Path

class TestBatchImageLoader:
    def test_input_types_structure(self, mock_comfyui):
        from nodes.batch_loader import BatchImageLoader

        input_types = BatchImageLoader.INPUT_TYPES()

        assert "required" in input_types
        assert "directory_path" in input_types["required"]

    def test_load_images_returns_correct_shape(self, mock_comfyui, tmp_path):
        from PIL import Image
        import numpy as np

        # Create test images
        for i in range(3):
            img = Image.fromarray(np.random.randint(0, 255, (64, 64, 3), dtype=np.uint8))
            img.save(tmp_path / f"test_{i}.png")

        from nodes.batch_loader import BatchImageLoader
        loader = BatchImageLoader()

        result = loader.load_images(directory_path=str(tmp_path))
        images = result[0]

        assert images.shape[0] == 3  # Batch size
        assert images.shape[3] == 3  # RGB channels
        assert images.dtype == torch.float32
        assert images.min() >= 0.0
        assert images.max() <= 1.0
```

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=nodes --cov-report=html

# Run specific test file
pytest tests/test_batch_loader.py -v
```

---

## pyproject.toml Template

**Confidence: HIGH** (Verified via [ComfyUI Registry Specifications](https://docs.comfy.org/registry/specifications))

```toml
[project]
name = "comfyui-batch-image-processing"
version = "1.0.0"
description = "Batch image processing nodes with graph-level looping for ComfyUI"
license = "MIT"
readme = "README.md"
requires-python = ">=3.10"

authors = [
    { name = "Your Name" }
]

keywords = [
    "comfyui",
    "batch",
    "image processing",
    "loop"
]

classifiers = [
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: OS Independent",
]

# Only list dependencies NOT provided by ComfyUI
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-mock>=3.10",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
]

[project.urls]
Repository = "https://github.com/yourusername/comfyui-batch-image-processing"

[tool.comfy]
PublisherId = "your-publisher-id"
DisplayName = "Batch Image Processing"
Icon = ""

# ComfyUI version compatibility
requires-comfyui = ">=0.3.0"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"

[tool.ruff]
line-length = 100
target-version = "py310"
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not Alternative |
|----------|-------------|-------------|---------------------|
| Loop Pattern | Node Expansion | Impact Pack dependency | Adds external dependency, less control |
| Loop Pattern | Node Expansion | Queue Trigger | Requires Auto Queue enabled, harder to test |
| Testing | pytest | unittest | pytest has better fixtures, cleaner syntax |
| Structure | Flat nodes/ | Single nodes.py | Harder to maintain as node count grows |

---

## Version Requirements Summary

| Component | Minimum Version | Recommended | Notes |
|-----------|-----------------|-------------|-------|
| Python | 3.10 | 3.11-3.12 | Match ComfyUI environment |
| ComfyUI | 0.3.0+ | Latest | Node expansion requires newer versions |
| PyTorch | 2.4+ | Latest stable | Provided by ComfyUI |
| pytest | 7.0+ | 8.0+ | For testing |

---

## Sources

### HIGH Confidence (Official Documentation)
- [ComfyUI Custom Nodes Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough)
- [ComfyUI Node Expansion](https://docs.comfy.org/custom-nodes/backend/expansion)
- [ComfyUI Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI Backend Lifecycle](https://docs.comfy.org/custom-nodes/backend/lifecycle)
- [ComfyUI Registry Specifications](https://docs.comfy.org/registry/specifications)
- [ComfyUI Messages API](https://docs.comfy.org/development/comfyui-server/comms_messages)
- [ComfyUI requirements.txt](https://github.com/comfyanonymous/ComfyUI/blob/master/requirements.txt)
- [ComfyUI folder_paths.py](https://github.com/comfyanonymous/ComfyUI/blob/master/folder_paths.py)

### MEDIUM Confidence (Community/Inferred)
- [ComfyUI-CryptIO Testing Pattern](https://github.com/Suzu008/ComfyUI-CryptIO)
- [ComfyUI-Impact-Pack Loop Reference](https://github.com/ltdrdata/ComfyUI-Impact-Pack)
- [ComfyUI tests-unit Structure](https://github.com/comfyanonymous/ComfyUI/tree/master/tests-unit)
