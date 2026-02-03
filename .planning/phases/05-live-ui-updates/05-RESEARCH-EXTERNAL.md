# Phase 5: Live UI Updates - External Research

**Researched:** 2026-02-02
**Sources:** GitHub, ComfyUI Official Docs, Community Discussions
**Confidence:** HIGH - Multiple sources confirm approach

## Executive Summary

Research confirms our planned approach is correct. The key findings:

1. **`send_sync(event, data, sid=None)` broadcasts to ALL clients** - Verified in ComfyUI server.py
2. **`UNIQUE_ID` is passed as a STRING** - Critical implementation detail
3. **Impact Pack's ImpactLogger is the canonical example** - Uses exact pattern we need
4. **OUTPUT_NODE is independent of send_sync** - Can use both together or separately
5. **Community has documented this exact problem** - client_id routing is a known issue

---

## 1. Confirmed: Broadcast Pattern

### Server Implementation (server.py)

```python
def send_sync(self, event, data, sid=None):
    """Queue a message for async delivery to WebSocket clients"""
    self.loop.call_soon_threadsafe(
        self.messages.put_nowait, (event, data, sid))

async def send_json(self, event, data, sid=None):
    """Format and send JSON message"""
    message = {"type": event, "data": data}

    if sid is None:
        # Broadcasts to ALL connected clients
        sockets = list(self.sockets.values())
        for ws in sockets:
            await send_socket_catch_exception(ws.send_json, message)
    elif sid in self.sockets:
        # Targeted delivery to specific client
        await send_socket_catch_exception(self.sockets[sid].send_json, message)
```

**Confirmed:** When `sid=None`, message broadcasts to ALL connected WebSocket clients.

---

## 2. Working Reference: ImpactLogger

From [ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/Main/modules/impact/util_nodes.py):

```python
from server import PromptServer

class ImpactLogger:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "data": (any_typ,),
                "text": ("STRING", {"multiline": True}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "unique_id": "UNIQUE_ID"
            },
        }

    CATEGORY = "ImpactPack/Debug"
    OUTPUT_NODE = True
    RETURN_TYPES = ()
    FUNCTION = "doit"

    def doit(self, data, text, prompt, extra_pnginfo, unique_id):
        shape = ""
        if hasattr(data, "shape"):
            shape = f"{data.shape} / "

        logging.info(f"[IMPACT LOGGER]: {shape}{data}")

        PromptServer.instance.send_sync(
            "impact-node-feedback",
            {
                "node_id": unique_id,
                "widget_name": "text",
                "type": "TEXT",
                "value": f"{data}"
            }
        )
        return {}
```

**Key Pattern:** Uses custom event type `"impact-node-feedback"` for targeted node updates.

---

## 3. Critical Detail: UNIQUE_ID is a STRING

```python
def my_function(self, unique_id):
    # unique_id is "5", not 5
    print(type(unique_id))  # <class 'str'>
    int_id = int(unique_id)  # Convert if needed
```

**Important:** UNIQUE_ID matches the `id` property of the node on the client side, but is passed as a string.

---

## 4. "executed" Event Payload Structure

### Wire Format (JSON over WebSocket)

```json
{
  "type": "executed",
  "data": {
    "node": "123",
    "display_node": "123",
    "output": {
      "images": [
        {"filename": "image.png", "subfolder": "", "type": "output"}
      ],
      "text": ["some text"],
      "audio": [...],
      "video": [...]
    },
    "prompt_id": "abc-123-uuid"
  }
}
```

### Frontend TypeScript Schema (apiSchema.ts)

```typescript
interface ExecutedWsMessage {
  node: string;           // Node ID
  display_node: string;   // Display node ID
  output: {
    images?: Array<{filename?: string, subfolder?: string, type?: string}>;
    audio?: Array<ResultItem>;
    video?: Array<ResultItem>;
    animated?: boolean[];
    text?: string | string[];
    // Additional properties allowed
  };
  prompt_id: string;
  merge?: boolean;        // Optional: merge with existing outputs
}
```

---

## 5. Standard ComfyUI Event Types

| Event | When Sent | Payload |
|-------|-----------|---------|
| `execution_start` | Prompt begins | `{ prompt_id, timestamp }` |
| `execution_cached` | Cached nodes skipped | `{ prompt_id, nodes }` |
| `executing` | Node about to execute | `{ node, display_node, prompt_id }` |
| `executed` | Node returns UI element | `{ node, display_node, output, prompt_id }` |
| `progress` | During node execution | `{ node, prompt_id, value, max }` |
| `execution_success` | All nodes complete | `{ prompt_id, timestamp }` |
| `execution_error` | Runtime failure | Error details |
| `status` | Queue changes | `{ exec_info: { queue_remaining } }` |

**Source:** [ComfyUI Messages Documentation](https://docs.comfy.org/development/comfyui-server/comms_messages)

---

## 6. OUTPUT_NODE vs send_sync Relationship

### They Are Independent

| Feature | Purpose |
|---------|---------|
| `OUTPUT_NODE = True` | Marks node as terminal; ensures always executes; enables `{"ui": ...}` return |
| `send_sync` | Manual messaging - any node can call at any time |

### Can Use Together

```python
class MyNode:
    OUTPUT_NODE = True  # For the return value to trigger "executed"

    def process(self, data, unique_id=None):
        # Manual broadcast during processing
        PromptServer.instance.send_sync("my.progress", {"node": unique_id, "status": "working"})

        # ... processing ...

        # Auto-triggered "executed" via return
        return {"ui": {"images": results}}
```

---

## 7. Frontend Message Handling

### WebSocket Reception (api.ts)

```typescript
this.socket.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data);
  switch (msg.type) {
    case 'executed':
      this.dispatchCustomEvent(msg.type, msg.data);
      break;
    default:
      // Custom events dispatched if registered
      if (this._registered.has(msg.type)) {
        super.dispatchEvent(new CustomEvent(msg.type, { detail: msg.data }));
      }
  }
});
```

### Executed Event Handler (app.ts)

```typescript
api.addEventListener('executed', ({ detail }) => {
  const nodeOutputStore = useNodeOutputStore();
  const executionId = String(detail.display_node || detail.node);

  // Store output in node output store
  nodeOutputStore.setNodeOutputsByExecutionId(executionId, detail.output, {
    merge: detail.merge
  });

  // Call node's onExecuted callback if exists
  const node = getNodeByExecutionId(this.rootGraph, executionId);
  if (node && node.onExecuted) {
    node.onExecuted(detail.output);
  }
});
```

**Key Insight:** Frontend routes messages to nodes via `display_node` or `node` field.

---

## 8. Confirmed Root Cause

From [GitHub Issue #8395](https://github.com/Comfy-Org/ComfyUI/issues/8395):

> The issue was a missing `client_id` parameter. The user wasn't including the `client_id` in their prompt POST request, which prevented ComfyUI from routing completion messages back to their WebSocket connection.

**Our situation:** `trigger_next_queue()` creates a NEW `client_id` each time, so the frontend's WebSocket (with its own client_id) never receives updates.

**Our solution:** Broadcast with `sid=None` to ALL clients.

---

## 9. Complete Implementation Pattern

### Import Guard

```python
try:
    from server import PromptServer
    HAS_SERVER = True
except ImportError:
    PromptServer = None
    HAS_SERVER = False
```

### HIDDEN Input Declaration

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {...},
        "optional": {...},
        "hidden": {
            "unique_id": "UNIQUE_ID",
        }
    }
```

### Function Signature

```python
def save_image(self, image, ..., unique_id=None):
```

### Broadcast Call

```python
# After producing output, broadcast to ALL clients
if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None and unique_id is not None:
    PromptServer.instance.send_sync(
        "executed",
        {
            "node": unique_id,
            "output": {
                "images": [{"filename": filename, "subfolder": subfolder, "type": "output"}]
            },
        },
        sid=None  # CRITICAL: Broadcast to ALL clients
    )
```

---

## 10. Known Gotchas

### 1. UNIQUE_ID is a String
```python
# Correct
if unique_id is not None:

# Not needed (already a string)
str(unique_id)
```

### 2. Guard Against Missing PromptServer
```python
if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None:
```

### 3. Check unique_id Before Broadcast
```python
if unique_id is not None:
    # Send broadcast
```

### 4. Thread Safety
`send_sync` is thread-safe via `loop.call_soon_threadsafe()`.

### 5. Message Naming Convention
For custom events, use namespaced names: `"mypack.nodetype.event"`

---

## 11. Alternative Approaches (Not Recommended)

| Approach | Why Not |
|----------|---------|
| Pass client_id through entire chain | Invasive, complex |
| Frontend polling | Increases load, poor UX |
| Modify ComfyUI core | Unmaintainable |
| Custom WebSocket endpoint | Overkill for this use case |

---

## 12. Sources

### Primary (HIGH confidence)
- [ComfyUI server.py](https://github.com/comfyanonymous/ComfyUI/blob/master/server.py)
- [ComfyUI execution.py](https://github.com/comfyanonymous/ComfyUI/blob/master/execution.py)
- [ComfyUI Messages Documentation](https://docs.comfy.org/development/comfyui-server/comms_messages)
- [ComfyUI Hidden Inputs Documentation](https://docs.comfy.org/custom-nodes/backend/more_on_inputs)

### Secondary (MEDIUM confidence)
- [ComfyUI-Impact-Pack util_nodes.py](https://github.com/ltdrdata/ComfyUI-Impact-Pack/blob/Main/modules/impact/util_nodes.py)
- [pythongosssss ComfyUI-Custom-Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts/blob/main/pysssss.py)
- [GitHub Issue #8395 - client_id routing](https://github.com/Comfy-Org/ComfyUI/issues/8395)

### Tertiary (Supporting context)
- [ComfyUI Custom Nodes Walkthrough](https://docs.comfy.org/custom-nodes/walkthrough)
- [ComfyUI nodes.py - SaveImage](https://github.com/comfyanonymous/ComfyUI/blob/master/nodes.py)

---

## 13. Validation Checklist

Before implementation, confirm:
- [ ] Import guard pattern: `try/except` with `HAS_SERVER` flag
- [ ] HIDDEN input: `"unique_id": "UNIQUE_ID"` in INPUT_TYPES
- [ ] Function signature: `unique_id=None` parameter
- [ ] Broadcast call: `send_sync(..., sid=None)`
- [ ] Guard checks: `if HAS_SERVER and PromptServer is not None and PromptServer.instance is not None and unique_id is not None`
- [ ] Output format: `{"node": unique_id, "output": {...}}`
- [ ] Tests: Mock PromptServer.instance.send_sync

---

*Research compiled: 2026-02-02*
*Valid until: 2026-03-02 (check for ComfyUI API changes)*
