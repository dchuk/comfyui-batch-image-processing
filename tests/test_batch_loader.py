"""Tests for BatchImageLoader node."""

import os
import tempfile
from unittest.mock import patch

import pytest
import torch
from PIL import Image

# Import BatchImageLoader through the root package (as ComfyUI would)
# This is necessary because batch_loader.py uses relative imports like ..utils
from comfyui_batch_image_processing import NODE_CLASS_MAPPINGS
from comfyui_batch_image_processing.utils.iteration_state import IterationState

BatchImageLoader = NODE_CLASS_MAPPINGS["BatchImageLoader"]


@pytest.fixture(autouse=True)
def clear_iteration_state():
    """Clear iteration state before and after each test."""
    IterationState.clear_all()
    yield
    IterationState.clear_all()


class TestInputTypes:
    """Tests for INPUT_TYPES class method."""

    def test_returns_dict_with_required_optional_and_hidden(self):
        """INPUT_TYPES returns dict with required, optional, and hidden keys."""
        result = BatchImageLoader.INPUT_TYPES()
        assert isinstance(result, dict)
        assert "required" in result
        assert "optional" in result
        # hidden inputs for native queue control (prompt, extra_pnginfo, unique_id)
        assert "hidden" in result
        assert "prompt" in result["hidden"]
        assert "extra_pnginfo" in result["hidden"]
        assert "unique_id" in result["hidden"]

    def test_directory_is_required_string(self):
        """Directory input is a required STRING type."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "directory" in result["required"]
        directory_config = result["required"]["directory"]
        assert directory_config[0] == "STRING"

    def test_filter_preset_is_combo(self):
        """Filter preset is a combo box with expected options."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "filter_preset" in result["required"]
        preset_options = result["required"]["filter_preset"][0]
        assert "All Images" in preset_options
        assert "PNG Only" in preset_options
        assert "JPG Only" in preset_options
        assert "Custom" in preset_options

    def test_custom_pattern_is_optional(self):
        """Custom pattern is an optional STRING."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "custom_pattern" in result["optional"]

    def test_iteration_mode_is_required(self):
        """Iteration mode is a required combo with Continue/Reset options."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "iteration_mode" in result["required"]
        mode_options = result["required"]["iteration_mode"][0]
        assert "Continue" in mode_options
        assert "Reset" in mode_options

    def test_error_handling_is_required(self):
        """Error handling is a required combo with Stop/Skip options."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "error_handling" in result["required"]
        error_options = result["required"]["error_handling"][0]
        assert "Stop on error" in error_options
        assert "Skip on error" in error_options

    def test_start_index_is_optional(self):
        """Start index is an optional INT."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "start_index" in result["optional"]
        start_config = result["optional"]["start_index"]
        assert start_config[0] == "INT"


class TestValidateInputs:
    """Tests for VALIDATE_INPUTS class method."""

    def test_empty_directory_returns_error(self):
        """Empty directory returns error string."""
        result = BatchImageLoader.VALIDATE_INPUTS("", "All Images")
        assert isinstance(result, str)
        assert "required" in result.lower() or "Directory" in result

    def test_whitespace_directory_returns_error(self):
        """Whitespace-only directory returns error string."""
        result = BatchImageLoader.VALIDATE_INPUTS("   ", "All Images")
        assert isinstance(result, str)
        assert "required" in result.lower() or "Directory" in result

    def test_nonexistent_directory_returns_error(self):
        """Nonexistent directory returns error string with path."""
        result = BatchImageLoader.VALIDATE_INPUTS("/nonexistent/path", "All Images")
        assert isinstance(result, str)
        assert "not exist" in result.lower() or "nonexistent" in result.lower()

    def test_zero_matching_files_returns_error(self, temp_real_image_dir):
        """Directory with no matching files returns error."""
        result = BatchImageLoader.VALIDATE_INPUTS(
            temp_real_image_dir, "Custom", "Continue", "Stop on error", "*.gif"
        )
        assert isinstance(result, str)
        assert "no images" in result.lower() or "No images" in result

    def test_valid_directory_returns_true(self, temp_real_image_dir):
        """Valid directory with images returns True."""
        result = BatchImageLoader.VALIDATE_INPUTS(
            temp_real_image_dir, "All Images"
        )
        assert result is True


class TestLoadImage:
    """Tests for load_image method."""

    def test_returns_tuple_of_nine_elements(self, temp_real_image_dir):
        """load_image returns a tuple with exactly 9 elements."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        assert isinstance(result, tuple)
        assert len(result) == 9

    def test_image_is_torch_tensor(self, temp_real_image_dir):
        """IMAGE output is a torch.Tensor."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        image = result[0]
        assert isinstance(image, torch.Tensor)

    def test_image_shape_is_batch_height_width_channels(self, temp_real_image_dir):
        """IMAGE tensor has shape [1, H, W, 3]."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        image = result[0]
        assert len(image.shape) == 4
        assert image.shape[0] == 1  # Batch dimension
        assert image.shape[3] == 3  # RGB channels

    def test_total_count_matches_file_count(self, temp_real_image_dir):
        """TOTAL_COUNT matches number of matching files."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        total_count = result[1]
        # temp_real_image_dir has 3 PNG files
        assert total_count == 3

    def test_load_image_returns_0_based_index(self, temp_real_image_dir):
        """INDEX is 0-based (first image returns 0)."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        index = result[2]
        assert index == 0

    def test_filename_includes_extension(self, temp_real_image_dir):
        """FILENAME includes the file extension."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        filename = result[3]
        assert "." in filename
        assert filename.endswith(".png")

    def test_basename_excludes_extension(self, temp_real_image_dir):
        """BASENAME excludes the file extension."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        basename = result[4]
        assert "." not in basename
        assert basename.startswith("img")

    def test_source_directory_output_exists(self, temp_real_image_dir):
        """SOURCE_DIRECTORY output is a string matching the input directory."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        source_directory = result[5]
        assert isinstance(source_directory, str)
        # Should match the normalized input directory
        import os
        assert source_directory == os.path.normpath(temp_real_image_dir)

    def test_original_format_output_exists(self, temp_real_image_dir):
        """ORIGINAL_FORMAT output is a string with the file extension."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        original_format = result[6]
        assert isinstance(original_format, str)
        assert original_format == "png"  # Test images are PNG

    def test_status_output_exists(self, temp_real_image_dir):
        """STATUS output is a string."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        status = result[7]
        assert isinstance(status, str)
        assert status in ["processing", "completed"]

    def test_batch_complete_output_exists(self, temp_real_image_dir):
        """BATCH_COMPLETE output is a boolean."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        batch_complete = result[8]
        assert isinstance(batch_complete, bool)


class TestNaturalSortOrder:
    """Tests for natural sort ordering."""

    def test_natural_sort_order(self, temp_real_image_dir):
        """Files are loaded in natural sort order (img1, img2, img10)."""
        loader = BatchImageLoader()

        # First load - should be img1.png at index 0
        result = loader.load_image(temp_real_image_dir, "All Images")
        assert result[3] == "img1.png"
        assert result[2] == 0  # INDEX is 0-based

    def test_index_advances_with_state(self, temp_real_image_dir):
        """Index advances via internal state, not input parameter."""
        loader = BatchImageLoader()

        # First load - should be img1.png at index 0
        result = loader.load_image(temp_real_image_dir, "All Images")
        assert result[3] == "img1.png"
        assert result[2] == 0

        # Second load - state has advanced, should be img2.png at index 1
        result = loader.load_image(temp_real_image_dir, "All Images")
        assert result[3] == "img2.png"
        assert result[2] == 1


class TestFilterPresets:
    """Tests for filter preset functionality."""

    def test_png_only_filters_correctly(self, temp_mixed_image_dir):
        """PNG Only preset only returns PNG files."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_mixed_image_dir, "PNG Only")
        assert result[1] == 1  # Only 1 PNG file
        assert result[3].endswith(".png")

    def test_custom_pattern_works(self, temp_mixed_image_dir):
        """Custom pattern filters files correctly."""
        loader = BatchImageLoader()
        result = loader.load_image(
            temp_mixed_image_dir, "Custom", custom_pattern="*.jpg"
        )
        assert result[1] == 1  # Only 1 JPG file
        assert result[3].endswith(".jpg")


class TestIsChanged:
    """Tests for IS_CHANGED class method."""

    def test_returns_string(self):
        """IS_CHANGED returns a string."""
        result = BatchImageLoader.IS_CHANGED("/some/path", "All Images")
        assert isinstance(result, str)

    def test_different_inputs_different_result(self):
        """Different inputs produce different IS_CHANGED results."""
        result1 = BatchImageLoader.IS_CHANGED("/path1", "All Images")
        result2 = BatchImageLoader.IS_CHANGED("/path2", "All Images")
        assert result1 != result2

    def test_empty_directory_returns_empty_string(self):
        """Empty directory returns empty string."""
        result = BatchImageLoader.IS_CHANGED("", "All Images")
        assert result == ""


class TestIterationModes:
    """Tests for iteration mode behavior."""

    def test_iteration_mode_reset_starts_from_zero(self, temp_real_image_dir):
        """Reset mode always starts from index 0."""
        loader = BatchImageLoader()

        # First load with Continue mode - starts at 0
        result1 = loader.load_image(temp_real_image_dir, "All Images", "Continue")
        assert result1[2] == 0
        assert result1[3] == "img1.png"

        # Second load advances to index 1 (after first load advanced state)
        # Now use Reset mode - should start from 0 again
        result2 = loader.load_image(temp_real_image_dir, "All Images", "Reset")
        assert result2[2] == 0
        assert result2[3] == "img1.png"

    def test_iteration_mode_continue_preserves_position(self, temp_real_image_dir):
        """Continue mode preserves position across executions."""
        loader = BatchImageLoader()

        # First execution - index 0
        result1 = loader.load_image(temp_real_image_dir, "All Images", "Continue")
        assert result1[2] == 0

        # Second execution - index 1 (advanced by first)
        result2 = loader.load_image(temp_real_image_dir, "All Images", "Continue")
        assert result2[2] == 1

        # Third execution - index 2 (advanced by second)
        result3 = loader.load_image(temp_real_image_dir, "All Images", "Continue")
        assert result3[2] == 2


class TestBatchCompletion:
    """Tests for batch completion detection."""

    def test_batch_complete_true_on_last_image(self, temp_real_image_dir):
        """BATCH_COMPLETE is True only when processing last image."""
        loader = BatchImageLoader()

        # First image (index 0) - not complete
        result1 = loader.load_image(temp_real_image_dir, "All Images")
        assert result1[8] is False  # batch_complete

        # Second image (index 1) - not complete
        result2 = loader.load_image(temp_real_image_dir, "All Images")
        assert result2[8] is False  # batch_complete

        # Third/last image (index 2) - complete
        result3 = loader.load_image(temp_real_image_dir, "All Images")
        assert result3[8] is True  # batch_complete

    def test_status_output_processing_vs_completed(self, temp_real_image_dir):
        """STATUS is 'processing' for non-last images, 'completed' for last."""
        loader = BatchImageLoader()

        # First image - processing
        result1 = loader.load_image(temp_real_image_dir, "All Images")
        assert result1[7] == "processing"

        # Second image - processing
        result2 = loader.load_image(temp_real_image_dir, "All Images")
        assert result2[7] == "processing"

        # Third/last image - completed
        result3 = loader.load_image(temp_real_image_dir, "All Images")
        assert result3[7] == "completed"


class TestStartIndex:
    """Tests for start_index input."""

    def test_start_index_input(self, temp_real_image_dir):
        """start_index allows starting from specific position."""
        loader = BatchImageLoader()

        # Start at index 1 (second image)
        result = loader.load_image(
            temp_real_image_dir, "All Images", start_index=1
        )
        assert result[2] == 1  # INDEX should be 1
        assert result[3] == "img2.png"  # Second image

    def test_start_index_only_applies_when_state_is_zero(self, temp_real_image_dir):
        """start_index only applies if current state index is 0."""
        loader = BatchImageLoader()

        # First load with start_index=0 (default)
        result1 = loader.load_image(temp_real_image_dir, "All Images")
        assert result1[2] == 0

        # Second load with start_index=1 - should NOT jump to 1 because state is already 1
        result2 = loader.load_image(
            temp_real_image_dir, "All Images", start_index=1
        )
        assert result2[2] == 1  # Continues from state, not start_index


class TestDirectoryChange:
    """Tests for directory change detection."""

    def test_directory_change_resets_state(self, temp_real_image_dir, temp_mixed_image_dir):
        """Switching directories resets the state."""
        loader = BatchImageLoader()

        # Load from first directory, advance index
        result1 = loader.load_image(temp_real_image_dir, "All Images")
        assert result1[2] == 0

        # Load again to advance to index 1
        result2 = loader.load_image(temp_real_image_dir, "All Images")
        assert result2[2] == 1

        # Switch to second directory - should reset
        result3 = loader.load_image(temp_mixed_image_dir, "All Images")
        assert result3[2] == 0

        # Switch back to first directory - should also reset (different from last)
        result4 = loader.load_image(temp_real_image_dir, "All Images")
        assert result4[2] == 0


class TestErrorHandling:
    """Tests for error handling modes."""

    def test_error_handling_stop_on_error(self, temp_real_image_dir):
        """Stop on error raises exception when image fails."""
        loader = BatchImageLoader()

        # Create a temp dir with a corrupt file
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a corrupt "image" file
            corrupt_path = os.path.join(tmpdir, "corrupt.png")
            with open(corrupt_path, "w") as f:
                f.write("not an image")

            with pytest.raises(RuntimeError) as exc_info:
                loader.load_image(tmpdir, "All Images", error_handling="Stop on error")

            assert "Failed to load image" in str(exc_info.value)

    def test_error_handling_skip_on_error(self, temp_real_image_dir):
        """Skip on error continues to next image when one fails."""
        loader = BatchImageLoader()

        # Create a temp dir with a corrupt file and a valid file
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a corrupt "image" file (sorts first alphabetically)
            corrupt_path = os.path.join(tmpdir, "aaa_corrupt.png")
            with open(corrupt_path, "w") as f:
                f.write("not an image")

            # Create a valid image
            valid_path = os.path.join(tmpdir, "bbb_valid.png")
            img = Image.new("RGB", (50, 50), color="green")
            img.save(valid_path)

            # Should skip corrupt file and return valid one
            result = loader.load_image(
                tmpdir, "All Images", error_handling="Skip on error"
            )
            assert result[3] == "bbb_valid.png"

    def test_error_handling_all_files_fail(self):
        """Raises error when all files fail to load."""
        loader = BatchImageLoader()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only corrupt files
            for name in ["a.png", "b.png"]:
                path = os.path.join(tmpdir, name)
                with open(path, "w") as f:
                    f.write("not an image")

            with pytest.raises(RuntimeError) as exc_info:
                loader.load_image(
                    tmpdir, "All Images", error_handling="Skip on error"
                )

            assert "all files skipped or failed" in str(exc_info.value).lower()


class TestInterruption:
    """Tests for interruption behavior."""

    def test_interruption_continue_mode_preserves_index(self, temp_real_image_dir):
        """In Continue mode, state index is preserved for resume after interrupt."""
        loader = BatchImageLoader()

        # Simulate: load first image, then "interrupt" by not completing
        # In reality, ComfyUI interrupt just stops execution, we don't advance
        # This test verifies state persistence

        # First execution
        result1 = loader.load_image(temp_real_image_dir, "All Images", "Continue")
        assert result1[2] == 0

        # Simulate getting state before next execution (as would happen on resume)
        state = IterationState.get_state(temp_real_image_dir)
        # State should have advanced to 1 after first successful load
        assert state["index"] == 1

        # Second execution continues from 1
        result2 = loader.load_image(temp_real_image_dir, "All Images", "Continue")
        assert result2[2] == 1

    def test_interruption_reset_mode_clears_index(self, temp_real_image_dir):
        """Reset mode always clears index regardless of prior state."""
        loader = BatchImageLoader()

        # Advance the state
        loader.load_image(temp_real_image_dir, "All Images", "Continue")
        loader.load_image(temp_real_image_dir, "All Images", "Continue")

        # State should be at 2 now
        state = IterationState.get_state(temp_real_image_dir)
        assert state["index"] == 2

        # Reset mode should start from 0
        result = loader.load_image(temp_real_image_dir, "All Images", "Reset")
        assert result[2] == 0


class TestQueueControl:
    """Tests for queue control function calls."""

    @patch("comfyui_batch_image_processing.nodes.batch_loader.trigger_next_queue")
    def test_trigger_next_queue_called_when_not_complete(
        self, mock_trigger, temp_real_image_dir
    ):
        """trigger_next_queue is called when not on last image."""
        loader = BatchImageLoader()

        # Load first image (not last)
        loader.load_image(temp_real_image_dir, "All Images")

        mock_trigger.assert_called_once()

    @patch("comfyui_batch_image_processing.nodes.batch_loader.trigger_next_queue")
    def test_trigger_next_queue_not_called_on_last_image(
        self, mock_trigger, temp_real_image_dir
    ):
        """trigger_next_queue is NOT called on last image."""
        loader = BatchImageLoader()

        # Advance to last image
        loader.load_image(temp_real_image_dir, "All Images")  # 0
        mock_trigger.reset_mock()
        loader.load_image(temp_real_image_dir, "All Images")  # 1
        mock_trigger.reset_mock()

        # Last image
        loader.load_image(temp_real_image_dir, "All Images")  # 2 (last)

        mock_trigger.assert_not_called()

    @patch("comfyui_batch_image_processing.nodes.batch_loader.stop_auto_queue")
    def test_stop_auto_queue_called_on_batch_complete(
        self, mock_stop, temp_real_image_dir
    ):
        """stop_auto_queue is called when batch completes."""
        loader = BatchImageLoader()

        # Load all images until last
        loader.load_image(temp_real_image_dir, "All Images")  # 0
        loader.load_image(temp_real_image_dir, "All Images")  # 1
        mock_stop.assert_not_called()

        # Load last image
        loader.load_image(temp_real_image_dir, "All Images")  # 2 (last)

        mock_stop.assert_called_once()

    @patch("comfyui_batch_image_processing.nodes.batch_loader.stop_auto_queue")
    def test_stop_auto_queue_not_called_before_complete(
        self, mock_stop, temp_real_image_dir
    ):
        """stop_auto_queue is NOT called before batch completes."""
        loader = BatchImageLoader()

        # Load first two images (not last)
        loader.load_image(temp_real_image_dir, "All Images")
        loader.load_image(temp_real_image_dir, "All Images")

        mock_stop.assert_not_called()


class TestIndexWraparound:
    """Tests for index wraparound after batch completion."""

    def test_index_wraps_after_completion(self, temp_real_image_dir):
        """Index wraps back to 0 after batch completes."""
        loader = BatchImageLoader()

        # Process all 3 images
        loader.load_image(temp_real_image_dir, "All Images")  # 0
        loader.load_image(temp_real_image_dir, "All Images")  # 1
        result = loader.load_image(temp_real_image_dir, "All Images")  # 2 (last)
        assert result[8] is True  # batch_complete

        # Next load should wrap to 0
        result = loader.load_image(temp_real_image_dir, "All Images")
        assert result[2] == 0
        assert result[3] == "img1.png"
