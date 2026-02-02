"""Tests for BatchProgressFormatter node."""

from unittest import mock

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

    def test_output_node_is_true(self):
        """OUTPUT_NODE is True (required for UI updates to display)."""
        assert BatchProgressFormatter.OUTPUT_NODE is True


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
        assert result["result"] == ("3 of 10 (30%)",)
        assert result["ui"]["text"] == ["3 of 10 (30%)"]

    def test_first_image(self):
        """index=0, total_count=5 -> '1 of 5 (20%)' (0-based to 1-based conversion)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=5)
        assert result["result"] == ("1 of 5 (20%)",)

    def test_last_image(self):
        """index=9, total_count=10 -> '10 of 10 (100%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=9, total_count=10)
        assert result["result"] == ("10 of 10 (100%)",)

    def test_single_image(self):
        """index=0, total_count=1 -> '1 of 1 (100%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=1)
        assert result["result"] == ("1 of 1 (100%)",)

    def test_percentage_truncates_not_rounds(self):
        """index=0, total_count=3 -> '1 of 3 (33%)' (33.33% truncates to 33%, not rounds to 33%)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=3)
        assert result["result"] == ("1 of 3 (33%)",)

    def test_divide_by_zero_protection(self):
        """index=0, total_count=0 -> '1 of 1 (100%)' (max(1, total_count) prevents crash)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=0)
        assert result["result"] == ("1 of 1 (100%)",)

    def test_returns_dict_with_ui_and_result(self):
        """Returns dict with 'ui' and 'result' keys (OUTPUT_NODE pattern)."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=10)
        assert isinstance(result, dict)
        assert "ui" in result
        assert "result" in result
        assert isinstance(result["result"], tuple)
        assert len(result["result"]) == 1
        assert isinstance(result["result"][0], str)


class TestEdgeCases:
    """Tests for edge cases."""

    def test_large_numbers(self):
        """index=999, total_count=1000 -> '1000 of 1000 (100%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=999, total_count=1000)
        assert result["result"] == ("1000 of 1000 (100%)",)

    def test_midway_percentage(self):
        """index=4, total_count=10 -> '5 of 10 (50%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=4, total_count=10)
        assert result["result"] == ("5 of 10 (50%)",)

    def test_ten_percent(self):
        """index=0, total_count=10 -> '1 of 10 (10%)'."""
        formatter = BatchProgressFormatter()
        result = formatter.format_progress(index=0, total_count=10)
        assert result["result"] == ("1 of 10 (10%)",)


class TestBroadcastBehavior:
    """Tests for live UI update broadcast behavior."""

    def test_hidden_inputs_declared(self):
        """INPUT_TYPES includes hidden section with unique_id."""
        result = BatchProgressFormatter.INPUT_TYPES()
        assert "hidden" in result
        assert "unique_id" in result["hidden"]
        assert result["hidden"]["unique_id"] == "UNIQUE_ID"

    def test_broadcasts_executed_event_when_server_available(self):
        """Broadcasts 'executed' event with correct args when server is available."""
        import comfyui_batch_image_processing.nodes.progress_formatter as progress_formatter_module

        # Create mock PromptServer
        mock_server_instance = mock.MagicMock()
        mock_prompt_server = mock.MagicMock()
        mock_prompt_server.instance = mock_server_instance

        with mock.patch.object(progress_formatter_module, "HAS_SERVER", True):
            with mock.patch.object(progress_formatter_module, "PromptServer", mock_prompt_server):
                formatter = BatchProgressFormatter()
                result = formatter.format_progress(index=2, total_count=10, unique_id="456")

        # Verify send_sync was called with correct arguments
        mock_server_instance.send_sync.assert_called_once()
        call_args = mock_server_instance.send_sync.call_args
        assert call_args[0][0] == "executed"  # Event type
        assert call_args[0][1]["node"] == "456"  # Node ID
        assert call_args[0][1]["output"]["text"] == ["3 of 10 (30%)"]  # Progress text
        assert call_args[1]["sid"] is None  # Broadcast to ALL clients

    def test_no_broadcast_without_unique_id(self):
        """No broadcast when unique_id is None."""
        import comfyui_batch_image_processing.nodes.progress_formatter as progress_formatter_module

        mock_server_instance = mock.MagicMock()
        mock_prompt_server = mock.MagicMock()
        mock_prompt_server.instance = mock_server_instance

        with mock.patch.object(progress_formatter_module, "HAS_SERVER", True):
            with mock.patch.object(progress_formatter_module, "PromptServer", mock_prompt_server):
                formatter = BatchProgressFormatter()
                result = formatter.format_progress(index=0, total_count=5, unique_id=None)

        # send_sync should NOT have been called
        mock_server_instance.send_sync.assert_not_called()

    def test_no_crash_without_server(self):
        """No crash when HAS_SERVER is False (default test environment)."""
        import comfyui_batch_image_processing.nodes.progress_formatter as progress_formatter_module

        # Ensure HAS_SERVER is False (simulating test environment)
        with mock.patch.object(progress_formatter_module, "HAS_SERVER", False):
            with mock.patch.object(progress_formatter_module, "PromptServer", None):
                formatter = BatchProgressFormatter()
                # Should not raise an exception
                result = formatter.format_progress(index=0, total_count=5, unique_id="789")

        # Should still return valid result
        assert "ui" in result
        assert "result" in result
