# Roadmap: ComfyUI Batch Image Processing Nodes

## Overview

This roadmap delivers a set of ComfyUI custom nodes that enable batch processing of images through any pipeline. The journey starts with foundational node infrastructure (proper registration, tensor handling), then builds the core loader and saver nodes, implements the queue-per-image execution pattern for iteration, and finishes with progress tracking and previews. Each phase delivers independently testable functionality.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Node infrastructure, basic image loading
- [x] **Phase 2: Image Saving** - Batch saver with format options and filename customization
- [x] **Phase 3: Batch Iteration** - Queue-per-image execution pattern
- [x] **Phase 3.1: Native Queue Control** - Remove Impact Pack dependency (INSERTED)
- [x] **Phase 4: Progress & Monitoring** - Progress display and image previews
- [ ] **Phase 5: Live UI Updates** - Fix frontend updates during batch iteration (from UAT)

## Phase Details

### Phase 1: Foundation
**Goal**: Users can load images from a directory with a properly registered ComfyUI node
**Depends on**: Nothing (first phase)
**Requirements**: LOAD-01, LOAD-02, LOAD-03, LOAD-04, LOAD-05, LOAD-06
**Success Criteria** (what must be TRUE):
  1. BatchImageLoader node appears in ComfyUI's "Add Node" menu under a custom category
  2. User can specify a directory path and see images loaded in natural sort order (img2 before img10)
  3. User can filter images using glob patterns (e.g., `*.png`)
  4. Node outputs current image, total count, and current filename as separate outputs
**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md - Project structure, node registration, utilities (natural sort, image loading)
- [x] 01-02-PLAN.md - Complete BatchImageLoader implementation with filtering and validation

### Phase 2: Image Saving
**Goal**: Users can save processed images with customizable output paths and filenames
**Depends on**: Phase 1
**Requirements**: SAVE-01, SAVE-02, SAVE-03, SAVE-04, SAVE-05, SAVE-06, SAVE-07, SAVE-08, SAVE-09
**Success Criteria** (what must be TRUE):
  1. BatchImageSaver node accepts output directory and saves images immediately upon receiving them
  2. Output filenames preserve the original source filename with optional prefix/suffix
  3. User can save as PNG, JPG (with quality), or WebP (with quality)
  4. When no output directory specified, images save to a folder named after the input directory
**Plans:** 2 plans

Plans:
- [x] 02-01-PLAN.md - Save image utilities and BatchImageSaver node implementation
- [x] 02-02-PLAN.md - Node registration and integration verification

### Phase 3: Batch Iteration
**Goal**: Users can process an entire directory by running the workflow once, with each image flowing through separately
**Depends on**: Phase 1, Phase 2
**Requirements**: ITER-01, ITER-02, ITER-03, ITER-04, ITER-05
**Success Criteria** (what must be TRUE):
  1. Clicking "Queue" once triggers processing of all images in the directory (one workflow execution per image via Auto Queue)
  2. User can interrupt processing at any time via ComfyUI's cancel/interrupt
  3. Each image processes in order through the full pipeline before the next begins
  4. Nodes correctly output current index (0-based) and total count for each iteration
**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md - Iteration state management and queue control utilities
- [x] 03-02-PLAN.md - Extend BatchImageLoader with iteration support

### Phase 3.1: Native Queue Control (INSERTED)
**Goal**: Batch iteration works without any external node dependencies (no Impact Pack required)
**Depends on**: Phase 3
**Requirements**: Derived from Phase 3 gap - current implementation uses Impact Pack events
**Success Criteria** (what must be TRUE):
  1. BatchImageLoader triggers next queue execution using native ComfyUI API (POST /prompt)
  2. Batch completion stops iteration without requiring Impact Pack's stop-auto-queue event
  3. All existing Phase 3 tests continue to pass
  4. No external custom node dependencies required for batch iteration
**Plans:** 1 plan

Plans:
- [x] 03.1-01-PLAN.md - Native HTTP POST queue control, hidden inputs for workflow access

### Phase 4: Progress & Monitoring
**Goal**: Users have visibility into batch progress with file mappings and image previews
**Depends on**: Phase 3.1
**Requirements**: PROG-01, PROG-02, PROG-03, PROG-04, PROG-05
**Success Criteria** (what must be TRUE):
  1. User sees a progress indicator showing "X of Y images processed"
  2. User sees a list of original filename to saved filename mappings that updates as each image completes
  3. User sees thumbnail previews of input (before) and output (after) images
**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md - Extend BatchImageSaver with passthrough outputs, create BatchProgressFormatter node
- [x] 04-02-PLAN.md - Node registration and comprehensive tests

### Phase 5: Live UI Updates
**Goal**: Frontend UI updates in real-time during batch processing iterations
**Depends on**: Phase 4
**Requirements**: Derived from UAT gaps - UI shows stale data after first iteration
**Success Criteria** (what must be TRUE):
  1. INDEX, TOTAL_COUNT outputs update visually for each batch iteration
  2. Progress text (BatchProgressFormatter) updates for each image processed
  3. Preview nodes show current image, not just first image
  4. SAVED_FILENAME and SAVED_PATH update for each iteration
**Root Cause**: trigger_next_queue() generates new client_id; ComfyUI sends execution_success with broadcast=False to original client_id only
**Plans:** 1 plan

Plans:
- [ ] 05-01-PLAN.md - Broadcast UI updates via PromptServer.send_sync with sid=None

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 3.1 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-02-01 |
| 2. Image Saving | 2/2 | Complete | 2026-02-01 |
| 3. Batch Iteration | 2/2 | Complete | 2026-02-01 |
| 3.1 Native Queue Control | 1/1 | Complete | 2026-02-02 |
| 4. Progress & Monitoring | 2/2 | Complete | 2026-02-02 |
| 5. Live UI Updates | 0/1 | Planned | - |

## Documentation Notes

**INPUT_DIRECTORY Output Clarification:**
The `INPUT_DIRECTORY` output from BatchImageLoader is metadata-only (folder name). It should NOT be wired to BatchImageSaver's `output_directory` input, as this creates nested directories (e.g., `output/input/file.png`). Leave `output_directory` empty to save directly to ComfyUI's output folder.

---
*Roadmap created: 2025-02-01*
*Last updated: 2026-02-02 - Phase 5 planned*
