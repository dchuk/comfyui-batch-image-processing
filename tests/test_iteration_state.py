"""Tests for iteration state management."""

import os
import tempfile

import pytest

from comfyui_batch_image_processing.utils.iteration_state import IterationState


class TestIterationStateBasics:
    """Test basic state management functionality."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_get_state_initializes_new_directory(self):
        """State is initialized with defaults for new directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = IterationState.get_state(tmpdir)

            assert state["index"] == 0
            assert state["total_count"] == 0
            assert state["status"] == "idle"
            assert state["directory"] == os.path.normpath(os.path.abspath(tmpdir))

    def test_get_state_returns_same_state_on_repeated_calls(self):
        """State persists across multiple get_state calls."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state1 = IterationState.get_state(tmpdir)
            state1["index"] = 5

            state2 = IterationState.get_state(tmpdir)

            assert state2["index"] == 5
            assert state1 is state2  # Same object

    def test_set_total_count(self):
        """Total count can be set for a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_total_count(tmpdir, 10)
            state = IterationState.get_state(tmpdir)

            assert state["total_count"] == 10


class TestIterationStateAdvance:
    """Test index advancement."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_advance_increments_index(self):
        """Advance increments index by 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.get_state(tmpdir)  # Initialize

            new_index = IterationState.advance(tmpdir)

            assert new_index == 1

    def test_advance_multiple_times(self):
        """Multiple advances increment sequentially."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.get_state(tmpdir)

            IterationState.advance(tmpdir)
            IterationState.advance(tmpdir)
            new_index = IterationState.advance(tmpdir)

            assert new_index == 3


class TestIterationStateCompletion:
    """Test completion detection."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_is_complete_false_when_index_less_than_total(self):
        """is_complete returns False when more images to process."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_total_count(tmpdir, 5)
            state = IterationState.get_state(tmpdir)
            state["index"] = 3

            assert IterationState.is_complete(tmpdir) is False

    def test_is_complete_true_when_index_equals_total(self):
        """is_complete returns True when all images processed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_total_count(tmpdir, 5)
            state = IterationState.get_state(tmpdir)
            state["index"] = 5

            assert IterationState.is_complete(tmpdir) is True

    def test_is_complete_true_when_index_exceeds_total(self):
        """is_complete returns True when index exceeds total."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_total_count(tmpdir, 5)
            state = IterationState.get_state(tmpdir)
            state["index"] = 10

            assert IterationState.is_complete(tmpdir) is True


class TestIterationStateReset:
    """Test reset functionality."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_reset_sets_index_to_zero(self):
        """Reset sets index back to 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = IterationState.get_state(tmpdir)
            state["index"] = 7

            IterationState.reset(tmpdir)

            assert IterationState.get_state(tmpdir)["index"] == 0

    def test_reset_sets_status_to_idle(self):
        """Reset sets status to idle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = IterationState.get_state(tmpdir)
            state["status"] = "processing"

            IterationState.reset(tmpdir)

            assert IterationState.get_state(tmpdir)["status"] == "idle"

    def test_reset_preserves_total_count(self):
        """Reset preserves the total_count value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_total_count(tmpdir, 15)

            IterationState.reset(tmpdir)

            assert IterationState.get_state(tmpdir)["total_count"] == 15

    def test_reset_on_nonexistent_initializes(self):
        """Reset on non-existent directory initializes state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.reset(tmpdir)

            state = IterationState.get_state(tmpdir)
            assert state["index"] == 0
            assert state["status"] == "idle"


class TestIterationStateWrapIndex:
    """Test index wrapping for re-runs."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_wrap_index_resets_to_zero(self):
        """wrap_index sets index back to 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = IterationState.get_state(tmpdir)
            state["index"] = 10

            IterationState.wrap_index(tmpdir)

            assert IterationState.get_state(tmpdir)["index"] == 0

    def test_wrap_index_preserves_status(self):
        """wrap_index preserves the current status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state = IterationState.get_state(tmpdir)
            state["index"] = 5
            state["status"] = "completed"

            IterationState.wrap_index(tmpdir)

            # Status is preserved (unlike reset which sets to idle)
            assert IterationState.get_state(tmpdir)["status"] == "completed"


class TestIterationStateDirectoryChange:
    """Test directory change detection with path variations."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_same_directory_returns_false(self):
        """Same directory path returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = IterationState.check_directory_change(tmpdir, tmpdir)
            assert result is False

    def test_different_directory_returns_true(self):
        """Different directories return True."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                result = IterationState.check_directory_change(tmpdir1, tmpdir2)
                assert result is True

    def test_trailing_slash_normalized(self):
        """Trailing slashes are normalized before comparison."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Same dir with and without trailing slash
            dir_no_slash = tmpdir.rstrip(os.sep)
            dir_with_slash = tmpdir + os.sep

            result = IterationState.check_directory_change(dir_no_slash, dir_with_slash)
            assert result is False

    def test_relative_vs_absolute_normalized(self):
        """Relative and absolute paths to same dir compare equal."""
        # Get current directory
        original_cwd = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Resolve symlinks for macOS temp directories (/var -> /private/var)
                tmpdir_real = os.path.realpath(tmpdir)
                parent = os.path.dirname(tmpdir_real)
                os.chdir(parent)
                relative = os.path.basename(tmpdir_real)

                result = IterationState.check_directory_change(relative, tmpdir_real)
                assert result is False
        finally:
            os.chdir(original_cwd)

    def test_dot_dot_normalized(self):
        """Paths with .. are normalized before comparison."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a subdir
            subdir = os.path.join(tmpdir, "sub")
            os.makedirs(subdir)

            # Path using ..
            dotdot_path = os.path.join(subdir, "..")

            result = IterationState.check_directory_change(tmpdir, dotdot_path)
            assert result is False


class TestIterationStateStatus:
    """Test status management."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_set_status_processing(self):
        """Status can be set to processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_status(tmpdir, "processing")

            assert IterationState.get_state(tmpdir)["status"] == "processing"

    def test_set_status_completed(self):
        """Status can be set to completed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_status(tmpdir, "completed")

            assert IterationState.get_state(tmpdir)["status"] == "completed"

    def test_set_status_idle(self):
        """Status can be set to idle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            IterationState.set_status(tmpdir, "processing")
            IterationState.set_status(tmpdir, "idle")

            assert IterationState.get_state(tmpdir)["status"] == "idle"


class TestIterationStateIsolation:
    """Test that different directories have isolated state."""

    def setup_method(self):
        """Clear state before each test."""
        IterationState.clear_all()

    def test_different_directories_have_separate_state(self):
        """State for different directories is independent."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                IterationState.set_total_count(tmpdir1, 5)
                IterationState.set_total_count(tmpdir2, 10)

                state1 = IterationState.get_state(tmpdir1)
                state1["index"] = 3

                state2 = IterationState.get_state(tmpdir2)
                state2["index"] = 7

                assert IterationState.get_state(tmpdir1)["total_count"] == 5
                assert IterationState.get_state(tmpdir1)["index"] == 3
                assert IterationState.get_state(tmpdir2)["total_count"] == 10
                assert IterationState.get_state(tmpdir2)["index"] == 7
