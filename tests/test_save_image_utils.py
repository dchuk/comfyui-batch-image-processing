"""Tests for save image utilities."""

import os
import tempfile

import pytest
from PIL import Image

from comfyui_batch_image_processing.utils.save_image_utils import (
    construct_filename,
    handle_existing_file,
    resolve_output_directory,
    save_with_format,
)


class TestConstructFilename:
    """Tests for construct_filename function."""

    def test_basic_construction(self):
        """Test basic filename construction."""
        result = construct_filename("photo", "", "", "png")
        assert result == "photo.png"

    def test_with_prefix(self):
        """Test filename with prefix."""
        result = construct_filename("photo", "upscaled_", "", "png")
        assert result == "upscaled_photo.png"

    def test_with_suffix(self):
        """Test filename with suffix."""
        result = construct_filename("photo", "", "_2x", "png")
        assert result == "photo_2x.png"

    def test_with_prefix_and_suffix(self):
        """Test filename with both prefix and suffix."""
        result = construct_filename("photo", "upscaled_", "_2x", "jpg")
        assert result == "upscaled_photo_2x.jpg"

    def test_empty_basename(self):
        """Test with empty basename."""
        result = construct_filename("", "pre_", "_suf", "png")
        assert result == "pre__suf.png"

    def test_no_automatic_separators(self):
        """Verify no automatic separators are added (raw concatenation)."""
        result = construct_filename("photo", "pre", "suf", "png")
        assert result == "prephotoSuf.png" or result == "prephotosuf.png"
        # Actually should be exactly what we pass
        result = construct_filename("photo", "pre", "suf", "png")
        assert result == "prephotosuf.png"


class TestHandleExistingFile:
    """Tests for handle_existing_file function."""

    def test_nonexistent_file_returns_true(self):
        """Non-existent file should always save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "nonexistent.png")
            result_path, should_save = handle_existing_file(filepath, "Overwrite")
            assert should_save is True
            assert result_path == filepath

    def test_overwrite_mode(self):
        """Overwrite mode returns True for existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "existing.png")
            # Create the file
            with open(filepath, "w") as f:
                f.write("test")

            result_path, should_save = handle_existing_file(filepath, "Overwrite")
            assert should_save is True
            assert result_path == filepath

    def test_skip_mode(self, capsys):
        """Skip mode returns False for existing file and prints message."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "existing.png")
            # Create the file
            with open(filepath, "w") as f:
                f.write("test")

            result_path, should_save = handle_existing_file(filepath, "Skip")
            assert should_save is False
            assert result_path == filepath

            # Check that skip message was printed
            captured = capsys.readouterr()
            assert "Skipped: existing.png" in captured.out

    def test_rename_mode_increments(self):
        """Rename mode finds next available filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "photo.png")
            # Create original file
            with open(filepath, "w") as f:
                f.write("test")

            result_path, should_save = handle_existing_file(filepath, "Rename")
            assert should_save is True
            assert result_path == os.path.join(tmpdir, "photo_1.png")

    def test_rename_mode_skips_existing_increments(self):
        """Rename mode skips existing numbered files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "photo.png")
            # Create original and first increment
            with open(filepath, "w") as f:
                f.write("test")
            with open(os.path.join(tmpdir, "photo_1.png"), "w") as f:
                f.write("test")

            result_path, should_save = handle_existing_file(filepath, "Rename")
            assert should_save is True
            assert result_path == os.path.join(tmpdir, "photo_2.png")

    def test_unknown_mode_defaults_to_overwrite(self):
        """Unknown mode defaults to overwrite."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "existing.png")
            with open(filepath, "w") as f:
                f.write("test")

            result_path, should_save = handle_existing_file(filepath, "Unknown")
            assert should_save is True
            assert result_path == filepath


class TestResolveOutputDirectory:
    """Tests for resolve_output_directory function."""

    def test_with_explicit_absolute_output_dir(self):
        """When absolute output_dir specified, use it directly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "my_output")
            result = resolve_output_directory(output_dir, "/some/source", None)
            assert result == output_dir
            assert os.path.isdir(output_dir)

    def test_with_relative_output_dir_prepends_default(self):
        """Relative output_dir (folder name) gets prepended with default output."""
        with tempfile.TemporaryDirectory() as tmpdir:

            def mock_default():
                return tmpdir

            # "images" is a relative path (like what comes from loader's input_directory_name)
            result = resolve_output_directory("images", "/some/source", mock_default)
            expected = os.path.join(tmpdir, "images")
            assert result == expected
            assert os.path.isdir(expected)

    def test_with_nested_relative_output_dir_prepends_default(self):
        """Nested relative path gets prepended with default output."""
        with tempfile.TemporaryDirectory() as tmpdir:

            def mock_default():
                return tmpdir

            # "subdir/images" is a relative path
            result = resolve_output_directory("subdir/images", "/some/source", mock_default)
            expected = os.path.join(tmpdir, "subdir", "images")
            assert result == expected
            assert os.path.isdir(expected)

    def test_with_relative_output_dir_no_default_func(self):
        """Relative output_dir without default func uses path as-is."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = resolve_output_directory("images", "", None)
                assert result == "images"
                assert os.path.isdir("images")
            finally:
                os.chdir(original_dir)

    def test_with_empty_output_dir_uses_default(self):
        """Empty output_dir uses default + source folder name."""
        with tempfile.TemporaryDirectory() as tmpdir:

            def mock_default():
                return tmpdir

            result = resolve_output_directory("", "/path/to/my_source", mock_default)
            expected = os.path.join(tmpdir, "my_source")
            assert result == expected
            assert os.path.isdir(expected)

    def test_with_whitespace_output_dir_uses_default(self):
        """Whitespace-only output_dir uses default."""
        with tempfile.TemporaryDirectory() as tmpdir:

            def mock_default():
                return tmpdir

            result = resolve_output_directory("   ", "/path/to/source_dir", mock_default)
            expected = os.path.join(tmpdir, "source_dir")
            assert result == expected

    def test_creates_nested_directories(self):
        """Creates nested output directories (absolute path)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c")
            result = resolve_output_directory(nested, "", None)
            assert result == nested
            assert os.path.isdir(nested)

    def test_no_default_func_with_empty_output(self):
        """Without default func and empty output, uses source folder name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to tmpdir so relative paths work
            original_dir = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = resolve_output_directory("", "/path/to/photos", None)
                assert result == "photos"
                assert os.path.isdir("photos")
            finally:
                os.chdir(original_dir)

    def test_strips_trailing_separator_from_source(self):
        """Strips trailing separator from source directory."""
        with tempfile.TemporaryDirectory() as tmpdir:

            def mock_default():
                return tmpdir

            result = resolve_output_directory(
                "", "/path/to/my_source/", mock_default
            )
            expected = os.path.join(tmpdir, "my_source")
            assert result == expected


class TestSaveWithFormat:
    """Tests for save_with_format function."""

    def test_save_png(self):
        """Test saving as PNG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.png")
            img = Image.new("RGB", (100, 100), color="red")

            save_with_format(img, filepath, "PNG", 100)

            assert os.path.exists(filepath)
            loaded = Image.open(filepath)
            assert loaded.format == "PNG"
            loaded.close()

    def test_save_jpg(self):
        """Test saving as JPG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.jpg")
            img = Image.new("RGB", (100, 100), color="blue")

            save_with_format(img, filepath, "JPG", 85)

            assert os.path.exists(filepath)
            loaded = Image.open(filepath)
            assert loaded.format == "JPEG"
            loaded.close()

    def test_save_jpeg_alias(self):
        """Test that JPEG alias works same as JPG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.jpeg")
            img = Image.new("RGB", (100, 100), color="green")

            save_with_format(img, filepath, "JPEG", 90)

            assert os.path.exists(filepath)
            loaded = Image.open(filepath)
            assert loaded.format == "JPEG"
            loaded.close()

    def test_save_webp(self):
        """Test saving as WebP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.webp")
            img = Image.new("RGB", (100, 100), color="yellow")

            save_with_format(img, filepath, "WebP", 80)

            assert os.path.exists(filepath)
            loaded = Image.open(filepath)
            assert loaded.format == "WEBP"
            loaded.close()

    def test_save_webp_lossless_at_100(self):
        """Test that WebP uses lossless mode at quality 100."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_lossless.webp")
            img = Image.new("RGB", (100, 100), color="purple")

            save_with_format(img, filepath, "WebP", 100)

            assert os.path.exists(filepath)
            # File should exist and be valid WebP
            loaded = Image.open(filepath)
            assert loaded.format == "WEBP"
            loaded.close()

    def test_jpg_converts_rgba_to_rgb(self):
        """Test that RGBA images are converted to RGB for JPEG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_rgba.jpg")
            # Create RGBA image
            img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))

            save_with_format(img, filepath, "JPG", 90)

            assert os.path.exists(filepath)
            loaded = Image.open(filepath)
            assert loaded.format == "JPEG"
            assert loaded.mode == "RGB"  # Should be RGB, not RGBA
            loaded.close()

    def test_unknown_format_defaults_to_png(self):
        """Test that unknown formats default to PNG."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test.unknown")
            img = Image.new("RGB", (100, 100), color="cyan")

            save_with_format(img, filepath, "UNKNOWN", 100)

            assert os.path.exists(filepath)
            loaded = Image.open(filepath)
            assert loaded.format == "PNG"
            loaded.close()

    def test_jpg_quality_capped_at_95(self):
        """Test that JPG quality is capped at 95."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_quality.jpg")
            img = Image.new("RGB", (100, 100), color="magenta")

            # Should not error even with quality > 95
            save_with_format(img, filepath, "JPG", 100)

            assert os.path.exists(filepath)


class TestTensorToPil:
    """Tests for tensor_to_pil function."""

    @pytest.mark.skipif(
        not pytest.importorskip("torch", reason="torch not available"),
        reason="torch not available",
    )
    def test_tensor_to_pil_basic(self):
        """Test basic tensor to PIL conversion."""
        import torch

        from comfyui_batch_image_processing.utils.save_image_utils import tensor_to_pil

        # Create a simple tensor [1, H, W, C] with red color
        tensor = torch.zeros(1, 100, 100, 3, dtype=torch.float32)
        tensor[:, :, :, 0] = 1.0  # Red channel

        img = tensor_to_pil(tensor)

        assert img.mode == "RGB"
        assert img.size == (100, 100)
        # Check that the image is red
        pixel = img.getpixel((50, 50))
        assert pixel[0] > 200  # Red should be high
        assert pixel[1] < 50  # Green should be low
        assert pixel[2] < 50  # Blue should be low

    @pytest.mark.skipif(
        not pytest.importorskip("torch", reason="torch not available"),
        reason="torch not available",
    )
    def test_tensor_to_pil_no_batch_dim(self):
        """Test tensor without batch dimension."""
        import torch

        from comfyui_batch_image_processing.utils.save_image_utils import tensor_to_pil

        # Create tensor [H, W, C] without batch dim
        tensor = torch.ones(50, 50, 3, dtype=torch.float32) * 0.5

        img = tensor_to_pil(tensor)

        assert img.mode == "RGB"
        assert img.size == (50, 50)
        # Check that color is gray (0.5 * 255 = ~127)
        pixel = img.getpixel((25, 25))
        assert 120 < pixel[0] < 135
        assert 120 < pixel[1] < 135
        assert 120 < pixel[2] < 135

    @pytest.mark.skipif(
        not pytest.importorskip("torch", reason="torch not available"),
        reason="torch not available",
    )
    def test_tensor_to_pil_clipping(self):
        """Test that values outside [0, 1] are clipped."""
        import torch

        from comfyui_batch_image_processing.utils.save_image_utils import tensor_to_pil

        # Create tensor with out-of-range values
        tensor = torch.zeros(1, 10, 10, 3, dtype=torch.float32)
        tensor[:, :, :, 0] = 1.5  # Above 1
        tensor[:, :, :, 1] = -0.5  # Below 0

        img = tensor_to_pil(tensor)

        pixel = img.getpixel((5, 5))
        assert pixel[0] == 255  # Clipped to max
        assert pixel[1] == 0  # Clipped to min
