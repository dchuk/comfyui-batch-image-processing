# Phase 3: Batch Iteration - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Process an entire directory by running the workflow once, with each image flowing through separately via queue-per-image pattern. User clicks Queue once and all images process in sequence. Progress display and previews are separate phases (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Iteration state
- In-memory counter that persists while ComfyUI is running (resets on restart)
- Combo dropdown input with "Continue" / "Reset" options controls iteration mode
- Auto-reset when directory path changes (in addition to manual dropdown)

### Queue triggering
- Claude's discretion on whether to use Auto Queue integration or self-queuing via API
- Output a `batch_complete` boolean signal when last image finishes
- Counter wraps back to 0 after last image (allows re-run without manual reset)
- Signal ComfyUI to stop Auto Queue when batch completes (if feasible with API)

### Interruption handling
- On cancel: behavior follows the mode dropdown
  - "Continue" mode: stay at current index, resume from that image next run
  - "Reset" mode: reset to start
- Add status output with values: 'processing', 'completed', 'interrupted'
- Add error handling toggle: "Stop on error" vs "Skip on error"
- Default: Stop on error (safe default — user notices failures immediately)

### Index semantics
- Current index output is 0-based (first image = 0)
- Add 'index' as new output alongside existing 'count' and 'filename'
- Index output as INT only — user converts/formats with other nodes if needed
- Add `start_index` input for resuming from specific position

### Claude's Discretion
- Queue integration approach (Auto Queue vs self-queuing)
- How to signal Auto Queue to stop (depends on ComfyUI API capabilities)
- Internal state management implementation details
- Status output update timing

</decisions>

<specifics>
## Specific Ideas

- Mode dropdown semantics: "Continue" means persist position, "Reset" means start fresh
- The batch_complete signal enables downstream nodes to trigger actions on completion
- start_index input enables resuming partial batches without relying on internal state

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-batch-iteration*
*Context gathered: 2026-02-01*
