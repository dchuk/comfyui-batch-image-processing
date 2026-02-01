"""Tests for BatchImageLoader node."""

import os
import sys
import tempfile

import pytest
import torch
from PIL import Image

# Import BatchImageLoader through the root package (as ComfyUI would)
# This is necessary because batch_loader.py uses relative imports like ..utils
from comfyui_batch_image_processing import NODE_CLASS_MAPPINGS

BatchImageLoader = NODE_CLASS_MAPPINGS["BatchImageLoader"]


class TestInputTypes:
    """Tests for INPUT_TYPES class method."""

    def test_returns_dict_with_required_and_optional(self):
        """INPUT_TYPES returns dict with required, optional, and hidden keys."""
        result = BatchImageLoader.INPUT_TYPES()
        assert isinstance(result, dict)
        assert "required" in result
        assert "optional" in result
        assert "hidden" in result

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

    def test_current_index_is_hidden(self):
        """Current index is hidden for iteration control."""
        result = BatchImageLoader.INPUT_TYPES()
        assert "current_index" in result["hidden"]


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
            temp_real_image_dir, "Custom", "*.gif"  # No GIF files exist
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

    def test_returns_tuple_of_five_elements(self, temp_real_image_dir):
        """load_image returns a tuple with exactly 5 elements."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images")
        assert isinstance(result, tuple)
        assert len(result) == 5

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

    def test_current_index_is_one_based(self, temp_real_image_dir):
        """CURRENT_INDEX is 1-based (first image returns 1)."""
        loader = BatchImageLoader()
        result = loader.load_image(temp_real_image_dir, "All Images", current_index=0)
        current_index = result[2]
        assert current_index == 1

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


class TestNaturalSortOrder:
    """Tests for natural sort ordering."""

    def test_natural_sort_order(self, temp_real_image_dir):
        """Files are loaded in natural sort order (img1, img2, img10)."""
        loader = BatchImageLoader()

        # Load at index 0 - should be img1.png
        result = loader.load_image(temp_real_image_dir, "All Images", current_index=0)
        assert result[3] == "img1.png"

        # Load at index 1 - should be img2.png (not img10.png)
        result = loader.load_image(temp_real_image_dir, "All Images", current_index=1)
        assert result[3] == "img2.png"

        # Load at index 2 - should be img10.png
        result = loader.load_image(temp_real_image_dir, "All Images", current_index=2)
        assert result[3] == "img10.png"

    def test_index_wraparound(self, temp_real_image_dir):
        """Index wraps around when exceeding total count."""
        loader = BatchImageLoader()

        # Index 3 should wrap to index 0 (3 files total)
        result = loader.load_image(temp_real_image_dir, "All Images", current_index=3)
        assert result[3] == "img1.png"
        assert result[2] == 1  # CURRENT_INDEX should be 1 (wrapped)


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
        result = loader.load_image(temp_mixed_image_dir, "Custom", "*.jpg")
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

    def test_same_inputs_same_result(self):
        """Same inputs produce same IS_CHANGED result."""
        result1 = BatchImageLoader.IS_CHANGED("/path", "All Images", "*.png", 0)
        result2 = BatchImageLoader.IS_CHANGED("/path", "All Images", "*.png", 0)
        assert result1 == result2
