# ComfyUI Batch Image Processing

Custom nodes for batch processing images through ComfyUI pipelines. Load a directory of images, run your workflow once, and have each image processed and saved automatically.

## Installation

Clone this repository into your ComfyUI custom nodes directory:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/dchuk/comfyui-batch-image-processing.git
```

Restart ComfyUI. The nodes appear under the `batch_processing` category.

## Nodes

### Batch Image Loader

Loads images from a directory one at a time for batch processing.

**Inputs:**
- `directory` - Path to folder containing images
- `filter_preset` - All Images, PNG Only, JPG Only, or Custom
- `custom_pattern` - Glob patterns when using Custom filter (e.g., `*.png,*.jpg`)
- `iteration_mode` - Continue (resume) or Reset (start over)
- `error_handling` - Stop on error or Skip on error
- `start_index` - Starting position (0-based)

**Outputs:**
- `IMAGE` - Current image tensor
- `INPUT_DIRECTORY` - Source directory path
- `INPUT_BASE_NAME` - Filename without extension
- `INPUT_FILE_TYPE` - File extension (png, jpg, etc.)
- `FILENAME` - Full filename
- `INDEX` - Current position (0-based)
- `TOTAL_COUNT` - Total images in directory
- `STATUS` - Human-readable status message
- `BATCH_COMPLETE` - True when all images processed

### Batch Image Saver

Saves processed images with configurable naming and format options.

**Inputs:**
- `image` - Image tensor to save
- `output_directory` - Destination folder (wire from INPUT_DIRECTORY or leave empty for ComfyUI output)
- `output_base_name` - Base filename (wire from INPUT_BASE_NAME)
- `output_file_type` - Format: png, jpg, jpeg, or webp (wire from INPUT_FILE_TYPE)
- `filename_prefix` - Text to prepend (include your own separator, e.g., `upscaled_`)
- `filename_suffix` - Text to append (include your own separator, e.g., `_2x`)
- `quality` - JPG/WebP quality 1-100 (PNG ignores this)
- `overwrite_mode` - Overwrite, Skip, or Rename existing files

**Outputs:**
- `OUTPUT_IMAGE` - Passthrough of input image (for preview nodes)
- `SAVED_FILENAME` - Name of saved file
- `SAVED_PATH` - Full path to saved file

### Batch Progress Formatter

Formats progress information as human-readable text.

**Inputs:**
- `current_index` - Wire from INDEX
- `total_count` - Wire from TOTAL_COUNT

**Outputs:**
- `PROGRESS_TEXT` - Formatted as "X of Y (Z%)"

## How It Works

ComfyUI doesn't have native looping. These nodes implement a **queue-per-image** pattern:

1. **First execution**: BatchImageLoader reads the directory, loads image #0, and queues another workflow execution
2. **Subsequent executions**: The loader increments its index, loads the next image, and queues again
3. **Final execution**: When all images are processed, BATCH_COMPLETE becomes true and no new execution is queued

Each image flows through your entire pipeline before the next one starts. This means:
- Only one image is in memory at a time
- If ComfyUI crashes, already-saved images are safe
- You can interrupt anytime without losing completed work
- Any downstream nodes work normally (upscalers, ControlNet, etc.)

The UI updates live during processing via WebSocket broadcasts, so you see current progress without refreshing.

## Example Workflow

```
[Batch Image Loader] → [Your Processing Nodes] → [Batch Image Saver]
         ↓                                               ↓
  [Progress Formatter] → [Show Text]              [Preview Image]
```

Wire the loader's outputs to the saver's inputs:
- `INPUT_DIRECTORY` → `output_directory`
- `INPUT_BASE_NAME` → `output_base_name`
- `INPUT_FILE_TYPE` → `output_file_type`

This preserves original filenames. Add prefix/suffix for variants (e.g., `photo.jpg` → `upscaled_photo_2x.jpg`).

## License

MIT
