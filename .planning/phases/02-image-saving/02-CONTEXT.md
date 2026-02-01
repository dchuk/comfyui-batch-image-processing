# Phase 2: Image Saving - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Save processed images with customizable output paths and filenames. BatchImageSaver node accepts images and saves them immediately with user-configured naming, format, and overwrite behavior. Creating the iteration mechanism is Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Filename Construction
- Pattern: `{prefix}{original}{suffix}.{ext}` — raw concatenation
- User provides separators in prefix/suffix fields (e.g., prefix `upscaled_` or suffix `_2x`)
- Empty prefix/suffix = no extra characters (no automatic separators)
- Extension replaced by output format (input.png → output.jpg if saving as JPG)

### Format & Quality
- Dropdown with options: "Match original", "PNG", "JPG", "WebP"
- Default: "Match original" (each output matches its input format)
- Quality slider 1-100 for lossy formats (JPG, WebP)
- Default quality: 100 (maximum)
- PNG has no compression options (always lossless, no config needed)

### Output Organization
- When output directory specified: use it directly
- When no output directory: save to ComfyUI output folder with input-folder-named subfolder
  - Example: input `/photos/vacation` → output `ComfyUI/output/vacation/`
- Create non-existent directories automatically (no warning)
- Flat output structure (all images in single folder, no subdirectory mirroring)

### Overwrite Behavior
- Configurable via dropdown: Overwrite / Skip / Rename
- Default: Overwrite (replace existing files)
- Skip mode: log "Skipped: filename.png" to ComfyUI console, continue to next
- Rename mode: simple increment (photo_1.png, photo_2.png) — not zero-padded

### Claude's Discretion
- Node input field ordering and grouping
- Internal error handling approach
- How to detect ComfyUI output folder path

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-image-saving*
*Context gathered: 2026-02-01*
