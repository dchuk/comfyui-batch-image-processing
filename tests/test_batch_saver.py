"""Tests for BatchImageSaver node."""

import os
import tempfile
from unittest import mock

import pytest
import torch
from PIL import Image

# Import BatchImageSaver through the root package (as ComfyUI would)
from comfyui_batch_image_processing import NODE_CLASS_MAPPINGS

BatchImageSaver = NODE_CLASS_MAPPINGS["BatchImageSaver"]


class TestInputTypes:
    """Tests for INPUT_TYPES class method."""

    def test_returns_dict_with_required_and_optional(self):
        """INPUT_TYPES returns dict with required and optional keys."""
        result = BatchImageSaver.INPUT_TYPES()
        assert isinstance(result, dict)
        assert "required" in result
        assert "optional" in result

    def test_image_is_required(self):
        """Image input is required."""
        result = BatchImageSaver.INPUT_TYPES()
        assert "image" in result["required"]
        assert result["required"]["image"][0] == "IMAGE"

    def test_output_format_is_combo(self):
        """Output format is a combo with expected options."""
        result = BatchImageSaver.INPUT_TYPES()
        assert "output_format" in result["required"]
        options = result["required"]["output_format"][0]
        assert "Match original" in options
        assert "PNG" in options
        assert "JPG" in options
        assert "WebP" in options

    def test_quality_is_int_with_range(self):
        """Quality is an INT with 1-100 range."""
        result = BatchImageSaver.INPUT_TYPES()
        assert "quality" in result["required"]
        quality_config = result["required"]["quality"]
        assert quality_config[0] == "INT"
        assert quality_config[1]["min"] == 1
        assert quality_config[1]["max"] == 100
        assert quality_config[1]["default"] == 100

    def test_overwrite_mode_is_combo(self):
        """Overwrite mode is a combo with expected options."""
        result = BatchImageSaver.INPUT_TYPES()
        assert "overwrite_mode" in result["required"]
        options = result["required"]["overwrite_mode"][0]
        assert "Overwrite" in options
        assert "Skip" in options
        assert "Rename" in options

    def test_optional_fields_exist(self):
        """All optional fields are present."""
        result = BatchImageSaver.INPUT_TYPES()
        optional = result["optional"]
        assert "output_directory" in optional
        assert "filename_prefix" in optional
        assert "filename_suffix" in optional
        assert "original_filename" in optional
        assert "source_directory" in optional
        assert "original_format" in optional


class TestClassAttributes:
    """Tests for class attributes."""

    def test_category(self):
        """CATEGORY is batch_processing."""
        assert BatchImageSaver.CATEGORY == "batch_processing"

    def test_return_types_empty(self):
        """RETURN_TYPES is empty tuple (output node)."""
        assert BatchImageSaver.RETURN_TYPES == ()

    def test_function_name(self):
        """FUNCTION is save_image."""
        assert BatchImageSaver.FUNCTION == "save_image"

    def test_output_node_is_true(self):
        """OUTPUT_NODE is True."""
        assert BatchImageSaver.OUTPUT_NODE is True


class TestSaveImagePng:
    """Tests for save_image with PNG format."""

    def test_save_png_basic(self, temp_output_dir):
        """Save image as PNG creates valid file."""
        # Create a test tensor
        tensor = torch.zeros(1, 100, 100, 3, dtype=torch.float32)
        tensor[:, :, :, 0] = 1.0  # Red

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="test_image",
        )

        # Check file was created
        filepath = os.path.join(temp_output_dir, "test_image.png")
        assert os.path.exists(filepath)

        # Check it's a valid PNG
        img = Image.open(filepath)
        assert img.format == "PNG"
        img.close()

        # Check return value
        assert "ui" in result
        assert "images" in result["ui"]
        assert len(result["ui"]["images"]) == 1
        assert result["ui"]["images"][0]["filename"] == "test_image.png"


class TestSaveImageJpg:
    """Tests for save_image with JPG format."""

    def test_save_jpg_basic(self, temp_output_dir):
        """Save image as JPG creates valid file."""
        tensor = torch.zeros(1, 100, 100, 3, dtype=torch.float32)
        tensor[:, :, :, 1] = 1.0  # Green

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="JPG",
            quality=85,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="test_jpg",
        )

        filepath = os.path.join(temp_output_dir, "test_jpg.jpg")
        assert os.path.exists(filepath)

        img = Image.open(filepath)
        assert img.format == "JPEG"
        img.close()


class TestSaveImageWebp:
    """Tests for save_image with WebP format."""

    def test_save_webp_basic(self, temp_output_dir):
        """Save image as WebP creates valid file."""
        tensor = torch.zeros(1, 100, 100, 3, dtype=torch.float32)
        tensor[:, :, :, 2] = 1.0  # Blue

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="WebP",
            quality=90,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="test_webp",
        )

        filepath = os.path.join(temp_output_dir, "test_webp.webp")
        assert os.path.exists(filepath)

        img = Image.open(filepath)
        assert img.format == "WEBP"
        img.close()


class TestMatchOriginalFormat:
    """Tests for 'Match original' format option."""

    def test_match_original_jpg(self, temp_output_dir):
        """Match original with jpg format creates .jpg file."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32) * 0.5

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="Match original",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="photo",
            original_format="jpg",
        )

        filepath = os.path.join(temp_output_dir, "photo.jpg")
        assert os.path.exists(filepath)

    def test_match_original_defaults_to_png(self, temp_output_dir):
        """Match original without format defaults to PNG."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="Match original",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="noformat",
            original_format="",  # Empty format
        )

        filepath = os.path.join(temp_output_dir, "noformat.png")
        assert os.path.exists(filepath)


class TestFilenameConstruction:
    """Tests for filename prefix/suffix."""

    def test_prefix_applied(self, temp_output_dir):
        """Prefix is applied to filename."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="photo",
            filename_prefix="upscaled_",
        )

        filepath = os.path.join(temp_output_dir, "upscaled_photo.png")
        assert os.path.exists(filepath)

    def test_suffix_applied(self, temp_output_dir):
        """Suffix is applied to filename."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="photo",
            filename_suffix="_2x",
        )

        filepath = os.path.join(temp_output_dir, "photo_2x.png")
        assert os.path.exists(filepath)

    def test_prefix_and_suffix_combined(self, temp_output_dir):
        """Both prefix and suffix are applied."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="photo",
            filename_prefix="upscaled_",
            filename_suffix="_2x",
        )

        filepath = os.path.join(temp_output_dir, "upscaled_photo_2x.png")
        assert os.path.exists(filepath)


class TestOverwriteSkipMode:
    """Tests for Skip overwrite mode."""

    def test_skip_mode_does_not_overwrite(self, temp_output_dir):
        """Skip mode leaves existing file unchanged."""
        filepath = os.path.join(temp_output_dir, "existing.png")

        # Create existing file with known content
        original_img = Image.new("RGB", (50, 50), color="red")
        original_img.save(filepath)
        original_size = os.path.getsize(filepath)

        # Try to save different image with Skip mode
        tensor = torch.ones(1, 100, 100, 3, dtype=torch.float32)  # Larger image

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Skip",
            output_directory=temp_output_dir,
            original_filename="existing",
        )

        # File should be unchanged
        assert os.path.getsize(filepath) == original_size

        # Result should have empty images list
        assert result["ui"]["images"] == []


class TestOverwriteRenameMode:
    """Tests for Rename overwrite mode."""

    def test_rename_mode_creates_new_file(self, temp_output_dir):
        """Rename mode creates new file with _1 suffix."""
        filepath = os.path.join(temp_output_dir, "photo.png")

        # Create existing file
        original_img = Image.new("RGB", (50, 50), color="red")
        original_img.save(filepath)

        # Save new image with Rename mode
        tensor = torch.ones(1, 100, 100, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Rename",
            output_directory=temp_output_dir,
            original_filename="photo",
        )

        # Original should still exist
        assert os.path.exists(filepath)

        # New file should exist with _1 suffix
        renamed_path = os.path.join(temp_output_dir, "photo_1.png")
        assert os.path.exists(renamed_path)

        # Result should reference the renamed file
        assert result["ui"]["images"][0]["filename"] == "photo_1.png"

    def test_rename_mode_increments_counter(self, temp_output_dir):
        """Rename mode finds next available number."""
        # Create existing files
        for i in ["", "_1", "_2"]:
            filepath = os.path.join(temp_output_dir, f"photo{i}.png")
            Image.new("RGB", (50, 50), color="red").save(filepath)

        # Save new image with Rename mode
        tensor = torch.ones(1, 100, 100, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Rename",
            output_directory=temp_output_dir,
            original_filename="photo",
        )

        # Should create photo_3.png
        assert result["ui"]["images"][0]["filename"] == "photo_3.png"
        assert os.path.exists(os.path.join(temp_output_dir, "photo_3.png"))


class TestDefaultOutputDirectory:
    """Tests for default output directory resolution."""

    def test_creates_output_directory(self, temp_output_dir):
        """Output directory is created if it doesn't exist."""
        nested_dir = os.path.join(temp_output_dir, "a", "b", "c")

        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=nested_dir,
            original_filename="deep",
        )

        assert os.path.exists(os.path.join(nested_dir, "deep.png"))

    def test_default_directory_uses_source_folder_name(self, temp_output_dir):
        """When no output_directory, uses source folder name as subfolder."""
        # Mock folder_paths.get_output_directory to return temp_output_dir
        import comfyui_batch_image_processing.nodes.batch_saver as batch_saver_module

        with mock.patch.object(
            batch_saver_module, "folder_paths", create=True
        ) as mock_folder_paths:
            mock_folder_paths.get_output_directory.return_value = temp_output_dir

            tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

            saver = BatchImageSaver()
            saver.save_image(
                image=tensor,
                output_format="PNG",
                quality=100,
                overwrite_mode="Overwrite",
                output_directory="",  # Empty - use default
                original_filename="test",
                source_directory="/path/to/vacation",  # Source folder name is "vacation"
            )

            # Should save to temp_output_dir/vacation/test.png
            expected_path = os.path.join(temp_output_dir, "vacation", "test.png")
            assert os.path.exists(expected_path)


class TestFallbackFilename:
    """Tests for fallback filename generation."""

    def test_generates_fallback_when_no_original(self, temp_output_dir):
        """Generates output_NNNN when no original_filename provided."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_format="PNG",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            original_filename="",  # Empty
        )

        # Filename should start with "output_" and have .png extension
        filename = result["ui"]["images"][0]["filename"]
        assert filename.startswith("output_")
        assert filename.endswith(".png")
        # Check file exists
        assert os.path.exists(os.path.join(temp_output_dir, filename))
