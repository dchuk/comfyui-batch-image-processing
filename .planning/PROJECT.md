# ComfyUI Batch Image Processing Nodes

## What This Is

A set of ComfyUI custom nodes for batch processing images through pipelines. Users load a directory of images, run a single pipeline execution that iterates through each image via queue-per-image pattern, and save results with live progress tracking. Shipped v1.0 with full batch iteration, multiple output formats, and real-time UI updates.

## Current State (v1.0 Shipped)

**Shipped:** 2026-02-02
**Lines of code:** 4,372 Python
**Tests:** 212 passing
**Nodes:** BatchImageLoader, BatchImageSaver, BatchProgressFormatter

**Tech stack:** Python, PIL, torch, numpy (ComfyUI-provided packages only)

## Core Value

Run a pipeline once and have it automatically process every image in a directory, saving each result as it completes with full progress visibility.

## Requirements

### Validated

**v1.0 (shipped 2026-02-02):**
- ✓ Batch Image Loader node loads images from a directory path — v1.0
- ✓ Images iterate in filename order (natural sort) — v1.0
- ✓ Queue-per-image pattern executes the downstream pipeline per image — v1.0
- ✓ Each image is saved immediately after processing (not batched at end) — v1.0
- ✓ Batch Image Saver node saves to user-specified output directory — v1.0
- ✓ Output directory defaults to ComfyUI output folder — v1.0
- ✓ Output filename preserves original image filename — v1.0
- ✓ Optional prefix/suffix for output filenames (e.g., `_upscaled`) — v1.0
- ✓ Progress text shows X of Y (Z%) via BatchProgressFormatter — v1.0
- ✓ Basic image preview via OUTPUT_IMAGE passthrough — v1.0
- ✓ Unit tests with mocked ComfyUI context (212 tests) — v1.0
- ✓ No dependencies on other ComfyUI node projects — v1.0
- ✓ Follow ComfyUI node development best practices — v1.0
- ✓ Live UI updates during batch iterations via PromptServer broadcasts — v1.0

### Active

(No active requirements — v1.0 milestone complete)

### Out of Scope

- Rich frontend UI with modal previews — deferred to v2, current wiring approach works well
- Click-to-expand zoom functionality — requires frontend component
- Resume capability with state persistence — v2 feature (Continue mode exists but doesn't survive restarts)
- Index range selection — v2 feature
- Recursive subfolder support — v2 feature

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
| Queue-per-image pattern (not in-graph loops) | Simpler, crash-safe, works with any downstream nodes | ✓ Good |
| Python-only initially | Reduces complexity, frontend can be added later | ✓ Good |
| Native HTTP POST queue control | Eliminated Impact Pack dependency using urllib.request | ✓ Good |
| Unit tests with mocks | Practical for CI/CD, 212 tests passing | ✓ Good |
| PromptServer.send_sync with sid=None | Broadcasts to all clients, fixes batch UI updates | ✓ Good |
| Image passthrough (same tensor reference) | Efficient, no copy overhead | ✓ Good |
| Raw filename concatenation | User provides separators in prefix/suffix | ✓ Good |

---
*Last updated: 2026-02-02 after v1.0 milestone*
