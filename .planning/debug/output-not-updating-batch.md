---
status: diagnosed
trigger: "UI outputs not updating between batch iterations despite correct processing"
created: 2026-02-02T12:00:00Z
updated: 2026-02-02T12:20:00Z
symptoms_prefilled: true
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - Programmatic queue via trigger_next_queue() creates new client_id each time, but frontend websocket only listens to its own client_id. Execution results go to the new client_id, so frontend never receives them.
test: Verified via ComfyUI documentation and source code analysis
expecting: N/A - hypothesis confirmed
next_action: Document root cause and suggested fix approaches

## Symptoms

expected: INDEX shows 0, 1, 2... as batch advances; PROGRESS_TEXT shows "1 of N", "2 of N", etc.; PreviewImage updates; SAVED_FILENAME/SAVED_PATH update
actual: INDEX shows "0" for all iterations; PROGRESS_TEXT shows "1 of N" always; PreviewImage shows first image; SAVED_FILENAME/SAVED_PATH show first file
errors: None - batch processes correctly (files are saved)
reproduction: Run batch with 3+ images; observe UI outputs after each iteration
started: Initial implementation - may have never worked correctly in UI

## Eliminated

## Evidence

- timestamp: 2026-02-02T12:01:00Z
  checked: BatchImageLoader.IS_CHANGED implementation
  found: Returns hash including index, queue_nonce, directory - changes each iteration
  implication: BatchImageLoader SHOULD re-execute each time

- timestamp: 2026-02-02T12:02:00Z
  checked: BatchProgressFormatter and BatchImageSaver for IS_CHANGED
  found: Neither node has IS_CHANGED defined
  implication: These downstream nodes rely on ComfyUI's default caching which only checks if inputs changed

- timestamp: 2026-02-02T12:03:00Z
  checked: How BatchImageLoader outputs connect to downstream nodes
  found: INDEX, TOTAL_COUNT wire to BatchProgressFormatter; OUTPUT_IMAGE, SAVED_FILENAME, SAVED_PATH are from BatchImageSaver
  implication: The cache issue is about whether ComfyUI recognizes these outputs as "changed"

- timestamp: 2026-02-02T12:04:00Z
  checked: ComfyUI caching documentation/discussions
  found: ComfyUI caches nodes based on IS_CHANGED return value; nodes without IS_CHANGED use input comparison; downstream nodes only re-execute if their inputs are considered "changed"
  implication: Even if BatchImageLoader re-executes, if ComfyUI's cache considers the output "unchanged" at the cache key level, downstream nodes won't re-run

- timestamp: 2026-02-02T12:10:00Z
  checked: ComfyUI PreviewImage frontend bugs
  found: Confirmed bug in ComfyUI frontend 1.13.1/1.13.2 where PreviewImage node doesn't show preview even when images are correctly generated (temp file exists). Fixed in 1.11.8.
  implication: Part of the UI not updating may be a known ComfyUI frontend bug, but doesn't explain STRING outputs (INDEX, PROGRESS_TEXT) not updating

- timestamp: 2026-02-02T12:11:00Z
  checked: Flow of trigger_next_queue and batch iteration
  found: Each batch iteration is a NEW queue execution via POST /prompt. Node outputs are returned per-execution but UI display may not refresh between separate queue executions.
  implication: The UI shows results from first queue execution; subsequent executions' results may not propagate to displayed widgets on screen

- timestamp: 2026-02-02T12:15:00Z
  checked: ComfyUI frontend/backend separation for widget display
  found: "The values of widgets are what is displayed in the browser and are serialized when the queue button is pressed. 'json_data' is a value only visible to the backend - manipulating this value affects the execution of the workflow but doesn't impact what is displayed in the browser."
  implication: CRITICAL - The browser UI shows serialized values from original queue press, NOT from backend execution results. Programmatically queued prompts don't update frontend widget displays.

- timestamp: 2026-02-02T12:16:00Z
  checked: How OUTPUT_NODE results get displayed
  found: OUTPUT_NODEs return {"ui": {...}, "result": (...)} dict. The "ui" part is sent via websocket to frontend. But for programmatic queue via /prompt API, frontend may not be listening to update the display for the NEW prompt_id.
  implication: The batch nodes are OUTPUT_NODEs and return correct "ui" data, but frontend doesn't display it because frontend isn't tracking the programmatically-generated prompt_id from trigger_next_queue().

## Resolution

root_cause: |
  CONFIRMED: ComfyUI architectural limitation in programmatic queue re-execution.

  **Primary Cause:**
  When trigger_next_queue() POSTs to /prompt, it creates a NEW client_id (uuid.uuid4()).
  The frontend (browser) websocket is connected with its OWN client_id. ComfyUI's execution_success
  message is sent with `broadcast=False`, meaning it only goes to the client_id that submitted the prompt.
  Since trigger_next_queue() uses a different client_id, the frontend never receives the execution results.

  **Location:** queue_control.py lines 97-102:
  ```python
  client_id = str(uuid.uuid4())  # <-- Creates NEW client_id each time
  payload = {
      "prompt": prompt,
      "client_id": client_id,  # <-- Frontend doesn't listen to this new client
  }
  ```

  **Secondary Issue:**
  Even if we fixed the client_id issue, ComfyUI's frontend display architecture has another limitation:
  "The values of widgets are what is displayed in the browser and are serialized when the queue button
  is pressed. 'json_data' is a value only visible to the backend - manipulating this value affects the
  execution of the workflow but doesn't impact what is displayed in the browser."

  This means the frontend captures node values at queue-time and displays those, not the actual
  execution results. OUTPUT_NODE's "ui" dict results are meant for showing generated images/text
  in output panels, but the INPUT values shown on nodes don't refresh.

  **Why Backend Works But UI Doesn't:**
  - Backend execution is 100% correct (files save, index advances, all nodes execute)
  - OUTPUT_NODE "ui" dicts are correctly returned by BatchImageSaver
  - But these results go to a different client_id than the frontend websocket
  - So frontend shows stale data from the first execution

fix: |
  **Approach 1: Get frontend's client_id and reuse it (PREFERRED)**
  Instead of generating new uuid, get the actual frontend client_id from the websocket connection
  and include it in trigger_next_queue(). This requires:
  - Capturing the frontend's client_id somehow (may need frontend integration)
  - Passing it through the prompt/execution chain
  - Using it in the /prompt POST

  **Approach 2: Use PromptServer.instance.send_sync with broadcast=True**
  The PromptServer has a send_sync() method that can broadcast to all clients.
  Nodes could send their own broadcast messages when their outputs change.
  This would require modifying the nodes to call PromptServer directly.

  **Approach 3: Frontend polling of /history endpoint**
  Instead of relying on websocket pushes, the frontend could poll /history/{prompt_id}
  to get execution results. This would require frontend JavaScript changes.

  **Approach 4: Accept UI limitation, focus on backend correctness**
  Document that the UI won't update during batch processing (known limitation),
  but the batch IS processing correctly. Users can check output folder for results.
  Add better logging/status output to console.

verification:
files_changed: []
