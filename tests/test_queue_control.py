"""Tests for queue control utilities."""

import urllib.error
from unittest.mock import MagicMock, Mock, patch

import pytest

from comfyui_batch_image_processing.utils import queue_control
from comfyui_batch_image_processing.utils.queue_control import (
    HAS_SERVER,
    get_server_address,
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


class TestTriggerNextQueueWithoutServer:
    """Test trigger_next_queue when PromptServer unavailable."""

    def test_returns_false_without_prompt(self):
        """Returns False when prompt is None."""
        assert trigger_next_queue(None) is False

    def test_returns_false_with_empty_prompt(self):
        """Returns False when prompt is empty dict."""
        assert trigger_next_queue({}) is False

    def test_returns_false_when_has_server_is_false(self):
        """Returns False when HAS_SERVER is False (outside ComfyUI)."""
        # In test environment, server.PromptServer import fails
        # so HAS_SERVER should be False
        assert HAS_SERVER is False
        assert trigger_next_queue({"nodes": {"1": {}}}) is False


class TestStopAutoQueueNative:
    """Test stop_auto_queue native implementation."""

    def test_always_returns_true(self):
        """stop_auto_queue always returns True (no external events needed)."""
        assert stop_auto_queue() is True

    def test_returns_true_regardless_of_server_state(self):
        """stop_auto_queue returns True even without server."""
        # Native approach: stopping = not queueing next, which always succeeds
        assert HAS_SERVER is False
        assert stop_auto_queue() is True


class TestTriggerNextQueueNative:
    """Test trigger_next_queue with mocked PromptServer and HTTP."""

    @patch("comfyui_batch_image_processing.utils.queue_control.urllib.request.urlopen")
    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_posts_to_prompt_endpoint(self, mock_server, mock_urlopen):
        """Calls urllib.request.urlopen with correct URL format."""
        mock_server.instance.address = "127.0.0.1"
        mock_server.instance.port = 8188
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = trigger_next_queue({"nodes": {"1": {}}})

        assert result is True
        mock_urlopen.assert_called_once()
        # Verify URL contains /prompt
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "/prompt" in request.full_url
        assert request.method == "POST"
        assert request.get_header("Content-type") == "application/json"

    @patch("comfyui_batch_image_processing.utils.queue_control.urllib.request.urlopen")
    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_returns_true_on_success(self, mock_server, mock_urlopen):
        """Returns True when response.status == 200."""
        mock_server.instance.address = "127.0.0.1"
        mock_server.instance.port = 8188
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        result = trigger_next_queue({"nodes": {"1": {}}})

        assert result is True

    @patch("comfyui_batch_image_processing.utils.queue_control.urllib.request.urlopen")
    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_returns_false_on_url_error(self, mock_server, mock_urlopen):
        """Returns False when URLError raised (network unreachable)."""
        mock_server.instance.address = "127.0.0.1"
        mock_server.instance.port = 8188
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        result = trigger_next_queue({"nodes": {"1": {}}})

        assert result is False

    @patch("comfyui_batch_image_processing.utils.queue_control.urllib.request.urlopen")
    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_returns_false_on_http_error(self, mock_server, mock_urlopen):
        """Returns False when HTTPError raised (server error)."""
        mock_server.instance.address = "127.0.0.1"
        mock_server.instance.port = 8188
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://127.0.0.1:8188/prompt", 500, "Server Error", {}, None
        )

        result = trigger_next_queue({"nodes": {"1": {}}})

        assert result is False

    @patch.object(queue_control, "HAS_SERVER", False)
    def test_returns_false_when_no_server(self):
        """Returns False when HAS_SERVER is False (outside ComfyUI)."""
        result = trigger_next_queue({"nodes": {"1": {}}})
        assert result is False

    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer", None)
    def test_returns_false_when_promptserver_is_none(self):
        """Returns False when PromptServer itself is None."""
        result = trigger_next_queue({"nodes": {"1": {}}})
        assert result is False

    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_returns_false_when_instance_is_none(self, mock_server):
        """Returns False when PromptServer.instance is None."""
        mock_server.instance = None

        result = trigger_next_queue({"nodes": {"1": {}}})

        assert result is False

    @patch("comfyui_batch_image_processing.utils.queue_control.urllib.request.urlopen")
    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_uses_server_port(self, mock_server, mock_urlopen):
        """Uses PromptServer.instance.port for URL."""
        mock_server.instance.address = "127.0.0.1"
        mock_server.instance.port = 9999  # Custom port
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response

        trigger_next_queue({"nodes": {"1": {}}})

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "9999" in request.full_url


class TestGetServerAddress:
    """Test get_server_address helper function."""

    def test_returns_default_when_no_server(self):
        """Returns ('127.0.0.1', 8188) when HAS_SERVER is False."""
        assert HAS_SERVER is False
        address, port = get_server_address()
        assert address == "127.0.0.1"
        assert port == 8188

    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_returns_server_address_when_available(self, mock_server):
        """Returns server address/port when PromptServer available."""
        mock_server.instance.address = "192.168.1.100"
        mock_server.instance.port = 9000

        address, port = get_server_address()

        assert address == "192.168.1.100"
        assert port == 9000

    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_converts_0000_to_localhost(self, mock_server):
        """Returns '127.0.0.1' when address is '0.0.0.0'."""
        mock_server.instance.address = "0.0.0.0"
        mock_server.instance.port = 8188

        address, port = get_server_address()

        assert address == "127.0.0.1"
        assert port == 8188

    @patch.object(queue_control, "HAS_SERVER", True)
    @patch.object(queue_control, "PromptServer")
    def test_returns_default_when_instance_is_none(self, mock_server):
        """Returns defaults when PromptServer.instance is None."""
        mock_server.instance = None

        address, port = get_server_address()

        assert address == "127.0.0.1"
        assert port == 8188
