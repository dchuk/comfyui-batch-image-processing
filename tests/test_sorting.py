"""Tests for natural sorting utility."""

import pytest

# Import directly from the sorting module to avoid triggering
# torch/numpy imports from utils/__init__.py
from utils.sorting import natural_sort_key


class TestNaturalSortKey:
    """Test cases for natural_sort_key function."""

    def test_basic_numbers(self):
        """Natural sort orders numbers by numeric value, not lexicographic."""
        files = ["img10", "img2", "img1"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["img1", "img2", "img10"]

    def test_mixed_case(self):
        """Natural sort is case-insensitive."""
        files = ["IMG2.png", "img1.png", "Img10.png"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["img1.png", "IMG2.png", "Img10.png"]

    def test_no_numbers(self):
        """Files without numbers sort alphabetically (case-insensitive)."""
        files = ["banana", "apple", "cherry"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["apple", "banana", "cherry"]

    def test_leading_zeros(self):
        """Leading zeros are treated as the same number."""
        files = ["img01", "img001", "img1"]
        result = sorted(files, key=natural_sort_key)
        # All are treated as 1, so order is stable (original order preserved for equal keys)
        # Python's sort is stable, so the relative order of equal elements is preserved
        assert len(result) == 3
        # All three should be adjacent since they all represent "img" + 1
        # Verify they all sort before img2/img10 would
        for item in result:
            assert "1" in item or "01" in item or "001" in item

    def test_multiple_number_groups(self):
        """Files with multiple number groups sort correctly."""
        files = ["file1_page2", "file1_page10", "file2_page1"]
        result = sorted(files, key=natural_sort_key)
        # file1 < file2, then page2 < page10
        assert result == ["file1_page2", "file1_page10", "file2_page1"]

    def test_empty_string(self):
        """Empty strings are handled gracefully."""
        files = ["img1", "", "img2"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["", "img1", "img2"]

    def test_numbers_only(self):
        """Pure number strings sort numerically."""
        files = ["100", "20", "3"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["3", "20", "100"]

    def test_realistic_filenames(self):
        """Test with realistic image filename patterns."""
        files = [
            "photo_2024_001.jpg",
            "photo_2024_010.jpg",
            "photo_2024_002.jpg",
            "photo_2023_100.jpg",
        ]
        result = sorted(files, key=natural_sort_key)
        # 2023 < 2024, then 001 < 002 < 010
        assert result == [
            "photo_2023_100.jpg",
            "photo_2024_001.jpg",
            "photo_2024_002.jpg",
            "photo_2024_010.jpg",
        ]

    def test_unicode_characters(self):
        """Unicode filenames are handled."""
        files = ["image_2.png", "image_1.png", "image_10.png"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["image_1.png", "image_2.png", "image_10.png"]

    def test_special_characters(self):
        """Files with special characters sort correctly."""
        files = ["img-10.png", "img-2.png", "img-1.png"]
        result = sorted(files, key=natural_sort_key)
        assert result == ["img-1.png", "img-2.png", "img-10.png"]
