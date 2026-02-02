---
status: diagnosed
trigger: "When input directory is 'input', BatchImageSaver creates output/input/[filename] instead of output/[filename]"
created: 2026-02-02T12:00:00Z
updated: 2026-02-02T12:01:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - output_directory receives folder NAME from loader, resolve_output_directory treats any non-empty string as intentional subdirectory
test: Traced code path through batch_saver.py and save_image_utils.py
expecting: Confirmed behavior matches this hypothesis
next_action: Return root cause diagnosis

## Symptoms

expected: When input_directory="input" and output_directory is default/empty, files should save to "output/[filename].png"
actual: Files save to "output/input/[filename].png" - nested structure
errors: None - functional but incorrect path
reproduction: Set input_directory to "input" folder name, leave output_directory as default
started: Unknown - discovered during UAT testing

## Eliminated

## Evidence

- timestamp: 2026-02-02T12:00:30Z
  checked: nodes/batch_saver.py lines 163-166
  found: BatchImageSaver calls resolve_output_directory(output_directory, "", get_default_output) with source_dir="" (empty)
  implication: The source_dir parameter that would trigger "ComfyUI output + source folder name" behavior is never populated

- timestamp: 2026-02-02T12:00:45Z
  checked: utils/save_image_utils.py lines 157-174 (resolve_output_directory function)
  found: When output_dir is non-empty AND not absolute path, it joins comfy_output + output_dir. "input" is a folder name, not absolute.
  implication: output_dir="input" becomes os.path.join(comfy_output, "input") = "output/input"

- timestamp: 2026-02-02T12:01:00Z
  checked: nodes/batch_loader.py line 349
  found: INPUT_DIRECTORY output is os.path.basename(directory) which returns just the folder name like "input"
  implication: When wired to saver, this folder name is treated as a subdirectory path, not metadata

## Resolution

root_cause: Semantic mismatch between BatchImageLoader.INPUT_DIRECTORY output and BatchImageSaver.output_directory input interpretation.

BatchImageLoader outputs INPUT_DIRECTORY as the folder NAME (e.g., "input") for informational/metadata purposes.
BatchImageSaver's resolve_output_directory() interprets ANY non-empty, non-absolute string as an intentional subdirectory path to create.

When INPUT_DIRECTORY ("input") is wired to output_directory, resolve_output_directory() at line 162-167 executes:
```python
if not os.path.isabs(stripped):  # "input" is not absolute
    comfy_output = default_output_func()  # Returns "/path/to/ComfyUI/output"
    resolved = os.path.join(comfy_output, stripped)  # = "/path/to/ComfyUI/output/input"
```

The code works exactly as designed - the bug is in the WIRING EXPECTATION, not the code logic.

fix:
verification:
files_changed: []
