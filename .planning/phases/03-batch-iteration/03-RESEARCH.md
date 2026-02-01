# Phase 3: Batch Iteration - Research

**Researched:** 2026-02-01
**Domain:** ComfyUI Batch Processing - State Management and Queue-Per-Image Pattern
**Confidence:** HIGH

## Summary

This phase implements the batch iteration mechanism that allows users to process an entire directory by clicking Queue once. Research confirms the queue-per-image pattern (already decided in roadmap) is the standard approach. The key implementation areas are: (1) in-memory state management for index tracking with class variables, (2) queue triggering via `PromptServer.instance.send_sync()` for self-queuing, and (3) batch completion signaling.

The user decisions from CONTEXT.md lock in the approach: in-memory counter with "Continue"/"Reset" dropdown, auto-reset on directory change, 0-based index output, `start_index` input for manual resume, `batch_complete` boolean signal, and status output. Claude has discretion on whether to use Auto Queue integration (user-enabled) vs self-queuing via API.

**Primary recommendation:** Use self-queuing via `PromptServer.instance.send_sync("impact-add-queue", {})` pattern for more control, with `batch_complete` output that can also signal Auto Queue to stop. This gives users flexibility to use either approach.

## Standard Stack

The established libraries/tools for this domain:

### Core (ComfyUI-Provided)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| server.PromptServer | ComfyUI built-in | Queue triggering, server communication | Singleton pattern provides `send_sync()` for WebSocket messages |
| torch | 2.4+ | Tensor operations | Required by ComfyUI for all image data |
| Python class variables | 3.10+ | In-memory state persistence | Persists across node executions within same ComfyUI session |

### Supporting (Built-in Python)
| Library | Purpose | When to Use |
|---------|---------|-------------|
| typing | Type hints | Method signatures for inputs/outputs |
| os | File path operations | Directory path comparison for auto-reset |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory state | JSON state file | Files persist across restarts but add I/O overhead; in-memory matches user decision |
| Self-queuing via send_sync | Auto Queue (user-enabled) | Auto Queue requires user to enable manually; send_sync gives programmatic control |
| `impact-add-queue` event | Direct `/prompt` API call | send_sync is simpler, handles all the complexity internally |

**Installation:** No additional dependencies - all required components are ComfyUI built-ins.

## Architecture Patterns

### Recommended Project Structure
```
comfyui_batch_image_processing/
├── nodes/
│   ├── batch_loader.py      # Extend with iteration state
│   └── batch_saver.py       # Already complete (no changes)
├── utils/
│   ├── iteration_state.py   # NEW: State management class
│   └── queue_control.py     # NEW: Queue triggering utilities
└── tests/
    ├── test_iteration_state.py
    └── test_queue_control.py
```

### Pattern 1: Class Variable State Persistence
**What:** Use class variables (not instance variables) to persist state across node executions within same ComfyUI session
**When to use:** Any state that should survive multiple executions but reset on ComfyUI restart
**Example:**
```python
# Source: ComfyUI pattern observed in ControlFlowUtils and Impact Pack
class BatchImageLoader:
    # Class-level state (persists across executions)
    _state = {}  # Keyed by directory path

    @classmethod
    def _get_state(cls, directory: str) -> dict:
        """Get or create state for a directory."""
        normalized = os.path.normpath(directory)
        if normalized not in cls._state:
            cls._state[normalized] = {
                "index": 0,
                "last_directory": normalized,
                "total_count": 0,
            }
        return cls._state[normalized]

    @classmethod
    def _reset_state(cls, directory: str):
        """Reset state for a directory."""
        normalized = os.path.normpath(directory)
        cls._state[normalized] = {
            "index": 0,
            "last_directory": normalized,
            "total_count": 0,
        }
```

### Pattern 2: Queue Triggering via send_sync
**What:** Use `PromptServer.instance.send_sync()` to trigger queue additions from within a node
**When to use:** When node needs to cause workflow re-execution (batch iteration)
**Example:**
```python
# Source: ComfyUI-Impact-Pack ImpactQueueTrigger implementation
# https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/Main/modules/impact/logics.py
try:
    from server import PromptServer
    HAS_SERVER = True
except ImportError:
    HAS_SERVER = False  # Testing outside ComfyUI

def trigger_queue():
    """Trigger a new queue execution."""
    if HAS_SERVER and PromptServer.instance is not None:
        PromptServer.instance.send_sync("impact-add-queue", {})
```

### Pattern 3: Countdown/Completion Detection
**What:** Track iteration count and signal when batch is complete
**When to use:** Determining when to stop queuing new executions
**Example:**
```python
# Source: ComfyUI-Impact-Pack ImpactQueueTriggerCountdown pattern
def should_continue(current_index: int, total_count: int) -> bool:
    """Determine if batch should continue iterating."""
    return current_index < total_count - 1  # -1 because we're about to process current

def process_with_queue_trigger(current_index, total_count, mode):
    """Process current item and trigger next if needed."""
    is_last = current_index >= total_count - 1
    batch_complete = is_last

    if not is_last and mode:  # mode=True means auto-continue
        trigger_queue()

    return batch_complete
```

### Pattern 4: Directory Change Auto-Reset
**What:** Automatically reset index when directory path changes
**When to use:** Preventing stale state when user switches to different input folder
**Example:**
```python
# Source: User decision from CONTEXT.md
class BatchImageLoader:
    @classmethod
    def _check_directory_change(cls, directory: str, state: dict) -> bool:
        """Check if directory changed and state should reset."""
        normalized = os.path.normpath(directory)
        if state.get("last_directory") != normalized:
            return True
        return False
```

### Pattern 5: Mode Dropdown for Iteration Control
**What:** Combo input with "Continue"/"Reset" options
**When to use:** Giving user explicit control over iteration behavior
**Example:**
```python
# Source: User decision from CONTEXT.md
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {
            "directory": ("STRING", {...}),
            "iteration_mode": (["Continue", "Reset"], {"default": "Continue"}),
            "error_handling": (["Stop on error", "Skip on error"], {"default": "Stop on error"}),
        },
        "optional": {
            "start_index": ("INT", {"default": 0, "min": 0, "max": 99999}),
        },
        # hidden inputs remain from Phase 1
    }
```

### Anti-Patterns to Avoid
- **Instance variables for state:** Use class variables. Instance may be recreated between executions.
- **File-based state for simple counters:** Adds I/O overhead and complexity. In-memory is sufficient per user decision.
- **Relying on Auto Queue without fallback:** User might not have Auto Queue enabled. Self-queuing provides control.
- **Tight coupling to Impact Pack:** Don't require Impact Pack. Implement self-contained queue triggering.
- **Blocking wait for queue completion:** Node should return immediately after triggering. ComfyUI handles execution flow.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Queue triggering | HTTP calls to /prompt | `PromptServer.instance.send_sync("impact-add-queue", {})` | Handles WebSocket, client notification, proper sequencing |
| Node widget updates | Manual JSON manipulation | `send_sync("impact-node-feedback", {...})` | Proper ComfyUI widget update protocol |
| Server singleton access | Create own server reference | `from server import PromptServer; PromptServer.instance` | ComfyUI's established pattern |

**Key insight:** ComfyUI's PromptServer singleton and send_sync pattern handle all the complexity of queue management. Use the established pattern from Impact Pack.

## Common Pitfalls

### Pitfall 1: State Lost Between Executions
**What goes wrong:** Counter resets to 0 on every execution, processing same image repeatedly
**Why it happens:** Using `self.counter` (instance variable) instead of class variable
**How to avoid:** Use `cls._state` dict keyed by directory path
**Warning signs:** First image processed repeatedly, never advances

### Pitfall 2: IS_CHANGED Not Updating
**What goes wrong:** ComfyUI caches result, doesn't re-execute even with new index
**Why it happens:** IS_CHANGED returns same value because it doesn't include index
**How to avoid:** Include current index in IS_CHANGED return value
**Warning signs:** "Image didn't change" behavior, same output despite state change

### Pitfall 3: Race Condition with Queue Trigger
**What goes wrong:** Multiple queue items added for same image
**Why it happens:** Trigger called before state is updated
**How to avoid:** Update state BEFORE calling trigger_queue()
**Warning signs:** Duplicate processing, index jumps unexpectedly

### Pitfall 4: Auto-Reset on Slight Path Variations
**What goes wrong:** State resets unexpectedly when user hasn't changed directories
**Why it happens:** Path not normalized (`/path/to/dir` vs `/path/to/dir/` vs `/path/to/../path/to/dir`)
**How to avoid:** Use `os.path.normpath()` before comparison
**Warning signs:** State resets when using "same" directory with different path format

### Pitfall 5: Queue Trigger Without Server Check
**What goes wrong:** Crash when running tests or outside ComfyUI
**Why it happens:** `PromptServer.instance` is None outside ComfyUI context
**How to avoid:** Guard with `if HAS_SERVER and PromptServer.instance is not None`
**Warning signs:** AttributeError or NoneType errors in tests

### Pitfall 6: Infinite Queue Loop
**What goes wrong:** Workflow keeps re-queuing forever even after batch completes
**Why it happens:** batch_complete signal not checked, or trigger called even on last image
**How to avoid:** Only trigger queue if `current_index < total_count - 1`
**Warning signs:** ComfyUI queue never empties, CPU stays high after batch should complete

## Code Examples

Verified patterns from official sources:

### Complete Iteration State Management
```python
# Source: Pattern derived from ComfyUI-Impact-Pack and ControlFlowUtils
class IterationState:
    """Manage batch iteration state across executions."""

    _instances: dict = {}  # Class-level state storage

    @classmethod
    def get_state(cls, directory: str) -> dict:
        """Get or initialize state for a directory."""
        key = os.path.normpath(os.path.abspath(directory))
        if key not in cls._instances:
            cls._instances[key] = {
                "index": 0,
                "total_count": 0,
                "directory": key,
                "status": "idle",
            }
        return cls._instances[key]

    @classmethod
    def reset(cls, directory: str):
        """Reset state for directory."""
        key = os.path.normpath(os.path.abspath(directory))
        if key in cls._instances:
            cls._instances[key]["index"] = 0
            cls._instances[key]["status"] = "idle"

    @classmethod
    def advance(cls, directory: str) -> int:
        """Advance index and return new value."""
        state = cls.get_state(directory)
        state["index"] += 1
        return state["index"]

    @classmethod
    def is_complete(cls, directory: str) -> bool:
        """Check if batch is complete."""
        state = cls.get_state(directory)
        return state["index"] >= state["total_count"]
```

### Queue Control Utilities
```python
# Source: ComfyUI-Impact-Pack pattern
# https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/Main/modules/impact/logics.py
try:
    from server import PromptServer
    HAS_SERVER = True
except ImportError:
    PromptServer = None
    HAS_SERVER = False

def trigger_next_queue():
    """Trigger ComfyUI to queue another execution."""
    if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None:
        PromptServer.instance.send_sync("impact-add-queue", {})
        return True
    return False

def update_node_widget(node_id: str, widget_name: str, value):
    """Update a node's widget value in the UI."""
    if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None:
        widget_type = "int" if isinstance(value, int) else "text"
        PromptServer.instance.send_sync("impact-node-feedback", {
            "node_id": node_id,
            "widget_name": widget_name,
            "type": widget_type,
            "value": value
        })
```

### Extended BatchImageLoader with Iteration
```python
# Source: Extension of existing BatchImageLoader based on Phase 3 requirements
class BatchImageLoader:
    """Batch image loader with iteration support."""

    # Class-level state (persists across executions)
    _iteration_state: dict = {}

    CATEGORY = "batch_processing"
    RETURN_TYPES = ("IMAGE", "INT", "INT", "INT", "STRING", "STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("IMAGE", "TOTAL_COUNT", "INDEX", "CURRENT_INDEX", "FILENAME", "BASENAME", "STATUS", "BATCH_COMPLETE")
    FUNCTION = "load_image"
    OUTPUT_NODE = False

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": "", "tooltip": "Directory path"}),
                "filter_preset": (["All Images", "PNG Only", "JPG Only", "Custom"],),
                "iteration_mode": (["Continue", "Reset"], {"default": "Continue"}),
                "error_handling": (["Stop on error", "Skip on error"], {"default": "Stop on error"}),
            },
            "optional": {
                "custom_pattern": ("STRING", {"default": "*.png,*.jpg,*.jpeg,*.webp"}),
                "start_index": ("INT", {"default": 0, "min": 0, "max": 99999}),
            },
        }

    @classmethod
    def IS_CHANGED(cls, directory, iteration_mode, **kwargs):
        """Return unique value to prevent caching."""
        state = cls._get_state(directory)
        return f"{directory}|{state.get('index', 0)}|{iteration_mode}"

    @classmethod
    def _get_state(cls, directory: str) -> dict:
        key = os.path.normpath(directory) if directory else ""
        if key not in cls._iteration_state:
            cls._iteration_state[key] = {"index": 0, "last_dir": key}
        return cls._iteration_state[key]
```

### IS_CHANGED with Index for Cache Busting
```python
# Source: ComfyUI pattern, extended for iteration
@classmethod
def IS_CHANGED(cls, directory, iteration_mode, start_index=0, **kwargs):
    """Ensure node re-executes for each iteration."""
    if not directory:
        return ""

    state = cls._get_state(directory)
    current_index = state.get("index", 0)

    # Include index in hash to force re-execution each iteration
    return f"{directory}|{current_index}|{iteration_mode}|{start_index}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| External loop node packs | Queue-per-image with Auto Queue | 2025 | Simpler, no dependencies, crash-safe |
| File-based state persistence | In-memory class variables | 2025 | Faster, appropriate for session-scoped state |
| Manual /prompt API calls | send_sync with event types | 2025 | Cleaner integration, proper sequencing |

**Deprecated/outdated:**
- WAS Node Suite batch nodes: Archived June 2025
- Complex in-graph loop patterns: Replaced by simpler queue-per-image

## Open Questions

Things that couldn't be fully resolved:

1. **Stopping Auto Queue programmatically**
   - What we know: Impact Pack and Book-Tools have EndQueue nodes that can stop queue
   - What's unclear: Whether we can stop Auto Queue without user action or third-party node
   - Recommendation: Output `batch_complete` boolean signal. If user has Auto Queue enabled, they can connect to EndQueue or similar. For self-queuing mode, we simply don't trigger next queue.

2. **Widget update propagation**
   - What we know: `send_sync("impact-node-feedback", {...})` can update node widgets
   - What's unclear: Whether this requires Impact Pack's JS handlers or works natively
   - Recommendation: Keep status as output (STRING) rather than widget update. Outputs are simpler and work without JS.

3. **Interrupt during batch**
   - What we know: ComfyUI has `/interrupt` endpoint
   - What's unclear: How to detect user pressed Cancel to update status appropriately
   - Recommendation: On Cancel with "Continue" mode, state stays at current index (resumes next run). On "Reset" mode or directory change, state resets.

## Sources

### Primary (HIGH confidence)
- [ComfyUI-Impact-Pack logics.py](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/Main/modules/impact/logics.py) - ImpactQueueTrigger implementation with `send_sync("impact-add-queue", {})`
- [ComfyUI server.py](https://github.com/comfyanonymous/ComfyUI/blob/master/server.py) - PromptServer singleton pattern
- [ComfyUI Routes Documentation](https://docs.comfy.org/development/comfyui-server/comms_routes) - Server communication endpoints
- [ComfyUI GitHub Issue #5667](https://github.com/comfyanonymous/ComfyUI/issues/5667) - How to trigger Queue Prompt from within a node

### Secondary (MEDIUM confidence)
- [ComfyUI-Impact-Pack ImpactQueueTriggerCountdown](https://comfyai.run/documentation/ImpactQueueTriggerCountdown) - Countdown pattern with state tracking
- [ControlFlowUtils Memory Storage](https://comfy.icu/extension/VykosX__ControlFlowUtils) - Persistent state patterns
- [ComfyUI EndQueue Node](https://www.runcomfy.com/comfyui-nodes/ComfyUI-Book-Tools/EndQueue) - Queue termination pattern

### Tertiary (LOW confidence)
- Community discussions on batch processing patterns (cross-verified where possible)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PromptServer and send_sync verified in Impact Pack source
- Architecture: HIGH - Class variable state pattern verified in multiple ComfyUI extensions
- Pitfalls: HIGH - Common issues documented in GitHub issues and discussions

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - queue patterns are stable)
