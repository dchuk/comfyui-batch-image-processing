"""Tests for file filtering utilities."""

import os
import tempfile

import pytest

from utils.file_utils import filter_files_by_patterns, get_pattern_for_preset


class TestGetPatternForPreset:
    """Tests for get_pattern_for_preset function."""

    def test_all_images_preset(self):
        """All Images preset returns all common image extensions."""
        result = get_pattern_for_preset("All Images")
        assert result == "*.png,*.jpg,*.jpeg,*.webp"

    def test_png_only_preset(self):
        """PNG Only preset returns only PNG pattern."""
        result = get_pattern_for_preset("PNG Only")
        assert result == "*.png"

    def test_jpg_only_preset(self):
        """JPG Only preset returns JPG and JPEG patterns."""
        result = get_pattern_for_preset("JPG Only")
        assert result == "*.jpg,*.jpeg"

    def test_custom_with_pattern(self):
        """Custom preset with pattern returns that pattern."""
        result = get_pattern_for_preset("Custom", "*.tiff,*.bmp")
        assert result == "*.tiff,*.bmp"

    def test_custom_with_empty_string_returns_default(self):
        """Custom preset with empty string returns default pattern."""
        result = get_pattern_for_preset("Custom", "")
        assert result == "*.png,*.jpg,*.jpeg,*.webp"

    def test_custom_with_whitespace_only_returns_default(self):
        """Custom preset with whitespace-only returns default pattern."""
        result = get_pattern_for_preset("Custom", "   ")
        assert result == "*.png,*.jpg,*.jpeg,*.webp"

    def test_unknown_preset_returns_default(self):
        """Unknown preset returns default pattern."""
        result = get_pattern_for_preset("Unknown Preset")
        assert result == "*.png,*.jpg,*.jpeg,*.webp"

    def test_custom_pattern_trimmed(self):
        """Custom pattern is trimmed of leading/trailing whitespace."""
        result = get_pattern_for_preset("Custom", "  *.gif  ")
        assert result == "*.gif"


class TestFilterFilesByPatterns:
    """Tests for filter_files_by_patterns function."""

    @pytest.fixture
    def test_dir(self):
        """Create temp directory with various file types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            files = [
                "image1.png",
                "image2.PNG",  # uppercase extension
                "image3.Png",  # mixed case
                "photo1.jpg",
                "photo2.jpeg",
                "document.txt",
                "archive.zip",
            ]
            for filename in files:
                filepath = os.path.join(tmpdir, filename)
                with open(filepath, "w") as f:
                    f.write("test")

            # Create a subdirectory (should be excluded)
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            yield tmpdir

    def test_matches_png_files(self, test_dir):
        """Matches PNG files with case-insensitive matching."""
        result = filter_files_by_patterns(test_dir, "*.png")
        # Should match image1.png, image2.PNG, image3.Png
        assert len(result) == 3
        assert "image1.png" in result
        assert "image2.PNG" in result
        assert "image3.Png" in result

    def test_matches_multiple_patterns(self, test_dir):
        """Matches files with multiple comma-separated patterns."""
        result = filter_files_by_patterns(test_dir, "*.png,*.jpg")
        # Should match all PNG and JPG files
        assert len(result) == 4
        assert "image1.png" in result
        assert "photo1.jpg" in result

    def test_excludes_non_matching_files(self, test_dir):
        """Non-matching files are excluded."""
        result = filter_files_by_patterns(test_dir, "*.png")
        assert "document.txt" not in result
        assert "archive.zip" not in result

    def test_excludes_subdirectories(self, test_dir):
        """Subdirectories are excluded from results."""
        result = filter_files_by_patterns(test_dir, "*")
        # Should return files, not the subdir
        assert "subdir" not in result
        # Files should still be present
        assert len(result) == 7  # All files, no subdirs

    def test_returns_filenames_only(self, test_dir):
        """Returns filenames without directory path."""
        result = filter_files_by_patterns(test_dir, "*.png")
        for filename in result:
            assert "/" not in filename
            assert "\\" not in filename

    def test_nonexistent_directory_returns_empty(self):
        """Nonexistent directory returns empty list."""
        result = filter_files_by_patterns("/nonexistent/path", "*.png")
        assert result == []

    def test_empty_pattern_returns_empty(self, test_dir):
        """Empty pattern string returns empty list."""
        result = filter_files_by_patterns(test_dir, "")
        assert result == []

    def test_whitespace_in_patterns_trimmed(self, test_dir):
        """Whitespace around patterns is trimmed."""
        result = filter_files_by_patterns(test_dir, "  *.png  ,  *.jpg  ")
        assert len(result) == 4
        assert "image1.png" in result
        assert "photo1.jpg" in result
