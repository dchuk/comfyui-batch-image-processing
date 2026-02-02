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

    def test_output_file_type_is_optional_string(self):
        """Output file type is an optional STRING with default 'png'."""
        result = BatchImageSaver.INPUT_TYPES()
        assert "output_file_type" in result["optional"]
        config = result["optional"]["output_file_type"]
        assert config[0] == "STRING"
        assert config[1]["default"] == "png"

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
        assert "output_base_name" in optional
        assert "output_file_type" in optional
        assert "filename_prefix" in optional
        assert "filename_suffix" in optional


class TestClassAttributes:
    """Tests for class attributes."""

    def test_category(self):
        """CATEGORY is batch_processing."""
        assert BatchImageSaver.CATEGORY == "batch_processing"

    def test_return_types_has_outputs(self):
        """RETURN_TYPES has IMAGE and STRING outputs for downstream wiring."""
        assert BatchImageSaver.RETURN_TYPES == ("IMAGE", "STRING", "STRING")

    def test_function_name(self):
        """FUNCTION is save_image."""
        assert BatchImageSaver.FUNCTION == "save_image"

    def test_output_node_is_true(self):
        """OUTPUT_NODE is True."""
        assert BatchImageSaver.OUTPUT_NODE is True


class TestReturnNames:
    """Tests for RETURN_NAMES attribute."""

    def test_return_names_defined(self):
        """RETURN_NAMES has correct output names."""
        assert BatchImageSaver.RETURN_NAMES == ("OUTPUT_IMAGE", "SAVED_FILENAME", "SAVED_PATH")


class TestSaveImageReturns:
    """Tests for save_image return values."""

    def test_returns_result_tuple(self, temp_output_dir):
        """save_image returns result tuple with image, filename, path."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="test_returns",
        )

        # Check result structure - must have both "ui" and "result" keys
        assert "ui" in result
        assert "result" in result
        assert len(result["result"]) == 3

        # Check result values
        output_image, saved_filename, saved_path = result["result"]

        # Image should be the SAME tensor reference (passthrough, not a copy)
        assert output_image is tensor

        # Filename should be just the filename (no path)
        assert saved_filename == "test_returns.png"

        # Path should be full absolute path
        assert saved_path == os.path.join(temp_output_dir, "test_returns.png")

    def test_skip_mode_returns_empty_strings(self, temp_output_dir):
        """Skip mode returns empty strings for filename/path but still passes image."""
        # Create existing file to trigger skip
        filepath = os.path.join(temp_output_dir, "existing.png")
        Image.new("RGB", (50, 50), color="red").save(filepath)

        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_file_type="png",
            quality=100,
            overwrite_mode="Skip",
            output_directory=temp_output_dir,
            output_base_name="existing",
        )

        # Check result structure
        assert "result" in result
        output_image, saved_filename, saved_path = result["result"]

        # Image STILL passes through even when skipped (for downstream preview)
        assert output_image is tensor

        # Filename and path are empty strings (not None) when skipped
        assert saved_filename == ""
        assert saved_path == ""

    def test_rename_mode_returns_renamed_path(self, temp_output_dir):
        """Rename mode returns the actual renamed filename and path."""
        # Create existing file to trigger rename
        filepath = os.path.join(temp_output_dir, "photo.png")
        Image.new("RGB", (50, 50), color="red").save(filepath)

        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_file_type="png",
            quality=100,
            overwrite_mode="Rename",
            output_directory=temp_output_dir,
            output_base_name="photo",
        )

        output_image, saved_filename, saved_path = result["result"]

        # Image passes through
        assert output_image is tensor

        # Should return the RENAMED filename (photo_1.png)
        assert saved_filename == "photo_1.png"
        assert saved_path == os.path.join(temp_output_dir, "photo_1.png")


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
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="test_image",
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
            output_file_type="jpg",
            quality=85,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="test_jpg",
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
            output_file_type="webp",
            quality=90,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="test_webp",
        )

        filepath = os.path.join(temp_output_dir, "test_webp.webp")
        assert os.path.exists(filepath)

        img = Image.open(filepath)
        assert img.format == "WEBP"
        img.close()


class TestJpegExtensionPreserved:
    """Tests for preserving .jpeg extension."""

    def test_jpeg_extension_preserved(self, temp_output_dir):
        """Jpeg file type creates .jpeg file (not .jpg)."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32) * 0.5

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_file_type="jpeg",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="photo",
        )

        # Should be .jpeg, NOT .jpg
        filepath = os.path.join(temp_output_dir, "photo.jpeg")
        assert os.path.exists(filepath), "Expected .jpeg extension to be preserved"
        # Verify .jpg was NOT created
        jpg_path = os.path.join(temp_output_dir, "photo.jpg")
        assert not os.path.exists(jpg_path), "Should not normalize .jpeg to .jpg"

    def test_empty_file_type_defaults_to_png(self, temp_output_dir):
        """Empty file type defaults to PNG."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_file_type="",  # Empty format
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="noformat",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="photo",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="photo",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="photo",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Skip",
            output_directory=temp_output_dir,
            output_base_name="existing",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Rename",
            output_directory=temp_output_dir,
            output_base_name="photo",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Rename",
            output_directory=temp_output_dir,
            output_base_name="photo",
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
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=nested_dir,
            output_base_name="deep",
        )

        assert os.path.exists(os.path.join(nested_dir, "deep.png"))

    def test_default_directory_uses_comfy_output(self, temp_output_dir):
        """When no output_directory, uses ComfyUI output directory."""
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
                output_file_type="png",
                quality=100,
                overwrite_mode="Overwrite",
                output_directory="",  # Empty - use default
                output_base_name="test",
            )

            # Should save to temp_output_dir/test.png
            expected_path = os.path.join(temp_output_dir, "test.png")
            assert os.path.exists(expected_path)

    def test_relative_path_prepends_comfy_output(self, temp_output_dir):
        """Relative path (wired from loader) is prepended with ComfyUI output dir."""
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
                output_file_type="png",
                quality=100,
                overwrite_mode="Overwrite",
                output_directory="images",  # Relative path (wired from loader)
                output_base_name="test",
            )

            # Should save to temp_output_dir/images/test.png
            expected_path = os.path.join(temp_output_dir, "images", "test.png")
            assert os.path.exists(expected_path), f"Expected {expected_path} to exist"

    def test_absolute_path_used_directly(self, temp_output_dir):
        """Absolute path is used directly without modification."""
        import comfyui_batch_image_processing.nodes.batch_saver as batch_saver_module

        # Create a separate directory for the absolute path test
        absolute_dir = os.path.join(temp_output_dir, "absolute_test")
        os.makedirs(absolute_dir, exist_ok=True)

        with mock.patch.object(
            batch_saver_module, "folder_paths", create=True
        ) as mock_folder_paths:
            mock_folder_paths.get_output_directory.return_value = temp_output_dir

            tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

            saver = BatchImageSaver()
            saver.save_image(
                image=tensor,
                output_file_type="png",
                quality=100,
                overwrite_mode="Overwrite",
                output_directory=absolute_dir,  # Absolute path
                output_base_name="test",
            )

            # Should save directly to absolute_dir/test.png, NOT temp_output_dir/absolute_test/test.png
            expected_path = os.path.join(absolute_dir, "test.png")
            assert os.path.exists(expected_path), f"Expected {expected_path} to exist"


class TestFallbackFilename:
    """Tests for fallback filename generation."""

    def test_generates_fallback_when_no_original(self, temp_output_dir):
        """Generates output_NNNN when no output_base_name provided."""
        tensor = torch.ones(1, 50, 50, 3, dtype=torch.float32)

        saver = BatchImageSaver()
        result = saver.save_image(
            image=tensor,
            output_file_type="png",
            quality=100,
            overwrite_mode="Overwrite",
            output_directory=temp_output_dir,
            output_base_name="",  # Empty
        )

        # Filename should start with "output_" and have .png extension
        filename = result["ui"]["images"][0]["filename"]
        assert filename.startswith("output_")
        assert filename.endswith(".png")
        # Check file exists
        assert os.path.exists(os.path.join(temp_output_dir, filename))
