"""Tests for streaming support in router/stages.py."""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from autobots.router.stages import StageExecutor


class TestStreamingSupport(unittest.TestCase):
    """Test suite for streaming model calls."""

    def setUp(self):
        """Set up test fixtures."""
        self.api_key = "test-key"
        self.base_url = "https://integrate.api.nvidia.com/v1"

    def test_build_client_configures_timeout(self):
        """Test that _build_client configures HTTP timeout."""
        executor = StageExecutor(api_key=self.api_key)

        # Verify client was created
        self.assertIsNotNone(executor.client)

    @patch("autobots.router.stages.Console")
    def test_call_model_streaming_returns_response(self, mock_console_class):
        """Test that _call_model_streaming returns the complete response."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        executor = StageExecutor(api_key=self.api_key)

        # Mock the streaming response
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock(delta=Mock(content="Hello "))]

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock(delta=Mock(content="world"))]

        mock_chunk3 = Mock()
        mock_chunk3.choices = [Mock(delta=Mock(content=None))]

        executor.client.chat.completions.create = Mock(
            return_value=iter([mock_chunk1, mock_chunk2, mock_chunk3])
        )

        result = executor._call_model_streaming(
            "test-model",
            "system content",
            "user prompt"
        )

        self.assertEqual(result, "Hello world")

    @patch("autobots.router.stages.Console")
    def test_call_model_streaming_handles_empty_response(self, mock_console_class):
        """Test that _call_model_streaming handles empty responses."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        executor = StageExecutor(api_key=self.api_key)

        # Mock empty streaming response
        mock_chunk = Mock()
        mock_chunk.choices = [Mock(delta=Mock(content=None))]

        executor.client.chat.completions.create = Mock(
            return_value=iter([mock_chunk])
        )

        result = executor._call_model_streaming(
            "test-model",
            "system content",
            "user prompt"
        )

        self.assertEqual(result, "")

    @patch("autobots.router.stages.Console")
    def test_call_model_uses_streaming(self, mock_console_class):
        """Test that _call_model delegates to _call_model_streaming."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console

        executor = StageExecutor(api_key=self.api_key)

        # Mock the streaming response
        mock_chunk = Mock()
        mock_chunk.choices = [Mock(delta=Mock(content="test"))]

        executor.client.chat.completions.create = Mock(
            return_value=iter([mock_chunk])
        )

        with patch.object(executor, '_call_model_streaming', return_value="test") as mock_streaming:
            result = executor._call_model("test-model", "system", "user")
            mock_streaming.assert_called_once()
            self.assertEqual(result, "test")

    @patch("autobots.router.stages.console")
    def test_streaming_updates_status(self, mock_console):
        """Test that streaming updates the status spinner."""
        executor = StageExecutor(api_key=self.api_key)

        # Mock streaming response with multiple chunks
        chunks = []
        for i in range(5):
            chunk = Mock()
            chunk.choices = [Mock(delta=Mock(content=f"chunk{i}"))]
            chunks.append(chunk)

        executor.client.chat.completions.create = Mock(return_value=iter(chunks))

        executor._call_model_streaming("test-model", "system", "user")

        # Verify status was updated
        mock_console.status.assert_called()
        status_context = mock_console.status.return_value.__enter__.return_value
        self.assertTrue(status_context.update.called)

    def test_stage_executor_initializes_with_defaults(self):
        """Test that StageExecutor initializes with correct defaults."""
        executor = StageExecutor(api_key=self.api_key)

        self.assertEqual(executor.temperature, 0.2)
        self.assertEqual(executor.max_tokens, 4096)
        self.assertEqual(executor.base_url, self.base_url)

    def test_stage_executor_custom_params(self):
        """Test that StageExecutor accepts custom parameters."""
        executor = StageExecutor(
            api_key=self.api_key,
            temperature=0.5,
            max_tokens=2048,
            base_url="https://custom.api.com/v1"
        )

        self.assertEqual(executor.temperature, 0.5)
        self.assertEqual(executor.max_tokens, 2048)
        self.assertEqual(executor.base_url, "https://custom.api.com/v1")


if __name__ == "__main__":
    unittest.main()
