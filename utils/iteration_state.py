"""Iteration state management for batch image processing.

Manages batch iteration state across workflow executions within the same
ComfyUI session. State is stored in class variables (not instance variables)
to persist across node executions.
"""

import os
from typing import Literal

# Status type for batch processing
StatusType = Literal["idle", "processing", "completed"]


class IterationState:
    """Manage batch iteration state across executions.

    Uses class-level storage to persist state across multiple node
    executions within the same ComfyUI session. State resets when
    ComfyUI restarts.

    State is keyed by normalized directory path to handle path variations
    (trailing slashes, relative vs absolute paths, etc.).
    """

    _instances: dict = {}  # Class-level state storage

    @classmethod
    def _normalize_path(cls, directory: str) -> str:
        """Normalize a directory path for consistent state lookup.

        Args:
            directory: Raw directory path

        Returns:
            Normalized absolute path
        """
        return os.path.normpath(os.path.abspath(directory))

    @classmethod
    def get_state(cls, directory: str) -> dict:
        """Get or initialize state for a directory.

        Args:
            directory: Directory path to get state for

        Returns:
            State dictionary with keys: index, total_count, directory, status
        """
        key = cls._normalize_path(directory)
        if key not in cls._instances:
            cls._instances[key] = {
                "index": 0,
                "total_count": 0,
                "directory": key,
                "status": "idle",
            }
        return cls._instances[key]

    @classmethod
    def reset(cls, directory: str) -> None:
        """Reset state for a directory.

        Resets index to 0 and status to 'idle'. Preserves total_count
        as it will be updated on next execution.

        Args:
            directory: Directory path to reset state for
        """
        key = cls._normalize_path(directory)
        if key in cls._instances:
            cls._instances[key]["index"] = 0
            cls._instances[key]["status"] = "idle"
        else:
            # Initialize if doesn't exist
            cls.get_state(directory)

    @classmethod
    def advance(cls, directory: str) -> int:
        """Advance index and return new value.

        Args:
            directory: Directory path to advance index for

        Returns:
            New index value after incrementing
        """
        state = cls.get_state(directory)
        state["index"] += 1
        return state["index"]

    @classmethod
    def is_complete(cls, directory: str) -> bool:
        """Check if batch processing is complete.

        Args:
            directory: Directory path to check

        Returns:
            True if index >= total_count (all images processed)
        """
        state = cls.get_state(directory)
        return state["index"] >= state["total_count"]

    @classmethod
    def set_total_count(cls, directory: str, count: int) -> None:
        """Set total image count for a directory.

        Args:
            directory: Directory path
            count: Total number of images in the batch
        """
        state = cls.get_state(directory)
        state["total_count"] = count

    @classmethod
    def check_directory_change(cls, directory: str, previous_directory: str) -> bool:
        """Check if directory has changed (after normalization).

        Used to detect when user switches to a different input folder,
        which should trigger a state reset.

        Args:
            directory: Current directory path
            previous_directory: Previously used directory path

        Returns:
            True if directories are different after normalization
        """
        current_normalized = cls._normalize_path(directory)
        previous_normalized = cls._normalize_path(previous_directory)
        return current_normalized != previous_normalized

    @classmethod
    def wrap_index(cls, directory: str) -> None:
        """Reset index to 0 when batch completes.

        Allows re-running the batch without manual reset.

        Args:
            directory: Directory path to wrap index for
        """
        state = cls.get_state(directory)
        state["index"] = 0

    @classmethod
    def set_status(cls, directory: str, status: StatusType) -> None:
        """Set the processing status for a directory.

        Args:
            directory: Directory path
            status: New status ('idle', 'processing', or 'completed')
        """
        state = cls.get_state(directory)
        state["status"] = status

    @classmethod
    def clear_all(cls) -> None:
        """Clear all state (useful for testing)."""
        cls._instances.clear()
