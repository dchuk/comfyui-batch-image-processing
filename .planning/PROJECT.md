# ComfyUI Batch Image Processing Nodes

## What This Is

A set of ComfyUI custom nodes for batch processing images through pipelines. Users load a directory of images, run a single pipeline execution that iterates through each image, and save results with progress tracking. Focused specifically on the batch processing workflow - simple, intuitive, no external node dependencies.

## Core Value

Run a pipeline once and have it automatically process every image in a directory, saving each result as it completes with full progress visibility.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Batch Image Loader node loads images from a directory path
- [ ] Images iterate in filename order
- [ ] Graph-level looping executes the downstream pipeline per image
- [ ] Each image is saved immediately after processing (not batched at end)
- [ ] Batch Image Saver node saves to user-specified output directory
- [ ] Output directory defaults to input folder name
- [ ] Output filename preserves original image filename
- [ ] Optional prefix/suffix for output filenames (e.g., `_upscaled`)
- [ ] File list displays original → saved filename mappings as processing completes
- [ ] Progress bar shows X of Y images processed
- [ ] Resume capability: option to start fresh or continue from last run
- [ ] Resume detection via existing output files or progress state
- [ ] Basic image preview (before/after thumbnails)
- [ ] Unit tests with mocked ComfyUI context
- [ ] No dependencies on other ComfyUI node projects
- [ ] Follow ComfyUI node development best practices

### Out of Scope

- Rich frontend UI with modal previews — deferred to future phase, start Python-only
- Click-to-expand zoom functionality — requires frontend component
- Dependencies on Impact Pack or other node projects — implement looping pattern independently
- Integration tests within live ComfyUI — unit tests with mocks sufficient for v1

## Context

**Technical environment:**
- ComfyUI node ecosystem
- Python nodes with optional JavaScript frontend extensions
- Images stored in ComfyUI's input folder structure
- Output to ComfyUI's output folder or user-specified paths

**Looping approach:**
- ComfyUI doesn't have native graph-level looping
- Impact Pack and similar projects implement execution control patterns
- We'll study these patterns and implement our own looping mechanism
- No runtime dependency on external node projects

**Resume capability:**
- Prefer ComfyUI-integrated state storage
- Fallback: detect existing output files to determine which inputs are done
- Alternative fallback: .progress file in output directory

**User's workflow:**
- Has a directory of images in ComfyUI input folder
- Wants to run an upscaling pipeline on all images
- Needs to be able to interrupt and resume large batches
- Wants visibility into progress as each image completes

## Constraints

- **Dependencies**: Minimize external dependencies; use what ComfyUI already provides (PIL, torch, numpy). Additional dependencies require explicit approval.
- **Frontend**: Start Python-only for v1. Frontend enhancements are a future phase.
- **Independence**: No runtime dependencies on other ComfyUI node projects (Impact Pack, etc.). Can study their patterns but must implement independently.
- **Testing**: Unit tests with mocked ComfyUI execution context. No requirement for integration tests in live ComfyUI.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Graph-level looping (not internal iteration) | Allows each image to flow through full pipeline per iteration, enables per-image save | — Pending |
| Python-only initially | Reduces complexity, frontend can be added later | — Pending |
| User specifies output directory | Flexibility, with input folder name as sensible default | — Pending |
| Unit tests with mocks | Practical for CI/CD, doesn't require ComfyUI installation | — Pending |
| Study Impact Pack patterns | Good reference for execution control, implement independently | — Pending |

---
*Last updated: 2025-02-01 after initialization*
