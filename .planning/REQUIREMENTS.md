# Requirements: ComfyUI Batch Image Processing Nodes

**Defined:** 2025-02-01
**Core Value:** Run a pipeline once and have it automatically process every image in a directory, saving each result as it completes with full progress visibility.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Image Loading

- [x] **LOAD-01**: Node accepts directory path input (relative to ComfyUI input folder) ✓
- [x] **LOAD-02**: Node loads images from specified directory ✓
- [x] **LOAD-03**: Node supports glob pattern filtering (e.g., `*.png`, `img_*.jpg`) ✓
- [x] **LOAD-04**: Images are sorted in natural order (img2 before img10) ✓
- [x] **LOAD-05**: Node outputs total image count for the directory ✓
- [x] **LOAD-06**: Node outputs current image filename ✓

### Batch Iteration

- [x] **ITER-01**: Each image triggers a separate workflow execution (queue-per-image pattern) ✓
- [x] **ITER-02**: Node outputs current image index (0-based per CONTEXT.md decision) ✓
- [x] **ITER-03**: Node outputs total image count ✓
- [x] **ITER-04**: Processing proceeds through all images in order ✓
- [x] **ITER-05**: User can interrupt processing via ComfyUI's cancel/interrupt ✓

### Image Saving

- [x] **SAVE-01**: Node accepts configurable output directory path ✓
- [x] **SAVE-02**: Output directory defaults to input folder name ✓
- [x] **SAVE-03**: Node preserves original source image filename ✓
- [x] **SAVE-04**: Node supports optional filename prefix ✓
- [x] **SAVE-05**: Node supports optional filename suffix (e.g., `_upscaled`) ✓
- [x] **SAVE-06**: Node supports PNG output format ✓
- [x] **SAVE-07**: Node supports JPG output format with quality setting ✓
- [x] **SAVE-08**: Node supports WebP output format with quality setting ✓
- [x] **SAVE-09**: Each image is saved immediately after processing (not batched) ✓

### Progress & Monitoring

*Refined during /gsd:discuss-phase - user chose wiring-based approach over custom UI components*

- [x] **PROG-01**: Helper node formats progress as "X of Y (Z%)" text for wiring to any text display ✓
- [x] **PROG-02**: BatchImageSaver outputs saved filename for per-image mapping visibility ✓
- [x] **PROG-03**: BatchImageSaver outputs saved path for full path access ✓
- [x] **PROG-04**: BatchImageSaver passes through input image for wiring to preview nodes ✓
- [x] **PROG-05**: User can wire OUTPUT_IMAGE to ComfyUI's PreviewImage for before/after previews ✓

## Quality Standards

Standards that apply to ALL phases. Not discrete requirements - these govern how we build.

| Standard | Description |
|----------|-------------|
| ComfyUI best practices | Follow official node development patterns |
| Tensor format | Use standard [B,H,W,C] image tensor format |
| Cache invalidation | Implement IS_CHANGED for file-based inputs |
| Memory management | No accumulation during long batches; cleanup between iterations |
| Test coverage | Unit tests with mocked ComfyUI context for each phase's code |
| Independence | No external ComfyUI node dependencies |
| Minimal dependencies | Use only ComfyUI-provided packages (PIL, torch, numpy) |

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Loading

- **LOAD-07**: Index range selection (process only images 50-100)
- **LOAD-08**: Companion text file loading (for ML datasets)
- **LOAD-09**: Recursive subfolder support

### Resume Capability

- **RSME-01**: Option to start fresh or continue from last position
- **RSME-02**: State persistence survives ComfyUI restarts
- **RSME-03**: Skip images where output file already exists

### Enhanced Preview

- **PREV-01**: Rich frontend with click-to-expand modal
- **PREV-02**: Zoom capability in modal view
- **PREV-03**: Side-by-side comparison slider

### Advanced Saving

- **SAVE-10**: Metadata preservation (EXIF from source)
- **SAVE-11**: Output directory mirroring (recreate source folder structure)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| In-graph loops with state | ComfyUI execution model makes stateful loops fragile. Use queue-per-image instead. |
| Parallel batch loading (all images in memory) | VRAM exhaustion risk. Load one, process, save, release, next. |
| Automatic image resizing | Silently modifying images is surprising behavior. Fail with clear error if incompatible. |
| Overwriting source files | Data loss risk too high. Always write to separate output directory. |
| Counter-only filenames | Loses traceability. Original filename + optional prefix/suffix is the pattern. |
| Complex regex for filename matching | Glob patterns sufficient. Regex is error-prone for users. |
| Dependencies on other node projects | Must be self-contained. Can study patterns but implement independently. |
| Integration tests in live ComfyUI | Unit tests with mocks sufficient for v1. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LOAD-01 | Phase 1 | Complete |
| LOAD-02 | Phase 1 | Complete |
| LOAD-03 | Phase 1 | Complete |
| LOAD-04 | Phase 1 | Complete |
| LOAD-05 | Phase 1 | Complete |
| LOAD-06 | Phase 1 | Complete |
| ITER-01 | Phase 3 | Complete |
| ITER-02 | Phase 3 | Complete |
| ITER-03 | Phase 3 | Complete |
| ITER-04 | Phase 3 | Complete |
| ITER-05 | Phase 3 | Complete |
| SAVE-01 | Phase 2 | Complete |
| SAVE-02 | Phase 2 | Complete |
| SAVE-03 | Phase 2 | Complete |
| SAVE-04 | Phase 2 | Complete |
| SAVE-05 | Phase 2 | Complete |
| SAVE-06 | Phase 2 | Complete |
| SAVE-07 | Phase 2 | Complete |
| SAVE-08 | Phase 2 | Complete |
| SAVE-09 | Phase 2 | Complete |
| PROG-01 | Phase 4 | Complete |
| PROG-02 | Phase 4 | Complete |
| PROG-03 | Phase 4 | Complete |
| PROG-04 | Phase 4 | Complete |
| PROG-05 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0

---
*Requirements defined: 2025-02-01*
*Last updated: 2026-02-02 - All v1 requirements complete*
