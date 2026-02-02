---
status: diagnosed
phase: 04-progress-monitoring
source: [04-01-SUMMARY.md, 04-02-SUMMARY.md]
started: 2026-02-02T14:05:00Z
updated: 2026-02-02T14:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. BatchProgressFormatter Node Available
expected: In ComfyUI, right-click to add node. Search for "Batch Progress Formatter" or browse the "batch_processing" category. Node appears and can be added to workflow.
result: pass

### 2. Progress Text Shows Correct Format
expected: Connect BatchImageLoader INDEX→index and TOTAL_COUNT→total_count to BatchProgressFormatter. Output shows "1 of N (X%)" format, updating correctly for each image.
result: issue
reported: "Format is correct (shows '1 of 10 (10%)') but doesn't update as iterations continue - same as Phase 3 Test 4 INDEX issue"
severity: major
related: "Phase 3 Test 4 - INDEX not updating"

### 3. BatchImageSaver Passes Image Through
expected: Connect BatchImageSaver OUTPUT_IMAGE to a PreviewImage node. The processed image appears in preview after save (or even if save is skipped).
result: issue
reported: "First processed image shows in preview, but no subsequent images on further iterations show up"
severity: major
related: "Same root cause as INDEX not updating - UI not refreshing between iterations"

### 4. Saved Filename Output Works
expected: Connect BatchImageSaver SAVED_FILENAME to a text display. Shows the actual saved filename (e.g., "photo_processed.png").
result: issue
reported: "Only the first saved_filename is shown"
severity: major
related: "Same root cause - outputs not updating between iterations"

### 5. Saved Path Output Works
expected: Connect BatchImageSaver SAVED_PATH to a text display. Shows the full file path where image was saved.
result: issue
reported: "Works for the first image but not for any other images in the loop"
severity: major
related: "Same root cause - outputs not updating between iterations"

## Summary

total: 5
passed: 1
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "Progress text updates correctly for each image in batch"
  status: failed
  reason: "User reported: Format correct but doesn't update as iterations continue - same root cause as Phase 3 Test 4"
  severity: major
  test: 2
  root_cause: "Same as Phase 3 Test 4 - ComfyUI client_id websocket routing prevents frontend updates from programmatic queue submissions"
  related: "Phase 3 Test 4"
  debug_session: ".planning/debug/output-not-updating-batch.md"

- truth: "Preview image updates for each iteration"
  status: failed
  reason: "User reported: First processed image shows in preview, but no subsequent images on further iterations show up"
  severity: major
  test: 3
  root_cause: "Same as Phase 3 Test 4 - ComfyUI client_id websocket routing + known PreviewImage frontend bug in v1.13.1/1.13.2"
  related: "Phase 3 Test 4"
  debug_session: ".planning/debug/output-not-updating-batch.md"

- truth: "SAVED_FILENAME updates for each iteration"
  status: failed
  reason: "User reported: Only the first saved_filename is shown"
  severity: major
  test: 4
  root_cause: "Same as Phase 3 Test 4 - ComfyUI client_id websocket routing"
  related: "Phase 3 Test 4"
  debug_session: ".planning/debug/output-not-updating-batch.md"

- truth: "SAVED_PATH updates for each iteration"
  status: failed
  reason: "User reported: Works for the first image but not for any other images in the loop"
  severity: major
  test: 5
  root_cause: "Same as Phase 3 Test 4 - ComfyUI client_id websocket routing"
  related: "Phase 3 Test 4"
  debug_session: ".planning/debug/output-not-updating-batch.md"
