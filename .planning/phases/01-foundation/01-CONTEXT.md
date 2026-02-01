# Phase 1: Foundation - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can load images from a directory with a properly registered ComfyUI node. The BatchImageLoader node appears in ComfyUI's "Add Node" menu, accepts a directory path with optional glob filtering, loads images in natural sort order, and outputs the current image along with count and filename metadata. Saving, iteration control, and progress display are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Directory input
- Text field with browse button for folder selection
- Default to ComfyUI's standard input folder
- Validate on queue (not immediate) — fail with clear error if path invalid
- No preview of matched files in the node UI

### Filter behavior
- Dropdown with preset options (PNG, JPG, All images) plus custom pattern option
- Default pattern: `*.png,*.jpg,*.jpeg,*.webp` (common image formats)
- Error with clear message when zero files match
- Skip non-image files silently (don't error on corrupt/unsupported files that match pattern)

### Node outputs
- IMAGE: Standard ComfyUI image tensor (no extra metadata)
- TOTAL_COUNT: Integer count of matched images
- CURRENT_INDEX: 1-based index (first image = 1)
- FILENAME: Full filename with extension (e.g., "image.png")
- BASENAME: Filename without extension (e.g., "image")
- No full path output — directory is known from input

### Sort behavior
- Natural sort ascending only (img2 before img10)
- No user-selectable sort options or reverse toggle
- Case-insensitive sorting
- Top-level directory only (no recursive subdirectory scanning)

### Claude's Discretion
- Node category name in ComfyUI's Add Node menu
- Exact widget layout and spacing
- Internal error message wording
- How to implement browse button (ComfyUI patterns)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard ComfyUI node implementation approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-02-01*
