# Phase 5: Live UI Updates - Research

**Researched:** 2026-02-02
**Domain:** ComfyUI websocket messaging, client_id routing, PromptServer API
**Confidence:** HIGH

## Summary

The root cause of UI not updating during batch processing is confirmed: when `trigger_next_queue()` POSTs to `/prompt`, it generates a NEW `client_id` (uuid.uuid4()). ComfyUI's `execution_success` message is sent with `broadcast=False`, meaning it only goes to the client_id that submitted the prompt. Since the frontend's websocket uses its OWN client_id, it never receives execution results from subsequent batch iterations.

**The solution is to broadcast UI updates directly from the nodes** using `PromptServer.instance.send_sync()` with `sid=None`, which broadcasts to ALL connected clients. This is the pattern used by ComfyUI-Impact-Pack's ImpactLogger node for real-time feedback.

**Primary recommendation:** Modify BatchImageSaver to call `PromptServer.instance.send_sync()` with a custom event type that broadcasts execution results to all clients, bypassing the client_id routing limitation.

## Standard Stack

### Core (Built-in to ComfyUI)

| Module | Import | Purpose | Why Standard |
|--------|--------|---------|--------------|
| PromptServer | `from server import PromptServer` | Access server instance for messaging | Official ComfyUI server API |
| send_sync | `PromptServer.instance.send_sync()` | Send websocket messages to clients | Built-in messaging mechanism |

### Supporting (Already in codebase)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| HIDDEN inputs | Access UNIQUE_ID, PROMPT | Already used in BatchImageLoader |

### No New Dependencies Required

This solution uses only built-in ComfyUI APIs. No external packages needed.

## Architecture Patterns

### Pattern 1: Broadcast UI Updates via send_sync

**What:** Nodes call `PromptServer.instance.send_sync()` with `sid=None` to broadcast messages to ALL connected websocket clients, bypassing client_id routing.

**When to use:** When a node needs to update the frontend UI during programmatic queue re-execution.

**Example:**
```python
# Source: ComfyUI server.py and Impact Pack ImpactLogger pattern
from server import PromptServer

class BatchImageSaver:
    # ... existing code ...

    def save_image(self, image, quality, overwrite_mode, ...):
        # ... save logic ...

        # Broadcast UI update to ALL connected clients
        if HAS_SERVER and PromptServer.instance is not None:
            PromptServer.instance.send_sync(
                "executed",  # Standard ComfyUI event type
                {
                    "node": unique_id,
                    "output": {
                        "images": [{"filename": saved_filename, "subfolder": subfolder, "type": "output"}]
                    },
                    "prompt_id": prompt_id  # From HIDDEN input
                },
                sid=None  # None = broadcast to ALL clients
            )
```

### Pattern 2: Custom Event Type for Batch Progress

**What:** Define a custom event type for batch-specific updates that frontend JavaScript can listen for.

**When to use:** For richer UI updates beyond standard "executed" events.

**Example:**
```python
# Source: Impact Pack "impact-node-feedback" pattern
PromptServer.instance.send_sync(
    "batch-progress-update",  # Custom event type
    {
        "node_id": unique_id,
        "index": current_index,
        "total": total_count,
        "saved_filename": filename,
        "saved_path": filepath,
    },
    sid=None  # Broadcast to all
)
```

### Pattern 3: Accessing HIDDEN Inputs for Context

**What:** Use HIDDEN input types to access execution context (UNIQUE_ID, PROMPT, EXTRA_PNGINFO).

**When to use:** When nodes need to know their own ID or access prompt metadata.

**Example (already implemented):**
```python
# Source: ComfyUI docs.comfy.org/custom-nodes/backend/more_on_inputs
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {...},
        "hidden": {
            "unique_id": "UNIQUE_ID",
            "prompt": "PROMPT",
            "extra_pnginfo": "EXTRA_PNGINFO",
        }
    }
```

### Anti-Patterns to Avoid

- **Generating new client_id for programmatic queue:** The current implementation creates a new uuid for each queue POST. This breaks UI routing.
- **Relying solely on OUTPUT_NODE return value:** The `{"ui": {...}}` return works for initial execution but not for re-queued prompts with different client_ids.
- **Frontend polling:** Adding polling would require JavaScript changes and increase server load.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Websocket messaging | Custom websocket code | `PromptServer.instance.send_sync()` | Built-in, thread-safe, handles client disconnects |
| Broadcast to all clients | Client_id tracking | `sid=None` parameter | ComfyUI's native broadcast mechanism |
| Node identification | Custom ID scheme | HIDDEN `UNIQUE_ID` input | Standard ComfyUI pattern |
| Event formatting | Custom message format | Standard `"executed"` event structure | Frontend already knows how to handle it |

**Key insight:** ComfyUI already has all the infrastructure for broadcasting messages. The only missing piece is calling `send_sync` with the right parameters from the batch nodes.

## Common Pitfalls

### Pitfall 1: Forgetting sid=None for Broadcast

**What goes wrong:** Message only goes to original client or no client at all.
**Why it happens:** `send_sync` defaults to using `server.client_id` which may be from a different session.
**How to avoid:** Always explicitly pass `sid=None` when broadcasting.
**Warning signs:** Frontend shows updates for first iteration only.

### Pitfall 2: Missing PromptServer Import Guard

**What goes wrong:** Node crashes when running in test environment or CLI.
**Why it happens:** `from server import PromptServer` fails outside ComfyUI.
**How to avoid:** Use try/except import with HAS_SERVER flag (already in codebase).
**Warning signs:** ImportError in tests.

### Pitfall 3: Sending Messages Without UNIQUE_ID

**What goes wrong:** Frontend can't route message to correct node widget.
**Why it happens:** Node doesn't declare UNIQUE_ID in HIDDEN inputs.
**How to avoid:** Always include `unique_id` in HIDDEN inputs and message payload.
**Warning signs:** Messages sent but UI doesn't update.

### Pitfall 4: Wrong Event Type

**What goes wrong:** Frontend ignores message or misinterprets it.
**Why it happens:** Using non-standard event type without frontend listener.
**How to avoid:** Use standard `"executed"` event for immediate compatibility, or add custom JS listener for custom events.
**Warning signs:** Console shows message sent but no UI change.

## Code Examples

### Complete Broadcasting Pattern for BatchImageSaver

```python
# Source: Pattern derived from ComfyUI server.py and Impact Pack
from server import PromptServer
HAS_SERVER = True
except ImportError:
    PromptServer = None
    HAS_SERVER = False

class BatchImageSaver:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {...},
            "optional": {...},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "prompt": "PROMPT",
            }
        }

    def save_image(self, ..., unique_id=None, prompt=None):
        # ... existing save logic ...

        # After saving, broadcast UI update
        if HAS_SERVER and PromptServer.instance is not None:
            PromptServer.instance.send_sync(
                "executed",
                {
                    "node": unique_id,
                    "output": {
                        "images": [{
                            "filename": saved_filename,
                            "subfolder": subfolder,
                            "type": "output"
                        }]
                    },
                },
                sid=None  # CRITICAL: Broadcast to ALL clients
            )

        return {"ui": {...}, "result": (...)}
```

### send_sync Signature Reference

```python
# Source: ComfyUI server.py
def send_sync(self, event, data, sid=None):
    """
    Queue a message for websocket delivery.

    Args:
        event: Event type string (e.g., "executed", "progress", "status")
        data: Dictionary payload to send
        sid: Session ID for targeted delivery, or None to broadcast to ALL clients
    """
    self.loop.call_soon_threadsafe(
        self.messages.put_nowait, (event, data, sid))
```

### Standard ComfyUI Event Types

```python
# Source: ComfyUI docs.comfy.org/development/comfyui-server/comms_messages
# Event types the frontend already understands:
"execution_start"      # Prompt begins running
"execution_success"    # All nodes completed successfully
"execution_error"      # Execution encountered an error
"executed"            # Node returned a UI element (images, text)
"executing"           # Before each node runs
"progress"            # During node execution (progress bars)
"status"              # Queue state changes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| client_id per request | Broadcast with sid=None | Always available | Enables multi-client updates |
| OUTPUT_NODE return only | Direct send_sync calls | Always available | Real-time updates during batch |

**Deprecated/outdated:**
- Relying solely on OUTPUT_NODE `{"ui": {...}}` return for batch scenarios - works for single executions but not re-queued prompts

## Implementation Strategy

### Recommended Approach: Broadcast from Nodes

1. **Modify BatchImageSaver** to call `send_sync("executed", ...)` with `sid=None` after saving
2. **Add HIDDEN inputs** (UNIQUE_ID, PROMPT) to BatchImageSaver if not present
3. **Keep existing OUTPUT_NODE return** for backwards compatibility
4. **Optional:** Modify BatchProgressFormatter similarly for progress text updates

### Why This Approach

- **Minimal changes:** Only modifies 1-2 files
- **No frontend changes:** Uses standard "executed" event type
- **No external dependencies:** Uses only built-in ComfyUI APIs
- **Backwards compatible:** Existing return value still works for normal usage

### Alternative Approaches (Not Recommended)

| Approach | Why Not |
|----------|---------|
| Pass frontend client_id through queue | Would require storing/passing client_id through entire prompt chain - invasive change |
| Frontend polling /history | Requires JavaScript changes, increases server load |
| Modify ComfyUI core | Not maintainable, breaks on updates |

## Open Questions

### Question 1: PreviewImage Node Updates

**What we know:** PreviewImage is a core ComfyUI node, not our custom node.
**What's unclear:** Whether broadcasting from BatchImageSaver will update PreviewImage nodes connected downstream.
**Recommendation:** Test with simple broadcast first. If PreviewImage doesn't update, may need to broadcast specifically for preview nodes or accept as limitation.

### Question 2: Event Type Compatibility

**What we know:** "executed" is the standard event for node UI updates.
**What's unclear:** Whether the exact payload format is documented anywhere.
**Recommendation:** Match the format used by existing ComfyUI nodes (observe in browser devtools).

## Sources

### Primary (HIGH confidence)

- ComfyUI server.py - send_sync implementation, sid parameter behavior
  - https://github.com/comfyanonymous/ComfyUI/blob/master/server.py
- ComfyUI execution.py - client_id handling, add_message with broadcast parameter
  - https://github.com/comfyanonymous/ComfyUI/blob/master/execution.py
- ComfyUI official docs - HIDDEN input types
  - https://docs.comfy.org/custom-nodes/backend/more_on_inputs
- ComfyUI official docs - Server message types
  - https://docs.comfy.org/development/comfyui-server/comms_messages

### Secondary (MEDIUM confidence)

- Impact Pack ImpactLogger - Pattern for send_sync usage from nodes
  - https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/Main/modules/impact/util_nodes.py
- DeepWiki ComfyUI analysis - Server architecture
  - https://deepwiki.com/comfyanonymous/ComfyUI/2.2-memory-management

### Tertiary (LOW confidence)

- Various WebSearch results about ComfyUI batch processing patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Uses only built-in ComfyUI APIs verified in source code
- Architecture: HIGH - Pattern verified in Impact Pack and ComfyUI source
- Pitfalls: MEDIUM - Based on understanding of the system, not empirical testing

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (ComfyUI is actively developed, check for API changes)
