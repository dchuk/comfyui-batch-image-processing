---
phase: 02-image-saving
plan: 01
subsystem: image-output
tags: [comfyui, pil, image-saving, output-node]
requires:
  - 01-foundation
provides:
  - BatchImageSaver node
  - save_image_utils module
affects:
  - 02-02-integration
  - 03-iteration
tech-stack:
  added: []
  patterns: [OUTPUT_NODE, tensor-to-pil, format-specific-saving]
key-files:
  created:
    - utils/save_image_utils.py
    - nodes/batch_saver.py
    - tests/test_save_image_utils.py
    - tests/test_batch_saver.py
  modified:
    - __init__.py
    - nodes/__init__.py
    - utils/__init__.py
    - tests/conftest.py
decisions:
  - id: raw-filename-concat
    choice: "Raw concatenation: {prefix}{original}{suffix}.{ext}"
    context: "User decision from 02-CONTEXT.md - user includes separators in prefix/suffix"
  - id: quality-100-default
    choice: "Default quality=100, capped at 95 for JPEG"
    context: "User wants maximum quality by default; PIL docs recommend <=95 for JPEG"
  - id: match-original-default
    choice: "'Match original' as default format option"
    context: "Preserves input format unless explicitly changed"
metrics:
  duration: 8m
  completed: 2026-02-01
---

# Phase 2 Plan 1: BatchImageSaver Node Summary

Save utilities and BatchImageSaver node with PNG/JPG/WebP format support, quality control, and customizable filename/overwrite handling.

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Create save image utilities | d4b7819 | utils/save_image_utils.py, tests/test_save_image_utils.py |
| 2 | Create BatchImageSaver node | f838dcb | nodes/batch_saver.py, __init__.py, nodes/__init__.py |
| 3 | Add tests for BatchImageSaver | caa3fb5 | tests/test_batch_saver.py, tests/conftest.py |

## Implementation Summary

### Save Image Utilities (utils/save_image_utils.py)

Five utility functions for image saving operations:

1. **tensor_to_pil(tensor)** - Convert ComfyUI [B,H,W,C] tensor to PIL Image
   - Handles batch dimension (squeeze if 4D)
   - Clips values to [0, 255] range
   - Returns RGB PIL Image

2. **save_with_format(img, filepath, format, quality)** - Format-specific saving
   - PNG: compress_level=4
   - JPG: quality capped at 95, RGBA converted to RGB
   - WebP: lossless at quality=100

3. **construct_filename(original_basename, prefix, suffix, extension)** - Build output filename
   - Raw concatenation: `{prefix}{original}{suffix}.{extension}`
   - No automatic separators

4. **handle_existing_file(filepath, mode)** - Handle existing files
   - Overwrite: replace
   - Skip: log and return False
   - Rename: increment counter (photo_1.png, photo_2.png)

5. **resolve_output_directory(output_dir, source_dir, default_output_func)** - Resolve output path
   - Explicit directory: use directly
   - Empty: ComfyUI output + source folder basename
   - Creates directory if needed

### BatchImageSaver Node (nodes/batch_saver.py)

ComfyUI OUTPUT_NODE for saving processed images:

**Inputs:**
- `image` (required): IMAGE tensor from pipeline
- `output_format` (required): Match original / PNG / JPG / WebP
- `quality` (required): 1-100, default 100
- `overwrite_mode` (required): Overwrite / Skip / Rename
- `output_directory` (optional): Custom output path
- `filename_prefix` (optional): Prefix for filename
- `filename_suffix` (optional): Suffix for filename
- `original_filename` (optional): Base name from BatchImageLoader
- `source_directory` (optional): For default subfolder naming
- `original_format` (optional): For "Match original" mode

**Returns:** `{"ui": {"images": [{filename, subfolder, type}]}}`

### Test Coverage

53 tests total:
- 29 tests for save_image_utils.py (all utility functions)
- 24 tests for batch_saver.py (INPUT_TYPES, attributes, save operations)

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Raw filename concatenation** - User provides separators in prefix/suffix
2. **Quality defaults to 100** - Maximum quality by default
3. **JPEG quality capped at 95** - Per PIL documentation recommendation
4. **WebP lossless at 100** - Quality=100 triggers lossless mode
5. **Graceful imports** - try/except pattern for torch/numpy/PIL

## Verification Results

All verification criteria met:
- [x] All utility functions in save_image_utils.py work correctly
- [x] BatchImageSaver node follows ComfyUI OUTPUT_NODE pattern
- [x] All tests pass: 53/53 passed
- [x] Node can save images in PNG, JPG, and WebP formats with quality control

## Next Phase Readiness

Ready for Phase 2 Plan 2 (integration):
- BatchImageSaver fully functional
- Can connect BASENAME from BatchImageLoader to original_filename input
- All format and overwrite options working
