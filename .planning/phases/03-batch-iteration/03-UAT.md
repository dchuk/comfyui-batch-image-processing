---
status: diagnosed
phase: 03-batch-iteration
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md]
started: 2026-02-02T03:00:00Z
updated: 2026-02-02T14:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Queue Once Processes All Images
expected: Click "Queue" once with Auto Queue enabled. All images in directory process automatically (one per execution). Queue stops after last image.
result: pass

### 2. Interrupt Processing Mid-Batch
expected: While batch is processing, click Cancel/Interrupt in ComfyUI. Processing stops immediately. On next Queue with Continue mode, resumes from where it left off.
result: pass

### 3. Images Process In Order
expected: Images process in natural sort order (img2 before img10). Each image flows through the full pipeline before the next begins.
result: pass

### 4. Index and Count Outputs Update
expected: INDEX output shows 0-based current position (0, 1, 2...). COUNT shows total images. These update correctly for each image in the batch.
result: issue
reported: "I see the first progress update (1 of 4), but it doesn't change once it goes past the first image during processing"
severity: major

### 5. Reset Mode Starts Fresh
expected: With iteration_mode set to "Reset", running the workflow always starts from image 0, ignoring any previous progress.
result: pass

### 6. Directory Change Resets State
expected: Change the directory path to a different folder. State resets - processing starts from image 0 in the new directory, not continuing from old position.
result: pass
note: Saver path issue discovered (logged separately) - not related to iteration state reset

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Batch iteration works without external dependencies"
  status: failed
  reason: "Discovery during UAT: queue_control.py uses Impact Pack events (impact-add-queue, impact-stop-auto-queue)"
  severity: blocker
  test: pre-testing
  root_cause: "trigger_next_queue() and stop_auto_queue() send Impact Pack-specific events that are ignored without Impact Pack installed"
  artifacts:
    - path: "utils/queue_control.py"
      issue: "Uses impact-add-queue and impact-stop-auto-queue events"
  missing:
    - "Native ComfyUI queue control via POST /prompt API"
  resolution: "Phase 3.1 inserted to implement native queue control"

- truth: "INDEX output updates correctly for each image in the batch"
  status: failed
  reason: "User reported: I see the first progress update (1 of 4), but it doesn't change once it goes past the first image during processing"
  severity: major
  test: 4
  root_cause: "ComfyUI client_id websocket routing - trigger_next_queue() generates new UUID client_id, but frontend has its own client_id. ComfyUI's execution_success uses broadcast=False, so frontend never receives results from programmatic queue submissions."
  artifacts:
    - path: "utils/queue_control.py"
      issue: "Lines 97-102: Creates new client_id for each queue trigger instead of reusing frontend's client_id"
  missing:
    - "Capture and reuse frontend client_id in trigger_next_queue()"
    - "Or use broadcast=True for execution result messages"
  debug_session: ".planning/debug/output-not-updating-batch.md"

- truth: "BatchImageSaver saves to correct output path based on input directory structure"
  status: failed
  reason: "User reported: When input directory is 'input', saver saved to 'output/input/[image_file]' instead of 'output/[image_file]'"
  severity: major
  test: 6
  cross_phase: "Phase 2 - Image Saving"
  root_cause: "Semantic mismatch - INPUT_DIRECTORY outputs folder name as metadata ('input'), but when wired to output_directory it's interpreted as subdirectory to create under ComfyUI output folder"
  artifacts:
    - path: "nodes/batch_loader.py"
      issue: "Line 349: Outputs folder basename as INPUT_DIRECTORY metadata"
    - path: "utils/save_image_utils.py"
      issue: "Lines 157-174: Treats non-empty relative path as intentional subdirectory"
  missing:
    - "Document that INPUT_DIRECTORY is metadata-only, not for wiring to output_directory"
    - "Or modify resolve_output_directory to distinguish metadata vs intentional subdirectory"
  debug_session: ".planning/debug/batch-saver-nested-output-path.md"

