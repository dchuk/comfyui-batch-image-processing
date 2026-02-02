"""Tests for queue control utilities."""

from unittest.mock import MagicMock, patch

import pytest

from comfyui_batch_image_processing.utils import queue_control
from comfyui_batch_image_processing.utils.queue_control import (
    HAS_SERVER,
    should_continue,
    stop_auto_queue,
    trigger_next_queue,
)


class TestShouldContinue:
    """Test should_continue function."""

    def test_returns_true_when_not_at_last_image(self):
        """Returns True when more images remain."""
        # First of 5 images (index 0)
        assert should_continue(0, 5) is True

    def test_returns_true_when_one_before_last(self):
        """Returns True when at second-to-last image."""
        # 4th of 5 images (index 3)
        assert should_continue(3, 5) is True

    def test_returns_false_when_at_last_image(self):
        """Returns False when at last image."""
        # 5th of 5 images (index 4)
        assert should_continue(4, 5) is False

    def test_returns_false_when_past_last_image(self):
        """Returns False when index exceeds total."""
        assert should_continue(10, 5) is False

    def test_returns_false_when_single_image_batch(self):
        """Returns False for single image batch."""
        assert should_continue(0, 1) is False

    def test_returns_false_when_empty_batch(self):
        """Returns False for empty batch."""
        assert should_continue(0, 0) is False


class TestTriggerNextQueueNoServer:
    """Test trigger_next_queue when PromptServer unavailable."""

    def test_returns_false_without_server(self):
        """Returns False when HAS_SERVER is False."""
        # In test environment, server.PromptServer import fails
        # so HAS_SERVER should be False
        assert HAS_SERVER is False
        assert trigger_next_queue() is False


class TestStopAutoQueueNoServer:
    """Test stop_auto_queue when PromptServer unavailable."""

    def test_returns_false_without_server(self):
        """Returns False when HAS_SERVER is False."""
        assert HAS_SERVER is False
        assert stop_auto_queue() is False


class TestTriggerNextQueueWithServer:
    """Test trigger_next_queue with mocked PromptServer."""

    def test_calls_send_sync_when_server_available(self):
        """Calls send_sync with correct event when server available."""
        mock_instance = MagicMock()
        mock_server = MagicMock()
        mock_server.instance = mock_instance

        # Patch module-level variables
        with patch.object(queue_control, "HAS_SERVER", True):
            with patch.object(queue_control, "PromptServer", mock_server):
                result = trigger_next_queue()

        assert result is True
        mock_instance.send_sync.assert_called_once_with("impact-add-queue", {})

    def test_returns_false_when_instance_is_none(self):
        """Returns False when PromptServer.instance is None."""
        mock_server = MagicMock()
        mock_server.instance = None

        with patch.object(queue_control, "HAS_SERVER", True):
            with patch.object(queue_control, "PromptServer", mock_server):
                result = trigger_next_queue()

        assert result is False

    def test_returns_false_when_promptserver_is_none(self):
        """Returns False when PromptServer itself is None."""
        with patch.object(queue_control, "HAS_SERVER", True):
            with patch.object(queue_control, "PromptServer", None):
                result = trigger_next_queue()

        assert result is False


class TestStopAutoQueueWithServer:
    """Test stop_auto_queue with mocked PromptServer."""

    def test_calls_send_sync_when_server_available(self):
        """Calls send_sync to stop auto queue when server available."""
        mock_instance = MagicMock()
        mock_server = MagicMock()
        mock_server.instance = mock_instance

        with patch.object(queue_control, "HAS_SERVER", True):
            with patch.object(queue_control, "PromptServer", mock_server):
                result = stop_auto_queue()

        assert result is True
        mock_instance.send_sync.assert_called_once_with("impact-stop-auto-queue", {})

    def test_returns_false_when_instance_is_none(self):
        """Returns False when PromptServer.instance is None."""
        mock_server = MagicMock()
        mock_server.instance = None

        with patch.object(queue_control, "HAS_SERVER", True):
            with patch.object(queue_control, "PromptServer", mock_server):
                result = stop_auto_queue()

        assert result is False

    def test_handles_exception_gracefully(self):
        """Returns True even if send_sync raises exception."""
        mock_instance = MagicMock()
        mock_instance.send_sync.side_effect = Exception("Test error")
        mock_server = MagicMock()
        mock_server.instance = mock_instance

        with patch.object(queue_control, "HAS_SERVER", True):
            with patch.object(queue_control, "PromptServer", mock_server):
                result = stop_auto_queue()

        # Should return True because we attempted to send signal
        assert result is True
