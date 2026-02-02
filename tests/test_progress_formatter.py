"""Tests for BatchProgressFormatter node."""

import pytest

# Import through root package (as ComfyUI would)
from comfyui_batch_image_processing import NODE_CLASS_MAPPINGS

BatchProgressFormatter = NODE_CLASS_MAPPINGS["BatchProgressFormatter"]


class TestClassAttributes:
    """Tests for class attributes."""

    def test_category(self):
        """CATEGORY is batch_processing."""
        assert BatchProgressFormatter.CATEGORY == "batch_processing"

    def test_return_types(self):
        """RETURN_TYPES is single STRING."""
        assert BatchProgressFormatter.RETURN_TYPES == ("STRING",)

    def test_return_names(self):
        """RETURN_NAMES is PROGRESS_TEXT."""
        assert BatchProgressFormatter.RETURN_NAMES == ("PROGRESS_TEXT",)

    def test_function_name(self):
        """FUNCTION is format_progress."""
        assert BatchProgressFormatter.FUNCTION == "format_progress"

    def test_not_output_node(self):
        """OUTPUT_NODE is False (not a terminal node)."""
        assert BatchProgressFormatter.OUTPUT_NODE is False


class TestInputTypes:
    """Tests for INPUT_TYPES class method."""

    def test_returns_dict_with_required(self):
        """INPUT_TYPES returns dict with required key."""
        result = BatchProgressFormatter.INPUT_TYPES()
        assert isinstance(result, dict)
        assert "required" in result

    def test_index_is_required_int_with_force_input(self):
        """index input is required INT with forceInput=True."""
        result = BatchProgressFormatter.INPUT_TYPES()
        index_config = result["required"]["index"]
        assert index_config[0] == "INT"
        assert index_config[1].get("forceInput") is True

    def test_total_count_is_required_int_with_force_input(self):
        """total_count input is required INT with forceInput=True."""
        result = BatchProgressFormatter.INPUT_TYPES()
        total_config = result["required"]["total_count"]
        assert total_config[0] == "INT"
        assert total_config[1].get("forceInput") is True


class TestFormatProgress:
    """Tests for format_progress method with concrete input/output cases."""

    def test_basic_formatting(self):
        """index=2, total_count=10 -> '3 of 10 (30%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=2, total_count=10)
        assert result == ("3 of 10 (30%)",)

    def test_first_image(self):
        """index=0, total_count=5 -> '1 of 5 (20%)' (0-based to 1-based conversion)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=5)
        assert result == ("1 of 5 (20%)",)

    def test_last_image(self):
        """index=9, total_count=10 -> '10 of 10 (100%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=9, total_count=10)
        assert result == ("10 of 10 (100%)",)

    def test_single_image(self):
        """index=0, total_count=1 -> '1 of 1 (100%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=1)
        assert result == ("1 of 1 (100%)",)

    def test_percentage_truncates_not_rounds(self):
        """index=0, total_count=3 -> '1 of 3 (33%)' (33.33% truncates to 33%, not rounds to 33%)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=3)
        assert result == ("1 of 3 (33%)",)

    def test_divide_by_zero_protection(self):
        """index=0, total_count=0 -> '1 of 1 (100%)' (max(1, total_count) prevents crash)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=0)
        assert result == ("1 of 1 (100%)",)

    def test_returns_tuple(self):
        """Returns a single-element tuple containing a string (ComfyUI requirement)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=10)
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert isinstance(result[0], str)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_large_numbers(self):
        """index=999, total_count=1000 -> '1000 of 1000 (100%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=999, total_count=1000)
        assert result == ("1000 of 1000 (100%)",)

    def test_midway_percentage(self):
        """index=4, total_count=10 -> '5 of 10 (50%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=4, total_count=10)
        assert result == ("5 of 10 (50%)",)

    def test_ten_percent(self):
        """index=0, total_count=10 -> '1 of 10 (10%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=10)
        assert result == ("1 of 10 (10%)",)
