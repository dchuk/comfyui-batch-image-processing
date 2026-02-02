# Phase 4: Progress & Monitoring - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Users have visibility into batch progress with file mappings and image previews. This phase adds outputs and a helper node to expose progress information—it does NOT add new batch processing capabilities.

**What exists from Phase 3/3.1:**
- BatchImageLoader outputs: INDEX (0-based), TOTAL_COUNT, STATUS ("processing"/"completed"), BATCH_COMPLETE (boolean), FILENAME
- Console logging already shows each image as it processes
- Queue-per-image pattern with native HTTP triggering (no Impact Pack dependency)

</domain>

<decisions>
## Implementation Decisions

### Progress indicator
- Use existing node outputs—no UI panel or separate display system
- Keep INDEX and TOTAL_COUNT as separate outputs (user wires to text display if needed)
- No new progress-specific outputs on BatchImageLoader (INDEX/TOTAL_COUNT/STATUS already sufficient)
- Console logging is sufficient for persistence—no summary file needed

### File mapping
- BatchImageSaver outputs SAVED_FILENAME and SAVED_PATH separately
- Each image's mapping shown as it processes—no cumulative list at batch end
- No mapping log file

### Thumbnail previews
- Use existing ComfyUI PreviewImage nodes—no custom preview node
- BatchImageSaver passes through input IMAGE as OUTPUT_IMAGE for downstream preview wiring
- No re-loading of saved file for verification

### Integration approach
- Extend existing nodes (BatchImageSaver needs new outputs)
- Add one helper node: progress text formatter
- Progress formatter outputs "X of Y (Z%)" format (e.g., "3 of 10 (30%)")

### Claude's Discretion
- Exact naming of new outputs (SAVED_FILENAME vs OUTPUT_FILENAME, etc.)
- Progress formatter node name and category placement
- Whether to add percentage as separate output or just include in formatted string
- Error handling if TOTAL_COUNT is 0 (avoid divide-by-zero)

</decisions>

<specifics>
## Specific Ideas

- Progress format should be "3 of 10 (30%)" with percentage included
- BatchImageSaver passthrough keeps image tensor unchanged—efficient, no re-encoding
- Formatter takes INDEX + TOTAL_COUNT as inputs, outputs formatted string

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-progress-monitoring*
*Context gathered: 2026-02-02*
