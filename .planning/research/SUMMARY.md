# Research Summary: ComfyUI Batch Image Processing Custom Nodes

**Project:** ComfyUI Batch Image Processing
**Research Completed:** 2026-02-01
**Overall Confidence:** HIGH

---

## Executive Summary

ComfyUI custom nodes for batch image processing should follow a **queue-per-image execution model** using ComfyUI's native Auto Queue mechanism. This is simpler and more robust than in-graph looping approaches used by Impact Pack and other solutions. Each image is processed in a separate workflow execution cycle, enabling immediate saves (crash-safe), natural resume points, and compatibility with any downstream processing nodes without special loop support.

The recommended architecture uses three core components: BatchImageLoader (directory scanning with state tracking), BatchImageSaver (output with filename preservation), and ProgressTracker (JSON-based state persistence). This approach leverages ComfyUI's built-in dependencies (PyTorch, PIL, NumPy) and requires no external node pack dependencies.

Critical risks center on ComfyUI's execution model nuances: tensor format must be [B,H,W,C] always, memory cleanup is mandatory for long batches, and the IS_CHANGED classmethod is essential for proper cache invalidation. Node registration requires exact boilerplate (tuples with trailing commas, specific class attributes) or nodes silently fail to register.

---

## Key Findings

### From STACK.md: Technology and Implementation Patterns

**Core Technologies (HIGH confidence):**
- **Python 3.10-3.12**: Match ComfyUI's environment
- **PyTorch 2.4+**: Provided by ComfyUI, tensor operations for images
- **PIL (Pillow)**: Image I/O, already available
- **NumPy**: Array conversions, available
- **pytest**: Testing framework (dev dependency only)

**Node Expansion Pattern (HIGH confidence):**
The research confirms node expansion with GraphBuilder is the correct pattern for graph-level looping, matching Impact Pack's approach but implemented independently:

```python
from comfy_execution.graph_utils import GraphBuilder
from comfy_execution.graph import ExecutionBlocker
```

However, ARCHITECTURE.md's recommendation to use **queue-per-image instead** is more pragmatic for this use case. Node expansion is complex and overkill for simple directory iteration.

**Critical Boilerplate Requirements:**
- `NODE_CLASS_MAPPINGS` dictionary in `__init__.py`
- `INPUT_TYPES` classmethod returning dict with "required"/"optional" keys
- `RETURN_TYPES` and `RETURN_NAMES` as tuples (trailing comma mandatory)
- `FUNCTION` attribute naming the execution method
- `CATEGORY` for menu organization
- Return values always as tuples: `return (result,)`

**Image Format Convention:**
```python
# IMAGE type is torch.Tensor with shape [B, H, W, C]
# - B: Batch size (≥1)
# - H, W: Height, Width
# - C: Channels (3 for RGB)
# - Values: float32 in range [0.0, 1.0]
```

### From FEATURES.md: User Expectations and Competitive Landscape

**Table Stakes (must-have for MVP):**
1. Directory loading with filename pattern filtering (*.png, *.jpg)
2. Image saving with configurable output format (PNG/JPG/WebP)
3. **Filename customization** - prefix + original + suffix (not just counters)
4. **Original filename preservation** - critical for traceability
5. Progress indication (X of Y)
6. Batch count output for downstream nodes
7. Multiple loading modes (single, incremental, random)

**Key Differentiators:**
1. **Graph-level looping per image** - process each through entire workflow individually
2. **Resume capability** - continue from where stopped after interruption
3. **Smart filename ordering** - natural sort (img2 before img10)
4. **Automatic state persistence** - survive crashes/restarts
5. Index range selection (process images 50-100 only)
6. Conditional skip based on output existence

**Anti-Features (explicitly avoid):**
- Parallel batch loading (all in memory) - causes OOM
- In-graph loops with state - fragile with ComfyUI execution model
- Complex regex for filename matching - user errors
- Automatic image resizing - surprising behavior
- Overwriting source files - data loss risk
- Counter-only filenames - loses traceability
- Silent failures - must log every skip with reason

**Competitive Gap:**
Existing solutions are either too complex (Impact Pack), abandoned (WAS Node Suite), or solve adjacent problems (Loop-image for masks). Opportunity exists for a clean, focused solution for "load directory → process each through workflow → save with original filename."

### From ARCHITECTURE.md: System Design and Patterns

**Recommended Pattern: Queue-Per-Image Execution**

```
[Load Image #1] → [User Pipeline] → [Save Image #1] → Auto Queue triggers
[Load Image #2] → [User Pipeline] → [Save Image #2] → Auto Queue triggers
[Load Image #3] → [User Pipeline] → [Save Image #3] → ...
```

**Why This Pattern:**
- Immediate saves after each image (crash-safe)
- Simple state management (JSON file tracking index)
- Natural resume points
- Works with any pipeline nodes (no special loop support needed)
- Memory released between iterations

**Component Responsibilities:**
| Component | Purpose | Dependencies |
|-----------|---------|--------------|
| **BatchImageLoader** | Load one image per execution, track index | ProgressTracker (read state) |
| **ProgressTracker** | Persist state to JSON, track completed items | None (pure utility) |
| **BatchImageSaver** | Save with naming, update progress | ProgressTracker (mark complete) |
| **User Pipeline** | Any ComfyUI nodes (KSampler, etc.) | None (decoupled) |

**State File Structure:**
```json
{
  "version": 1,
  "directory": "/path/to/input",
  "current_index": 5,
  "total_files": 100,
  "completed": [0, 1, 2, 3, 4],
  "failed": [],
  "started_at": "2026-02-01T10:00:00Z",
  "last_updated": "2026-02-01T10:05:00Z"
}
```

**Critical Patterns to Follow:**
1. **IS_CHANGED for cache busting** - return unique value per index to prevent stale results
2. **OUTPUT_NODE = True** for saver - ensures node always executes
3. **State file atomic writes** - use temp file + os.replace() to prevent corruption
4. **IMAGE tensor format [B,H,W,C]** - always maintain batch dimension
5. **folder_paths API** - use ComfyUI's standard directory helpers

**Anti-Patterns to Avoid:**
- In-graph looping for simple batches (complex, fragile)
- Relying on execution order (non-deterministic in ComfyUI)
- Loading all images at once (memory exhaustion)
- External node dependencies (installation complexity)

### From PITFALLS.md: Critical Risks and Prevention

**Critical Pitfalls (require architectural decisions):**

1. **Incorrect Node Registration Structure** (Phase 1)
   - Missing NODE_CLASS_MAPPINGS or malformed class attributes
   - Node silently fails to register, appears in UI then crashes
   - **Prevention:** Use exact boilerplate, tuples with trailing commas

2. **Image Tensor Format Mismatch** (Phase 1)
   - Assuming [H,W,C] instead of [B,H,W,C]
   - Causes dimension errors, corrupted output
   - **Prevention:** Always check shape, maintain batch dimension

3. **Memory Accumulation in Batch Processing** (Phase 2)
   - RAM/VRAM grows unbounded, OOM after 50-200 images
   - **Prevention:** Call gc.collect() and torch.cuda.empty_cache() periodically, never accumulate in instance variables

4. **Execution Model Misunderstanding** (Phase 3)
   - ComfyUI execution is front-to-back topological sort, non-deterministic order
   - State doesn't persist between iterations without explicit management
   - **Prevention:** Use queue-per-image pattern, store state in class variables or external files

5. **IS_CHANGED and Caching Misuse** (Phase 2)
   - Nodes re-execute unnecessarily or use stale results
   - Resume fails, always starts from beginning
   - **Prevention:** Implement IS_CHANGED returning file mtime + size hash

**Moderate Pitfalls (cause delays):**
- Inconsistent batch sizes across nodes
- Directory path handling (cross-platform issues)
- Frontend extension sync issues
- Optional input validation changes (ComfyUI v3)
- Type matching issues ("*" type deprecated)

**Minor Pitfalls (annoying but fixable):**
- Missing trailing comma in tuples (RETURN_TYPES)
- Dependency version conflicts
- Empty directory handling
- Not testing with ComfyUI Manager installation

---

## Implications for Roadmap

### Recommended Phase Structure

The research strongly suggests a **4-phase build** with early focus on getting the queue-per-image pattern working correctly:

#### Phase 1: Core Infrastructure (Foundation)
**Rationale:** Establish correct patterns before building features. Many pitfalls (#1, #2, #9) occur in foundational code.

**Deliverables:**
- ProgressTracker module (JSON state management, atomic writes)
- Node registration boilerplate (`__init__.py`, NODE_CLASS_MAPPINGS)
- Image tensor utilities (load PIL → [B,H,W,C], save [B,H,W,C] → PIL)
- Basic test fixtures (mock ComfyUI environment)

**Features from FEATURES.md:**
- None yet (infrastructure only)

**Pitfalls to address:**
- #1: Node registration structure
- #2: Tensor format [B,H,W,C]
- #6: Batch size validation
- #9: Optional input validation
- #11: Trailing commas in tuples

**Research depth:** Standard patterns, well-documented. No additional research needed.

---

#### Phase 2: Batch Processing Loop (Core Value)
**Rationale:** This is the fundamental value proposition. Get the queue-per-image execution working before adding polish.

**Deliverables:**
- BatchImageLoader node (directory scan, sort, load one image per execution)
- BatchImageSaver node (save with format options)
- State integration (read/write current index)
- IS_CHANGED implementation for cache invalidation

**Features from FEATURES.md:**
- Directory loading (table stakes)
- Filename pattern filtering (table stakes)
- Natural sort order (differentiator)
- Original filename preservation (table stakes)
- Image saving with format options (table stakes)
- Batch count output (table stakes)

**Pitfalls to address:**
- #3: Memory accumulation (gc.collect() strategy)
- #5: IS_CHANGED and caching
- #7: Directory path handling
- #13: Empty directory validation

**Research depth:** Queue-per-image pattern is well-understood. Testing at scale may reveal edge cases but no deep research needed.

---

#### Phase 3: Progress Tracking and Resume (Differentiator)
**Rationale:** Resume capability is a key competitive advantage. Builds naturally on Phase 2's state management.

**Deliverables:**
- Enhanced state file (completed/failed tracking)
- Skip-if-exists logic
- Progress indicator outputs (current/total/is_last)
- Atomic state updates after each save

**Features from FEATURES.md:**
- Progress indication (table stakes)
- Resume capability (differentiator)
- Automatic state persistence (differentiator)
- Conditional skip based on output existence (differentiator)

**Pitfalls to address:**
- #5: IS_CHANGED for resume (must detect state changes)
- Atomic writes must handle concurrent access

**Research depth:** Standard file-based state patterns. No additional research needed.

---

#### Phase 4: Polish and Advanced Features (Optional)
**Rationale:** After core loop works reliably, add user experience improvements.

**Deliverables:**
- Index range selection (start/end parameters)
- Multiple naming modes (sequential, timestamp, preserve original)
- Error logging and retry tracking
- Integration tests with realistic workflows

**Features from FEATURES.md:**
- Index range selection (differentiator)
- Filename customization modes (table stakes)
- Metadata preservation (deferred - nice to have)
- Before/after preview (deferred - users can use existing nodes)

**Pitfalls to address:**
- #12: Dependency conflicts (test with common node packs)
- #14: ComfyUI Manager installation testing

**Research depth:** Well-understood features. Standard implementation patterns.

---

### Research Flags

**Which phases need `/gsd:research-phase`?**

| Phase | Needs Research? | Reason |
|-------|-----------------|--------|
| Phase 1 | NO | Standard node registration patterns, well-documented |
| Phase 2 | NO | Queue-per-image pattern verified, architecture clear |
| Phase 3 | NO | State file persistence is standard pattern |
| Phase 4 | NO | UI/polish features use documented APIs |

**Overall:** This domain is well-researched. Official ComfyUI docs + community implementations provide clear patterns. No phase-specific research needed unless unexpected issues arise during implementation.

**When to research during planning:**
- If implementing node expansion (GraphBuilder) instead of queue-per-image
- If adding frontend extensions for UI progress (PromptServer API)
- If integrating with ComfyUI Manager publishing (registry specifications)

---

### Build Order Dependencies

```
Phase 1 (Foundation)
    ↓
Phase 2 (Batch Loop) ← Must complete before testing resume
    ↓
Phase 3 (Resume & Progress) ← Builds on Phase 2 state management
    ↓
Phase 4 (Polish) ← Independent features, can be prioritized flexibly
```

**Critical Path:**
1. ProgressTracker utility (pure Python, no ComfyUI dependencies)
2. BatchImageLoader (depends on ProgressTracker)
3. BatchImageSaver (depends on ProgressTracker)
4. Integration test (verify queue-per-image execution)
5. Resume capability (enhanced state tracking)
6. Polish features (independent)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | Official docs, verified dependencies. PyTorch/PIL/NumPy provided by ComfyUI. Node registration boilerplate well-documented. |
| **Features** | MEDIUM-HIGH | Table stakes verified via WAS Node Suite, Impact Pack. Differentiators (resume, graph-looping) validated by user complaints about existing solutions. Anti-features confirmed by community pitfall reports. |
| **Architecture** | HIGH | Queue-per-image pattern verified in official docs and community guides. State file persistence is standard pattern. Component boundaries clear. |
| **Pitfalls** | HIGH | Critical pitfalls (#1-5) verified in official troubleshooting docs and GitHub issues. Memory accumulation confirmed by user reports. Execution model changes documented in official migration guides. |

**Overall Confidence: HIGH**

The domain is mature with official documentation, established patterns, and active community. Research synthesized from:
- Official ComfyUI docs (custom nodes, execution model, datatypes)
- GitHub issues tracking common problems
- Reference implementations (Impact Pack, WAS Node Suite)
- Community guides (batch processing at scale)

---

## Gaps to Address During Planning

### 1. Memory Management Strategy Details
**Gap:** Exact thresholds for gc.collect() frequency unclear. Research says "periodically" but doesn't specify.

**Validation needed:** Test with 100-1000 images at various sizes to determine optimal cleanup frequency. Monitor memory growth.

**Phase affected:** Phase 2 (Batch Processing)

**Risk:** Low. Can start with "every 10 images" and adjust based on profiling.

---

### 2. Auto Queue Stop Mechanism
**Gap:** How to gracefully stop Auto Queue when batch completes? Research mentions `model_management.interrupt_current_processing()` but unclear if this is the best approach.

**Validation needed:** Test with actual Auto Queue enabled. Verify workflow stops cleanly without errors.

**Phase affected:** Phase 2 (Batch Processing)

**Risk:** Low. Worst case, user manually stops queue after completion.

---

### 3. ComfyUI Version Compatibility Range
**Gap:** Research says "ComfyUI 0.3.0+" but doesn't specify upper bound or breaking changes.

**Validation needed:** Test with ComfyUI versions: latest stable, latest nightly, 0.3.0 minimum.

**Phase affected:** Phase 4 (Release Testing)

**Risk:** Low. Node patterns are stable across recent versions per execution model docs.

---

### 4. Frontend Progress Indicator Implementation
**Gap:** If adding UI progress bar, PromptServer.send_sync() API details not fully researched.

**Validation needed:** Only if implementing frontend extension. Can defer to Phase 4 or skip entirely (backend progress is sufficient).

**Phase affected:** Phase 4 (Polish - optional)

**Risk:** Very low. This is optional polish, not core functionality.

---

## Recommended Next Steps for Orchestrator

### 1. Proceed to Requirements Definition
Research is comprehensive. No blocking gaps. Ready to define requirements based on:
- **Table stakes from FEATURES.md** → Must-have requirements
- **Differentiators from FEATURES.md** → Should-have requirements
- **Anti-features from FEATURES.md** → Explicit non-requirements

### 2. Structure Roadmap as 4 Phases
Use phase structure from "Implications for Roadmap" section:
- Phase 1: Foundation (1-2 days)
- Phase 2: Batch Loop (2-3 days)
- Phase 3: Resume & Progress (1-2 days)
- Phase 4: Polish (1-2 days)

Total estimated: 5-9 days for MVP with resume capability.

### 3. Prioritize Early Testing
Given pitfalls #3 (memory) and #4 (execution model), create integration tests early in Phase 2:
- Test with 50+ images to catch memory leaks
- Test Auto Queue behavior with state persistence
- Test resume from interrupted state

### 4. No Additional Research Phases Needed
Skip `/gsd:research-phase` during roadmap execution unless:
- Switching from queue-per-image to node expansion (not recommended)
- Adding complex frontend extensions
- Encountering undocumented ComfyUI API changes

---

## Sources

### HIGH Confidence (Official Documentation)
- [ComfyUI Custom Nodes Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough)
- [ComfyUI Node Expansion](https://docs.comfy.org/custom-nodes/backend/expansion)
- [ComfyUI Datatypes](https://docs.comfy.org/custom-nodes/backend/datatypes)
- [ComfyUI Execution Model Inversion Guide](https://docs.comfy.org/development/comfyui-server/execution_model_inversion_guide)
- [ComfyUI Tensor Documentation](https://docs.comfy.org/custom-nodes/backend/tensors)
- [ComfyUI Troubleshooting](https://docs.comfy.org/troubleshooting/custom-node-issues)

### MEDIUM Confidence (Verified Community)
- [ComfyUI Batch Processing Guide 2025](https://apatero.com/blog/batch-process-1000-images-comfyui-guide-2025)
- [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)
- [ComfyUI-Loop-image](https://github.com/WainWong/ComfyUI-Loop-image)
- [WAS Node Suite](https://github.com/WASasquatch/was-node-suite-comfyui)

### GitHub Issues (Pitfall Verification)
- [Memory Leak #11301](https://github.com/Comfy-Org/ComfyUI/issues/11301)
- [RETURN_NAMES Bug #4629](https://github.com/comfyanonymous/ComfyUI/issues/4629)
- [IS_CHANGED Feature #3111](https://github.com/comfyanonymous/ComfyUI/issues/3111)

---

## Ready for Requirements

This research provides sufficient foundation for requirements definition. Key inputs for requirements phase:

**From FEATURES.md:**
- Table stakes → Functional requirements (must-have)
- Differentiators → Functional requirements (should-have)
- Anti-features → Non-functional requirements (must NOT do)

**From STACK.md:**
- Technology constraints (Python 3.10+, PyTorch, PIL)
- Interface requirements (IMAGE type format, node registration structure)

**From ARCHITECTURE.md:**
- Component structure (3 nodes + 1 utility module)
- Integration requirements (Auto Queue, folder_paths API)

**From PITFALLS.md:**
- Quality requirements (memory cleanup, atomic state writes)
- Testing requirements (scale testing, Manager installation)

Orchestrator can proceed to requirements synthesis and roadmap creation.
