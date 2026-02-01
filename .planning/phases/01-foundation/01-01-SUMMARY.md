---
phase: 01-foundation
plan: 01
subsystem: core-infrastructure
tags: [comfyui, nodes, natural-sort, project-structure]
dependency-graph:
  requires: []
  provides: [project-structure, node-registration, natural-sort-utility, image-loading-utility]
  affects: [01-02]
tech-stack:
  added: [pytest]
  patterns: [comfyui-node-registration, natural-sort, graceful-dependency-handling]
key-files:
  created:
    - __init__.py
    - nodes/__init__.py
    - nodes/batch_loader.py
    - utils/__init__.py
    - utils/sorting.py
    - utils/image_utils.py
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_sorting.py
    - pyproject.toml
  modified: []
decisions:
  - id: graceful-imports
    description: Use try/except for torch/numpy imports to enable testing without ComfyUI
    rationale: Allows pytest to run sorting tests without installing heavy dependencies
metrics:
  duration: ~15 minutes
  completed: 2026-02-01
---

# Phase 1 Plan 1: Project Structure and Node Registration Summary

**One-liner:** ComfyUI node package structure with BatchImageLoader skeleton, natural sort utility (img2 before img10), and test infrastructure that runs without torch.

## What Was Built

### Project Structure
Created the standard ComfyUI custom node package structure:
```
comfyui_batch_image_processing/
├── __init__.py              # NODE_CLASS_MAPPINGS registration
├── nodes/
│   ├── __init__.py
│   └── batch_loader.py      # BatchImageLoader skeleton
├── utils/
│   ├── __init__.py
│   ├── sorting.py           # natural_sort_key function
│   └── image_utils.py       # load_image_as_tensor function
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest fixtures
│   └── test_sorting.py      # 10 natural sort test cases
└── pyproject.toml           # pytest configuration
```

### BatchImageLoader Node (Skeleton)
- CATEGORY: `batch_processing`
- INPUT_TYPES: directory (STRING), filter_preset (COMBO), custom_pattern (STRING)
- RETURN_TYPES: IMAGE, INT (TOTAL_COUNT), INT (CURRENT_INDEX), STRING (FILENAME), STRING (BASENAME)
- FUNCTION: `load_image` (placeholder returning dummy values - to be completed in Plan 02)

### Natural Sort Utility
- `natural_sort_key(s: str) -> list` - generates sort key for natural ordering
- Case-insensitive comparison
- Handles: numeric sorting (img2 < img10), multiple number groups, special characters

### Image Loading Utility
- `load_image_as_tensor(filepath: str) -> torch.Tensor`
- Handles EXIF rotation via ImageOps.exif_transpose()
- Handles 16-bit grayscale (mode 'I') images
- Converts to ComfyUI tensor format [1, H, W, C] float32 [0.0, 1.0]

### Test Infrastructure
- pytest configured in pyproject.toml
- 10 comprehensive test cases for natural_sort_key
- Tests run without torch/numpy/PIL installed (graceful import handling)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pytest import conflicts with ComfyUI dependencies**
- **Found during:** Task 2
- **Issue:** pytest was importing root `__init__.py` which requires torch, causing test collection to fail
- **Fix:** Made imports in `__init__.py` and `utils/__init__.py` graceful with try/except blocks
- **Files modified:** `__init__.py`, `utils/__init__.py`
- **Commit:** 847c790

## Verification Results

1. **Structure verification:** All files exist in correct locations
2. **Import chain:** NODE_CLASS_MAPPINGS exports correctly (empty dict without torch)
3. **Natural sort:** `sorted(['img10', 'img2', 'img1'], key=natural_sort_key)` returns `['img1', 'img2', 'img10']`
4. **Tests:** All 10 pytest tests pass

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 97bfe04 | feat | Create project structure with node registration and utilities |
| 847c790 | test | Add test infrastructure with natural sort tests |

## Next Phase Readiness

**Plan 01-02 can proceed:**
- Project structure is in place
- BatchImageLoader skeleton exists with correct interface
- Natural sort and image loading utilities are ready
- Test infrastructure allows adding more tests

**Prerequisites for 01-02:**
- Implement actual image loading logic in BatchImageLoader.load_image()
- Add file filtering by glob pattern
- Add VALIDATE_INPUTS for path validation
- Add IS_CHANGED for execution control

## Technical Notes

### Graceful Imports Pattern
The package uses try/except for importing modules that require ComfyUI dependencies:
```python
try:
    from .nodes.batch_loader import BatchImageLoader
    NODE_CLASS_MAPPINGS = {"BatchImageLoader": BatchImageLoader}
except ImportError:
    NODE_CLASS_MAPPINGS = {}
```
This allows tests to run without torch/numpy/PIL while maintaining full functionality in ComfyUI.

### ComfyUI Tensor Format
Images must be [B, H, W, C] format with:
- B: Batch dimension (1 for single images)
- H: Height
- W: Width
- C: Channels (3 for RGB)
- dtype: float32
- range: [0.0, 1.0]
