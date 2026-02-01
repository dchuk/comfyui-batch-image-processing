# Requirements: ComfyUI Batch Image Processing Nodes

**Defined:** 2025-02-01
**Core Value:** Run a pipeline once and have it automatically process every image in a directory, saving each result as it completes with full progress visibility.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Image Loading

- [ ] **LOAD-01**: Node accepts directory path input (relative to ComfyUI input folder)
- [ ] **LOAD-02**: Node loads images from specified directory
- [ ] **LOAD-03**: Node supports glob pattern filtering (e.g., `*.png`, `img_*.jpg`)
- [ ] **LOAD-04**: Images are sorted in natural order (img2 before img10)
- [ ] **LOAD-05**: Node outputs total image count for the directory
- [ ] **LOAD-06**: Node outputs current image filename

### Batch Iteration

- [ ] **ITER-01**: Each image triggers a separate workflow execution (queue-per-image pattern)
- [ ] **ITER-02**: Node outputs current image index (1-based)
- [ ] **ITER-03**: Node outputs total image count
- [ ] **ITER-04**: Processing proceeds through all images in order
- [ ] **ITER-05**: User can interrupt processing via ComfyUI's cancel/interrupt

### Image Saving

- [ ] **SAVE-01**: Node accepts configurable output directory path
- [ ] **SAVE-02**: Output directory defaults to input folder name
- [ ] **SAVE-03**: Node preserves original source image filename
- [ ] **SAVE-04**: Node supports optional filename prefix
- [ ] **SAVE-05**: Node supports optional filename suffix (e.g., `_upscaled`)
- [ ] **SAVE-06**: Node supports PNG output format
- [ ] **SAVE-07**: Node supports JPG output format with quality setting
- [ ] **SAVE-08**: Node supports WebP output format with quality setting
- [ ] **SAVE-09**: Each image is saved immediately after processing (not batched)

### Progress & Monitoring

- [ ] **PROG-01**: Node displays progress bar showing X of Y images processed
- [ ] **PROG-02**: Node displays file list with original filename → saved filename mappings
- [ ] **PROG-03**: File list updates as each image completes
- [ ] **PROG-04**: Node shows basic thumbnail preview of before (input) image
- [ ] **PROG-05**: Node shows basic thumbnail preview of after (output) image

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
| LOAD-01 | TBD | Pending |
| LOAD-02 | TBD | Pending |
| LOAD-03 | TBD | Pending |
| LOAD-04 | TBD | Pending |
| LOAD-05 | TBD | Pending |
| LOAD-06 | TBD | Pending |
| ITER-01 | TBD | Pending |
| ITER-02 | TBD | Pending |
| ITER-03 | TBD | Pending |
| ITER-04 | TBD | Pending |
| ITER-05 | TBD | Pending |
| SAVE-01 | TBD | Pending |
| SAVE-02 | TBD | Pending |
| SAVE-03 | TBD | Pending |
| SAVE-04 | TBD | Pending |
| SAVE-05 | TBD | Pending |
| SAVE-06 | TBD | Pending |
| SAVE-07 | TBD | Pending |
| SAVE-08 | TBD | Pending |
| SAVE-09 | TBD | Pending |
| PROG-01 | TBD | Pending |
| PROG-02 | TBD | Pending |
| PROG-03 | TBD | Pending |
| PROG-04 | TBD | Pending |
| PROG-05 | TBD | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 0
- Unmapped: 25 (pending roadmap creation)

---
*Requirements defined: 2025-02-01*
*Last updated: 2025-02-01 after initial definition*
