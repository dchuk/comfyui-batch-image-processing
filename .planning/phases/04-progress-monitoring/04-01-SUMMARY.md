---
phase: 04-progress-monitoring
plan: 01
subsystem: progress-visibility
tags: [comfyui-nodes, passthrough, progress-formatting]

dependency_graph:
  requires:
    - "02-01: BatchImageSaver foundation"
    - "01-01: BatchImageLoader INDEX and TOTAL_COUNT outputs"
  provides:
    - "BatchImageSaver passthrough outputs (IMAGE, STRING, STRING)"
    - "BatchProgressFormatter node for human-readable progress"
  affects:
    - "04-02: Package exports and __init__.py registration"
    - "Downstream workflows needing image passthrough"

tech_stack:
  added: []
  patterns:
    - "OUTPUT_NODE with RETURN_TYPES pattern (ui + result dict)"
    - "forceInput for required wire connections"

key_files:
  created:
    - path: "nodes/progress_formatter.py"
      purpose: "New node for formatting batch progress as string"
  modified:
    - path: "nodes/batch_saver.py"
      changes: "Added RETURN_TYPES, RETURN_NAMES, result tuples"

decisions:
  - id: "04-01-01"
    choice: "Image passthrough uses same tensor reference (no copy)"
    rationale: "Efficient memory usage; image data is unchanged"
  - id: "04-01-02"
    choice: "Skip mode returns empty strings but still passes image"
    rationale: "Enables downstream preview even when save is skipped"
  - id: "04-01-03"
    choice: "Percentage uses int() truncation not round()"
    rationale: "Matches plan specification; 33.33% becomes 33%"

metrics:
  duration: "93 seconds"
  completed: "2026-02-02"
---

# Phase 04 Plan 01: Progress Visibility Outputs Summary

**One-liner:** BatchImageSaver now passes image through with filename/path outputs; BatchProgressFormatter formats progress as "X of Y (Z%)"

## What Was Built

### 1. BatchImageSaver Passthrough Outputs

Extended the existing BatchImageSaver node to output data for downstream wiring:

```python
RETURN_TYPES = ("IMAGE", "STRING", "STRING")
RETURN_NAMES = ("OUTPUT_IMAGE", "SAVED_FILENAME", "SAVED_PATH")
```

**Output behavior by mode:**
| Mode | OUTPUT_IMAGE | SAVED_FILENAME | SAVED_PATH |
|------|--------------|----------------|------------|
| Normal save | Input tensor (passthrough) | "photo.png" | "/full/path/photo.png" |
| Skip | Input tensor (passthrough) | "" | "" |
| Rename | Input tensor (passthrough) | "photo_1.png" | "/full/path/photo_1.png" |

The image is always passed through (same tensor reference, no copy), enabling downstream PreviewImage nodes even when save is skipped.

### 2. BatchProgressFormatter Node

New utility node that formats batch progress for display:

```python
class BatchProgressFormatter:
    CATEGORY = "batch_processing"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("PROGRESS_TEXT",)
    FUNCTION = "format_progress"
    OUTPUT_NODE = False
```

**Input/Output examples:**
| index | total_count | Output |
|-------|-------------|--------|
| 0 | 10 | "1 of 10 (10%)" |
| 2 | 10 | "3 of 10 (30%)" |
| 9 | 10 | "10 of 10 (100%)" |
| 0 | 3 | "1 of 3 (33%)" |
| 0 | 0 | "1 of 1 (100%)" |

**Key features:**
- `forceInput: True` on both inputs (requires wiring from BatchImageLoader)
- 0-based to 1-based index conversion for human display
- Divide-by-zero protection: `safe_total = max(1, total_count)`
- Integer percentage truncation (not rounded)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 824d66c | feat | add passthrough outputs to BatchImageSaver |
| 436e515 | feat | create BatchProgressFormatter node |

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| 04-01-01 | Image passthrough uses same tensor reference | Efficient; no memory duplication |
| 04-01-02 | Skip mode passes image with empty strings | Preview works even without save |
| 04-01-03 | Percentage uses truncation not rounding | Per specification; 33.33% -> 33% |

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

```
BatchImageSaver:
  RETURN_TYPES = ("IMAGE", "STRING", "STRING") - PASS
  RETURN_NAMES = ("OUTPUT_IMAGE", "SAVED_FILENAME", "SAVED_PATH") - PASS
  "result" key count: 2 (normal + skip) - PASS

BatchProgressFormatter:
  CATEGORY = "batch_processing" - PASS
  RETURN_TYPES = ("STRING",) - PASS
  OUTPUT_NODE = False - PASS
  format_progress(4, 10) = ("5 of 10 (50%)",) - PASS
  format_progress(0, 5) = ("1 of 5 (20%)",) - PASS
  format_progress(0, 0) = ("1 of 1 (100%)",) - PASS (divide-by-zero protection)
```

## Next Phase Readiness

**Plan 04-02:** Package exports and registration
- BatchProgressFormatter needs to be exported from `nodes/__init__.py`
- NODE_CLASS_MAPPINGS needs BatchProgressFormatter registration
- No blockers identified
