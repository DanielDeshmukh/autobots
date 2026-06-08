"""Tests for enhanced Ctrl+C interrupt handling."""

import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from autobots.cli import InterruptHandler


class TestInterruptHandler(unittest.TestCase):
    """Test suite for InterruptHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir)
        self.console = Mock()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_interrupt_handler_initialization(self):
        """Test that InterruptHandler initializes correctly."""
        handler = InterruptHandler(self.console)
        self.assertFalse(handler.interrupted)
        self.assertIsNone(handler.workspace)
        self.assertIsNone(handler.state_manager)

    def test_interrupt_handler_setup(self):
        """Test that setup configures the signal handler."""
        handler = InterruptHandler(self.console)

        with patch("autobots.cli.signal.signal") as mock_signal:
            handler.setup()
            # Verify signal.signal was called with SIGINT
            mock_signal.assert_called_once()
            args = mock_signal.call_args[0]
            self.assertEqual(args[0], signal.SIGINT)
            self.assertTrue(callable(args[1]))

    def test_interrupt_handler_sets_interrupted_flag(self):
        """Test that Ctrl+C sets the interrupted flag."""
        handler = InterruptHandler(self.console)

        # Store the signal handler that gets registered
        registered_handler = None
        def capture_handler(sig, handler_func):
            nonlocal registered_handler
            registered_handler = handler_func

        with patch("autobots.cli.signal.signal", side_effect=capture_handler):
            handler.setup()

        # Simulate Ctrl+C
        if registered_handler:
            registered_handler(signal.SIGINT, None)
            self.assertTrue(handler.interrupted)

    def test_set_checkpoint_data(self):
        """Test that checkpoint data is stored correctly."""
        handler = InterruptHandler(self.console)

        handler.set_checkpoint_data(
            session_id="test-session",
            mode="supervised",
            phase_index=1,
            phase_title="Test Phase",
            phases_completed=["P1"],
        )

        self.assertIsNotNone(handler.checkpoint_data)
        self.assertEqual(handler.checkpoint_data["session_id"], "test-session")
        self.assertEqual(handler.checkpoint_data["mode"], "supervised")
        self.assertEqual(handler.checkpoint_data["phase_index"], 1)

    def test_cleanup_releases_stale_locks(self):
        """Test that cleanup releases stale locks."""
        from autobots.workspace import TargetProjectWorkspace

        workspace = TargetProjectWorkspace(self.workspace_root)
        handler = InterruptHandler(self.console)
        handler.workspace = workspace

        # Create a stale lock
        lock_dir = self.workspace_root / "context" / ".autobots-locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        lock_file = lock_dir / "architecture.md.lock.json"
        lock_file.write_text('{"path": "architecture.md", "owner": "test", "acquired_at": 0, "expires_at": 0}')

        handler._cleanup_on_interrupt()

        # Lock should be released
        self.assertFalse(lock_file.exists())

    def test_cleanup_saves_checkpoint(self):
        """Test that cleanup saves checkpoint when data is available."""
        handler = InterruptHandler(self.console)
        handler.workspace = Mock()
        handler.workspace.target_root = Path(self.temp_dir)
        handler.set_checkpoint_data(
            session_id="test-session",
            mode="supervised",
            phase_index=0,
            phase_title="Test",
            phases_completed=[],
        )

        with patch("autobots.executor.modes.ExecutionModeManager") as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            handler._cleanup_on_interrupt()
            mock_instance.save_checkpoint.assert_called_once()

    def test_restore_signal_handler(self):
        """Test that restore brings back original handler."""
        original_handler = Mock()
        handler = InterruptHandler(self.console)

        with patch("autobots.cli.signal.signal") as mock_signal:
            handler._original_handler = original_handler
            handler.restore()
            mock_signal.assert_called_once_with(signal.SIGINT, original_handler)


if __name__ == "__main__":
    unittest.main()
